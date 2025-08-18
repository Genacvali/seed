# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import time, json, re
from typing import Dict, Any, List
from fastapi import FastAPI, Request, Response
from contextlib import asynccontextmanager

import core.config as config
import core.notify as notify
from core.queue import queue_manager
from core.redis_throttle import RedisThrottler
from core.alert_processor import fingerprint, process_one_alert

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await queue_manager.connect()
    yield
    # Shutdown
    await queue_manager.close()

app = FastAPI(title="SEED v2", lifespan=lifespan)

TH = RedisThrottler()   # Redis-based throttling с fallback на memory


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
            if TH.suppressed(fingerprint(a), ttl_seconds=config.ALERT_TTL()):
                continue
            # Отправляем в очередь вместо синхронной обработки
            await queue_manager.publish_alert(a)
            TH.mark(fingerprint(a), ttl_seconds=config.ALERT_TTL())
            queued += 1
        except Exception as e:
            notify.log(f"[ERR] queue alert: {e}")
    return {"ok": True, "queued": queued}
