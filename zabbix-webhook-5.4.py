#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

def send_to_seed_agent(seed_url, zabbix_data):
    """Отправляет alert в SEED Agent"""
    try:
        subject = zabbix_data.get('subject', 'Zabbix Alert')
        message = zabbix_data.get('message', '')
        
        # Извлекаем название хоста и триггера
        host = zabbix_data.get('host', 'unknown')
        trigger = zabbix_data.get('trigger', subject)
        
        severity = extract_severity(subject, message)
        
        # Создаем прямой JSON для нового универсального парсера
        alert_payload = {
            "subject": subject,
            "message": message,
            "host": host,
            "trigger": trigger,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        response = requests.post(
            seed_url,
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
        # 1) URL из argv[1] или из переменной окружения
        seed_url = None
        raw_data = None
        
        if len(sys.argv) > 1 and sys.argv[1].startswith("http"):
            # Первый аргумент - URL
            seed_url = sys.argv[1]
            if len(sys.argv) > 2:
                raw_data = sys.argv[2]
        elif len(sys.argv) > 1:
            # Первый аргумент - данные
            raw_data = sys.argv[1]
        
        # Если URL не найден в аргументах, берем из ENV
        if not seed_url:
            seed_url = os.getenv("SEED_URL")
        
        if not seed_url:
            return 1
        
        # Если данных нет, читаем из stdin
        if not raw_data:
            if not sys.stdin.isatty():
                raw_data = sys.stdin.read().strip()
        
        if not raw_data:
            # Минимальный дефолт для теста
            raw_data = json.dumps({
                "event": {"value": "1"},
                "trigger": {"name": "Zabbix CLI Test", "severity_text": "Information"},
                "host": {"name": "test"},
                "item": {"name": "test", "lastvalue": "42", "port": "0"}
            })
        
        zabbix_data = parse_zabbix_data(raw_data)
        return send_to_seed_agent(seed_url, zabbix_data)
        
    except:
        return 1

if __name__ == '__main__':
    sys.exit(main())