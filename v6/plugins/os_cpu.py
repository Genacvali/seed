# -*- coding: utf-8 -*-
"""
Plugin: os_cpu

Маршрут (configs/alerts.yaml):
  - match: {alertname: "HighCPUUsage"}
    plugin: "os_cpu"
    params: {}
"""
from typing import Any, Dict

# ── Схема параметров (читается admin-панелью) ────────────────────────────────
PARAMS_SCHEMA = {
    "title": "CPU плагин",
    "fields": [
        {
            "key": "top_processes",
            "type": "bool",
            "label": "Показывать топ процессов",
            "description": "Требует process-exporter на целевом хосте",
            "default": True,
        },
        {
            "key": "top_n",
            "type": "int",
            "label": "Кол-во процессов в топе",
            "default": 10,
            "min": 1,
            "max": 20,
        },
        {
            "key": "show_network",
            "type": "bool",
            "label": "Показывать сетевой трафик",
            "default": True,
        },
        {
            "key": "extra_metrics",
            "type": "metrics_list",
            "label": "Дополнительные Prometheus-метрики",
            "description": "Любые PromQL-запросы. Используй {instance} — подставится автоматически.",
            "default": [],
            "presets": [
                {"label": "System Load 1m",  "query": "system_load1{{instance=\"{instance}\"}}", "unit": ""},
                {"label": "System Load 5m",  "query": "system_load5{{instance=\"{instance}\"}}", "unit": ""},
                {"label": "System Load 15m", "query": "system_load15{{instance=\"{instance}\"}}", "unit": ""},
                {"label": "Context switches", "query": "rate(node_context_switches_total{{instance=\"{instance}\"}}[5m])", "unit": "/s"},
                {"label": "Interrupts",       "query": "rate(node_intr_total{{instance=\"{instance}\"}}[5m])", "unit": "/s"},
            ],
        },
    ],
}


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels      = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    instance  = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "HighCPUUsage")
    severity  = labels.get("severity", "")

    out = []
    out.append(f"🖥  Instance: {instance}")
    if severity:
        out.append(f"⚠  Severity: {severity}")
    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        out.append(f"📋 {summary}")

    if not prom:
        return {"title": f"🔥 {alertname} @ {instance}", "lines": out}

    # ── PromHelper с авто-разрешением instance ────────────────
    try:
        from prom_helpers import PromHelper
        h = PromHelper(instance)
        if h.instance != instance:
            out.append(f"🔍 Resolved: {instance} → {h.instance}")
    except ImportError:
        h = _FallbackHelper(instance, prom)

    out.append("")  # разделитель

    # ── CPU ───────────────────────────────────────────────────
    cpu = h.cpu_usage_pct()
    if isinstance(cpu, (int, float)):
        bar = _bar(cpu, 100)
        level = "🔴" if cpu >= 90 else ("🟡" if cpu >= 70 else "🟢")
        out.append(f"{level} CPU:    {cpu:5.1f}%  {bar}")

    l1, l5, l15 = h.load_avg()
    if isinstance(l1, (int, float)):
        l5s  = f"{l5:.2f}"  if isinstance(l5,  (int, float)) else "n/a"
        l15s = f"{l15:.2f}" if isinstance(l15, (int, float)) else "n/a"
        out.append(f"📈 Load:   {l1:.2f} / {l5s} / {l15s}  (1m / 5m / 15m)")

    cores = h.cpu_count()
    procs_run = h.procs_running()
    meta = []
    if cores:
        meta.append(f"cores: {cores}")
    if procs_run is not None:
        meta.append(f"running procs: {procs_run}")
    if meta:
        out.append(f"🧮 {' · '.join(meta)}")

    # ── Топ процессов по CPU (process-exporter) ───────────────
    show_top = params.get("top_processes", True)
    top_n    = int(params.get("top_n", 10))
    if show_top:
        has_pe = h.process_exporter_available() if hasattr(h, 'process_exporter_available') else False
        if has_pe:
            top = h.top_processes_cpu(n=top_n)
            if top:
                out.append("")
                out.append(f"🏆 Top {top_n} processes by CPU:")
                for i, p in enumerate(top[:top_n], 1):
                    out.append(f"   {i:2}. {p['name']:<30} {p['cpu_pct']:.1f}%")
        else:
            out.append("ℹ️  Top processes: установи process-exporter для детального анализа")

    # ── Сеть ──────────────────────────────────────────────────
    if params.get("show_network", True):
        net = h.network_mbps()
        if isinstance(net.get("rx"), (int, float)) or isinstance(net.get("tx"), (int, float)):
            rx = f"{net['rx']:.2f} MB/s" if isinstance(net.get("rx"), (int, float)) else "n/a"
            tx = f"{net['tx']:.2f} MB/s" if isinstance(net.get("tx"), (int, float)) else "n/a"
            out.append(f"🌐 Network: ↓ {rx}  ↑ {tx}")

    # ── Дополнительные метрики из params ──────────────────────
    _append_extra_metrics(out, h, params)

    return {
        "title": f"🔥 {alertname} @ {h.instance}",
        "lines": out,
    }


# ─── Утилиты ──────────────────────────────────────────────────

def _append_extra_metrics(out: list, h, params: dict) -> None:
    """Запрашивает дополнительные метрики из params['extra_metrics']."""
    extras = params.get("extra_metrics", [])
    if not extras:
        return
    out.append("")
    out.append("📡 Custom metrics:")
    for m in extras:
        query = m.get("query", "").strip()
        label = m.get("label", query[:40])
        unit  = m.get("unit", "")
        if not query:
            continue
        try:
            val = h.qv(query) if hasattr(h, "qv") else None
        except Exception:
            val = None
        if isinstance(val, (int, float)):
            out.append(f"   {label}: {val:.4g}{(' ' + unit) if unit else ''}")
        else:
            out.append(f"   {label}: n/a")


def _bar(val: float, total: float, width: int = 10) -> str:
    filled = min(int(round(val / total * width)), width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


class _FallbackHelper:
    """Если prom_helpers.py не установлен — работаем напрямую через prom."""
    def __init__(self, instance: str, prom_mod):
        self.instance = instance
        self._p = prom_mod

    def cpu_usage_pct(self):
        return self._p.query_value(
            f'100 - (avg by(instance)(rate(node_cpu_seconds_total{{mode="idle",instance="{self.instance}"}}[5m])) * 100)'
        )
    def load_avg(self):
        qv = self._p.query_value
        i = self.instance
        return (qv(f'node_load1{{instance="{i}"}}'),
                qv(f'node_load5{{instance="{i}"}}'),
                qv(f'node_load15{{instance="{i}"}}'))
    def cpu_count(self):
        v = self._p.query_value(f'count(node_cpu_seconds_total{{mode="idle",instance="{self.instance}"}})')
        return int(v) if isinstance(v, float) else None
    def procs_running(self):
        v = self._p.query_value(f'node_procs_running{{instance="{self.instance}"}}')
        return int(v) if isinstance(v, float) else None
    def network_mbps(self):
        i = self.instance
        rx = self._p.query_value(f'sum by(instance)(rate(node_network_receive_bytes_total{{instance="{i}",device!="lo"}}[5m]))')
        tx = self._p.query_value(f'sum by(instance)(rate(node_network_transmit_bytes_total{{instance="{i}",device!="lo"}}[5m]))')
        return {"rx": rx/1e6 if isinstance(rx,(int,float)) else None,
                "tx": tx/1e6 if isinstance(tx,(int,float)) else None}
    def top_processes_cpu(self, n=10): return []
    def top_processes_mem(self, n=10): return []
