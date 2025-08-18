# -*- coding: utf-8 -*-
import json, requests, sys

URL = "http://127.0.0.1:8080/alert"

def send_host_inventory(host):
    data = {
      "alerts":[
        {
          "status":"firing",
          "labels":{"alertname":"host_inventory","host":host},
          "annotations":{"summary":"manual test"},
          "startsAt":"2025-08-16T12:00:00Z"
        }
      ]
    }
    r = requests.post(URL, json=data, timeout=10)
    print(r.status_code, r.text)

def send_mongo_collscan(host):
    hotspots = """namespace                     op       time      details
------------------------------------------------------------
seed_demo.events              query      221ms  plan:COLLSCAN docs:200000 keys:0
seed_demo.events              command    415ms  plan:COLLSCAN docs:200000 keys:0
"""
    data = {
      "alerts":[
        {
          "status":"firing",
          "labels":{"alertname":"mongo_collscan","host":host,"env":"prod"},
          "annotations":{"summary":"COLLSCAN > 200ms","hotspots":hotspots,"last_ts":"2025-08-16T12:34:56Z"},
          "startsAt":"2025-08-16T12:30:00Z"
        }
      ]
    }
    r = requests.post(URL, json=data, timeout=10)
    print(r.status_code, r.text)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/send_alert.py <type> <host>")
        print(" types: host|mongo")
        sys.exit(1)
    t, host = sys.argv[1], sys.argv[2]
    if t=="host":
        send_host_inventory(host)
    else:
        send_mongo_collscan(host)
