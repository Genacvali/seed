# -*- coding: utf-8 -*-
"""
SEED Agent Configuration Management
Unified configuration system for the new architecture
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv


class Config:
    """Unified configuration manager for SEED Agent"""
    
    def __init__(self, config_path: str = "seed.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load_config()
        
        # Load environment variables
        env_path = self.config_path.parent / "seed.env"
        if env_path.exists():
            load_dotenv(env_path.as_posix())
    
    def load_config(self) -> None:
        """Load configuration from YAML file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            else:
                logging.warning(f"Configuration file not found: {self.config_path}")
                self._config = {}
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            self._config = {}
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self.load_config()
        logging.info("Configuration reloaded successfully")
    
    def get(self, path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    # System configuration properties
    @property
    def bind_host(self) -> str:
        return self.get("system.agent.bind_host", "0.0.0.0")
    
    @property
    def bind_port(self) -> int:
        return self.get("system.agent.bind_port", 8080)
    
    @property
    def debug(self) -> bool:
        return self.get("system.agent.debug", False) or os.getenv("DEBUG", "").lower() == "true"
    
    @property
    def alert_ttl(self) -> int:
        return self.get("system.alerts.ttl_seconds", 30)
    
    @property
    def max_retries(self) -> int:
        return self.get("system.alerts.max_retries", 3)
    
    @property
    def retry_delay(self) -> int:
        return self.get("system.alerts.retry_delay", 10)
    
    # Infrastructure configuration
    @property
    def rabbitmq_config(self) -> Dict[str, Any]:
        return self.get("infrastructure.rabbitmq", {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "vhost": "/"
        })
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        return self.get("infrastructure.redis", {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None
        })
    
    @property
    def queue_config(self) -> Dict[str, str]:
        return self.get("infrastructure.rabbitmq.queues", {
            "alerts": "seed.alerts",
            "retry": "seed.alerts.retry",
            "dlq": "seed.alerts.dlq"
        })
    
    # Notification configuration
    @property
    def notification_config(self) -> Dict[str, Any]:
        return self.get("notifications", {})
    
    # Alert routing
    def get_alert_route(self, alertname: str, labels: Dict[str, str]) -> Dict[str, Any]:
        """Get alert routing configuration"""
        routes = self.get("routing.alerts", {})
        route = routes.get(alertname)
        
        if not route:
            return {}
        
        # Copy and substitute labels in payload
        import copy
        payload = copy.deepcopy(route.get("payload", {}))
        
        # Simple label substitution
        for key, value in list(payload.items()):
            if isinstance(value, str):
                try:
                    payload[key] = value.format(**labels)
                except KeyError:
                    pass  # Skip if label not found
        
        return {
            "plugin": route["plugin"],
            "payload": payload
        }
    
    def get_host_config(self, hostname: str) -> Dict[str, Any]:
        """Get host-specific configuration"""
        # Check individual host overrides
        individual = self.get("hosts.individual", {})
        if hostname in individual:
            return individual[hostname]
        
        # Check group-based configuration
        groups = self.get("hosts.groups", {})
        for group_name, group_config in groups.items():
            hosts = group_config.get("hosts", [])
            if hostname in hosts:
                return group_config.get("overrides", {})
        
        return {}
    
    def enrich_payload_with_host_config(self, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich payload with host-specific configuration"""
        host_config = self.get_host_config(hostname)
        
        if host_config:
            payload = dict(payload)
            
            # Apply host-specific overrides
            for key, value in host_config.items():
                if isinstance(value, str) and "{}" in value:
                    # Substitute hostname in URLs like "http://{}:9216/metrics"
                    payload[key] = value.format(hostname)
                else:
                    payload[key] = value
        
        return payload
    
    # Default Telegraf URL generation
    def get_telegraf_url(self, hostname: str) -> str:
        """Get Telegraf URL for host"""
        host_config = self.get_host_config(hostname)
        
        if "telegraf_url" in host_config:
            url = host_config["telegraf_url"]
            return url.format(hostname) if "{}" in url else url
        
        # Use system defaults
        telegraf = self.get("infrastructure.telegraf", {})
        scheme = telegraf.get("scheme", "http")
        port = telegraf.get("port", 9216)
        endpoint = telegraf.get("endpoint", "/metrics")
        
        return f"{scheme}://{hostname}:{port}{endpoint}"
    
    # Plugin configuration
    def get_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Get plugin-specific configuration"""
        return self.get(f"plugins.{plugin_name}", {})
    
    # Logging configuration
    @property
    def log_level(self) -> str:
        return os.getenv("LOG_LEVEL", self.get("logging.level", "INFO"))
    
    @property
    def log_format(self) -> str:
        return self.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Health check configuration
    @property
    def health_config(self) -> Dict[str, Any]:
        return self.get("health", {"enabled": True, "interval": 60})
    
    # Metrics configuration
    @property
    def metrics_enabled(self) -> bool:
        return self.get("metrics.enabled", True)
    
    @property
    def prometheus_config(self) -> Dict[str, Any]:
        return self.get("metrics.prometheus", {"enabled": True, "path": "/metrics"})