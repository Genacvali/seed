#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus Integration Client for SEED Agent v6
Handles querying Prometheus for metrics and alert context
"""

import requests
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class PrometheusClient:
    """Client for querying Prometheus API"""
    
    def __init__(self, base_url: str, username: str = None, password: str = None,
                 verify_ssl: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        if username and password:
            self.session.auth = (username, password)
    
    def query(self, query: str, time: str = None) -> Dict[str, Any]:
        """
        Execute an instant query
        
        Args:
            query: PromQL query string
            time: Evaluation timestamp (RFC3339 or Unix timestamp)
        """
        try:
            url = f"{self.base_url}/api/v1/query"
            params = {'query': query}
            
            if time:
                params['time'] = time
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus query failed: {e}")
            raise
    
    def query_range(self, query: str, start: str, end: str, step: str = "15s") -> Dict[str, Any]:
        """
        Execute a range query
        
        Args:
            query: PromQL query string
            start: Start time (RFC3339 or Unix timestamp)
            end: End time (RFC3339 or Unix timestamp)
            step: Query resolution step
        """
        try:
            url = f"{self.base_url}/api/v1/query_range"
            params = {
                'query': query,
                'start': start,
                'end': end,
                'step': step
            }
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus range query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus range query failed: {e}")
            raise
    
    def get_series(self, match: List[str], start: str = None, end: str = None) -> Dict[str, Any]:
        """
        Get time series that match label selectors
        
        Args:
            match: List of series selectors (e.g., ['up', 'process_start_time_seconds{job="prometheus"}'])
            start: Start time
            end: End time
        """
        try:
            url = f"{self.base_url}/api/v1/series"
            params = {'match[]': match}
            
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus series query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus series query failed: {e}")
            raise
    
    def get_label_names(self, start: str = None, end: str = None) -> List[str]:
        """Get list of label names"""
        try:
            url = f"{self.base_url}/api/v1/labels"
            params = {}
            
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus labels query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus labels query failed: {e}")
            raise
    
    def get_label_values(self, label_name: str, start: str = None, end: str = None) -> List[str]:
        """Get list of label values for a specific label"""
        try:
            url = f"{self.base_url}/api/v1/label/{label_name}/values"
            params = {}
            
            if start:
                params['start'] = start
            if end:
                params['end'] = end
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus label values query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus label values query failed: {e}")
            raise
    
    def health_check(self) -> bool:
        """Check if Prometheus is healthy"""
        try:
            url = f"{self.base_url}/-/healthy"
            response = self.session.get(url, timeout=10)
            return response.status_code == 200
            
        except requests.exceptions.RequestException:
            return False
    
    def get_config(self) -> Dict[str, Any]:
        """Get Prometheus configuration"""
        try:
            url = f"{self.base_url}/api/v1/status/config"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus config query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus config query failed: {e}")
            raise
    
    def get_targets(self) -> Dict[str, Any]:
        """Get list of discovered targets"""
        try:
            url = f"{self.base_url}/api/v1/targets"
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') != 'success':
                raise Exception(f"Prometheus targets query failed: {result.get('error', 'Unknown error')}")
            
            return result.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Prometheus targets query failed: {e}")
            raise

class PrometheusQueryHelper:
    """Helper class for common Prometheus queries related to alerts"""
    
    def __init__(self, client: PrometheusClient, default_range: str = "5m"):
        self.client = client
        self.default_range = default_range
    
    def get_instance_metrics(self, instance: str, time_range: str = None) -> Dict[str, Any]:
        """Get common metrics for a specific instance"""
        if not time_range:
            time_range = self.default_range
        
        queries = {
            'cpu_usage': f'100 - (avg by (instance) (irate(node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[{time_range}])) * 100)',
            'memory_usage': f'(1 - (node_memory_MemAvailable_bytes{{instance="{instance}"}} / node_memory_MemTotal_bytes{{instance="{instance}"}}) * 100)',
            'disk_usage': f'100 - ((node_filesystem_avail_bytes{{instance="{instance}",mountpoint="/"}} * 100) / node_filesystem_size_bytes{{instance="{instance}",mountpoint="/"}})',
            'load_average': f'node_load1{{instance="{instance}"}}',
            'network_in': f'irate(node_network_receive_bytes_total{{instance="{instance}",device!~"lo|veth.*|docker.*|virbr.*|br-.*"}}[{time_range}])',
            'network_out': f'irate(node_network_transmit_bytes_total{{instance="{instance}",device!~"lo|veth.*|docker.*|virbr.*|br-.*"}}[{time_range}])'
        }
        
        results = {}
        for name, query in queries.items():
            try:
                result = self.client.query(query)
                results[name] = result
            except Exception as e:
                logger.warning(f"Failed to query {name} for instance {instance}: {e}")
                results[name] = None
        
        return results
    
    def get_service_metrics(self, job: str, service: str = None, time_range: str = None) -> Dict[str, Any]:
        """Get metrics for a specific service/job"""
        if not time_range:
            time_range = self.default_range
        
        job_selector = f'job="{job}"'
        if service:
            job_selector += f',service="{service}"'
        
        queries = {
            'up_instances': f'up{{{job_selector}}}',
            'request_rate': f'sum(rate(http_requests_total{{{job_selector}}}[{time_range}]))',
            'error_rate': f'sum(rate(http_requests_total{{{job_selector},code=~"5.."}}[{time_range}]))',
            'response_time': f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{{job_selector}}}[{time_range}])) by (le))'
        }
        
        results = {}
        for name, query in queries.items():
            try:
                result = self.client.query(query)
                results[name] = result
            except Exception as e:
                logger.warning(f"Failed to query {name} for job {job}: {e}")
                results[name] = None
        
        return results
    
    def get_alert_context(self, labels: Dict[str, str], time_range: str = None) -> Dict[str, Any]:
        """Get contextual metrics for an alert based on its labels"""
        if not time_range:
            time_range = self.default_range
        
        context = {}
        
        # Instance-specific context
        if 'instance' in labels:
            instance = labels['instance']
            context['instance_metrics'] = self.get_instance_metrics(instance, time_range)
        
        # Job/service-specific context
        if 'job' in labels:
            job = labels['job']
            service = labels.get('service')
            context['service_metrics'] = self.get_service_metrics(job, service, time_range)
        
        # Database-specific queries
        if 'job' in labels and 'postgres' in labels['job'].lower():
            context['database_metrics'] = self._get_postgres_metrics(labels, time_range)
        
        if 'job' in labels and 'mongo' in labels['job'].lower():
            context['database_metrics'] = self._get_mongodb_metrics(labels, time_range)
        
        return context
    
    def _get_postgres_metrics(self, labels: Dict[str, str], time_range: str) -> Dict[str, Any]:
        """Get PostgreSQL-specific metrics"""
        instance = labels.get('instance', '')
        
        queries = {
            'connections': f'pg_stat_database_numbackends{{instance="{instance}"}}',
            'slow_queries': f'rate(pg_stat_database_tup_fetched{{instance="{instance}"}}[{time_range}])',
            'locks': f'pg_locks_count{{instance="{instance}"}}',
            'replication_lag': f'pg_replication_lag{{instance="{instance}"}}'
        }
        
        results = {}
        for name, query in queries.items():
            try:
                result = self.client.query(query)
                results[name] = result
            except Exception as e:
                logger.warning(f"Failed to query PostgreSQL {name}: {e}")
                results[name] = None
        
        return results
    
    def _get_mongodb_metrics(self, labels: Dict[str, str], time_range: str) -> Dict[str, Any]:
        """Get MongoDB-specific metrics"""
        instance = labels.get('instance', '')
        
        queries = {
            'connections': f'mongodb_connections{{instance="{instance}",state="current"}}',
            'operations': f'rate(mongodb_op_counters_total{{instance="{instance}"}}[{time_range}])',
            'memory': f'mongodb_memory{{instance="{instance}",type="resident"}}',
            'replication_lag': f'mongodb_replset_member_replication_lag{{instance="{instance}"}}'
        }
        
        results = {}
        for name, query in queries.items():
            try:
                result = self.client.query(query)
                results[name] = result
            except Exception as e:
                logger.warning(f"Failed to query MongoDB {name}: {e}")
                results[name] = None
        
        return results