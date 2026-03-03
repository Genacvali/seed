#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый плагин echo — работает "из коробки" и нужен как безопасный дефолт.

Он:
- просто красиво раскладывает поля алерта (labels / annotations)
- ничего не запрашивает у Prometheus
- не зависит от дополнительных настроек

Так пользователь сразу видит понятное сообщение даже без своих плагинов.
"""
from typing import Dict, Any


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    alertname = labels.get("alertname", "Alert")
    instance = labels.get("instance", "unknown")
    severity = labels.get("severity", "")

    lines = []

    # Основная строка
    lines.append(f"🛰  Alert: {alertname}")
    lines.append(f"🖥  Instance: {instance}")
    if severity:
        lines.append(f"⚠  Severity: {severity}")

    # Summary / description
    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        lines.append(f"📋 Summary: {summary}")

    description = annotations.get("description", "")
    if description and description != summary:
        lines.append(f"📝 {description}")

    # Остальные метки, кроме базовых
    extra_labels = {
        k: v
        for k, v in labels.items()
        if k not in {"alertname", "instance", "severity"}
    }
    if extra_labels:
        kv = ", ".join(f"{k}={v}" for k, v in sorted(extra_labels.items()))
        lines.append(f"🏷  Labels: {kv}")

    return {
        "title": f"{alertname} @ {instance}",
        "lines": lines,
    }

