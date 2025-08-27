#!/usr/bin/env python3
"""
Zabbix Webhook для SEED Agent
Отправляет уведомления из Zabbix в SEED Agent для дальнейшей обработки через LLM и уведомления
"""

import json
import sys
import requests
from datetime import datetime

def send_to_seed_agent(zabbix_data):
    """Конвертирует данные Zabbix в формат SEED Agent и отправляет"""
    
    # Извлекаем данные из Zabbix
    subject = zabbix_data.get('subject', '')
    message = zabbix_data.get('message', '')
    
    # Определяем severity на основе триггера Zabbix
    severity_map = {
        'disaster': 'critical',
        'high': 'high', 
        'average': 'warning',
        'warning': 'warning',
        'information': 'info',
        'not classified': 'info'
    }
    
    # Парсим severity из subject или message
    severity = 'warning'  # default
    for zab_sev, seed_sev in severity_map.items():
        if zab_sev.lower() in subject.lower() or zab_sev.lower() in message.lower():
            severity = seed_sev
            break
    
    # Создаем alert в формате SEED Agent (совместимый с Alertmanager)
    alert = {
        "alerts": [{
            "labels": {
                "alertname": f"Zabbix_{subject.split(':')[0].strip() if ':' in subject else 'ZabbixAlert'}",
                "instance": "zabbix-server",
                "severity": severity,
                "source": "zabbix"
            },
            "annotations": {
                "summary": subject,
                "description": message,
                "timestamp": datetime.now().isoformat()
            },
            "status": "firing",
            "startsAt": datetime.now().isoformat(),
            "generatorURL": "http://zabbix-server/alerts"
        }]
    }
    
    # Отправляем в SEED Agent
    try:
        response = requests.post(
            'http://localhost:8080/alert',
            json=alert,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Alert sent to SEED Agent successfully")
            return 0
        else:
            print(f"❌ Failed to send alert: {response.status_code} - {response.text}")
            return 1
            
    except Exception as e:
        print(f"❌ Error sending to SEED Agent: {str(e)}")
        return 1

def main():
    """Main webhook handler"""
    try:
        # Zabbix передает данные через аргументы командной строки
        if len(sys.argv) < 4:
            print("Usage: zabbix-webhook.py <to> <subject> <message>")
            return 1
        
        to = sys.argv[1]       # получатель (не используется)
        subject = sys.argv[2]  # тема сообщения
        message = sys.argv[3]  # текст сообщения
        
        # Формируем данные для обработки
        zabbix_data = {
            'to': to,
            'subject': subject,
            'message': message
        }
        
        print(f"📨 Received Zabbix webhook: {subject}")
        
        # Отправляем в SEED Agent
        return send_to_seed_agent(zabbix_data)
        
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())