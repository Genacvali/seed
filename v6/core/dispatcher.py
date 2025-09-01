# -*- coding: utf-8 -*-
import importlib
from typing import Dict, Any
from core.log import get_logger

log = get_logger("dispatcher")

def handle_event(evt: Dict[str, Any]) -> str:
    """
    evt: {"type": <plugin>, "host": <host>, "payload": {...}}
    """
    plugin = (evt.get("type") or "echo").strip()
    host = evt.get("host") or "unknown"
    payload = evt.get("payload") or {}

    mod_name = f"plugins.{plugin}"
    fmt_name = f"formatters.{plugin}"

    try:
        mod = importlib.import_module(mod_name)
    except Exception as e:
        log.exception("Import plugin failed: %s", e)
        # echo fallback
        mod = importlib.import_module("plugins.echo")

    data = {}
    try:
        data = mod.run(host, payload)  # plugin returns a dict structure
    except Exception as e:
        log.exception("Plugin '%s' failed: %s", plugin, e)
        return f"SEED: ❌ Ошибка плагина {plugin}: {e}"

    # try dedicated formatter, else generic
    try:
        fmt = importlib.import_module(fmt_name)
        return fmt.render(data)
    except Exception:
        from formatters.common import render_generic
        return render_generic(data)