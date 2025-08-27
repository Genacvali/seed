#!/usr/bin/env python3
"""
Zabbix 5.4.9 Webhook для SEED Agent
Получает JSON данные из Zabbix и отправляет в SEED Agent
"""

import json
import sys
import requests
import os
from datetime import datetime

def parse_zabbix_data(data):
    """Парсит данные от Zabbix 5.4"""
    try:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except:
                data = {
                    'subject': data.split('\n')[0] if '\n' in data else data,
                    'message': data
                }
        return data
    except:
        return {'subject': 'Zabbix Alert', 'message': str(data)}

def extract_severity(subject, message):
    """Определяет severity из данных Zabbix"""
    text = f"{subject} {message}".lower()
    
    if any(word in text for word in ['disaster', 'критический', 'critical']):
        return 'critical'
    elif any(word in text for word in ['high', 'высокий']):
        return 'high'
    elif any(word in text for word in ['average', 'средний', 'warning', 'предупреждение']):
        return 'warning'
    elif any(word in text for word in ['information', 'информация', 'info']):
        return 'info'
    else:
        return 'warning'  # default

def send_to_seed_agent(zabbix_data):
    """Отправляет alert в SEED Agent"""
    try:
        subject = zabbix_data.get('subject', 'Zabbix Alert')
        message = zabbix_data.get('message', '')
        
        # Извлекаем название хоста и триггера
        host = zabbix_data.get('host', 'unknown')
        trigger = zabbix_data.get('trigger', subject)
        
        severity = extract_severity(subject, message)
        
        # Создаем alert в формате SEED Agent
        alert_payload = {
            "alerts": [{
                "labels": {
                    "alertname": f"Zabbix_{trigger.replace(' ', '_')}",
                    "instance": host,
                    "severity": severity,
                    "source": "zabbix",
                    "trigger": trigger
                },
                "annotations": {
                    "summary": subject,
                    "description": message,
                    "timestamp": datetime.now().isoformat(),
                    "host": host
                },
                "status": "firing",
                "startsAt": datetime.now().isoformat(),
                "generatorURL": f"http://zabbix-server/zabbix"
            }]
        }
        
        response = requests.post(
            'http://localhost:8080/alert',
            json=alert_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return 0
        else:
            return 1
            
    except:
        return 1

def main():
    """Main webhook handler для Zabbix 5.4"""
    try:
        if len(sys.argv) >= 2:
            raw_data = sys.argv[1]
        else:
            raw_data = sys.stdin.read().strip()
        
        if not raw_data:
            return 1
        
        zabbix_data = parse_zabbix_data(raw_data)
        return send_to_seed_agent(zabbix_data)
        
    except:
        return 1

if __name__ == '__main__':
    sys.exit(main())