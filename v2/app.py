# -*- coding: utf-8 -*-
import os, time, json, re
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Response
from core import config, notify, throttle, plugins

app = FastAPI(title="SEED v2")

TH = throttle.Throttler()   # простая дедуп/троттлинг в памяти

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

@app.post("/alert")  # Alertmanager webhook
async def alert(req: Request):
    body = await req.json()
    alerts: List[Dict[str, Any]] = body.get("alerts") or []
    sent = 0
    for a in alerts:
        try:
            if TH.suppressed(_fingerprint(a), ttl_seconds= config.ALERT_TTL()):
                continue
            msg = process_one_alert(a)
            if msg:
                notify.send_mm(msg)
                TH.mark(_fingerprint(a))
                sent += 1
        except Exception as e:
            notify.log(f"[ERR] process alert: {e}")
    return {"ok": True, "sent": sent}

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
