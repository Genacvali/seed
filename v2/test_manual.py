#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый ручной тест для проверки работы системы
"""
import requests
import json
from datetime import datetime

def quick_test():
    """Быстрая проверка базового флоу"""
    
    # 1. Health check
    print("🔍 Проверка health...")
    try:
        r = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Health: {r.json()}")
    except Exception as e:
        print(f"❌ Health failed: {e}")
        return False
    
    # 2. Статистика до отправки
    print("\n📊 Статистика до отправки алерта:")
    try:
        r = requests.get("http://localhost:8000/stats", timeout=5)
        stats_before = r.json()
        print(f"   Очереди: {stats_before.get('queues', {})}")
        print(f"   Throttling: {stats_before.get('throttle', {})}")
    except Exception as e:
        print(f"❌ Stats failed: {e}")
        return False
    
    # 3. Отправка тестового алерта
    print("\n📤 Отправка тестового алерта host_inventory...")
    
    alert_payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "host_inventory",
                "host": "quick-test-host",
                "instance": "quick-test-host:9216"
            },
            "annotations": {
                "summary": "Quick test alert for host inventory"
            },
            "startsAt": datetime.now().isoformat(),
            "generatorURL": "http://prometheus:9090/test"
        }]
    }
    
    try:
        r = requests.post("http://localhost:8000/alert", 
                         json=alert_payload, 
                         timeout=5)
        print(f"✅ Алерт отправлен: {r.json()}")
    except Exception as e:
        print(f"❌ Alert send failed: {e}")
        return False
    
    # 4. Статистика после отправки (через 1 секунду)
    print("\n⏱️ Ждем 1 секунду...")
    import time
    time.sleep(1)
    
    print("📊 Статистика после отправки:")
    try:
        r = requests.get("http://localhost:8000/stats", timeout=5)
        stats_after = r.json()
        print(f"   Очереди: {stats_after.get('queues', {})}")
        print(f"   Throttling: {stats_after.get('throttle', {})}")
        
        # Проверяем изменения
        before_queued = stats_before.get('queues', {}).get('alerts', {}).get('message_count', 0)
        after_queued = stats_after.get('queues', {}).get('alerts', {}).get('message_count', 0)
        
        if after_queued != before_queued:
            print(f"✅ Алерт добавлен в очередь (было: {before_queued}, стало: {after_queued})")
        else:
            print(f"⚠️  Очередь не изменилась, возможно алерт уже обработан")
            
    except Exception as e:
        print(f"❌ Stats after failed: {e}")
        return False
    
    print("\n🎉 Базовый тест прошел успешно!")
    print("\n💡 Что проверить дальше:")
    print("   1. Логи worker'а: должен показать '[WORKER] Alert processed successfully'")
    print("   2. Mattermost: должно прийти сообщение с инвентори хоста")
    print("   3. RabbitMQ UI: http://localhost:15672")
    
    return True

if __name__ == "__main__":
    print("🚀 === БЫСТРЫЙ ТЕСТ SEED v2 ===\n")
    
    if quick_test():
        print("\n✅ Система работает корректно!")
    else:
        print("\n❌ Обнаружены проблемы. Проверьте:")
        print("   - uvicorn app:app --reload")
        print("   - python worker.py") 
        print("   - docker-compose up -d rabbitmq redis")