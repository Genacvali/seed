#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест системы плагинов SEED v6
"""
import requests
import json

def test_plugin_health():
    """Проверка состояния плагинов в health endpoint"""
    print("🏥 Testing Plugin System Health")
    print("=" * 40)
    
    try:
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            print(f"✅ SEED Agent: {data.get('status', 'unknown')}")
            print(f"🔌 Plugins enabled: {data.get('plugins_enabled', False)}")
            print(f"📊 Plugin routes: {data.get('plugin_routes', 0)}")
            print(f"🔄 Default plugin: {data.get('default_plugin', 'unknown')}")
            
            available = data.get('available_plugins', [])
            if available:
                print(f"📦 Available plugins: {', '.join(available)}")
            
            if data.get('plugin_error'):
                print(f"❌ Plugin error: {data['plugin_error']}")
            
            return data.get('plugins_enabled', False)
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to SEED: {e}")
        return False

def test_os_basic_plugin():
    """Тест os_basic плагина с DiskSpaceHigh алертом"""
    print("\n💽 Testing os_basic Plugin (DiskSpaceHigh)")
    print("=" * 50)
    
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "DiskSpaceHigh",
                "instance": "web-server-01", 
                "mountpoint": "/var/lib/postgresql",
                "severity": "critical",
                "job": "node-exporter"
            },
            "annotations": {
                "summary": "Disk usage is 94% on /var/lib/postgresql",
                "description": "PostgreSQL data directory is running out of space"
            }
        }]
    }
    
    return send_test_alert(payload, "os_basic plugin")

def test_pg_slow_plugin():
    """Тест pg_slow плагина с PostgreSQL алертом"""
    print("\n🐘 Testing pg_slow Plugin (PG_IdleInTransaction_Storm)")
    print("=" * 55)
    
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "PG_IdleInTransaction_Storm",
                "instance": "pg-prod-03",
                "severity": "warning", 
                "job": "postgres-exporter"
            },
            "annotations": {
                "summary": "Много сеансов idle in transaction, старый держится > 600s",
                "description": "PostgreSQL has many idle in transaction sessions"
            }
        }]
    }
    
    return send_test_alert(payload, "pg_slow plugin")

def test_mongo_hot_plugin():
    """Тест mongo_hot плагина"""
    print("\n🍃 Testing mongo_hot Plugin (MongoCollscan)")
    print("=" * 45)
    
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "MongoCollscan",
                "instance": "mongo-prod-01",
                "severity": "high",
                "job": "mongodb-exporter"
            },
            "annotations": {
                "summary": "High collection scan rate detected",
                "description": "MongoDB is performing too many collection scans"
            }
        }]
    }
    
    return send_test_alert(payload, "mongo_hot plugin")

def test_host_inventory_plugin():
    """Тест host_inventory плагина"""
    print("\n🖥️ Testing host_inventory Plugin (InstanceDown)")
    print("=" * 48)
    
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "InstanceDown",
                "instance": "api-server-05",
                "severity": "critical",
                "job": "blackbox-exporter"
            },
            "annotations": {
                "summary": "Instance is down for more than 5 minutes",
                "description": "API server is not responding to health checks"
            }
        }]
    }
    
    return send_test_alert(payload, "host_inventory plugin")

def test_default_plugin():
    """Тест default плагина с неизвестным алертом"""
    print("\n❓ Testing Default Plugin (Unknown Alert)")
    print("=" * 42)
    
    payload = {
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "UnknownCustomAlert",
                "instance": "custom-app-01",
                "severity": "info"
            },
            "annotations": {
                "summary": "Custom application alert",
                "description": "This should trigger the default echo plugin"
            }
        }]
    }
    
    return send_test_alert(payload, "default/echo plugin")

def send_test_alert(payload, description):
    """Отправляет тестовый алерт и анализирует ответ"""
    try:
        print(f"📤 Sending {description} test alert...")
        response = requests.post(
            "http://localhost:8080/alertmanager",
            json=payload,
            timeout=30
        )
        
        print(f"📨 Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Alert sent successfully")
            print(f"📝 Response: {response.text[:100]}{'...' if len(response.text) > 100 else ''}")
            
            print(f"👀 Expected plugin behavior:")
            alert_name = payload['alerts'][0]['labels']['alertname']
            
            if 'Disk' in alert_name:
                print("   • Should show disk usage metrics and cleanup recommendations")
            elif 'PG_' in alert_name or 'Postgres' in alert_name:
                print("   • Should show PostgreSQL metrics and idle transaction analysis")
            elif 'Mongo' in alert_name:
                print("   • Should show MongoDB metrics and collection scan analysis")
            elif 'Instance' in alert_name:
                print("   • Should show host inventory and service status")
            else:
                print("   • Should use default echo plugin with basic info")
                
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("🧩 SEED v6 Plugin System Test")
    print("=" * 60)
    
    # 1. Проверка состояния плагинов
    if not test_plugin_health():
        print("\n💡 To fix:")
        print("   1. Start SEED Agent: cd v6/ && ./start.sh")
        print("   2. Check configs/alerts.yaml exists")
        print("   3. Verify all plugins are in plugins/ directory")
        return
    
    # 2. Тестирование различных плагинов
    tests = [
        test_os_basic_plugin,
        test_pg_slow_plugin, 
        test_mongo_hot_plugin,
        test_host_inventory_plugin,
        test_default_plugin
    ]
    
    results = []
    for test_func in tests:
        success = test_func()
        results.append(success)
    
    # 3. Итоги
    print(f"\n📊 Test Results Summary:")
    print(f"   Total tests: {len(results)}")
    print(f"   Passed: {sum(results)}")
    print(f"   Failed: {len(results) - sum(results)}")
    
    if all(results):
        print("🎉 All plugin tests passed!")
    else:
        print("⚠️ Some tests failed - check logs for details")
    
    print(f"\n📋 Next Steps:")
    print("1. Check logs: tail -f v6/logs/agent.log | grep -E '(PLUGIN|ENRICH)'")
    print("2. Look for plugin routing messages and execution results")
    print("3. Verify Mattermost notifications contain plugin sections")

if __name__ == "__main__":
    main()