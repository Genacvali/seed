#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой реплей сохранённых Alertmanager-пакетов в локальный SEED v6 агент.

Использование:

  python3 replay_alert.py path/to/alert.json
  python3 replay_alert.py alerts_dir/

Ожидается формат как у Alertmanager webhook:
{
  "alerts": [ ... ]
}

Если в файле лежит один alert (dict без поля alerts),
он будет обёрнут в {"alerts": [ ... ]}.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests


AGENT_URL = os.getenv("SEED_AGENT_URL", "http://localhost:8080/alertmanager")


def _load_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "alerts" in data and isinstance(data["alerts"], list):
        return data
    # одиночный alert -> пакет
    if isinstance(data, dict):
        return {"alerts": [data]}
    if isinstance(data, list):
        return {"alerts": data}
    raise ValueError(f"Unsupported JSON structure in {path}")


def iter_payloads(target: Path) -> List[Dict[str, Any]]:
    if target.is_file():
        return [_load_json_file(target)]

    if target.is_dir():
        result: List[Dict[str, Any]] = []
        for p in sorted(target.glob("*.json")):
            try:
                result.append(_load_json_file(p))
            except Exception as e:
                print(f"[REPLAY] skip {p}: {e}")
        return result

    raise FileNotFoundError(target)


def send_payload(payload: Dict[str, Any]) -> None:
    try:
        r = requests.post(AGENT_URL, json=payload, timeout=10)
        print(f"[REPLAY] {AGENT_URL} -> {r.status_code}")
        if r.status_code // 100 != 2:
            print(r.text[:500])
    except Exception as e:
        print(f"[REPLAY] request error: {e}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: replay_alert.py <file.json|dir>")
        sys.exit(1)

    target = Path(sys.argv[1])
    payloads = iter_payloads(target)
    print(f"[REPLAY] sending {len(payloads)} payload(s) to {AGENT_URL}")
    for i, p in enumerate(payloads, 1):
        print(f"[REPLAY] #{i}")
        send_payload(p)


if __name__ == "__main__":
    main()

