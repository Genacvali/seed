#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SberDevices Alertmanager Integration Script
API: https://alertmanager.sberdevices.ru/api/v2/alerts

Fetches active alerts from SberDevices Alertmanager and forwards them to SEED Agent
"""

import requests
import json
import time
import os
from typing import List, Dict, Any
from datetime import datetime

class SberAlertmanagerClient:
    def __init__(self, alertmanager_url: str, seed_agent_url: str, auth_token: str = None):
        self.alertmanager_url = alertmanager_url.rstrip('/')
        self.seed_agent_url = seed_agent_url.rstrip('/')
        self.auth_token = auth_token
        
        self.session = requests.Session()
        if auth_token:
            self.session.headers.update({'Authorization': f'Bearer {auth_token}'})
    
    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Fetch active alerts from SberDevices Alertmanager"""
        try:
            url = f"{self.alertmanager_url}/api/v2/alerts"
            params = {'filter': 'state="active"'}
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            alerts = response.json()
            print(f"✅ Fetched {len(alerts)} active alerts from SberDevices Alertmanager")
            return alerts
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to fetch alerts from Alertmanager: {e}")
            return []
    
    def convert_to_seed_format(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Alertmanager alerts to SEED Agent format"""
        seed_alerts = []
        
        for alert in alerts:
            # Extract alert data
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            
            seed_alert = {
                'labels': {
                    'alertname': labels.get('alertname', 'unknown'),
                    'instance': labels.get('instance', labels.get('hostname', 'unknown')),
                    'severity': labels.get('severity', 'warning'),
                    'job': labels.get('job', ''),
                    'service': labels.get('service', ''),
                    'team': labels.get('team', ''),
                    'environment': labels.get('environment', 'production')
                },
                'annotations': {
                    'summary': annotations.get('summary', 'SberDevices Alert'),
                    'description': annotations.get('description', ''),
                    'runbook_url': annotations.get('runbook_url', ''),
                    'dashboard_url': annotations.get('dashboard_url', ''),
                    'source': 'sberdevices-alertmanager'
                },
                'status': 'firing',  # Active alerts are always firing
                'startsAt': alert.get('startsAt', datetime.utcnow().isoformat() + 'Z'),
                'endsAt': alert.get('endsAt', ''),
                'generatorURL': alert.get('generatorURL', '')
            }
            
            # Add all original labels for context
            for key, value in labels.items():
                if key not in seed_alert['labels']:
                    seed_alert['labels'][key] = value
            
            seed_alerts.append(seed_alert)
        
        return {'alerts': seed_alerts}
    
    def send_to_seed_agent(self, alert_data: Dict[str, Any]) -> bool:
        """Send alerts to SEED Agent"""
        try:
            # Try v5 endpoint first
            url = f"{self.seed_agent_url}/alert"
            response = self.session.post(url, json=alert_data, timeout=30)
            
            if response.status_code == 404:
                # Try v6 endpoint
                url = f"{self.seed_agent_url}/alertmanager"
                response = self.session.post(url, json=alert_data, timeout=30)
            
            response.raise_for_status()
            print(f"✅ Sent {len(alert_data['alerts'])} alerts to SEED Agent")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send alerts to SEED Agent: {e}")
            return False
    
    def sync_alerts(self):
        """Fetch alerts from Alertmanager and forward to SEED Agent"""
        print(f"🔄 Syncing alerts from {self.alertmanager_url}")
        
        # Fetch active alerts
        alerts = self.get_active_alerts()
        if not alerts:
            print("ℹ️  No active alerts found")
            return
        
        # Convert to SEED format
        seed_data = self.convert_to_seed_format(alerts)
        
        # Send to SEED Agent
        success = self.send_to_seed_agent(seed_data)
        
        if success:
            print(f"🎉 Successfully processed {len(alerts)} alerts")
        else:
            print("❌ Failed to process alerts")

def main():
    # Configuration from environment variables
    ALERTMANAGER_URL = os.getenv('SBER_ALERTMANAGER_URL', 'https://alertmanager.sberdevices.ru')
    SEED_AGENT_URL = os.getenv('SEED_AGENT_URL', 'http://localhost:8080')
    AUTH_TOKEN = os.getenv('SBER_AUTH_TOKEN')  # Optional
    SYNC_INTERVAL = int(os.getenv('SYNC_INTERVAL', '60'))  # seconds
    
    client = SberAlertmanagerClient(ALERTMANAGER_URL, SEED_AGENT_URL, AUTH_TOKEN)
    
    print(f"🚀 Starting SberDevices Alertmanager integration")
    print(f"📡 Alertmanager: {ALERTMANAGER_URL}")
    print(f"🎯 SEED Agent: {SEED_AGENT_URL}")
    print(f"⏱️  Sync interval: {SYNC_INTERVAL}s")
    print("─" * 50)
    
    # One-time sync if run directly
    if len(os.sys.argv) > 1 and os.sys.argv[1] == '--once':
        client.sync_alerts()
        return
    
    # Continuous sync
    try:
        while True:
            client.sync_alerts()
            print(f"😴 Sleeping for {SYNC_INTERVAL} seconds...")
            time.sleep(SYNC_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n👋 Stopped by user")

if __name__ == '__main__':
    main()