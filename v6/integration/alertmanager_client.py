#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alertmanager Integration Client for SEED Agent v6
Handles fetching alerts from Alertmanager and processing them
"""

import requests
import json
import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AlertmanagerClient:
    """Client for interacting with Alertmanager API"""
    
    def __init__(self, base_url: str, api_path: str = "/api/v2", auth_token: str = None, 
                 verify_ssl: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_path = api_path.strip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        if auth_token:
            self.session.headers.update({'Authorization': f'Bearer {auth_token}'})
    
    def get_alerts(self, active_only: bool = True, receiver: str = None, 
                   silenced: bool = None, inhibited: bool = None) -> List[Dict[str, Any]]:
        """
        Fetch alerts from Alertmanager
        
        Args:
            active_only: Only return active alerts
            receiver: Filter by receiver name
            silenced: Filter silenced/unsilenced alerts
            inhibited: Filter inhibited/uninhibited alerts
        """
        try:
            url = f"{self.base_url}/{self.api_path}/alerts"
            params = {}
            
            # Build filter parameters
            filters = []
            if active_only:
                filters.append('state="active"')
            if receiver:
                filters.append(f'receiver="{receiver}"')
            if silenced is not None:
                filters.append(f'silenced={str(silenced).lower()}')
            if inhibited is not None:
                filters.append(f'inhibited={str(inhibited).lower()}')
            
            if filters:
                params['filter'] = filters
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            alerts = response.json()
            logger.info(f"Fetched {len(alerts)} alerts from Alertmanager")
            return alerts
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch alerts from Alertmanager: {e}")
            return []
    
    def get_alert_groups(self) -> List[Dict[str, Any]]:
        """Fetch alert groups from Alertmanager"""
        try:
            url = f"{self.base_url}/{self.api_path}/alerts/groups"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            groups = response.json()
            logger.info(f"Fetched {len(groups)} alert groups from Alertmanager")
            return groups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch alert groups: {e}")
            return []
    
    def get_silences(self) -> List[Dict[str, Any]]:
        """Fetch active silences"""
        try:
            url = f"{self.base_url}/{self.api_path}/silences"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            silences = response.json()
            logger.info(f"Fetched {len(silences)} silences from Alertmanager")
            return silences
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch silences: {e}")
            return []
    
    def create_silence(self, matchers: List[Dict[str, str]], duration_hours: int = 1,
                      created_by: str = "seed-agent", comment: str = "Auto-created by SEED") -> bool:
        """
        Create a new silence
        
        Args:
            matchers: List of label matchers [{"name": "alertname", "value": "TestAlert", "isRegex": False}]
            duration_hours: Duration in hours
            created_by: Who created the silence
            comment: Comment for the silence
        """
        try:
            url = f"{self.base_url}/{self.api_path}/silences"
            
            starts_at = datetime.utcnow()
            ends_at = starts_at + timedelta(hours=duration_hours)
            
            silence_data = {
                "matchers": matchers,
                "startsAt": starts_at.isoformat() + "Z",
                "endsAt": ends_at.isoformat() + "Z",
                "createdBy": created_by,
                "comment": comment
            }
            
            response = self.session.post(url, json=silence_data, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            silence_id = result.get('silenceID', 'unknown')
            logger.info(f"Created silence {silence_id} for {duration_hours}h")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create silence: {e}")
            return False
    
    def delete_silence(self, silence_id: str) -> bool:
        """Delete a silence by ID"""
        try:
            url = f"{self.base_url}/{self.api_path}/silence/{silence_id}"
            response = self.session.delete(url, timeout=self.timeout)
            response.raise_for_status()
            
            logger.info(f"Deleted silence {silence_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete silence {silence_id}: {e}")
            return False
    
    def convert_to_seed_format(self, alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert Alertmanager alerts to SEED Agent format"""
        seed_alerts = []
        
        for alert in alerts:
            labels = alert.get('labels', {})
            annotations = alert.get('annotations', {})
            
            # Map Alertmanager status to SEED format
            status = alert.get('status', {})
            alert_state = status.get('state', 'active')
            seed_status = 'firing' if alert_state == 'active' else 'resolved'
            
            seed_alert = {
                'labels': {
                    'alertname': labels.get('alertname', 'UnknownAlert'),
                    'instance': labels.get('instance', labels.get('hostname', 'unknown')),
                    'severity': labels.get('severity', 'warning'),
                    'job': labels.get('job', ''),
                    'service': labels.get('service', ''),
                    'team': labels.get('team', ''),
                    'environment': labels.get('environment', 'production')
                },
                'annotations': {
                    'summary': annotations.get('summary', 'Alert from Alertmanager'),
                    'description': annotations.get('description', ''),
                    'runbook_url': annotations.get('runbook_url', ''),
                    'dashboard_url': annotations.get('dashboard_url', ''),
                    'source': 'alertmanager'
                },
                'status': seed_status,
                'startsAt': alert.get('startsAt', datetime.utcnow().isoformat() + 'Z'),
                'endsAt': alert.get('endsAt', ''),
                'generatorURL': alert.get('generatorURL', ''),
                'fingerprint': alert.get('fingerprint', '')
            }
            
            # Preserve all original labels and annotations
            for key, value in labels.items():
                if key not in seed_alert['labels']:
                    seed_alert['labels'][key] = value
                    
            for key, value in annotations.items():
                if key not in seed_alert['annotations']:
                    seed_alert['annotations'][key] = value
            
            seed_alerts.append(seed_alert)
        
        return {'alerts': seed_alerts}
    
    def health_check(self) -> bool:
        """Check if Alertmanager is healthy"""
        try:
            url = f"{self.base_url}/{self.api_path}/status"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            status = response.json()
            logger.info(f"Alertmanager health: {status}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Alertmanager health check failed: {e}")
            return False

class AlertmanagerPoller:
    """Polls Alertmanager for alerts and sends them to SEED Agent"""
    
    def __init__(self, alertmanager_client: AlertmanagerClient, seed_agent_url: str,
                 poll_interval: int = 60):
        self.client = alertmanager_client
        self.seed_agent_url = seed_agent_url.rstrip('/')
        self.poll_interval = poll_interval
        self.session = requests.Session()
        self.running = False
    
    def send_to_seed(self, alert_data: Dict[str, Any]) -> bool:
        """Send alerts to SEED Agent"""
        try:
            url = f"{self.seed_agent_url}/alertmanager"
            response = self.session.post(url, json=alert_data, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Sent {len(alert_data['alerts'])} alerts to SEED Agent")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send alerts to SEED Agent: {e}")
            return False
    
    def poll_once(self) -> bool:
        """Perform one polling cycle"""
        try:
            # Fetch active alerts
            alerts = self.client.get_alerts(active_only=True)
            if not alerts:
                logger.info("No active alerts found")
                return True
            
            # Convert to SEED format
            seed_data = self.client.convert_to_seed_format(alerts)
            
            # Send to SEED Agent
            return self.send_to_seed(seed_data)
            
        except Exception as e:
            logger.error(f"Error during polling cycle: {e}")
            return False
    
    def start_polling(self):
        """Start continuous polling"""
        self.running = True
        logger.info(f"Starting Alertmanager polling (interval: {self.poll_interval}s)")
        
        while self.running:
            try:
                self.poll_once()
                time.sleep(self.poll_interval)
                
            except KeyboardInterrupt:
                logger.info("Polling stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in polling loop: {e}")
                time.sleep(10)  # Wait before retrying
    
    def stop_polling(self):
        """Stop continuous polling"""
        self.running = False
        logger.info("Polling stopped")