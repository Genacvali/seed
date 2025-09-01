#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Реалистичные тесты SEED v6 с Prometheus метриками и LLM
"""
import json
import requests
import time
from datetime import datetime, timedelta

# Конфигурация
SEED_URL = "http://localhost:8080"
PROMETHEUS_URL = "http://localhost:9090"  # Замените на ваш Prometheus

def query_prometheus(query: str, prometheus_url: str = PROMETHEUS_URL):
    """Запрос к Prometheus API"""
    try:
        url = f"{prometheus_url}/api/v1/query"
        params = {"query": query}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"❌ Prometheus query failed: {e}")
        return None

def create_disk_alert(host: str, usage_percent: float, mount: str = "/"):
    """Создает алерт о нехватке места на диске"""
    return {
        "status": "firing",
        "labels": {
            "alertname": "DiskSpaceLow",
            "instance": host,
            "severity": "critical" if usage_percent > 90 else "warning",
            "mountpoint": mount,
            "job": "node_exporter"
        },
        "annotations": {
            "summary": f"Disk space usage is {usage_percent:.1f}% on {mount}",
            "description": f"Host {host} has {usage_percent:.1f}% disk usage on {mount} mount. Free space is critically low.",
            "runbook_url": "https://wiki.company.com/runbooks/disk-space"
        },
        "startsAt": (datetime.now() - timedelta(minutes=5)).isoformat() + "Z",
        "generatorURL": f"{PROMETHEUS_URL}/graph?g0.expr=disk_used_percent&g0.tab=1"
    }

def create_memory_alert(host: str, usage_percent: float):
    """Создает алерт о нехватке памяти"""
    return {
        "status": "firing",
        "labels": {
            "alertname": "HighMemoryUsage",
            "instance": host,
            "severity": "high" if usage_percent > 85 else "warning",
            "job": "node_exporter"
        },
        "annotations": {
            "summary": f"High memory usage {usage_percent:.1f}% on {host}",
            "description": f"Memory usage on {host} is {usage_percent:.1f}%. This may affect system performance.",
            "runbook_url": "https://wiki.company.com/runbooks/memory"
        },
        "startsAt": (datetime.now() - timedelta(minutes=2)).isoformat() + "Z",
        "generatorURL": f"{PROMETHEUS_URL}/graph?g0.expr=memory_usage_percent"
    }

def create_cpu_alert(host: str, usage_percent: float):
    """Создает алерт о высокой нагрузке CPU"""
    return {
        "status": "firing", 
        "labels": {
            "alertname": "HighCPUUsage",
            "instance": host,
            "severity": "high" if usage_percent > 80 else "warning",
            "job": "node_exporter"
        },
        "annotations": {
            "summary": f"High CPU usage {usage_percent:.1f}% on {host}",
            "description": f"CPU usage on {host} has been above {usage_percent:.1f}% for more than 5 minutes.",
            "runbook_url": "https://wiki.company.com/runbooks/cpu"
        },
        "startsAt": (datetime.now() - timedelta(minutes=8)).isoformat() + "Z"
    }

def create_database_alert(host: str, connections: int):
    """Создает алерт о проблемах с базой данных"""
    return {
        "status": "firing",
        "labels": {
            "alertname": "DatabaseConnectionsHigh", 
            "instance": host,
            "severity": "critical" if connections > 90 else "high",
            "job": "postgresql_exporter",
            "database": "production"
        },
        "annotations": {
            "summary": f"High database connections: {connections}/100",
            "description": f"PostgreSQL on {host} has {connections} active connections out of 100 max. Database may become unresponsive.",
            "runbook_url": "https://wiki.company.com/runbooks/postgresql"
        },
        "startsAt": (datetime.now() - timedelta(minutes=3)).isoformat() + "Z"
    }

def send_to_seed(alerts: list, test_name: str):
    """Отправляет алерты в SEED"""
    payload = {
        "receiver": "seed-webhook",
        "status": "firing",
        "alerts": alerts,
        "groupKey": f"test-{int(time.time())}",
        "version": "4",
        "groupLabels": {},
        "commonLabels": {},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager.local:9093"
    }
    
    print(f"\n🧪 Test: {test_name}")
    print("=" * 50)
    
    try:
        r = requests.post(f"{SEED_URL}/alertmanager", json=payload, timeout=15)
        if r.status_code == 200:
            result = r.json()
            print(f"✅ SEED responded: {result}")
        else:
            print(f"❌ SEED error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_with_prometheus_data():
    """Тест с реальными данными из Prometheus"""
    print("🔍 Querying Prometheus for real metrics...")
    
    # Запрос диск usage
    disk_data = query_prometheus('100 - (node_filesystem_free_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes * 100)')
    
    # Запрос memory usage  
    mem_data = query_prometheus('(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100')
    
    # Запрос CPU usage
    cpu_data = query_prometheus('100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)')
    
    alerts = []
    
    if disk_data and disk_data.get("data", {}).get("result"):
        for metric in disk_data["data"]["result"][:3]:  # Берем первые 3
            instance = metric["metric"].get("instance", "unknown")
            mountpoint = metric["metric"].get("mountpoint", "/")
            usage = float(metric["value"][1])
            
            if usage > 70:  # Только если usage > 70%
                alerts.append(create_disk_alert(instance, usage, mountpoint))
    
    if mem_data and mem_data.get("data", {}).get("result"):
        for metric in mem_data["data"]["result"][:2]:  # Берем первые 2
            instance = metric["metric"].get("instance", "unknown") 
            usage = float(metric["value"][1])
            
            if usage > 60:  # Только если usage > 60%
                alerts.append(create_memory_alert(instance, usage))
    
    if alerts:
        send_to_seed(alerts, "Real Prometheus Metrics")
    else:
        print("⚠️ No high-usage metrics found in Prometheus, running synthetic test...")
        test_synthetic_alerts()

def test_synthetic_alerts():
    """Синтетические тесты для демонстрации"""
    
    # Тест 1: Критический алерт диска
    print("\n" + "="*60)
    alerts = [create_disk_alert("db-prod-01.company.com", 94.2, "/var/lib/postgresql")]
    send_to_seed(alerts, "Critical Disk Space Alert")
    time.sleep(2)
    
    # Тест 2: Множественные алерты с разными severity
    print("\n" + "="*60) 
    alerts = [
        create_memory_alert("app-web-01.company.com", 87.5),
        create_cpu_alert("app-web-02.company.com", 92.1), 
        create_disk_alert("app-web-03.company.com", 78.3, "/tmp")
    ]
    send_to_seed(alerts, "Multiple Alerts (Different Severities)")
    time.sleep(2)
    
    # Тест 3: База данных
    print("\n" + "="*60)
    alerts = [create_database_alert("postgres-master.company.com", 95)]
    send_to_seed(alerts, "Database Connection Alert")
    time.sleep(2)
    
    # Тест 4: Комплексный инцидент
    print("\n" + "="*60)
    alerts = [
        create_disk_alert("mongo-01.company.com", 96.8, "/data/mongodb"),
        create_memory_alert("mongo-01.company.com", 89.2),
        create_cpu_alert("mongo-01.company.com", 85.7),
    ]
    send_to_seed(alerts, "Complex Infrastructure Incident")

def test_health_check():
    """Проверка работоспособности SEED"""
    try:
        r = requests.get(f"{SEED_URL}/health", timeout=5)
        health = r.json()
        print("🏥 SEED Health Check:")
        print(f"   Status: {'✅' if health.get('status') == 'ok' else '❌'}")
        print(f"   LLM: {'✅' if health.get('use_llm') else '⏸️'}")
        print(f"   Mattermost: {'✅' if health.get('mm_webhook') else '❌'}")
        print(f"   RabbitMQ: {'✅' if health.get('rabbit_enabled') else '⏸️'}")
        print(f"   Version: {health.get('version', 'unknown')}")
        return health.get("status") == "ok"
    except Exception as e:
        print(f"❌ SEED health check failed: {e}")
        return False

def main():
    print("🌌 SEED v6 Realistic Testing Suite")
    print("=" * 60)
    
    # Проверка доступности SEED
    if not test_health_check():
        print("❌ SEED is not available. Please start it first with ./start.sh")
        return
    
    print(f"\n🎯 Testing SEED at: {SEED_URL}")
    print(f"🎯 Prometheus at: {PROMETHEUS_URL}")
    
    # Пробуем с реальными данными Prometheus
    try:
        test_with_prometheus_data()
    except Exception as e:
        print(f"⚠️ Prometheus test failed ({e}), falling back to synthetic...")
        test_synthetic_alerts()
    
    print("\n" + "="*60)
    print("🎉 Testing completed!")
    print("\n💡 Tips:")
    print("   - Check Mattermost for formatted alerts with FF styling")
    print("   - LLM recommendations should appear as '🧠 Магия кристалла'")
    print("   - Colors should match severity levels")
    print(f"   - Monitor logs: tail -f logs/agent.log")

if __name__ == "__main__":
    main()