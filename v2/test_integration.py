#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для демонстрации RabbitMQ интеграции
"""
import asyncio
import json
import requests
import time
from datetime import datetime

# Конфигурация
API_URL = "http://localhost:8000"
STATS_URL = f"{API_URL}/stats"
ALERT_URL = f"{API_URL}/alert"

def test_alert_payload(alertname: str, host: str = "test-host", **extra_labels):
    """Создание тестового алерта"""
    labels = {
        "alertname": alertname,
        "host": host,
        "instance": f"{host}:27017",
        **extra_labels
    }
    
    annotations = {
        "summary": f"Test alert {alertname} on {host}",
        "description": f"This is a test alert for demonstration purposes"
    }
    
    # Для mongo_collscan добавим специфичные данные
    if alertname == "mongo_collscan":
        annotations.update({
            "hotspots": """namespace                   op       time     details
----------------------------------------------------------
mydb.users                 find     1250ms   plan:COLLSCAN
mydb.orders                find      890ms   plan:COLLSCAN
mydb.products              find      670ms   plan:COLLSCAN""",
            "last_ts": datetime.now().isoformat()
        })
        labels.update({
            "db": "mydb",
            "ns": "mydb.users",
            "millis": "1250"
        })
    
    return {
        "alerts": [{
            "status": "firing",
            "labels": labels,
            "annotations": annotations,
            "startsAt": datetime.now().isoformat(),
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": f"http://prometheus:9090/graph?g0.expr=up%7Binstance%3D%22{host}%22%7D"
        }]
    }

def send_test_alert(alertname: str, host: str = "test-host", **kwargs):
    """Отправка тестового алерта"""
    payload = test_alert_payload(alertname, host, **kwargs)
    
    print(f"📤 Отправляем алерт: {alertname} для {host}")
    
    try:
        response = requests.post(ALERT_URL, json=payload, timeout=5)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Алерт отправлен в очередь: {result}")
            return True
        else:
            print(f"❌ Ошибка отправки: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False

def get_stats():
    """Получение статистики системы"""
    try:
        response = requests.get(STATS_URL, timeout=5)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Ошибка получения статистики: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка подключения к stats: {e}")
        return None

def print_stats():
    """Вывод статистики в удобном формате"""
    stats = get_stats()
    if not stats:
        return
    
    print("📊 Статистика системы:")
    print(f"   Время: {datetime.fromtimestamp(stats.get('time', 0))}")
    
    # Throttling stats
    throttle = stats.get('throttle', {})
    print(f"   Throttling: {throttle.get('backend', 'unknown')} backend")
    print(f"   Подавлено алертов: {throttle.get('suppressed_count', 0)}")
    print(f"   Redis подключен: {throttle.get('redis_connected', False)}")
    
    # Queue stats
    queues = stats.get('queues', {})
    if isinstance(queues, dict) and 'error' not in queues:
        print("   Очереди:")
        for name, info in queues.items():
            print(f"     {name}: {info.get('message_count', 0)} сообщений")
    else:
        print(f"   Очереди: {queues}")

def demo_basic_flow():
    """Демонстрация базового потока обработки алертов"""
    print("\n🎭 === ДЕМОНСТРАЦИЯ БАЗОВОГО ПОТОКА ===")
    
    print("\n1️⃣ Проверяем начальное состояние:")
    print_stats()
    
    print("\n2️⃣ Отправляем тестовый алерт host_inventory:")
    send_test_alert("host_inventory", "demo-server-01")
    
    print("\n3️⃣ Ждем 2 секунды для обработки...")
    time.sleep(2)
    print_stats()
    
    print("\n4️⃣ Отправляем алерт mongo_collscan:")
    send_test_alert("mongo_collscan", "mongo-prod-01")
    
    print("\n5️⃣ Ждем еще 2 секунды...")
    time.sleep(2)
    print_stats()
    
    print("\n6️⃣ Повторно отправляем тот же алерт (должен быть подавлен):")
    send_test_alert("mongo_collscan", "mongo-prod-01")
    
    print("\n7️⃣ Финальная статистика:")
    time.sleep(1)
    print_stats()

def demo_throttling():
    """Демонстрация throttling механизма"""
    print("\n🛡️  === ДЕМОНСТРАЦИЯ THROTTLING ===")
    
    host = "throttle-test-host"
    
    print(f"\n1️⃣ Отправляем 3 одинаковых алерта для {host}:")
    for i in range(3):
        print(f"   Попытка {i+1}:")
        send_test_alert("host_inventory", host)
        time.sleep(0.5)
    
    print("\n2️⃣ Проверяем статистику throttling:")
    print_stats()
    
    print(f"\n3️⃣ Отправляем алерт для другого хоста (должен пройти):")
    send_test_alert("host_inventory", "another-host")
    
    print("\n4️⃣ Финальная статистика:")
    time.sleep(1)
    print_stats()

def demo_multiple_alerts():
    """Демонстрация массовой отправки алертов"""
    print("\n🚀 === ДЕМОНСТРАЦИЯ МАССОВОЙ ОБРАБОТКИ ===")
    
    hosts = ["server-01", "server-02", "server-03", "db-01", "db-02"]
    alerts = ["host_inventory", "mongo_collscan"]
    
    print(f"\n1️⃣ Отправляем {len(hosts) * len(alerts)} алертов одновременно:")
    
    for host in hosts:
        for alert in alerts:
            send_test_alert(alert, host)
    
    print("\n2️⃣ Ждем обработки...")
    time.sleep(3)
    
    print("\n3️⃣ Проверяем очереди:")
    print_stats()

def health_check():
    """Проверка доступности API"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API доступен")
            return True
        else:
            print(f"❌ API недоступен: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API недоступен: {e}")
        return False

def main():
    """Главная функция тестирования"""
    print("🧪 === ТЕСТИРОВАНИЕ SEED v2 RabbitMQ INTEGRATION ===")
    
    if not health_check():
        print("\n❌ Система недоступна. Убедитесь что запущены:")
        print("   - uvicorn app:app --reload")
        print("   - python worker.py")
        print("   - docker-compose up -d rabbitmq redis")
        return
    
    try:
        demo_basic_flow()
        demo_throttling()
        demo_multiple_alerts()
        
        print("\n🎉 === ТЕСТИРОВАНИЕ ЗАВЕРШЕНО ===")
        print("\nДля мониторинга:")
        print("   - Статистика: http://localhost:8000/stats")
        print("   - RabbitMQ UI: http://localhost:15672 (guest/guest)")
        
    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")

if __name__ == "__main__":
    main()