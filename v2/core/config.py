# -*- coding: utf-8 -*-
import os, yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parents[1]
CFG  = BASE / "configs"

# .env
env_path = BASE / "seed.env"
if env_path.exists():
    load_dotenv(env_path.as_posix())

def _yaml(p: Path) -> Dict[str, Any]:
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}

ROUTING = _yaml(CFG / "routing.yaml")
HOSTS   = _yaml(CFG / "hosts.yaml")

def ALERT_TTL() -> int:
    try:
        return int(os.getenv("ALERT_SUPPRESS_SECONDS", "30"))
    except:
        return 30

def route_for(alertname: str, labels: Dict[str, str]) -> Dict[str, Any]:
    rules = ROUTING.get("alerts") or {}
    r = rules.get(alertname)
    if not r:
        return {}
    # простая подстановка {label} в payload при необходимости
    import copy
    payload = copy.deepcopy(r.get("payload", {}))
    for k, v in list(payload.items()):
        if isinstance(v, str):
            payload[k] = v.format(**labels)
    return {"plugin": r["plugin"], "payload": payload}

def enrich_with_host_overrides(host: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    h = (HOSTS.get("hosts") or {}).get(host) or {}
    if "telegraf_url" in h:
        payload = dict(payload)
        payload["telegraf_url"] = h["telegraf_url"]
    return payload

# defaults for Telegraf if URL не задан в hosts.yaml
def default_telegraf_url(host: str) -> str:
    scheme = os.getenv("TELEGRAF_SCHEME", "http")
    port   = os.getenv("TELEGRAF_PORT", "9216")
    return f"{scheme}://{host}:{port}/metrics"
