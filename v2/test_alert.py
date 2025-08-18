#!/usr/bin/env python3
import requests
import json
from datetime import datetime, timezone

# Формат алерта Alertmanager (обернутый в объект)
test_alert = {
    "alerts": [
        {
        "status": "firing",
        "labels": {
            "alertname": "DiskSpaceHigh",
            "instance": "d-dba-mng-adv-msk02",
            "job": "telegraf",
            "path": "/data",
            "severity": "warning",
            "service_type": "mng",
            "env": "DEV",
            "project": "dba"
        },
        "annotations": {
            "summary": "Disk space 87% full on d-dba-mng-adv-msk02",
            "description": "Mountpoint /data is 87% full",
            "runbook_url": "https://wiki.company.com/disk-space-runbook"
        },
        "startsAt": datetime.now(timezone.utc).isoformat(),
        "endsAt": "",
        "generatorURL": "http://prometheus:9090/graph?g0.expr=disk_used+%2F+disk_total+%2A+100+%3E+85",
        "fingerprint": "7c677265703432ca"
        }
    ]
}

# URL вашего SEED агента
url = "http://d-dba-mng-adv-msk01:8000/alert"

try:
    response = requests.post(
        url, 
        json=test_alert,
        headers={'Content-Type': 'application/json'},
        timeout=10
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        print("✅ Алерт успешно отправлен!")
    else:
        print("❌ Ошибка при отправке алерта")
        
except requests.exceptions.ConnectionError:
    print("❌ Не удалось подключиться к агенту")
except requests.exceptions.Timeout:
    print("❌ Таймаут при подключении")
except Exception as e:
    print(f"❌ Ошибка: {e}")