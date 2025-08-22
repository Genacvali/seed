# -*- coding: utf-8 -*-
"""
SEED Agent Alert Processing System
Core alert processing logic with plugin integration
"""
import hashlib
import json
import time
import importlib.util
import sys
import asyncio
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path


class AlertProcessor:
    """Core alert processing engine"""
    
    def __init__(self, plugins_file: str = "plugins.py"):
        self.plugins_file = Path(plugins_file)
        self._plugins: Dict[str, Callable] = {}
        self.load_plugins()
    
    def load_plugins(self) -> None:
        """Load plugins from plugins file"""
        try:
            if not self.plugins_file.exists():
                raise FileNotFoundError(f"Plugins file not found: {self.plugins_file}")
            
            # Load the plugins module
            spec = importlib.util.spec_from_file_location("plugins", self.plugins_file)
            plugins_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugins_module)
            
            # Get available plugins from the module
            if hasattr(plugins_module, 'PLUGINS'):
                self._plugins = plugins_module.PLUGINS
            else:
                # Fallback: look for plugin functions directly
                self._plugins = {
                    name: getattr(plugins_module, name)
                    for name in dir(plugins_module)
                    if callable(getattr(plugins_module, name)) and not name.startswith('_')
                }
            
        except Exception as e:
            import logging
            logging.error(f"Failed to load plugins: {e}")
            self._plugins = {}
    
    def reload_plugins(self) -> None:
        """Reload plugins from file"""
        # Clear module cache to force reload
        if "plugins" in sys.modules:
            del sys.modules["plugins"]
        
        self.load_plugins()
    
    def get_plugin(self, name: str) -> Optional[Callable]:
        """Get plugin function by name"""
        return self._plugins.get(name)
    
    def list_plugins(self) -> List[str]:
        """List available plugins"""
        return list(self._plugins.keys())
    
    def fingerprint(self, alert: Dict[str, Any]) -> str:
        """Generate unique fingerprint for alert"""
        # Create fingerprint from alertname, instance, and key labels
        labels = alert.get("labels", {})
        
        # Key components for fingerprint
        components = [
            labels.get("alertname", "unknown"),
            labels.get("instance", "unknown"),
            labels.get("job", ""),
            labels.get("service", ""),
            # Add more label keys as needed for uniqueness
        ]
        
        # Create hash
        fingerprint_str = "|".join(str(c) for c in components)
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:12]
    
    async def process_alert(self, alert: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single alert through appropriate plugin"""
        try:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            alertname = labels.get("alertname", "unknown")
            instance = labels.get("instance", "unknown")
            
            # Extract hostname from instance (format: "host:port" or just "host")
            hostname = instance.split(":")[0] if ":" in instance else instance
            
            return {
                "alertname": alertname,
                "hostname": hostname,
                "labels": labels,
                "annotations": annotations,
                "fingerprint": self.fingerprint(alert),
                "timestamp": int(time.time())
            }
            
        except Exception as e:
            import logging
            logging.error(f"Alert processing failed: {e}")
            return None
    
    async def process_alert_with_plugin(self, alert: Dict[str, Any], 
                                      plugin_name: str, 
                                      payload: Dict[str, Any]) -> Optional[str]:
        """Process alert with specific plugin"""
        plugin_func = self.get_plugin(plugin_name)
        if not plugin_func:
            raise ValueError(f"Plugin '{plugin_name}' not found")
        
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        instance = labels.get("instance", "unknown")
        
        # Extract hostname
        hostname = instance.split(":")[0] if ":" in instance else instance
        
        try:
            # Call plugin function
            if asyncio.iscoroutinefunction(plugin_func):
                result = await plugin_func(hostname, labels, annotations, payload)
            else:
                result = plugin_func(hostname, labels, annotations, payload)
            
            return result
            
        except Exception as e:
            import logging
            logging.error(f"Plugin '{plugin_name}' execution failed: {e}")
            raise


# Legacy compatibility functions
def fingerprint(alert: Dict[str, Any]) -> str:
    """Legacy fingerprint function for compatibility"""
    processor = AlertProcessor()
    return processor.fingerprint(alert)

def process_one_alert(alert: Dict[str, Any]) -> Optional[str]:
    """Legacy alert processing function"""
    # This is a simplified version for backward compatibility
    # In the new architecture, routing and plugin execution are handled separately
    try:
        labels = alert.get("labels", {})
        alertname = labels.get("alertname", "unknown")
        instance = labels.get("instance", "unknown")
        
        # Simple message format for compatibility
        return f"Alert: {alertname} on {instance}"
    except Exception:
        return None