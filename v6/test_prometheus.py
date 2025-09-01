#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест интеграции SEED с Prometheus для обогащения алертов
"""
import json
import requests
import time

SEED_URL = "http://localhost:8080"

def test_prometheus_enrichment():
    """Тест обогащения алертов данными из Prometheus"""
    
    # Проверяем статус SEED и Prometheus интеграции
    try:
        r = requests.get(f"{SEED_URL}/health", timeout=5)
        health = r.json()
        print("🏥 SEED Health Check:")
        print(f"   Status: {'✅' if health.get('status') == 'ok' else '❌'}")
        print(f"   LLM: {'✅' if health.get('use_llm') else '⏸️'}")
        print(f"   Prometheus: {'✅' if health.get('prometheus_enrichment') else '⏸️'}")
        if health.get('prometheus_url'):
            print(f"   Prometheus URL: {health['prometheus_url']}")
            
        if not health.get('prometheus_enrichment'):
            print("\n⚠️ Prometheus enrichment disabled. To enable:")
            print("   1. Set PROM_URL in configs/seed.env")
            print("   2. Restart SEED: ./stop.sh && ./start.sh")
            print("   3. Will fallback to basic alerts without metrics")
            
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return

    # Тестовые алерты с реалистичными данными
    test_scenarios = [
        {
            "name": "Disk Space Alert with Mount",
            "alert": {
                "status": "firing",
                "labels": {
                    "alertname": "DiskSpaceLow",
                    "instance": "web-app-01.company.local:9100",
                    "severity": "critical",
                    "mountpoint": "/var/lib/postgresql",
                    "job": "node_exporter",
                    "device": "/dev/sda1"
                },
                "annotations": {
                    "summary": "Disk space usage is 92% on /var/lib/postgresql",
                    "description": "PostgreSQL database partition is running critically low on space"
                }
            }
        },
        {
            "name": "High Memory Alert",
            "alert": {
                "status": "firing",
                "labels": {
                    "alertname": "HighMemoryUsage",
                    "instance": "api-server-02.company.local:9100",
                    "severity": "high",
                    "job": "node_exporter"
                },
                "annotations": {
                    "summary": "High memory usage 89% on api-server-02",
                    "description": "Memory consumption is consistently high, may impact performance"
                }
            }
        },
        {
            "name": "CPU Alert",
            "alert": {
                "status": "firing", 
                "labels": {
                    "alertname": "HighCPUUsage",
                    "instance": "worker-03.company.local:9100",
                    "severity": "warning",
                    "job": "node_exporter"
                },
                "annotations": {
                    "summary": "High CPU usage 85% on worker-03",
                    "description": "CPU load has been consistently high for 10+ minutes"
                }
            }
        }
    ]
    
    print(f"\n🧪 Testing Prometheus enrichment scenarios...")
    print("=" * 60)
    
    for scenario in test_scenarios:
        print(f"\n📊 Test: {scenario['name']}")
        print("-" * 40)
        
        # Отправляем алерт в SEED
        payload = {
            "receiver": "seed-webhook",
            "status": "firing",
            "alerts": [scenario["alert"]],
            "groupKey": f"test-{int(time.time())}",
            "version": "4"
        }
        
        try:
            r = requests.post(f"{SEED_URL}/alertmanager", json=payload, timeout=15)
            if r.status_code == 200:
                result = r.json()
                print(f"✅ Alert sent successfully: {result}")
                print("📱 Expected in Mattermost:")
                print("   • FF-style formatting with emoji")
                print("   • 📊 Prometheus metrics (if configured)")
                print("   • 🧠 Enhanced LLM recommendations")
            else:
                print(f"❌ Error {r.status_code}: {r.text}")
        except Exception as e:
            print(f"❌ Request failed: {e}")
            
        time.sleep(2)  # Небольшая пауза между тестами

def test_multi_alert_enrichment():
    """Тест комплексного инцидента с обогащением"""
    print(f"\n🔥 Testing complex multi-alert incident with enrichment...")
    print("=" * 60)
    
    # Комплексный инцидент на одном хосте
    alerts = [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighCPUUsage",
                "instance": "db-primary.company.local:9100",
                "severity": "high",
                "job": "node_exporter"
            },
            "annotations": {
                "summary": "High CPU usage 91% on db-primary",
                "description": "Database server CPU load is critically high"
            }
        },
        {
            "status": "firing", 
            "labels": {
                "alertname": "HighMemoryUsage",
                "instance": "db-primary.company.local:9100",
                "severity": "high",
                "job": "node_exporter"
            },
            "annotations": {
                "summary": "High memory usage 87% on db-primary", 
                "description": "Database server memory consumption is very high"
            }
        },
        {
            "status": "firing",
            "labels": {
                "alertname": "DiskSpaceLow",
                "instance": "db-primary.company.local:9100",
                "severity": "critical",
                "mountpoint": "/var/lib/postgresql",
                "job": "node_exporter"
            },
            "annotations": {
                "summary": "Disk space usage is 94% on /var/lib/postgresql",
                "description": "Database partition is critically full"
            }
        }
    ]
    
    payload = {
        "receiver": "seed-webhook",
        "status": "firing", 
        "alerts": alerts,
        "groupKey": f"complex-incident-{int(time.time())}",
        "version": "4"
    }
    
    try:
        r = requests.post(f"{SEED_URL}/alertmanager", json=payload, timeout=20)
        if r.status_code == 200:
            result = r.json()
            print(f"✅ Complex incident sent: {result}")
            print("📱 Expected in Mattermost:")
            print("   • Multiple alerts with individual enrichment")
            print("   • 📊 Summary statistics")
            print("   • 🧠 Comprehensive LLM analysis of the incident")
            print("   • Color coding based on highest severity (critical=red)")
        else:
            print(f"❌ Error {r.status_code}: {r.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

def main():
    print("🌌 SEED v6.1 Prometheus Integration Test")
    print("=" * 60)
    
    test_prometheus_enrichment()
    test_multi_alert_enrichment()
    
    print("\n" + "=" * 60)
    print("🎉 Prometheus integration testing completed!")
    print("\n📋 What to check:")
    print("   📊 Enriched metrics in alert cards (CPU ~ X%, MEM ~ Y%, Disk ~ Z%)")
    print("   🧠 More accurate LLM recommendations using actual metrics")
    print("   📈 Trends and context from Prometheus queries")
    print("   🎯 Host-specific performance data")
    
    print(f"\n🔍 Monitor enrichment logs: tail -f logs/agent.log | grep ENRICH")

if __name__ == "__main__":
    main()