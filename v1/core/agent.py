# -*- coding: utf-8 -*-
"""Main SEED agent orchestrator."""
import sys
import pathlib
import json
import logging
from typing import Any, Dict

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

from core.bus import consume
from core.config import load_settings, resolve_handler
from core.notifier import send_mm

logging.basicConfig(level=logging.INFO)

def _on_alert(msg: bytes) -> None:
    """Process incoming alert message."""
    try:
        alert: Dict[str, Any] = json.loads(msg.decode("utf-8"))
    except Exception as e:
        logging.error(f"Failed to parse JSON message: {e}")
        send_mm("SEED: ⚠️ Invalid JSON message received, skipping")
        return
    
    plugin_name, payload = resolve_handler(alert)
    if not plugin_name:
        send_mm(f"SEED: 🤷 No handler found for type='{alert.get('type')}'")
        return
    
    try:
        mod = __import__(f"plugins.{plugin_name}", fromlist=["run"])
        if not hasattr(mod, "run"):
            send_mm(f"SEED: ❌ Plugin `{plugin_name}` missing run() function")
            return
        
        text = mod.run(alert["host"], payload)
        if text:
            send_mm(text)
            
    except ImportError as e:
        logging.error(f"Plugin import error: {e}")
        send_mm(f"SEED: ❌ Plugin import error `{plugin_name}`: {e}")
    except Exception as e:
        logging.error(f"Plugin execution error: {e}")
        send_mm(f"SEED: ❌ Plugin execution error `{plugin_name}`: {e}")

def main():
    load_settings()      # загрузим конфиг и плагины в память
    consume(_on_alert)   # слушаем RabbitMQ и передаём сообщения коллбэку

if __name__ == "__main__":
    main()