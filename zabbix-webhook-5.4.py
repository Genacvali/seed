#!/usr/bin/env python3
"""
Zabbix 5.4.9 Webhook для SEED Agent
Получает JSON данные из Zabbix и отправляет в SEED Agent
"""

import json
import sys
import requests
import os
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/zabbix-webhook.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def parse_zabbix_data(data):
    """Парсит данные от Zabbix 5.4"""
    try:
        # Zabbix 5.4 может отправлять разные форматы
        if isinstance(data, str):
            # Пытаемся распарсить JSON
            try:
                data = json.loads(data)
            except:
                # Если не JSON, создаем структуру из строки
                data = {
                    'subject': data.split('\n')[0] if '\n' in data else data,
                    'message': data
                }
        
        logger.info(f"Parsed Zabbix data: {json.dumps(data, indent=2)}")
        return data
        
    except Exception as e:
        logger.error(f"Error parsing Zabbix data: {e}")
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
        
        logger.info(f"Sending to SEED Agent: {json.dumps(alert_payload, indent=2)}")
        
        # Отправляем в SEED Agent
        response = requests.post(
            'http://localhost:8080/alert',
            json=alert_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info("✅ Alert sent to SEED Agent successfully")
            print("SUCCESS: Alert sent to SEED Agent")
            return 0
        else:
            logger.error(f"❌ SEED Agent returned {response.status_code}: {response.text}")
            print(f"ERROR: SEED Agent returned {response.status_code}")
            return 1
            
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to SEED Agent at localhost:8080")
        print("ERROR: Cannot connect to SEED Agent")
        return 1
    except Exception as e:
        logger.error(f"❌ Error sending to SEED Agent: {str(e)}")
        print(f"ERROR: {str(e)}")
        return 1

def main():
    """Main webhook handler для Zabbix 5.4"""
    try:
        logger.info(f"Webhook started with {len(sys.argv)} arguments")
        logger.info(f"Arguments: {sys.argv}")
        
        # Логируем переменные окружения для отладки
        for key in ['ZABBIX_ALERT_SENDTO', 'ZABBIX_ALERT_SUBJECT', 'ZABBIX_ALERT_MESSAGE']:
            value = os.environ.get(key, 'NOT_SET')
            logger.info(f"ENV {key}: {value}")
        
        # Zabbix 5.4 может передавать данные разными способами
        if len(sys.argv) >= 2:
            # Через аргументы командной строки
            raw_data = sys.argv[1]
            logger.info(f"Received data via args: {raw_data}")
        else:
            # Читаем из stdin
            raw_data = sys.stdin.read().strip()
            logger.info(f"Received data via stdin: {raw_data}")
        
        if not raw_data:
            logger.error("No data received")
            print("ERROR: No data received")
            return 1
        
        # Парсим данные
        zabbix_data = parse_zabbix_data(raw_data)
        
        # Отправляем в SEED Agent
        return send_to_seed_agent(zabbix_data)
        
    except Exception as e:
        logger.error(f"❌ Webhook fatal error: {str(e)}")
        print(f"FATAL ERROR: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())