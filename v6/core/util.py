# -*- coding: utf-8 -*-
import json
from typing import Any, Dict

def try_json(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        return {}