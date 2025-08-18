# -*- coding: utf-8 -*-
import os, requests, time

WEBHOOK = os.getenv("MM_WEBHOOK")
VERIFY  = os.getenv("MM_VERIFY_SSL", "1") == "1"

def log(msg: str):
    print(msg, flush=True)

def send_mm(text: str):
    if not WEBHOOK:
        log("[MM] no webhook set")
        return
    try:
        r = requests.post(WEBHOOK, json={"text": text}, timeout=10, verify=VERIFY)
        if r.status_code != 200:
            log(f"[MM ERROR] {r.status_code}: {r.text[:200]}")
        else:
            log("[MM] OK")
    except Exception as e:
        log(f"[MM ERROR] {e}")
