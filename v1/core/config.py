# -*- coding: utf-8 -*-
import os, yaml
from pathlib import Path

_CFG = {}
_BASE = Path(__file__).resolve().parents[1]
_CFG_FILE = os.getenv("SEED_CONFIG", str(_BASE / "configs" / "seed.yaml"))

def load_settings():
    global _CFG
    p = Path(_CFG_FILE)
    if not p.exists():
        raise RuntimeError(f"Нет конфига: {p}")
    _CFG = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def _match_host_group(host: str) -> list:
    """вернём список групп, в которые входит host"""
    res = []
    for gname, g in (_CFG.get("groups") or {}).items():
        include = g.get("include") or []
        if host in include:
            res.append(gname)
    return res

def resolve_handler(alert: dict):
    """
    Находим для type + host подходящий плагин и payload.
    Возвращает (plugin_name, payload_dict) или (None, {}).
    """
    atype = alert.get("type")
    host  = alert.get("host")
    if not atype or not host:
        return None, {}

    rules = _CFG.get("alerts") or {}
    rule = rules.get(atype)
    if not rule:
        return None, {}

    # Базовый payload из правила
    payload = dict(rule.get("payload_default") or {})
    # Перекрытие параметров по группам (если заданы)
    host_groups = set(_match_host_group(host))
    for override in (rule.get("overrides") or []):
        groups = set(override.get("groups") or [])
        if groups & host_groups:
            payload.update(override.get("payload") or {})

    # Перекрытие из самого события
    payload.update(alert.get("payload") or {})

    plugin = rule.get("plugin")
    return plugin, payload