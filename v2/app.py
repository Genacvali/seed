# -*- coding: utf-8 -*-
import os, time, json, re
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager
from core import config, notify, plugins
from core.queue import queue_manager
from core.redis_throttle import RedisThrottler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await queue_manager.connect()
    yield
    # Shutdown
    await queue_manager.close()

app = FastAPI(title="SEED v2", lifespan=lifespan)

TH = RedisThrottler()   # Redis-based throttling с fallback на memory

def _host_from_labels(labels: Dict[str, str]) -> str:
    # host или instance (host:port) — вытащим host
    host = labels.get("host") or labels.get("nodename") or labels.get("instance")
    if host and ":" in host:
        host = host.split(":")[0]
    return host or "unknown"

def _fingerprint(alert: Dict[str, Any]) -> str:
    lab = alert.get("labels", {})
    ann = alert.get("annotations", {})
    key = f"{lab.get('alertname','?')}|{lab.get('host',lab.get('instance','?'))}|{ann.get('summary','')}"
    return key

@app.get("/health")
def health():
    return {"status": "ok", "time": int(time.time())}

@app.get("/stats")
async def stats():
    queue_stats = {}
    try:
        if queue_manager.channel:
            for name, queue in queue_manager.queues.items():
                queue_info = await queue_manager.channel.queue_declare(queue.name, passive=True)
                queue_stats[name] = {"message_count": queue_info.message_count}
    except Exception as e:
        queue_stats = {"error": str(e)}
    
    return {
        "throttle": TH.get_stats(),
        "queues": queue_stats,
        "time": int(time.time())
    }

@app.post("/alert")  # Alertmanager webhook
async def alert(req: Request):
    body = await req.json()
    alerts: List[Dict[str, Any]] = body.get("alerts") or []
    queued = 0
    for a in alerts:
        try:
            if TH.suppressed(_fingerprint(a), ttl_seconds=config.ALERT_TTL()):
                continue
            # Отправляем в очередь вместо синхронной обработки
            await queue_manager.publish_alert(a)
            TH.mark(_fingerprint(a), ttl_seconds=config.ALERT_TTL())
            queued += 1
        except Exception as e:
            notify.log(f"[ERR] queue alert: {e}")
    return {"ok": True, "queued": queued}

def process_one_alert(a: Dict[str, Any]) -> str:
    labels = a.get("labels", {})
    annotations = a.get("annotations", {})
    alertname = labels.get("alertname") or "unknown"

    host = _host_from_labels(labels)
    route = config.route_for(alertname, labels)
    if not route:
        return f"SEED: 🤷 не найден маршрут для alertname='{alertname}'"

    plugin_name = route["plugin"]
    payload = route.get("payload", {})
    # автоматом подставим telegraf_url из hosts.yaml если есть
    payload = config.enrich_with_host_overrides(host, payload)

    fn = plugins.get_plugin(plugin_name)
    if not fn:
        return f"SEED: 🤷 не найден плагин '{plugin_name}'"

    # плагин сам форматирует «красоту» под MM
    return fn(host=host, labels=labels, annotations=annotations, payload=payload)
