# -*- coding: utf-8 -*-
import json, requests
from core.config import CFG
from core.log import get_logger

log = get_logger("mm")

def post_to_mm(text: str) -> None:
    if not CFG.mm_webhook:
        log.warning("[MM] no webhook set")
        return
    try:
        r = requests.post(
            CFG.mm_webhook,
            json={"text": text},
            timeout=10,
            verify=CFG.mm_verify_ssl
        )
        r.raise_for_status()
        log.info("[MM] OK")
    except Exception as e:
        log.exception("[MM ERROR] %s", e)