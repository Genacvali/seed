# -*- coding: utf-8 -*-
from typing import Dict, Any

def run(host: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "plugin": "echo",
        "title": f"SEED · Echo @ {host}",
        "lines": [
            "Получено событие без явного обработчика.",
            f"host: {host}",
            f"payload keys: {list((payload or {}).keys())}"
        ],
        "raw": payload,
    }