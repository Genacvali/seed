#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование нового компактного формата сообщений
"""

import sys
import os

# Добавляем путь к core модулям
sys.path.insert(0, os.path.dirname(__file__))

from core.formatter import AlertMessageFormatter

def test_new_format():
    """Тестирование нового компактного формата"""
    
    # Тестовые данные в стиле вашего примера
    test_alert = {
        "alertname": "MongoDB Процессов нет",
        "instance": "p-homesecurity-mng-adv-msk01:27017",
        "severity": "high", 
        "priority": 2,
        "labels": {
            "alertname": "MongoDB Процессов нет",
            "instance": "p-homesecurity-mng-adv-msk01:27017",
            "job": "mongodb-exporter",
            "service": "homesecurity",
            "env": "production",
            "os": "RedHat"
        },
        "annotations": {
            "summary": "Процессы MongoDB не найдены на сервере",
            "description": "ЭТО ТЕСТ - мониторинг не обнаружил активные процессы MongoDB"
        },
        "llm_response": """
Возможные причины проблемы:
• Служба MongoDB была остановлена или упала
• Процесс mongod завершился с ошибкой
• Недостаточно места на диске для работы MongoDB
• Проблемы с файлами конфигурации или правами доступа

Рекомендуемые действия:
systemctl status mongod
systemctl start mongod
journalctl -u mongod --since "10 minutes ago"
df -h /var/lib/mongo
mongosh --eval "db.adminCommand('ping')"
        """,
        "time_context": " // ⏱️ 4m 33s"
    }
    
    print("=== ТЕСТ НОВОГО КОМПАКТНОГО ФОРМАТА ===\n")
    
    # Тест обычного алерта
    message = AlertMessageFormatter.format_alert_message(
        alertname=test_alert["alertname"],
        instance=test_alert["instance"], 
        severity=test_alert["severity"],
        priority=test_alert["priority"],
        labels=test_alert["labels"],
        annotations=test_alert["annotations"],
        llm_response=test_alert["llm_response"],
        time_context=test_alert["time_context"],
        status="firing"
    )
    
    print("НОВЫЙ ФОРМАТ (firing):")
    print(message)
    print("\n" + "="*60 + "\n")
    
    # Тест resolved алерта
    resolved_message = AlertMessageFormatter.format_alert_message(
        alertname="MongoDB Процессов нет",
        instance="p-homesecurity-mng-adv-msk01:27017",
        severity="high",
        priority=2,
        labels=test_alert["labels"],
        annotations=test_alert["annotations"],
        llm_response="",
        status="resolved"
    )
    
    print("НОВЫЙ ФОРМАТ (resolved):")
    print(resolved_message)
    print("\n" + "="*60 + "\n")
    
    # Тест цветовых кодов
    print("ЦВЕТОВЫЕ КОДЫ:")
    for severity in ['critical', 'high', 'warning', 'info', 'unknown']:
        color = AlertMessageFormatter.get_severity_color(severity)
        print(f"{severity.upper()}: {color}")

if __name__ == "__main__":
    test_new_format()