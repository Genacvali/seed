# -*- coding: utf-8 -*-
"""Configuration management for SEED monitoring system."""
import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

_CFG: Dict[str, Any] = {}
_BASE = Path(__file__).resolve().parents[1] 
_CFG_FILE = os.getenv("SEED_CONFIG", str(_BASE / "configs" / "seed.yaml"))

def load_settings() -> None:
    """Load configuration from YAML file."""
    global _CFG
    p = Path(_CFG_FILE)
    if not p.exists():
        raise RuntimeError(f"Configuration file not found: {p}")
    _CFG = yaml.safe_load(p.read_text(encoding="utf-8")) or {}

def _match_host_group(host: str) -> List[str]:
    """Return list of groups that contain the host."""
    res = []
    for gname, g in (_CFG.get("groups") or {}).items():
        include = g.get("include") or []
        if host in include:
            res.append(gname)
    return res

def get_connection_for_host(host: str, connection_type: str) -> Optional[str]:
    """Get connection string for host from its group."""
    host_groups = _match_host_group(host)
    for gname in host_groups:
        group = _CFG.get("groups", {}).get(gname, {})
        connections = group.get("connections", {})
        if connection_type in connections:
            conn_str = connections[connection_type]
            return conn_str.replace("{host}", host)
    return None

def resolve_handler(alert: Dict[str, Any]) -> Tuple[Optional[str], Dict[str, Any]]:
    """
    Find plugin and payload for alert type + host.
    Returns (plugin_name, payload_dict) or (None, {}).
    """
    atype = alert.get("type")
    host  = alert.get("host")
    if not atype or not host:
        return None, {}

    rules = _CFG.get("alerts") or {}
    rule = rules.get(atype)
    if not rule:
        return None, {}

    payload = dict(rule.get("payload_default") or {})
    
    host_groups = set(_match_host_group(host))
    for override in (rule.get("overrides") or []):
        groups = set(override.get("groups") or [])
        if groups & host_groups:
            payload.update(override.get("payload") or {})

    payload.update(alert.get("payload") or {})

    host_connections = {}
    host_groups_list = _match_host_group(host)
    for gname in host_groups_list:
        group = _CFG.get("groups", {}).get(gname, {})
        connections = group.get("connections", {})
        for conn_type, conn_str in connections.items():
            host_connections[conn_type] = conn_str.replace("{host}", host)
    
    for conn_type, conn_str in host_connections.items():
        if conn_type not in payload:
            payload[conn_type] = conn_str

    plugin = rule.get("plugin")
    return plugin, payload