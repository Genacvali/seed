#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Direct test of Mattermost notifications without RabbitMQ
"""
import json
from core.agent import _on_alert
from core.notifier import send_mm

def test_direct_notification():
    """Test direct Mattermost notification"""
    print("=== Direct MM Test ===")
    send_mm("SEED: 🧪 Прямое тестовое сообщение")

def test_alert_processing():
    """Test alert processing that should send MM notification"""
    print("=== Alert Processing Test ===")
    
    # Test message that should trigger a "no handler" response
    test_alert = {
        "type": "unknown_type",
        "host": "test-host",
        "timestamp": "2025-08-16T10:00:00",
        "severity": "info",
        "payload": {}
    }
    
    message_bytes = json.dumps(test_alert).encode("utf-8")
    _on_alert(message_bytes)

if __name__ == "__main__":
    test_direct_notification()
    test_alert_processing()