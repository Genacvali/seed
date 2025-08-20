#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED Plugins - All monitoring plugins in one file
Each plugin should implement: run(host: str, labels: dict, annotations: dict, payload: dict) -> str
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import httpx
from pymongo import MongoClient


# =============================================================================
# Host Inventory Plugin - System monitoring via Telegraf
# =============================================================================

async def host_inventory(host: str, labels: Dict[str, str], annotations: Dict[str, str], payload: Dict[str, Any]) -> Optional[str]:
    """
    Collects system inventory data via Telegraf metrics endpoint
    
    Args:
        host: Target hostname
        labels: Alert labels
        annotations: Alert annotations  
        payload: Plugin configuration
    
    Returns:
        Formatted message string or None
    """
    try:
        telegraf_url = payload.get("telegraf_url", f"http://{host}:9216/metrics")
        timeout = payload.get("timeout", 30)
        paths = payload.get("paths", ["/"])
        alert_type = payload.get("alert_type", "general")
        priority = payload.get("priority", "normal")
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(telegraf_url)
            response.raise_for_status()
            
            metrics_data = response.text
            inventory = _parse_telegraf_metrics(metrics_data, paths)
            
            if not inventory:
                return None
                
            # Format message based on alert type
            if alert_type == "disk_space":
                return _format_disk_alert(host, inventory, labels, priority)
            elif alert_type == "cpu_load":
                return _format_cpu_alert(host, inventory, labels, priority)
            elif alert_type == "memory":
                return _format_memory_alert(host, inventory, labels, priority)
            else:
                return _format_general_inventory(host, inventory, labels, priority)
                
    except Exception as e:
        return f"⚠️ **Host Inventory Error**\n**Host:** {host}\n**Error:** {str(e)}"


def _parse_telegraf_metrics(metrics_data: str, paths: List[str]) -> Dict[str, Any]:
    """Parse Telegraf metrics into structured data"""
    inventory = {
        "disk": {},
        "cpu": {},
        "memory": {},
        "system": {},
        "timestamp": int(time.time())
    }
    
    for line in metrics_data.split('\n'):
        if line.startswith('#') or not line.strip():
            continue
            
        try:
            # Parse Prometheus format: metric_name{labels} value timestamp
            parts = line.split(' ')
            if len(parts) < 2:
                continue
                
            metric_with_labels = parts[0]
            value = float(parts[1])
            
            # Extract metric name and labels
            if '{' in metric_with_labels:
                metric_name = metric_with_labels.split('{')[0]
                labels_str = metric_with_labels.split('{')[1].rstrip('}')
            else:
                metric_name = metric_with_labels
                labels_str = ""
            
            # Parse labels
            metric_labels = {}
            if labels_str:
                for label_pair in labels_str.split(','):
                    key, val = label_pair.split('=', 1)
                    metric_labels[key.strip()] = val.strip('"')
            
            # Store relevant metrics
            if metric_name == "disk_used_percent" and metric_labels.get("path") in paths:
                inventory["disk"][metric_labels["path"]] = {
                    "used_percent": value,
                    "device": metric_labels.get("device", "unknown")
                }
            elif metric_name == "cpu_usage_idle":
                inventory["cpu"]["idle_percent"] = value
            elif metric_name == "mem_used_percent":
                inventory["memory"]["used_percent"] = value
            elif metric_name == "system_load1":
                inventory["system"]["load1"] = value
                
        except (ValueError, IndexError):
            continue
    
    return inventory


def _format_disk_alert(host: str, inventory: Dict[str, Any], labels: Dict[str, str], priority: str) -> str:
    """Format disk space alert message"""
    emoji = "🔴" if priority == "critical" else "🟡" if priority == "high" else "🟢"
    
    message = f"{emoji} **Disk Space Alert**\n"
    message += f"**Host:** {host}\n"
    message += f"**Priority:** {priority.upper()}\n\n"
    
    for path, info in inventory["disk"].items():
        used_pct = info["used_percent"]
        device = info["device"]
        message += f"**{path}** ({device}): {used_pct:.1f}% used\n"
    
    message += f"\n**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    return message


def _format_cpu_alert(host: str, inventory: Dict[str, Any], labels: Dict[str, str], priority: str) -> str:
    """Format CPU load alert message"""
    emoji = "🔥" if priority == "critical" else "⚡" if priority == "high" else "📊"
    
    cpu_used = 100 - inventory["cpu"].get("idle_percent", 0)
    load1 = inventory["system"].get("load1", 0)
    
    message = f"{emoji} **CPU Load Alert**\n"
    message += f"**Host:** {host}\n"
    message += f"**Priority:** {priority.upper()}\n"
    message += f"**CPU Usage:** {cpu_used:.1f}%\n"
    message += f"**Load Average:** {load1:.2f}\n"
    message += f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    return message


def _format_memory_alert(host: str, inventory: Dict[str, Any], labels: Dict[str, str], priority: str) -> str:
    """Format memory usage alert message"""
    emoji = "💾"
    
    mem_used = inventory["memory"].get("used_percent", 0)
    
    message = f"{emoji} **Memory Usage Alert**\n"
    message += f"**Host:** {host}\n"
    message += f"**Priority:** {priority.upper()}\n"
    message += f"**Memory Usage:** {mem_used:.1f}%\n"
    message += f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    
    return message


def _format_general_inventory(host: str, inventory: Dict[str, Any], labels: Dict[str, str], priority: str) -> str:
    """Format general system inventory message"""
    emoji = "📋"
    
    message = f"{emoji} **System Inventory**\n"
    message += f"**Host:** {host}\n"
    message += f"**Priority:** {priority.upper()}\n\n"
    
    # CPU info
    if inventory["cpu"]:
        cpu_used = 100 - inventory["cpu"].get("idle_percent", 0)
        message += f"**CPU Usage:** {cpu_used:.1f}%\n"
    
    # Memory info
    if inventory["memory"]:
        mem_used = inventory["memory"].get("used_percent", 0)
        message += f"**Memory Usage:** {mem_used:.1f}%\n"
    
    # System load
    if inventory["system"]:
        load1 = inventory["system"].get("load1", 0)
        message += f"**Load Average:** {load1:.2f}\n"
    
    # Disk info
    if inventory["disk"]:
        message += f"\n**Disk Usage:**\n"
        for path, info in inventory["disk"].items():
            used_pct = info["used_percent"]
            message += f"• {path}: {used_pct:.1f}%\n"
    
    message += f"\n**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    return message


# =============================================================================
# MongoDB Hotspots Plugin - MongoDB performance monitoring
# =============================================================================

async def mongo_hot(host: str, labels: Dict[str, str], annotations: Dict[str, str], payload: Dict[str, Any]) -> Optional[str]:
    """
    Analyzes MongoDB performance and identifies slow operations
    
    Args:
        host: MongoDB hostname  
        labels: Alert labels
        annotations: Alert annotations
        payload: Plugin configuration with MongoDB connection details
    
    Returns:
        Formatted message string or None
    """
    try:
        # MongoDB connection parameters
        mongo_host = payload.get("mongo_host", host)
        mongo_port = payload.get("mongo_port", 27017)
        username = payload.get("username")
        password = payload.get("password")
        auth_db = payload.get("auth_db", "admin")
        
        # Query parameters
        min_ms = payload.get("min_ms", 50)
        limit = payload.get("limit", 10)
        priority = payload.get("priority", "normal")
        
        # Build connection string
        if username and password:
            connection_string = f"mongodb://{username}:{password}@{mongo_host}:{mongo_port}/{auth_db}"
        else:
            connection_string = f"mongodb://{mongo_host}:{mongo_port}/"
        
        # Connect to MongoDB
        client = MongoClient(connection_string, serverSelectionTimeoutMS=10000)
        
        # Test connection
        client.admin.command('ping')
        
        # Collect performance data
        hotspots = await _analyze_mongo_performance(client, min_ms, limit)
        
        client.close()
        
        if not hotspots:
            return None
            
        return _format_mongo_alert(host, hotspots, labels, priority, min_ms)
        
    except Exception as e:
        return f"⚠️ **MongoDB Analysis Error**\n**Host:** {host}\n**Error:** {str(e)}"


async def _analyze_mongo_performance(client: MongoClient, min_ms: int, limit: int) -> Dict[str, Any]:
    """Analyze MongoDB performance metrics"""
    hotspots = {
        "slow_queries": [],
        "current_operations": [],
        "server_status": {},
        "timestamp": int(time.time())
    }
    
    try:
        # Get server status
        server_status = client.admin.command("serverStatus")
        hotspots["server_status"] = {
            "connections": server_status.get("connections", {}),
            "opcounters": server_status.get("opcounters", {}),
            "mem": server_status.get("mem", {}),
            "globalLock": server_status.get("globalLock", {})
        }
        
        # Get current operations (slow queries)
        current_ops = client.admin.command("currentOp", {"active": True, "secs_running": {"$gte": min_ms / 1000}})
        
        for op in current_ops.get("inprog", [])[:limit]:
            if op.get("secs_running", 0) * 1000 >= min_ms:
                hotspots["slow_queries"].append({
                    "ns": op.get("ns", "unknown"),
                    "op": op.get("op", "unknown"),
                    "command": _sanitize_command(op.get("command", {})),
                    "duration_ms": int(op.get("secs_running", 0) * 1000),
                    "client": op.get("client", "unknown")
                })
        
        # Get profiler data if available
        try:
            profiler_data = client.admin.command("profile", -1)  # Get profiling status
            if profiler_data.get("level", 0) > 0:
                # Query profiler collection for slow operations
                system_profile = client.admin.system.profile
                slow_ops = list(system_profile.find(
                    {"millis": {"$gte": min_ms}}, 
                    limit=limit
                ).sort("ts", -1))
                
                for op in slow_ops:
                    hotspots["current_operations"].append({
                        "ns": op.get("ns", "unknown"),
                        "op": op.get("op", "unknown"),
                        "command": _sanitize_command(op.get("command", {})),
                        "duration_ms": op.get("millis", 0),
                        "timestamp": op.get("ts")
                    })
        except:
            pass  # Profiler may not be enabled
            
    except Exception as e:
        hotspots["error"] = str(e)
    
    return hotspots


def _sanitize_command(command: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize MongoDB command for logging (remove sensitive data)"""
    if not isinstance(command, dict):
        return {}
    
    sanitized = {}
    for key, value in command.items():
        if key in ["find", "aggregate", "update", "delete", "insert"]:
            sanitized[key] = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
        elif key in ["filter", "query"]:
            sanitized[key] = "<filtered>"
        else:
            sanitized[key] = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
    
    return sanitized


def _format_mongo_alert(host: str, hotspots: Dict[str, Any], labels: Dict[str, str], priority: str, min_ms: int) -> str:
    """Format MongoDB performance alert message"""
    emoji = "🔥" if priority == "critical" else "⚡" if priority == "high" else "🐌"
    
    message = f"{emoji} **MongoDB Performance Alert**\n"
    message += f"**Host:** {host}\n"
    message += f"**Priority:** {priority.upper()}\n"
    message += f"**Threshold:** >{min_ms}ms\n\n"
    
    # Server status
    if hotspots.get("server_status"):
        status = hotspots["server_status"]
        connections = status.get("connections", {})
        opcounters = status.get("opcounters", {})
        
        message += "**Server Status:**\n"
        message += f"• Connections: {connections.get('current', 'N/A')}/{connections.get('available', 'N/A')}\n"
        message += f"• Operations/sec: {opcounters.get('query', 0) + opcounters.get('insert', 0) + opcounters.get('update', 0) + opcounters.get('delete', 0)}\n\n"
    
    # Slow queries
    slow_queries = hotspots.get("slow_queries", [])
    if slow_queries:
        message += f"**Slow Queries ({len(slow_queries)}):**\n"
        for i, query in enumerate(slow_queries[:5], 1):
            message += f"{i}. **{query['ns']}** ({query['op']}) - {query['duration_ms']}ms\n"
            if query.get('command'):
                cmd_str = str(query['command'])[:100]
                message += f"   `{cmd_str}{'...' if len(cmd_str) == 100 else ''}`\n"
        
        if len(slow_queries) > 5:
            message += f"   ... and {len(slow_queries) - 5} more\n"
        message += "\n"
    
    # Current operations from profiler
    current_ops = hotspots.get("current_operations", [])
    if current_ops:
        message += f"**Recent Slow Operations ({len(current_ops)}):**\n"
        for i, op in enumerate(current_ops[:3], 1):
            message += f"{i}. **{op['ns']}** ({op['op']}) - {op['duration_ms']}ms\n"
        message += "\n"
    
    message += f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
    return message


# =============================================================================
# Plugin Registry and Loader
# =============================================================================

# Available plugins registry
PLUGINS = {
    "host_inventory": host_inventory,
    "mongo_hot": mongo_hot,
}


def get_plugin(name: str):
    """Get plugin function by name"""
    return PLUGINS.get(name)


def list_plugins() -> List[str]:
    """List all available plugins"""
    return list(PLUGINS.keys())


def reload_plugins():
    """Reload plugins (for dynamic reloading)"""
    # This could be extended to reload from file or external source
    pass


# =============================================================================
# Plugin Testing and Validation
# =============================================================================

async def test_plugin(plugin_name: str, host: str = "localhost", test_payload: Optional[Dict[str, Any]] = None) -> str:
    """
    Test a plugin with sample data
    
    Args:
        plugin_name: Name of plugin to test
        host: Test hostname
        test_payload: Test payload, uses defaults if None
    
    Returns:
        Test result message
    """
    plugin_func = get_plugin(plugin_name)
    if not plugin_func:
        return f"❌ Plugin '{plugin_name}' not found. Available: {', '.join(list_plugins())}"
    
    # Default test payloads
    default_payloads = {
        "host_inventory": {
            "paths": ["/"],
            "alert_type": "general",
            "priority": "normal",
            "timeout": 10
        },
        "mongo_hot": {
            "mongo_host": "localhost",
            "mongo_port": 27017,
            "min_ms": 50,
            "limit": 10,
            "priority": "normal"
        }
    }
    
    payload = test_payload or default_payloads.get(plugin_name, {})
    labels = {"alertname": f"Test_{plugin_name}", "instance": host}
    annotations = {"description": "Test alert"}
    
    try:
        result = await plugin_func(host, labels, annotations, payload)
        if result:
            return f"✅ Plugin '{plugin_name}' test successful:\n\n{result}"
        else:
            return f"⚠️ Plugin '{plugin_name}' returned no result (may be normal for current system state)"
    except Exception as e:
        return f"❌ Plugin '{plugin_name}' test failed: {str(e)}"


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python plugins.py <command>")
        print("Commands:")
        print("  list                    - List all plugins")
        print("  test <plugin> [host]    - Test a plugin")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        print("Available plugins:")
        for plugin in list_plugins():
            print(f"  - {plugin}")
    
    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: python plugins.py test <plugin_name> [host]")
            sys.exit(1)
        
        plugin_name = sys.argv[2]
        host = sys.argv[3] if len(sys.argv) > 3 else "localhost"
        
        async def run_test():
            result = await test_plugin(plugin_name, host)
            print(result)
        
        asyncio.run(run_test())
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)