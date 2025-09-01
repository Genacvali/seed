#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест LLM функциональности SEED
"""
import requests
import json

SEED_URL = "http://localhost:8080"

# Тестовые алерты с разными уровнями критичности
test_scenarios = {
    "critical_disk": {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "DiskSpaceLow",
                "instance": "db-prod-01.company.local", 
                "severity": "critical",
                "mountpoint": "/var/lib/postgresql",
                "job": "node_exporter"
            },
            "annotations": {
                "summary": "Disk space usage is 94.2% on /var/lib/postgresql",
                "description": "PostgreSQL database server is running out of disk space. Only 1.2GB remaining on /var/lib/postgresql mount.",
                "runbook_url": "https://wiki.company.com/disk-cleanup"
            }
        }]
    },
    
    "memory_pressure": {
        "alerts": [{
            "status": "firing", 
            "labels": {
                "alertname": "HighMemoryUsage",
                "instance": "web-app-02.company.local",
                "severity": "high",
                "job": "node_exporter"
            },
            "annotations": {
                "summary": "High memory usage 89.4% on web-app-02",
                "description": "Memory consumption has been consistently high for 10+ minutes. Application performance may be degraded.",
                "runbook_url": "https://wiki.company.com/memory-analysis"
            }
        }]
    },
    
    "mongodb_slow": {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "MongoSlowQueries", 
                "instance": "mongo-cluster-01.company.local",
                "severity": "warning",
                "database": "ecommerce_prod",
                "job": "mongodb_exporter"
            },
            "annotations": {
                "summary": "MongoDB slow queries detected: 25 queries > 1000ms",
                "description": "High number of slow queries detected on ecommerce_prod database. Average query time increased to 1.8 seconds.",
                "runbook_url": "https://wiki.company.com/mongodb-performance"
            }
        }]
    },
    
    "multi_service_incident": {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighCPUUsage",
                    "instance": "k8s-worker-03.company.local", 
                    "severity": "high",
                    "job": "kubernetes-nodes"
                },
                "annotations": {
                    "summary": "High CPU usage 91.2% on k8s-worker-03",
                    "description": "Kubernetes worker node experiencing sustained high CPU load"
                }
            },
            {
                "status": "firing", 
                "labels": {
                    "alertname": "PodCrashLooping",
                    "instance": "k8s-worker-03.company.local",
                    "severity": "critical", 
                    "namespace": "production",
                    "pod": "payment-service-7d8f9",
                    "job": "kubernetes-pods"
                },
                "annotations": {
                    "summary": "Pod payment-service-7d8f9 is crash looping",
                    "description": "Payment service pod has restarted 12 times in the last 30 minutes"
                }
            }
        ]
    }
}

def send_test_alert(scenario_name: str, scenario_data: dict):
    """Отправляет тестовый алерт в SEED"""
    payload = {
        "receiver": "seed-webhook",
        "status": "firing", 
        "alerts": scenario_data["alerts"],
        "groupKey": f"test-llm-{scenario_name}",
        "version": "4"
    }
    
    print(f"\n🧪 Testing scenario: {scenario_name}")
    print("-" * 50)
    
    try:
        r = requests.post(f"{SEED_URL}/alertmanager", json=payload, timeout=20)
        if r.status_code == 200:
            result = r.json()
            print(f"✅ Alert sent successfully: {result}")
            print("📱 Check Mattermost for:")
            print("   • FF-style formatting with emoji icons")
            print("   • Color-coded severity levels") 
            print("   • 🧠 'Магия кристалла' LLM recommendations")
        else:
            print(f"❌ Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_health_and_llm():
    """Проверяет состояние SEED и LLM"""
    try:
        r = requests.get(f"{SEED_URL}/health", timeout=5)
        health = r.json()
        
        print("🏥 SEED System Status:")
        print(f"   Agent: {'✅ Running' if health.get('status') == 'ok' else '❌ Down'}")
        print(f"   LLM: {'✅ Enabled' if health.get('use_llm') else '⚠️ Disabled'}")
        print(f"   Mattermost: {'✅ Configured' if health.get('mm_webhook') else '❌ Not configured'}")
        
        if not health.get('use_llm'):
            print("\n⚠️ LLM is disabled! To enable:")
            print("   1. Set USE_LLM=1 in configs/seed.env")
            print("   2. Add GigaChat credentials")
            print("   3. Restart: ./stop.sh && ./start.sh")
            return False
        
        if not health.get('mm_webhook'):
            print("\n⚠️ Mattermost not configured! Add MM_WEBHOOK to configs/seed.env")
            
        return health.get('status') == 'ok'
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    print("🌌 SEED v6 LLM Testing Suite")
    print("="*60)
    
    # Проверка системы
    if not test_health_and_llm():
        print("\n❌ System not ready. Fix issues above and try again.")
        return
    
    print(f"\n🎯 Target: {SEED_URL}")
    print("🧠 Testing LLM integration with realistic scenarios...")
    
    # Запуск тестов
    for scenario_name, scenario_data in test_scenarios.items():
        send_test_alert(scenario_name, scenario_data)
        
        # Небольшая пауза между тестами
        import time
        time.sleep(3)
    
    print("\n" + "="*60)
    print("🎉 LLM testing completed!")
    print("\n📋 What to check in Mattermost:")
    print("   💎🔥 Critical alerts in RED")
    print("   ⚔️ High alerts in ORANGE") 
    print("   🛡️ Warning alerts in YELLOW")
    print("   🧠 LLM recommendations should appear")
    print("   📊 Summary for multi-alert incidents")
    
    print(f"\n📊 Monitor logs: tail -f logs/agent.log")

if __name__ == "__main__":
    main()