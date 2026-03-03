# -*- coding: utf-8 -*-
"""
Plugin: os_cpu
Алерты на высокую загрузку CPU.

Маршрут (configs/alerts.yaml):
  - match: {alertname: "HighCPUUsage"}
    plugin: "os_cpu"
    params: {}

Поддерживаемые alertname (укажи нужный в alerts.yaml):
  HighCPUUsage, NodeCPUUsage, CPUThrottling, HostHighCpuLoad
"""
from typing import Any, Dict


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels      = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    instance  = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "HighCPUUsage")
    severity  = labels.get("severity", "")

    out = []

    # ── Базовая инфо ──────────────────────────────────────────
    out.append(f"🖥  Instance: {instance}")
    if severity:
        out.append(f"⚠  Severity: {severity}")

    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        out.append(f"📋 {summary}")

    # ── Данные из Prometheus ──────────────────────────────────
    if prom:
        # Текущая загрузка CPU (среднее по всем ядрам, 5-минутный интервал)
        cpu_query = (
            f'100 - (avg by(instance)(rate('
            f'node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[5m])) * 100)'
        )
        cpu = prom.query_value(cpu_query)
        if isinstance(cpu, (int, float)):
            bar = _bar(cpu, 100)
            out.append(f"🔥 CPU:   {cpu:.1f}%  {bar}")

        # Load average 1 / 5 / 15 минут
        load1  = prom.query_value(f'node_load1{{instance="{instance}"}}')
        load5  = prom.query_value(f'node_load5{{instance="{instance}"}}')
        load15 = prom.query_value(f'node_load15{{instance="{instance}"}}')
        if isinstance(load1, (int, float)):
            l5_s  = f"{load5:.2f}"  if isinstance(load5,  (int, float)) else "n/a"
            l15_s = f"{load15:.2f}" if isinstance(load15, (int, float)) else "n/a"
            out.append(f"📈 Load:  {load1:.2f} / {l5_s} / {l15_s}  (1/5/15m)")

        # Число CPU
        cpus = prom.query_value(
            f'count(node_cpu_seconds_total{{mode="idle",instance="{instance}"}})'
        )
        if isinstance(cpus, (int, float)):
            out.append(f"🧮 Cores: {int(cpus)}")

    return {
        "title": f"🔥 {alertname} @ {instance}",
        "lines": out,
    }


def _bar(val: float, total: float, width: int = 10) -> str:
    """Простой ASCII progress-bar."""
    filled = int(round(val / total * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"
