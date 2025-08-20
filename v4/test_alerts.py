#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Agent v4 - Test Alert Scripts
Send test alerts to SEED Agent for testing plugins
"""
import json
import requests
import time
from datetime import datetime


def send_alert(alert_data: dict, agent_url: str = "http://localhost:8080"):
    """Send alert to SEED Agent"""
    try:
        response = requests.post(
            f"{agent_url}/alert",
            json=alert_data,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Alert sent successfully")
            print(f"   Status: {'Success' if result.get('success') else 'Failed'}")
            if result.get('action'):
                print(f"   Action: {result['action']}")
            if result.get('execution_time'):
                print(f"   Execution time: {result['execution_time']:.2f}s")
            return True
        else:
            print(f"❌ Alert failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error sending alert: {e}")
        return False


def test_host_inventory():
    """Test host inventory plugin"""
    print("\n🧪 Testing Host Inventory Plugin")
    print("=" * 50)
    
    # Test disk space alert
    disk_alert = {
        "alertname": "DiskSpaceHigh",
        "instance": "localhost:9216",
        "labels": {
            "severity": "high",
            "hostname": "localhost",
            "device": "/dev/sda1",
            "mountpoint": "/"
        },
        "annotations": {
            "description": "Disk space is running high on localhost",
            "summary": "High disk usage detected"
        },
        "startsAt": datetime.utcnow().isoformat() + "Z"
    }
    
    print("📦 Sending DiskSpaceHigh alert...")
    success = send_alert(disk_alert)
    
    if success:
        time.sleep(2)  # Wait between alerts
        
        # Test CPU alert
        print("\n📦 Sending HighCpuLoad alert...")
        cpu_alert = {
            "alertname": "HighCpuLoad",
            "instance": "localhost:9216",
            "labels": {
                "severity": "warning",
                "hostname": "localhost"
            },
            "annotations": {
                "description": "High CPU load detected on localhost",
                "summary": "CPU usage is above threshold"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }
        send_alert(cpu_alert)
        
        time.sleep(2)
        
        # Test memory alert
        print("\n📦 Sending HighMemoryUsage alert...")
        memory_alert = {
            "alertname": "HighMemoryUsage",
            "instance": "localhost:9216",
            "labels": {
                "severity": "warning",
                "hostname": "localhost"
            },
            "annotations": {
                "description": "High memory usage detected on localhost",
                "summary": "Memory usage is above threshold"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }
        send_alert(memory_alert)


def test_mongo_plugin():
    """Test MongoDB plugin"""
    print("\n🧪 Testing MongoDB Plugin")
    print("=" * 50)
    
    # Test slow query alert
    mongo_alert = {
        "alertname": "MongoSlowQuery",
        "instance": "mongo-prod-01:27017",
        "labels": {
            "severity": "high",
            "hostname": "mongo-prod-01",
            "database": "myapp"
        },
        "annotations": {
            "description": "Slow MongoDB queries detected",
            "summary": "Multiple slow queries found in myapp database"
        },
        "startsAt": datetime.utcnow().isoformat() + "Z"
    }
    
    print("📦 Sending MongoSlowQuery alert...")
    success = send_alert(mongo_alert)
    
    if success:
        time.sleep(2)
        
        # Test collection scan alert
        print("\n📦 Sending MongoCollscan alert...")
        collscan_alert = {
            "alertname": "MongoCollscan",
            "instance": "mongo-prod-01:27017",
            "labels": {
                "severity": "high",
                "hostname": "mongo-prod-01",
                "database": "myapp",
                "collection": "users"
            },
            "annotations": {
                "description": "Collection scan detected in users collection",
                "summary": "Inefficient query causing full collection scan"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z"
        }
        send_alert(collscan_alert)


def test_general_inventory():
    """Test general host inventory"""
    print("\n🧪 Testing General Host Inventory")
    print("=" * 50)
    
    general_alert = {
        "alertname": "TestHostInventory",
        "instance": "localhost:9216",
        "labels": {
            "severity": "info",
            "hostname": "localhost",
            "environment": "test"
        },
        "annotations": {
            "description": "Test alert for general host inventory",
            "summary": "Testing SEED Agent functionality"
        },
        "startsAt": datetime.utcnow().isoformat() + "Z"
    }
    
    print("📦 Sending TestHostInventory alert...")
    send_alert(general_alert)


def test_throttling():
    """Test alert throttling"""
    print("\n🧪 Testing Alert Throttling")
    print("=" * 50)
    
    throttle_alert = {
        "alertname": "TestHostInventory",
        "instance": "localhost:9216",
        "labels": {
            "severity": "info",
            "hostname": "localhost",
            "test": "throttling"
        },
        "annotations": {
            "description": "Testing alert throttling - this should be suppressed",
            "summary": "Duplicate alert for throttling test"
        },
        "startsAt": datetime.utcnow().isoformat() + "Z"
    }
    
    print("📦 Sending first alert (should succeed)...")
    send_alert(throttle_alert)
    
    time.sleep(1)
    
    print("📦 Sending duplicate alert (should be throttled)...")
    send_alert(throttle_alert)
    
    print("ℹ️  Check SEED Agent logs to see throttling in action")


def test_unknown_alert():
    """Test unknown alert handling"""
    print("\n🧪 Testing Unknown Alert Handling")
    print("=" * 50)
    
    unknown_alert = {
        "alertname": "UnknownAlert",
        "instance": "unknown-host:9999",
        "labels": {
            "severity": "critical",
            "hostname": "unknown-host"
        },
        "annotations": {
            "description": "This alert has no routing configuration",
            "summary": "Testing unknown alert handling"
        },
        "startsAt": datetime.utcnow().isoformat() + "Z"
    }
    
    print("📦 Sending unknown alert (should fail with routing error)...")
    send_alert(unknown_alert)


def check_agent_status():
    """Check SEED Agent status"""
    print("🔍 Checking SEED Agent Status")
    print("=" * 50)
    
    try:
        # Health check
        response = requests.get("http://localhost:8080/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print("✅ SEED Agent is healthy")
            print(f"   Version: {health.get('version', 'unknown')}")
            print(f"   Environment: {health.get('environment', 'unknown')}")
            
            services = health.get('services', {})
            for service, status in services.items():
                icon = "✅" if status else "❌"
                print(f"   {service.title()}: {icon}")
                
            return True
        else:
            print(f"❌ SEED Agent health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot connect to SEED Agent: {e}")
        print("   Make sure SEED Agent is running on http://localhost:8080")
        return False


def main():
    """Run all test scenarios"""
    print("🚀 SEED Agent v4 - Test Alert Suite")
    print("=" * 60)
    
    # Check if agent is running
    if not check_agent_status():
        print("\n❌ SEED Agent is not accessible. Please start it first:")
        print("   cd v4/")
        print("   ./dist/seed-agent --config seed.yaml")
        return
    
    print("\n⏳ Starting test scenarios in 3 seconds...")
    time.sleep(3)
    
    # Run test scenarios
    test_host_inventory()
    
    print("\n" + "─" * 60)
    test_mongo_plugin()
    
    print("\n" + "─" * 60) 
    test_general_inventory()
    
    print("\n" + "─" * 60)
    test_throttling()
    
    print("\n" + "─" * 60)
    test_unknown_alert()
    
    print("\n" + "=" * 60)
    print("🎉 Test suite completed!")
    print("\n📋 Next steps:")
    print("   1. Check SEED Agent logs for plugin execution details")
    print("   2. Configure notifications in seed.yaml to see alerts in Mattermost/Slack")
    print("   3. Set up Telegraf on monitored hosts for real metrics")
    print("   4. Configure MongoDB monitoring for production databases")
    
    print("\n📊 Useful endpoints:")
    print("   Health:  http://localhost:8080/health")
    print("   Config:  http://localhost:8080/config")  
    print("   Metrics: http://localhost:8080/metrics")


if __name__ == "__main__":
    main()