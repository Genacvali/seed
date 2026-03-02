# -*- coding: utf-8 -*-
import json, requests
from typing import Optional
from core.config import CFG
from core.log import get_logger

log = get_logger("mm")

def post_to_mm(text: str, color: Optional[str] = None) -> bool:
    """
    Отправляет сообщение в Mattermost.
    Если указан color, используется attachment с цветом (как в seed-agent.py).
    Возвращает True при успешной отправке, иначе False.
    """
    if not CFG.mm_webhook:
        log.warning("[MM] no webhook set")
        return False

    try:
        if color:
            payload = {
                "attachments": [{
                    "color": color,
                    "text": text,
                    "mrkdwn_in": ["text"],
                }]
            }
        else:
            payload = {"text": text}

        r = requests.post(
            CFG.mm_webhook,
            json=payload,
            timeout=10,
            verify=CFG.mm_verify_ssl,
        )
        if r.status_code // 100 == 2:
            log.info("[MM] OK")
            return True

        log.warning("[MM] ERR %s: %s", r.status_code, r.text[:200])
        return False
    except Exception as e:
        log.exception("[MM ERROR] %s", e)
        return False