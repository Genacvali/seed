#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Alert Sender - Command-line tool for sending test alerts to RabbitMQ.
Can send alerts directly to RabbitMQ or via HTTP webhook.
"""
import json
import sys
import argparse
import os
from datetime import datetime
from typing import Dict, Any
import pika
import requests
from dotenv import load_dotenv

load_dotenv("../seed.env")

# RabbitMQ Configuration
RABBIT_HOST = os.getenv("RABBIT_HOST", "127.0.0.1")
RABBIT_USER = os.getenv("RABBIT_USER", "seed")
RABBIT_PASS = os.getenv("RABBIT_PASS", "seedpass")
RABBIT_QUEUE = os.getenv("RABBIT_QUEUE", "seed-inbox")
RABBIT_VHOST = os.getenv("RABBIT_VHOST", "/")

# Webhook Configuration
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:8080/webhook/custom")

def send_to_rabbit_direct(alert: Dict[str, Any]) -> bool:
    """Send alert directly to RabbitMQ."""
    try:
        params = pika.ConnectionParameters(
            host=RABBIT_HOST,
            virtual_host=RABBIT_VHOST,
            credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASS),
            heartbeat=30
        )
        conn = pika.BlockingConnection(params)
        ch = conn.channel()
        ch.queue_declare(queue=RABBIT_QUEUE, durable=True)
        
        message = json.dumps(alert, ensure_ascii=False, indent=2)
        ch.basic_publish(
            exchange="",
            routing_key=RABBIT_QUEUE,
            body=message.encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        
        conn.close()
        print(f"✅ Alert sent directly to RabbitMQ: {alert['type']} @ {alert['host']}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send alert to RabbitMQ: {e}")
        return False

def send_to_webhook(alert: Dict[str, Any], webhook_url: str) -> bool:
    """Send alert via HTTP webhook."""
    try:
        response = requests.post(
            webhook_url,
            json=alert,
            timeout=10,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        print(f"✅ Alert sent via webhook: {alert['type']} @ {alert['host']}")
        print(f"Response: {response.json()}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send alert via webhook: {e}")
        return False

def create_test_alerts():
    """Generate various test alerts."""
    base_time = datetime.now().isoformat()
    
    return {
        "os_basic": {
            "type": "os_basic",
            "host": "centos-s-1vcpu-512mb-10gb-fra1-01",
            "timestamp": base_time,
            "severity": "info",
            "payload": {}
        },
        "host_inventory": {
            "type": "host_inventory", 
            "host": "centos-s-1vcpu-512mb-10gb-fra1-01",
            "timestamp": base_time,
            "severity": "info",
            "payload": {
                "paths": ["/", "/data"]
            }
        },
        "mongo_hotspots": {
            "type": "mongo_hotspots",
            "host": "centos-s-1vcpu-512mb-10gb-fra1-01",
            "timestamp": base_time,
            "severity": "warning",
            "payload": {
                "db": "seed_demo",
                "min_ms": 50,
                "limit": 10
            }
        },
        "high_load": {
            "type": "os_basic",
            "host": "centos-s-1vcpu-512mb-10gb-fra1-01", 
            "timestamp": base_time,
            "severity": "critical",
            "payload": {
                "trigger": "high_cpu_load",
                "value": 95.5,
                "threshold": 90
            }
        },
        "disk_space": {
            "type": "host_inventory",
            "host": "centos-s-1vcpu-512mb-10gb-fra1-01",
            "timestamp": base_time,
            "severity": "warning",
            "payload": {
                "paths": ["/"],
                "trigger": "low_disk_space", 
                "usage_percent": 85
            }
        }
    }

def main():
    parser = argparse.ArgumentParser(
        description="Send test alerts to SEED system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send OS basic check alert directly to RabbitMQ
  python send_alert.py --type os_basic --host myserver.com
  
  # Send test alert via webhook
  python send_alert.py --type os_basic --host myserver.com --webhook
  
  # Send predefined test alert
  python send_alert.py --preset mongo_hotspots
  
  # Send custom alert from JSON
  python send_alert.py --json '{"type":"custom","host":"test","payload":{}}'
  
  # List available presets
  python send_alert.py --list-presets
        """
    )
    
    parser.add_argument("--type", help="Alert type")
    parser.add_argument("--host", help="Target host")
    parser.add_argument("--severity", default="info", choices=["info", "warning", "critical"], help="Alert severity")
    parser.add_argument("--payload", help="JSON payload string")
    parser.add_argument("--preset", choices=["os_basic", "host_inventory", "mongo_hotspots", "high_load", "disk_space"], help="Use predefined test alert")
    parser.add_argument("--json", help="Send custom alert from JSON string")
    parser.add_argument("--webhook", action="store_true", help="Send via webhook instead of direct RabbitMQ")
    parser.add_argument("--webhook-url", default=WEBHOOK_URL, help="Webhook URL")
    parser.add_argument("--list-presets", action="store_true", help="List available preset alerts")
    
    args = parser.parse_args()
    
    if args.list_presets:
        print("Available preset alerts:")
        test_alerts = create_test_alerts()
        for name, alert in test_alerts.items():
            print(f"  {name}: {alert['type']} @ {alert['host']} ({alert['severity']})")
        return
    
    alert = None
    
    if args.preset:
        test_alerts = create_test_alerts()
        alert = test_alerts.get(args.preset)
        if not alert:
            print(f"❌ Unknown preset: {args.preset}")
            return
    
    elif args.json:
        try:
            alert = json.loads(args.json)
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return
    
    elif args.type and args.host:
        payload = {}
        if args.payload:
            try:
                payload = json.loads(args.payload)
            except json.JSONDecodeError as e:
                print(f"❌ Invalid payload JSON: {e}")
                return
        
        alert = {
            "type": args.type,
            "host": args.host,
            "timestamp": datetime.now().isoformat(),
            "severity": args.severity,
            "payload": payload
        }
    
    else:
        print("❌ Must specify either --preset, --json, or --type + --host")
        parser.print_help()
        return
    
    print(f"Sending alert: {json.dumps(alert, indent=2)}")
    print()
    
    if args.webhook:
        success = send_to_webhook(alert, args.webhook_url)
    else:
        success = send_to_rabbit_direct(alert)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()