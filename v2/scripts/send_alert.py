# -*- coding: utf-8 -*-
import json, requests, sys

URL = "http://127.0.0.1:8000/alert"

def send_host_inventory(host):
    data = {
      "receiver": "seed",
      "status": "firing",
      "alerts":[
        {
          "status":"firing",
          "labels":{
            "alertname":"host_inventory",
            "host":host,
            "instance":f"{host}:9100",
            "job":"node_exporter",
            "severity":"info"
          },
          "annotations":{
            "summary":"Host inventory check requested",
            "description":f"Manual inventory check for host {host}"
          },
          "startsAt":"2025-08-18T12:00:00Z",
          "endsAt":"0001-01-01T00:00:00Z",
          "generatorURL":"http://prometheus:9090/graph",
          "fingerprint":"xyz789abc123"
        }
      ],
      "groupLabels":{
        "alertname":"host_inventory"
      },
      "commonLabels":{
        "alertname":"host_inventory",
        "host":host
      },
      "commonAnnotations":{},
      "externalURL":"http://alertmanager:9093",
      "version":"4",
      "groupKey":"{}/{host=\"" + host + "\"}:{alertname=\"host_inventory\"}"
    }
    r = requests.post(URL, json=data, timeout=10)
    print(r.status_code, r.text)

def send_mongo_collscan(host):
    hotspots = """namespace                     op       time      details
------------------------------------------------------------
seed_demo.users               find      1221ms  plan:COLLSCAN docs:50000 keys:0
seed_demo.users               aggregate  815ms  plan:COLLSCAN docs:50000 keys:0
seed_demo.events              find      521ms  plan:COLLSCAN docs:25000 keys:0
"""
    data = {
      "receiver": "seed",
      "status": "firing",
      "alerts":[
        {
          "status":"firing",
          "labels":{
            "alertname":"mongo_collscan",
            "host":host,
            "env":"prod",
            "instance":f"{host}:27017",
            "job":"mongodb",
            "severity":"warning"
          },
          "annotations":{
            "summary":"MongoDB COLLSCAN detected - slow queries without indexes",
            "description":f"COLLSCAN operations detected on {host} with execution time > 500ms",
            "hotspots":hotspots,
            "last_ts":"2025-08-18T12:34:56Z",
            "runbook_url":"https://docs.mongodb.com/manual/tutorial/create-indexes-to-support-queries/"
          },
          "startsAt":"2025-08-18T12:30:00Z",
          "endsAt":"0001-01-01T00:00:00Z",
          "generatorURL":"http://prometheus:9090/graph?g0.expr=mongodb_collscan_total",
          "fingerprint":"abc123def456"
        }
      ],
      "groupLabels":{
        "alertname":"mongo_collscan"
      },
      "commonLabels":{
        "alertname":"mongo_collscan",
        "host":host,
        "env":"prod"
      },
      "commonAnnotations":{},
      "externalURL":"http://alertmanager:9093",
      "version":"4",
      "groupKey":"{}/{host=\"" + host + "\"}:{alertname=\"mongo_collscan\"}"
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
