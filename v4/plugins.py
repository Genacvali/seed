# -*- coding: utf-8 -*-
"""
SEED Agent v4 - Unified Plugin System

This module provides a centralized plugin system with proper configuration management.
All plugins use the unified Config system for consistent configuration loading.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# Import fetchers and config
from fetchers.telegraf import TelegrafFetcher
from fetchers.mongo import MongoFetcher
from core.config import Config

logger = logging.getLogger(__name__)


class Plugin:
    """Base class for all SEED plugins"""
    
    def __init__(self, config: Config):
        self.config = config
        self.plugin_config = config.get_plugin_config(self.plugin_name)
    
    @property
    def plugin_name(self) -> str:
        """Override in subclasses"""
        return "base"
    
    async def execute(self, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute plugin logic - override in subclasses"""
        raise NotImplementedError("Subclasses must implement execute()")
    
    def enrich_payload(self, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich payload with host-specific configuration"""
        return self.config.enrich_payload_with_host_config(hostname, payload)


class HostInventoryPlugin(Plugin):
    """Host inventory plugin using Telegraf metrics"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.telegraf_fetcher = TelegrafFetcher(config)
    
    @property
    def plugin_name(self) -> str:
        return "host_inventory"
    
    async def execute(self, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute host inventory collection"""
        start_time = time.time()
        
        try:
            # Enrich payload with host config
            enriched_payload = self.enrich_payload(hostname, payload)
            
            # Get Telegraf URL
            telegraf_url = enriched_payload.get("telegraf_url") or self.config.get_telegraf_url(hostname)
            timeout = enriched_payload.get("timeout", self.plugin_config.get("default_timeout", 30))
            
            logger.info(f"Collecting host inventory for {hostname} from {telegraf_url}")
            
            # Fetch metrics from Telegraf
            metrics = await self.telegraf_fetcher.fetch_metrics(telegraf_url, timeout)
            
            if not metrics:
                return {
                    "success": False,
                    "error": "No metrics received from Telegraf",
                    "execution_time": time.time() - start_time
                }
            
            # Process metrics based on alert type
            alert_type = payload.get("alert_type", "general")
            processed_data = self._process_metrics(metrics, alert_type, enriched_payload)
            
            return {
                "success": True,
                "hostname": hostname,
                "alert_type": alert_type,
                "data": processed_data,
                "metrics_count": len(metrics),
                "execution_time": time.time() - start_time,
                "telegraf_url": telegraf_url
            }
            
        except Exception as e:
            logger.error(f"Host inventory plugin failed for {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "hostname": hostname,
                "execution_time": time.time() - start_time
            }
    
    def _process_metrics(self, metrics: List[Dict[str, Any]], alert_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process Telegraf metrics based on alert type"""
        
        if alert_type in ["disk_space", "disk_critical"]:
            return self._process_disk_metrics(metrics, payload)
        elif alert_type == "cpu_load":
            return self._process_cpu_metrics(metrics, payload)
        elif alert_type == "memory":
            return self._process_memory_metrics(metrics, payload)
        else:
            return self._process_general_metrics(metrics, payload)
    
    def _process_disk_metrics(self, metrics: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process disk space metrics"""
        paths = payload.get("paths", ["/"])
        disk_info = []
        
        for metric in metrics:
            if metric.get("name") == "disk" and "path" in metric.get("tags", {}):
                path = metric["tags"]["path"]
                if path in paths:
                    fields = metric.get("fields", {})
                    disk_info.append({
                        "path": path,
                        "used_percent": fields.get("used_percent", 0),
                        "free": fields.get("free", 0),
                        "total": fields.get("total", 0),
                        "used": fields.get("used", 0)
                    })
        
        return {
            "disk_usage": disk_info,
            "paths_checked": paths,
            "critical_threshold": 90,
            "warning_threshold": 80
        }
    
    def _process_cpu_metrics(self, metrics: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process CPU metrics"""
        cpu_info = {}
        
        for metric in metrics:
            if metric.get("name") == "cpu":
                fields = metric.get("fields", {})
                cpu_info.update({
                    "usage_idle": fields.get("usage_idle", 0),
                    "usage_system": fields.get("usage_system", 0),
                    "usage_user": fields.get("usage_user", 0),
                    "usage_iowait": fields.get("usage_iowait", 0)
                })
            elif metric.get("name") == "system":
                fields = metric.get("fields", {})
                cpu_info.update({
                    "load1": fields.get("load1", 0),
                    "load5": fields.get("load5", 0),
                    "load15": fields.get("load15", 0)
                })
        
        return {
            "cpu_metrics": cpu_info,
            "cpu_usage_percent": 100 - cpu_info.get("usage_idle", 100)
        }
    
    def _process_memory_metrics(self, metrics: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process memory metrics"""
        memory_info = {}
        
        for metric in metrics:
            if metric.get("name") == "mem":
                fields = metric.get("fields", {})
                memory_info.update({
                    "total": fields.get("total", 0),
                    "available": fields.get("available", 0),
                    "used": fields.get("used", 0),
                    "used_percent": fields.get("used_percent", 0),
                    "free": fields.get("free", 0)
                })
        
        return {
            "memory_metrics": memory_info,
            "memory_usage_gb": memory_info.get("used", 0) / (1024**3),
            "memory_total_gb": memory_info.get("total", 0) / (1024**3)
        }
    
    def _process_general_metrics(self, metrics: List[Dict[str, Any]], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process general system metrics"""
        return {
            "metrics_summary": {
                "total_metrics": len(metrics),
                "metric_types": list(set(m.get("name", "unknown") for m in metrics)),
                "collection_time": datetime.now(timezone.utc).isoformat()
            },
            "raw_metrics": metrics[:10]  # First 10 metrics for debugging
        }


class MongoHotPlugin(Plugin):
    """MongoDB hotspot analysis plugin"""
    
    def __init__(self, config: Config):
        super().__init__(config)
        self.mongo_fetcher = MongoFetcher(config)
    
    @property
    def plugin_name(self) -> str:
        return "mongo_hot"
    
    async def execute(self, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MongoDB hotspot analysis"""
        start_time = time.time()
        
        try:
            # Enrich payload with host config
            enriched_payload = self.enrich_payload(hostname, payload)
            
            # Get MongoDB connection details from host group config
            connection_string = self.config.get_mongodb_connection_string(
                self._get_host_group(hostname)
            )
            
            if not connection_string:
                return {
                    "success": False,
                    "error": f"No MongoDB configuration found for host {hostname}",
                    "execution_time": time.time() - start_time
                }
            
            # Extract parameters
            min_ms = enriched_payload.get("min_ms", self.plugin_config.get("default_min_ms", 50))
            limit = enriched_payload.get("limit", self.plugin_config.get("default_limit", 10))
            timeout = enriched_payload.get("timeout", 30)
            
            logger.info(f"Analyzing MongoDB hotspots for {hostname}, min_ms={min_ms}, limit={limit}")
            
            # Fetch hotspot data
            hotspots = await self.mongo_fetcher.fetch_slow_queries(
                connection_string, min_ms, limit, timeout
            )
            
            return {
                "success": True,
                "hostname": hostname,
                "connection_string": connection_string.split('@')[0] + '@***',  # Hide credentials in logs
                "parameters": {
                    "min_ms": min_ms,
                    "limit": limit,
                    "timeout": timeout
                },
                "data": {
                    "slow_queries": hotspots,
                    "query_count": len(hotspots),
                    "analysis_time": datetime.now(timezone.utc).isoformat()
                },
                "execution_time": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"MongoDB hotspot plugin failed for {hostname}: {e}")
            return {
                "success": False,
                "error": str(e),
                "hostname": hostname,
                "execution_time": time.time() - start_time
            }
    
    def _get_host_group(self, hostname: str) -> Optional[str]:
        """Determine which host group a hostname belongs to"""
        groups = self.config.get("hosts.groups", {})
        for group_name, group_config in groups.items():
            hosts = group_config.get("hosts", [])
            if hostname in hosts:
                return group_name
        return None


class PluginManager:
    """Centralized plugin management system"""
    
    def __init__(self, config: Config):
        self.config = config
        self.plugins: Dict[str, Plugin] = {}
        self._register_plugins()
    
    def _register_plugins(self):
        """Register all available plugins"""
        self.plugins["host_inventory"] = HostInventoryPlugin(self.config)
        self.plugins["mongo_hot"] = MongoHotPlugin(self.config)
        
        logger.info(f"Registered {len(self.plugins)} plugins: {list(self.plugins.keys())}")
    
    async def execute_plugin(self, plugin_name: str, hostname: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific plugin"""
        if plugin_name not in self.plugins:
            return {
                "success": False,
                "error": f"Plugin '{plugin_name}' not found",
                "available_plugins": list(self.plugins.keys())
            }
        
        plugin = self.plugins[plugin_name]
        
        try:
            result = await plugin.execute(hostname, payload)
            result["plugin"] = plugin_name
            return result
            
        except Exception as e:
            logger.error(f"Plugin '{plugin_name}' execution failed: {e}")
            return {
                "success": False,
                "error": f"Plugin execution failed: {e}",
                "plugin": plugin_name,
                "hostname": hostname
            }
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all registered plugins"""
        return {
            "total_plugins": len(self.plugins),
            "plugins": {
                name: {
                    "name": plugin.plugin_name,
                    "config": plugin.plugin_config
                }
                for name, plugin in self.plugins.items()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of all plugins"""
        health_status = {
            "healthy": True,
            "plugins": {}
        }
        
        for name, plugin in self.plugins.items():
            try:
                # Basic plugin health check - ensure it can be instantiated
                plugin_health = {
                    "healthy": True,
                    "name": plugin.plugin_name,
                    "config_loaded": bool(plugin.plugin_config)
                }
            except Exception as e:
                plugin_health = {
                    "healthy": False,
                    "error": str(e)
                }
                health_status["healthy"] = False
            
            health_status["plugins"][name] = plugin_health
        
        return health_status


# Global plugin manager instance
plugin_manager: Optional[PluginManager] = None


def init_plugins(config: Config) -> PluginManager:
    """Initialize global plugin manager"""
    global plugin_manager
    plugin_manager = PluginManager(config)
    return plugin_manager


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager"""
    if plugin_manager is None:
        raise RuntimeError("Plugin manager not initialized. Call init_plugins() first.")
    return plugin_manager