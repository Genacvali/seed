#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for SberDevices Alertmanager integration
"""

import requests
import json
import time
from datetime import datetime

def test_seed_agent_health(seed_url: str):
    """Test if SEED Agent is running"""
    try:
        response = requests.get(f"{seed_url}/health", timeout=5)
        response.raise_for_status()
        health = response.json()
        print(f"✅ SEED Agent health: {json.dumps(health, indent=2)}")
        return True
    except Exception as e:
        print(f"❌ SEED Agent health check failed: {e}")
        return False

def test_mock_alert_to_seed(seed_url: str):
    """Send a mock SberDevices alert to SEED Agent"""
    mock_alert = {
        "alerts": [
            {
                "labels": {
                    "alertname": "SberDevices_Test_Alert",
                    "instance": "test-host.sberdevices.ru",
                    "severity": "warning",
                    "job": "sber-monitoring",
                    "service": "test-service",
                    "team": "platform",
                    "environment": "production"
                },
                "annotations": {
                    "summary": "Test alert from SberDevices Alertmanager",
                    "description": "This is a test alert to verify SEED Agent integration",
                    "runbook_url": "https://wiki.sberdevices.ru/runbooks/test",
                    "source": "sberdevices-alertmanager"
                },
                "status": "firing",
                "startsAt": datetime.utcnow().isoformat() + "Z",
                "generatorURL": "https://alertmanager.sberdevices.ru"
            }
        ]
    }
    
    # Try v5 endpoint first
    try:
        response = requests.post(f"{seed_url}/alert", json=mock_alert, timeout=10)
        if response.status_code == 200:
            print("✅ Mock alert sent successfully to v5 endpoint (/alert)")
            return True
    except Exception as e:
        print(f"⚠️  v5 endpoint failed: {e}")
    
    # Try v6 endpoint
    try:
        response = requests.post(f"{seed_url}/alertmanager", json=mock_alert, timeout=10)
        if response.status_code == 200:
            print("✅ Mock alert sent successfully to v6 endpoint (/alertmanager)")
            return True
    except Exception as e:
        print(f"❌ v6 endpoint failed: {e}")
    
    print("❌ Failed to send mock alert to any endpoint")
    return False

def test_sber_alertmanager_access():
    """Test access to SberDevices Alertmanager"""
    url = "https://alertmanager.sberdevices.ru/api/v2/alerts"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"🔍 SberDevices Alertmanager response: HTTP {response.status_code}")
        
        if response.status_code == 401:
            print("🔐 Authentication required - this is expected")
            print("   Set SBER_AUTH_TOKEN environment variable")
            return True
        elif response.status_code == 200:
            alerts = response.json()
            print(f"✅ Successfully fetched {len(alerts)} alerts")
            return True
        else:
            print(f"⚠️  Unexpected response code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Cannot reach SberDevices Alertmanager: {e}")
        return False

def main():
    print("🧪 Testing SberDevices Alertmanager Integration")
    print("=" * 50)
    
    seed_url = "http://localhost:8080"
    
    # Test 1: SEED Agent health
    print("\n1️⃣  Testing SEED Agent health...")
    seed_ok = test_seed_agent_health(seed_url)
    
    # Test 2: SberDevices Alertmanager access
    print("\n2️⃣  Testing SberDevices Alertmanager access...")
    sber_ok = test_sber_alertmanager_access()
    
    # Test 3: Mock alert delivery
    if seed_ok:
        print("\n3️⃣  Testing mock alert delivery...")
        mock_ok = test_mock_alert_to_seed(seed_url)
    else:
        print("\n3️⃣  Skipping mock alert test (SEED Agent not available)")
        mock_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"   SEED Agent:           {'✅ OK' if seed_ok else '❌ FAIL'}")
    print(f"   SberDevices Access:   {'✅ OK' if sber_ok else '❌ FAIL'}")
    print(f"   Mock Alert Delivery:  {'✅ OK' if mock_ok else '❌ FAIL'}")
    
    if seed_ok and sber_ok:
        print("\n🎉 Integration setup looks good!")
        print("   Run: ./run-sber-integration.sh")
    else:
        print("\n⚠️  Fix issues before running integration")

if __name__ == '__main__':
    main()