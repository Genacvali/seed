# -*- coding: utf-8 -*-
"""
Plugin: os_memory
Алерты на высокое потребление памяти.

Маршрут (configs/alerts.yaml):
  - match: {alertname: "HighMemoryUsage"}
    plugin: "os_memory"
    params: {}

Поддерживаемые alertname:
  HighMemoryUsage, NodeMemoryUsage, HostOutOfMemory, LowMemory
"""
from typing import Any, Dict


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels      = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    instance  = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "HighMemoryUsage")
    severity  = labels.get("severity", "")

    out = []

    out.append(f"🖥  Instance: {instance}")
    if severity:
        out.append(f"⚠  Severity: {severity}")

    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        out.append(f"📋 {summary}")

    if prom:
        # Процент использованной памяти
        used_pct = prom.query_value(
            f'(1 - node_memory_MemAvailable_bytes{{instance="{instance}"}}'
            f' / node_memory_MemTotal_bytes{{instance="{instance}"}}) * 100'
        )
        # Общий объём (в ГБ)
        total_bytes = prom.query_value(
            f'node_memory_MemTotal_bytes{{instance="{instance}"}}'
        )
        # Свободно
        avail_bytes = prom.query_value(
            f'node_memory_MemAvailable_bytes{{instance="{instance}"}}'
        )
        # Буферы + кэш
        cached_bytes = prom.query_value(
            f'node_memory_Cached_bytes{{instance="{instance}"}}'
            f' + node_memory_Buffers_bytes{{instance="{instance}"}}'
        )

        if isinstance(used_pct, (int, float)):
            bar = _bar(used_pct, 100)
            out.append(f"🧠 RAM:   {used_pct:.1f}%  {bar}")

        if isinstance(total_bytes, (int, float)) and isinstance(avail_bytes, (int, float)):
            total_gb = total_bytes / 1024 ** 3
            avail_gb = avail_bytes / 1024 ** 3
            used_gb  = total_gb - avail_gb
            out.append(f"📦 Used:  {used_gb:.1f} GB / {total_gb:.1f} GB")

        if isinstance(cached_bytes, (int, float)):
            out.append(f"💾 Cache+Buffers: {cached_bytes / 1024**3:.1f} GB")

        # Swap
        swap_total = prom.query_value(
            f'node_memory_SwapTotal_bytes{{instance="{instance}"}}'
        )
        swap_free = prom.query_value(
            f'node_memory_SwapFree_bytes{{instance="{instance}"}}'
        )
        if isinstance(swap_total, (int, float)) and swap_total > 0:
            swap_used = swap_total - (swap_free if isinstance(swap_free, (int, float)) else 0)
            swap_pct  = swap_used / swap_total * 100
            out.append(f"🔄 Swap:  {swap_pct:.1f}%  ({swap_used/1024**3:.1f} / {swap_total/1024**3:.1f} GB)")

    return {
        "title": f"🧠 {alertname} @ {instance}",
        "lines": out,
    }


def _bar(val: float, total: float, width: int = 10) -> str:
    filled = int(round(val / total * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"
