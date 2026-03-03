# -*- coding: utf-8 -*-
"""
Plugin: os_memory
"""
from typing import Any, Dict

# ── Схема параметров (читается admin-панелью) ────────────────────────────────
PARAMS_SCHEMA = {
    "title": "Memory плагин",
    "fields": [
        {
            "key": "top_processes",
            "type": "bool",
            "label": "Показывать топ процессов",
            "description": "Требует process-exporter",
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
            "key": "extra_metrics",
            "type": "metrics_list",
            "label": "Дополнительные Prometheus-метрики",
            "description": "Любые PromQL-запросы. Используй {instance} — подставится автоматически.",
            "default": [],
            "presets": [
                {"label": "OOM kills",      "query": "increase(node_vmstat_oom_kill{{instance=\"{instance}\"}}[1h])", "unit": "kills/h"},
                {"label": "Page faults",    "query": "rate(node_vmstat_pgfault{{instance=\"{instance}\"}}[5m])", "unit": "/s"},
                {"label": "Swap in rate",   "query": "rate(node_vmstat_pswpin{{instance=\"{instance}\"}}[5m])", "unit": "pg/s"},
                {"label": "Swap out rate",  "query": "rate(node_vmstat_pswpout{{instance=\"{instance}\"}}[5m])", "unit": "pg/s"},
            ],
        },
    ],
}


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

    if not prom:
        return {"title": f"🧠 {alertname} @ {instance}", "lines": out}

    try:
        from prom_helpers import PromHelper
        h = PromHelper(instance)
        if h.instance != instance:
            out.append(f"🔍 Resolved: {instance} → {h.instance}")
    except ImportError:
        h = _FallbackHelper(instance, prom)

    out.append("")

    # ── RAM ───────────────────────────────────────────────────
    used_pct = h.memory_used_pct()
    mem = h.memory_bytes()

    if isinstance(used_pct, (int, float)):
        bar   = _bar(used_pct, 100)
        level = "🔴" if used_pct >= 90 else ("🟡" if used_pct >= 75 else "🟢")
        out.append(f"{level} RAM:   {used_pct:5.1f}%  {bar}")

    total = mem.get("total")
    avail = mem.get("avail")
    if isinstance(total, (int, float)) and isinstance(avail, (int, float)):
        used_gb  = (total - avail) / 1e9
        total_gb = total / 1e9
        out.append(f"📦 Used:  {used_gb:.1f} GB / {total_gb:.1f} GB  (free {avail/1e9:.1f} GB)")

    cached = mem.get("cached")
    if isinstance(cached, (int, float)):
        out.append(f"💾 Cache+Buffers: {cached/1e9:.1f} GB")

    # ── Swap ──────────────────────────────────────────────────
    st = mem.get("swap_total")
    sf = mem.get("swap_free")
    if isinstance(st, (int, float)) and st > 0:
        used_swap = st - (sf if isinstance(sf, (int, float)) else 0)
        swap_pct  = used_swap / st * 100
        level     = "🔴" if swap_pct >= 50 else ("🟡" if swap_pct > 0 else "🟢")
        out.append(f"{level} Swap:  {swap_pct:.1f}%  ({used_swap/1e9:.1f} / {st/1e9:.1f} GB)")

    # ── Топ процессов по памяти (process-exporter) ────────────
    show_top = params.get("top_processes", True)
    top_n    = int(params.get("top_n", 10))
    if show_top:
        has_pe = h.process_exporter_available() if hasattr(h, 'process_exporter_available') else False
        if has_pe:
            top = h.top_processes_mem(n=top_n)
            if top:
                out.append("")
                out.append(f"🏆 Top {top_n} processes by Memory (RSS):")
                for i, p in enumerate(top[:top_n], 1):
                    out.append(f"   {i:2}. {p['name']:<30} {p['mem_mb']:.0f} MB")
        else:
            out.append("ℹ️  Top processes: установи process-exporter для детального анализа")

    # ── Дополнительные метрики из params ──────────────────────
    _append_extra_metrics(out, h, params)

    return {
        "title": f"🧠 {alertname} @ {h.instance}",
        "lines": out,
    }


def _append_extra_metrics(out: list, h, params: dict) -> None:
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
    def __init__(self, instance: str, prom_mod):
        self.instance = instance
        self._p = prom_mod

    def memory_used_pct(self):
        i = self.instance
        return self._p.query_value(
            f'(1 - node_memory_MemAvailable_bytes{{instance="{i}"}}'
            f' / node_memory_MemTotal_bytes{{instance="{i}"}}) * 100'
        )
    def memory_bytes(self):
        i = self.instance
        qv = self._p.query_value
        return {
            "total":      qv(f'node_memory_MemTotal_bytes{{instance="{i}"}}'),
            "avail":      qv(f'node_memory_MemAvailable_bytes{{instance="{i}"}}'),
            "cached":     qv(f'node_memory_Cached_bytes{{instance="{i}"}} + node_memory_Buffers_bytes{{instance="{i}"}}'),
            "swap_total": qv(f'node_memory_SwapTotal_bytes{{instance="{i}"}}'),
            "swap_free":  qv(f'node_memory_SwapFree_bytes{{instance="{i}"}}'),
        }
    def process_exporter_available(self): return False
    def top_processes_mem(self, n=10): return []
