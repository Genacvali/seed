# seed/v1/plugins/host_inventory.py
# -*- coding: utf-8 -*-
"""
SEED plugin: host_inventory (через Telegraf Prometheus exporter).
Забирает метрики ОС только по HTTP-эндпоинту Telegraf (без /proc, без SSH).
Ожидаемые метрики (Telegraf metric_version=2):
- mem_total, mem_available
- system_load1, system_load5, system_n_cpus (если есть)
- disk_used_percent{path=...}, disk_used{path=...}, disk_total{path=...}
"""

import os
from typing import Dict, List

# Берём get_gauge из fetchers.telegraf
from fetchers.telegraf import get_gauge

def _fmt_bytes(n: float | int | None) -> str:
    if n is None:
        return "n/a"
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} EB"

def _percent(v: float | None) -> str:
    return f"{v:.0f}%" if isinstance(v, (int, float)) else "n/a"

def run(host: str, payload: Dict) -> str:
    """
    payload:
      paths: ["/", "/data"]  # какие точки монтирования показывать
      port:  9216            # если не дефолтный
    """
    port  = int(payload.get("port") or os.getenv("TELEGRAF_PORT", 9216))
    paths: List[str] = payload.get("paths") or ["/", "/data"]

    # --- RAM ---
    mem_total = get_gauge(host, "mem_total", port=port)
    mem_avail = get_gauge(host, "mem_available", port=port)
    mem_used  = (mem_total - mem_avail) if (isinstance(mem_total,(int,float)) and isinstance(mem_avail,(int,float))) else None

    # --- CPU / Load (если есть) ---
    load1  = get_gauge(host, "system_load1", port=port)
    load5  = get_gauge(host, "system_load5", port=port)
    ncpu   = get_gauge(host, "system_n_cpus", port=port)  # может отсутствовать
    if load1 is not None or load5 is not None:
        if ncpu:
            cpu_line = f"CPU/Load: {int(ncpu)} vCPU · load1 {load1:.2f} · load5 {load5:.2f}"
        else:
            cpu_line = f"CPU/Load: load1 {load1:.2f} · load5 {load5:.2f}"
    else:
        cpu_line = "CPU/Load: n/a"

    # --- Disks per path ---
    disk_lines = []
    for p in paths:
        used_pct   = get_gauge(host, "disk_used_percent", labels={"path": p}, port=port)
        used_bytes = get_gauge(host, "disk_used",         labels={"path": p}, port=port)
        tot_bytes  = get_gauge(host, "disk_total",        labels={"path": p}, port=port)
        disk_lines.append(f"- `{p}` — **{_percent(used_pct)}** ({_fmt_bytes(used_bytes)} / {_fmt_bytes(tot_bytes)})")

    lines = []
    lines.append(f"### SEED · Профиль хоста `{host}`")
    # RAM
    if isinstance(mem_total,(int,float)):
        lines.append(f"**RAM:** {_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)} (free {_fmt_bytes(mem_avail)})")
    else:
        lines.append("**RAM:** n/a")
    # CPU/Load
    lines.append(cpu_line)
    # Disks
    lines.append("**Диски:**")
    lines.extend(disk_lines)

    # --- Короткий совет от LLM (опционально) ---
    try:
        use_llm = os.getenv("USE_LLM", "0") == "1"
        if use_llm:
            from core.llm import GigaChat
            tip = GigaChat().ask(
                "Оцени паспорт сервера (RAM, load, диски) и дай 1–2 очень кратких практичных совета. Без воды.",
                max_tokens=80,
            )
            if tip:
                lines.append("\n**LLM-совет:** " + tip.strip())
    except Exception as e:
        lines.append(f"\n_(LLM недоступен: {e})_")

    return "\n".join(lines)