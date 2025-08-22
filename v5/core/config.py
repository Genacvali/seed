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
                    raw_config = yaml.safe_load(f) or {}
                # Apply environment variable interpolation
                self._config = self._interpolate_env_vars(raw_config)
            else:
                logging.warning(f"Configuration file not found: {self.config_path}")
                self._config = {}
        except Exception as e:
            logging.error(f"Failed to load configuration: {e}")
            self._config = {}
    
    def _interpolate_env_vars(self, config: Any) -> Any:
        """Recursively interpolate environment variables in config
        
        Supports syntax: ${VARIABLE_NAME:default_value}
        """
        if isinstance(config, dict):
            return {key: self._interpolate_env_vars(value) for key, value in config.items()}
        elif isinstance(config, list):
            return [self._interpolate_env_vars(item) for item in config]
        elif isinstance(config, str):
            return self._interpolate_string(config)
        else:
            return config
    
    def _interpolate_string(self, value: str) -> str:
        """Interpolate environment variables in a string"""
        import re
        import os
        
        def replace_var(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default = var_expr.split(':', 1)
            else:
                var_name, default = var_expr, ""
            
            # Get environment variable value
            env_value = os.getenv(var_name)
            return env_value if env_value is not None else default
        
        # Pattern: ${VARIABLE_NAME:default}
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_var, value)
    
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
        port = self.get("system.agent.bind_port", 8080)
        return int(port) if isinstance(port, str) and port.isdigit() else port
    
    @property
    def debug(self) -> bool:
        debug_val = self.get("system.agent.debug", False)
        if isinstance(debug_val, str):
            return debug_val.lower() in ["true", "1", "yes", "on"]
        return bool(debug_val) or os.getenv("DEBUG", "").lower() == "true"
    
    @property
    def alert_ttl(self) -> int:
        ttl = self.get("system.alerts.ttl_seconds", 30)
        return int(ttl) if isinstance(ttl, str) and ttl.isdigit() else ttl
    
    @property
    def max_retries(self) -> int:
        retries = self.get("system.alerts.max_retries", 3)
        return int(retries) if isinstance(retries, str) and retries.isdigit() else retries
    
    @property
    def retry_delay(self) -> int:
        delay = self.get("system.alerts.retry_delay", 10)
        return int(delay) if isinstance(delay, str) and delay.isdigit() else delay
    
    # Infrastructure configuration
    @property
    def rabbitmq_config(self) -> Dict[str, Any]:
        config = self.get("infrastructure.rabbitmq", {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "vhost": "/"
        })
        
        # Ensure port is integer
        if "port" in config and isinstance(config["port"], str):
            config["port"] = int(config["port"])
        
        return config
    
    @property
    def redis_config(self) -> Dict[str, Any]:
        config = self.get("infrastructure.redis", {
            "host": "localhost",
            "port": 6379,
            "db": 0,
            "password": None
        })
        
        # Ensure port and db are integers
        if "port" in config and isinstance(config["port"], str):
            config["port"] = int(config["port"])
        if "db" in config and isinstance(config["db"], str):
            config["db"] = int(config["db"])
        
        return config
    
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
    
    def get_mongodb_connection_string(self, group_name: Optional[str] = None) -> Optional[str]:
        """Build MongoDB connection string for a group"""
        if not group_name:
            return None
            
        host_config = self.get_host_config_for_group(group_name)
        if not host_config:
            return None
        
        host = host_config.get("mongo_host")
        port = host_config.get("mongo_port", 27017)
        username = host_config.get("username")
        password = host_config.get("password")
        auth_db = host_config.get("auth_db", "admin")
        
        if not host:
            return None
        
        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}/{auth_db}"
        else:
            return f"mongodb://{host}:{port}/"
    
    def get_host_config_for_group(self, group_name: str) -> Dict[str, Any]:
        """Get configuration for a specific host group"""
        groups = self.get("hosts.groups", {})
        if group_name in groups:
            return groups[group_name].get("overrides", {})
        return {}
    
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