#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Test script for Zabbix webhook validation
Helps debug JSON formatting and webhook functionality
"""

import json
import subprocess
import sys
import os
from pathlib import Path

def create_test_jsons():
    """Create various test JSON payloads for different scenarios"""
    
    # 1. Minimal valid JSON
    minimal_json = {
        "event": {"value": "1", "id": "12345"},
        "trigger": {"name": "Test Alert", "severity_text": "High"},
        "host": {"name": "testhost", "ip": "192.168.1.1"}
    }
    
    # 2. Enriched JSON (full template)
    enriched_json = {
        "event": {
            "id": "67890",
            "value": "1",
            "date": "2024-01-15",
            "time": "14:30:25",
            "r_date": "",
            "r_time": ""
        },
        "trigger": {
            "name": "MongoDB Процессов нет",
            "description": "Процессы MongoDB не найдены на сервере",
            "severity_text": "High",
            "tags": "service:mongodb,env:production"
        },
        "host": {
            "name": "p-homesecurity-mng-adv-msk01",
            "ip": "10.20.30.40",
            "groups": "MongoDB Servers,Production"
        },
        "item": {
            "name": "MongoDB process count",
            "key": "proc.num[mongod]",
            "lastvalue": "0",
            "id": "98765",
            "port": "27017"
        }
    }
    
    # 3. Problem JSON (should trigger rule engine for MongoDB)
    mongodb_problem = {
        "event": {"value": "1", "id": "11111"},
        "trigger": {
            "name": "MongoDB not running",
            "description": "MongoDB процессов нет на p-homesecurity-mng-adv-msk01:27017",
            "severity_text": "Critical"
        },
        "host": {"name": "p-homesecurity-mng-adv-msk01", "ip": "10.0.0.100"},
        "item": {"key": "proc.num[mongod]", "lastvalue": "0"}
    }
    
    # 4. Zabbix agent problem (should trigger rule engine for Zabbix agent)
    zabbix_agent_problem = {
        "event": {"value": "1", "id": "22222"},
        "trigger": {
            "name": "Zabbix agent not accessible",
            "description": "Zabbix agent недоступен на хосте",
            "severity_text": "Warning"
        },
        "host": {"name": "web-server-01", "ip": "10.0.0.200"},
        "item": {"key": "agent.ping", "lastvalue": "0"}
    }
    
    return {
        "minimal": minimal_json,
        "enriched": enriched_json,
        "mongodb": mongodb_problem,
        "zabbix_agent": zabbix_agent_problem
    }

def test_webhook_script(json_payload, test_name, seed_url=None):
    """Test the webhook script with given JSON payload"""
    
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {test_name}")
    print('='*60)
    
    # Convert to JSON string
    json_str = json.dumps(json_payload, ensure_ascii=False)
    print(f"📝 JSON length: {len(json_str)} characters")
    print(f"📋 JSON preview: {json_str[:100]}...")
    
    # Find webhook script
    webhook_script = Path("zabbix-webhook-enriched.py")
    if not webhook_script.exists():
        print(f"❌ Webhook script not found: {webhook_script}")
        return False
    
    # Prepare command
    cmd = ["python3", str(webhook_script)]
    if seed_url:
        cmd.append(seed_url)
    cmd.append(json_str)
    
    print(f"🚀 Running: {' '.join(cmd[:3])} '<json_data>'")
    
    try:
        # Run the webhook script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"📤 Exit code: {result.returncode}")
        
        if result.stdout:
            print("📤 STDOUT:")
            for line in result.stdout.splitlines():
                print(f"  {line}")
        
        if result.stderr:
            print("❌ STDERR:")
            for line in result.stderr.splitlines():
                print(f"  {line}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("⏰ Test timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"💥 Test failed with exception: {e}")
        return False

def main():
    """Main test function"""
    
    if len(sys.argv) > 1:
        seed_url = sys.argv[1]
    else:
        seed_url = "http://localhost:8080/zabbix"
        print(f"ℹ️  Using default SEED URL: {seed_url}")
        print(f"ℹ️  To test with different URL: python3 {sys.argv[0]} <seed_url>")
    
    # Check if SEED Agent is running
    print(f"\n🔍 Checking if SEED Agent is accessible at {seed_url}")
    
    try:
        import requests
        health_url = seed_url.replace('/zabbix', '/health')
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print("✅ SEED Agent is running and accessible")
        else:
            print(f"⚠️  SEED Agent returned status {response.status_code}")
    except Exception as e:
        print(f"❌ SEED Agent not accessible: {e}")
        print("ℹ️  Tests will continue but won't reach SEED Agent")
    
    # Create test cases
    test_cases = create_test_jsons()
    
    results = {}
    
    # Run tests
    for test_name, json_payload in test_cases.items():
        success = test_webhook_script(json_payload, test_name, seed_url)
        results[test_name] = success
    
    # Summary
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print('='*60)
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {test_name:15} {status}")
    
    print(f"\n🎯 Overall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Webhook is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())