# /opt/seed/pollers/mongo_hotspots_poller.py
import os, time, requests
from datetime import datetime, timedelta
from urllib.parse import urljoin
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
DB        = os.getenv("MONGO_DB", "seed_demo")
MIN_MS    = int(os.getenv("MIN_MS", "50"))
LIMIT     = int(os.getenv("LIMIT", "10"))
LISTENER  = os.getenv("SEED_LISTENER", "http://127.0.0.1:8080/webhook/custom")
HOST      = os.getenv("SEED_HOSTNAME") or os.uname().nodename

def has_hot_ops():
    cli = MongoClient(MONGO_URI, connectTimeoutMS=3000, serverSelectionTimeoutMS=3000)
    prof = cli[DB]["system.profile"]
    since = datetime.utcnow() - timedelta(minutes=1)
    q = {"millis": {"$gte": MIN_MS}, "ts": {"$gte": since}}
    return prof.count_documents(q) > 0

def send_alert():
    payload = {
      "type": "mongo_hotspots",
      "host": HOST,
      "payload": {
        "mongo_uri": MONGO_URI, "db": DB, "min_ms": MIN_MS, "limit": LIMIT
      }
    }
    r = requests.post(LISTENER, json=payload, timeout=5)
    print("POST", r.status_code, r.text[:200])

if __name__ == "__main__":
    while True:
        try:
            if has_hot_ops():
                send_alert()
        except Exception as e:
            print("ERR:", e)
        time.sleep(15)