# -*- coding: utf-8 -*-
import os, requests, urllib3, pathlib
from dotenv import load_dotenv

# Load .env from parent directory (v1/)
env_path = pathlib.Path(__file__).resolve().parents[1] / ".env"
load_dotenv(env_path)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

MM_WEBHOOK = os.getenv("MM_WEBHOOK")
MM_VERIFY  = os.getenv("MM_VERIFY_SSL","1") != "0"

def send_mm(text: str):
    if not MM_WEBHOOK:
        print("[MM] no webhook set"); return
    try:
        r = requests.post(MM_WEBHOOK, json={"text": text}, timeout=15, verify=MM_VERIFY)
        print("[MM]", r.status_code, r.text[:160])
    except Exception as e:
        print("[MM][ERR]", e)