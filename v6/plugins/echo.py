# -*- coding: utf-8 -*-

def run(alert: dict, prom_client, params: dict) -> dict:
    """Default fallback plugin - just echoes alert info"""
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    instance = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "Alert")
    
    lines = [
        f"📢 Echo Plugin - No specific handler for '{alertname}'",
        f"🏠 Instance: {instance}",
        f"📋 Labels: {', '.join([f'{k}={v}' for k, v in labels.items()])}",
        f"📝 Summary: {annotations.get('summary', 'N/A')}"
    ]
    
    return {
        "title": f"Echo - {alertname} @ {instance}",
        "lines": lines
    }