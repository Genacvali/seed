#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Enriched Zabbix webhook for SEED Agent v5
Proxies enriched JSON directly to /zabbix endpoint without modification
"""

import sys
import os
import json
import requests
from urllib.parse import urljoin

def proxy_to_seed(json_data: str, seed_url: str = None) -> int:
    """
    Proxy enriched Zabbix JSON directly to SEED Agent /zabbix endpoint
    
    Args:
        json_data: Enriched JSON string from Zabbix template
        seed_url: SEED Agent URL (from env var or arg)
    
    Returns:
        0 on success, 1 on failure
    """
    
    # Determine SEED URL
    if not seed_url:
        seed_url = os.environ.get('SEED_URL', 'http://localhost:8080/zabbix')
    
    # Parse JSON to validate format
    try:
        payload = json.loads(json_data)
        print(f"[INFO] Parsed JSON payload with {len(payload)} top-level keys")
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON: {e}")
        print(f"[DEBUG] Problematic JSON (first 500 chars): {repr(json_data[:500])}")
        print("\n[HINT] Common issues:")
        print("  1. JSON might be truncated by Zabbix")
        print("  2. Special characters not properly escaped")
        print("  3. Single quotes instead of double quotes")
        print("  4. Missing closing braces")
        print("\n[SUGGESTION] Try with a simple test JSON first:")
        print('{"event":{"value":"1"},"trigger":{"name":"Test"},"host":{"name":"test"}}')
        return 1
    
    # Ensure we have required fields
    required_sections = ['event', 'trigger', 'host']
    missing = [section for section in required_sections if section not in payload]
    if missing:
        print(f"[WARNING] Missing sections in JSON: {missing}")
    
    print(f"[DEBUG] Enriched payload preview:")
    print(f"  Event: {payload.get('event', {}).get('id', 'N/A')}")
    print(f"  Trigger: {payload.get('trigger', {}).get('name', 'N/A')}")
    print(f"  Host: {payload.get('host', {}).get('name', 'N/A')}")
    print(f"  Item key: {payload.get('item', {}).get('key', 'N/A')}")
    
    # Send to SEED Agent
    try:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Zabbix-Webhook-Enriched/1.0'
        }
        
        response = requests.post(
            seed_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        
        print(f"[SUCCESS] Alert sent to SEED Agent: {response.status_code}")
        if response.text:
            try:
                result = response.json()
                print(f"[RESPONSE] {result.get('status', 'Unknown status')}")
            except:
                print(f"[RESPONSE] {response.text[:100]}")
        
        return 0
        
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to send to SEED Agent: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


def main():
    """Main entry point for Zabbix webhook"""
    
    if len(sys.argv) < 2:
        print("Usage: python3 zabbix-webhook-enriched.py [<seed_url>] '<json_data>'")
        print("   or: SEED_URL='http://host:8080/zabbix' python3 zabbix-webhook-enriched.py '<json_data>'")
        print("\nExample with enriched template:")
        print('python3 zabbix-webhook-enriched.py \'{"event":{"id":"123","value":"1"},"trigger":{"name":"Test Alert","severity_text":"High"},"host":{"name":"testhost","ip":"192.168.1.1"}}\'')
        return 1
    
    # Handle both URL as first arg and JSON as second, or just JSON as first
    if len(sys.argv) >= 3:
        # URL provided as first argument
        seed_url = sys.argv[1]
        json_data = sys.argv[2]
    else:
        # Only JSON provided, use env var or default
        seed_url = None
        json_data = sys.argv[1]
    
    print(f"[INFO] SEED URL: {seed_url or os.environ.get('SEED_URL', 'http://localhost:8080/zabbix')}")
    print(f"[INFO] JSON data length: {len(json_data)} characters")
    print(f"[DEBUG] Raw JSON data: '{json_data[:200]}{'...' if len(json_data) > 200 else ''}'")
    
    # Additional validation
    if len(json_data) < 10:
        print(f"[ERROR] JSON data too short ({len(json_data)} chars). Expected enriched Zabbix JSON.")
        print("Check that Zabbix is passing the complete message template.")
        return 1
    
    if not json_data.strip():
        print("[ERROR] Empty JSON data received")
        return 1
    
    return proxy_to_seed(json_data, seed_url)


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)