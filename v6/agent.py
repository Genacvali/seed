# -*- coding: utf-8 -*-
import sys, json, time
from pathlib import Path
from typing import Any, Dict

from core.config import CFG
from core.log import get_logger
from core.dispatcher import handle_event
from core.mm import post_to_mm
from core.amqp import consume_json

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
log = get_logger("agent")

def main() -> None:
    if not CFG.rabbit_enabled:
        log.info("RabbitMQ disabled (RABBIT_ENABLE=0); exiting")
        return

    log.info(f"[*] SEED listening on queue '{CFG.rabbit_queue}' @ {CFG.rabbit_host}")
    for msg in consume_json():
        try:
            # ожидаем {"type": "...", "host": "...", "payload": {...}}
            text = handle_event(msg)
            post_to_mm(text)
        except Exception as e:
            log.exception("Failed to handle message: %s", e)

if __name__ == "__main__":
    main()