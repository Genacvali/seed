# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Response
from core.config import CFG
from core.log import get_logger
from core.dispatcher import handle_event
from core.mm import post_to_mm

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

log = get_logger("http")

app = FastAPI(title="SEED v6")

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "version": "v6"}

@app.post("/test")
async def test() -> Dict[str, Any]:
    evt = {
        "type": "host_inventory",
        "host": "demo-host",
        "payload": {"paths": ["/", "/data"]},
    }
    text = handle_event(evt)
    post_to_mm(text)
    return {"sent": True}

@app.post("/alertmanager")
async def from_alertmanager(req: Request) -> Response:
    """
    Примет JSON Alertmanager:
      { "alerts":[ { "labels":{...}, "annotations":{...}, "status":"firing", ... }, ... ] }
    Маппинг:
      plugin = labels.alertname (или annotations.seed_plugin)
      host   = labels.instance | labels.hostname | "unknown"
      payload = annotations.seed_payload (JSON) + labels/annotations raw
    """
    body = await req.json()
    alerts: List[Dict[str, Any]] = body.get("alerts", [])
    count = 0

    for a in alerts:
        labels = a.get("labels", {}) or {}
        ann    = a.get("annotations", {}) or {}

        plugin = ann.get("seed_plugin") or labels.get("alertname") or "echo"
        host   = labels.get("instance") or labels.get("hostname") or "unknown"

        # seed_payload может быть JSON-строкой
        payload: Dict[str, Any] = {}
        seed_payload = ann.get("seed_payload")
        if seed_payload:
            try:
                payload.update(json.loads(seed_payload))
            except Exception:
                payload["seed_payload_raw"] = seed_payload

        # полезно также отдать labels/annotations плагину
        payload["labels"] = labels
        payload["annotations"] = ann
        payload["status"] = a.get("status")
        payload["startsAt"] = a.get("startsAt")
        payload["endsAt"] = a.get("endsAt")

        evt = {"type": plugin, "host": host, "payload": payload}
        text = handle_event(evt)
        post_to_mm(text)
        count += 1

    return Response(content=json.dumps({"handled": count}), media_type="application/json")