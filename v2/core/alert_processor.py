# -*- coding: utf-8 -*-
"""
Shared alert processing logic
"""
from typing import Dict, Any
import core.config as config
import core.plugins as plugins

def host_from_labels(labels: Dict[str, str]) -> str:
    """Extract host from alert labels"""
    host = labels.get("host") or labels.get("nodename") or labels.get("instance")
    if host and ":" in host:
        host = host.split(":")[0]
    return host or "unknown"

def process_one_alert(alert: Dict[str, Any]) -> str:
    """Process a single alert and return formatted message"""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    alertname = labels.get("alertname") or "unknown"

    host = host_from_labels(labels)
    route = config.route_for(alertname, labels)
    if not route:
        return f"SEED: 🤷 не найден маршрут для alertname='{alertname}'"

    plugin_name = route["plugin"]
    payload = route.get("payload", {})
    payload = config.enrich_with_host_overrides(host, payload)

    fn = plugins.get_plugin(plugin_name)
    if not fn:
        return f"SEED: 🤷 не найден плагин '{plugin_name}'"

    return fn(host=host, labels=labels, annotations=annotations, payload=payload)

def fingerprint(alert: Dict[str, Any]) -> str:
    """Generate alert fingerprint for throttling"""
    lab = alert.get("labels", {})
    ann = alert.get("annotations", {})
    key = f"{lab.get('alertname','?')}|{lab.get('host',lab.get('instance','?'))}|{ann.get('summary','')}"
    return key