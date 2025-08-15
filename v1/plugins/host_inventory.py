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
import re
from typing import Dict, List, Union, Optional

from fetchers.telegraf import get_gauge  # HTTP-скрейпер одной метрики

def _fmt_bytes(n: Optional[Union[float, int]]) -> str:
    if n is None:
        return "n/a"
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} EB"

def _percent(v: Optional[float]) -> str:
    return f"{v:.0f}%" if isinstance(v, (int, float)) else "n/a"

def run(host: str, payload: Dict) -> str:
    """
    payload:
      paths: ["/", "/data"]        # какие точки монтирования показывать
      port:  9216                  # если не дефолтный
      telegraf_url: "http://h:9216/metrics"  # можно передать явный URL
    """
    port  = int(payload.get("port") or os.getenv("TELEGRAF_PORT", 9216))
    paths: List[str] = payload.get("paths") or ["/", "/data"]

    # telegraf_url может приехать из overrides — корректно извлечём host:port
    telegraf_url = payload.get("telegraf_url")
    if telegraf_url:
        m = re.match(r"https?://([^:/]+):(\d+)", telegraf_url.strip())
        if m:
            host = m.group(1)
            port = int(m.group(2))

    # --- RAM ---
    mem_total = get_gauge(host, "mem_total", port=port)
    mem_avail = get_gauge(host, "mem_available", port=port)
    mem_used  = (mem_total - mem_avail) if (
        isinstance(mem_total, (int, float)) and isinstance(mem_avail, (int, float))
    ) else None

    # --- CPU / Load (если есть) ---
    load1  = get_gauge(host, "system_load1", port=port)
    load5  = get_gauge(host, "system_load5", port=port)
    ncpu   = get_gauge(host, "system_n_cpus", port=port)  # может отсутствовать

    if (load1 is not None) or (load5 is not None):
        l1 = load1 if isinstance(load1, (int, float)) else 0.0
        l5 = load5 if isinstance(load5, (int, float)) else 0.0
        if isinstance(ncpu, (int, float)) and ncpu > 0:
            cpu_line = f"CPU/Load: {int(ncpu)} vCPU · load1 {l1:.2f} · load5 {l5:.2f}"
        else:
            cpu_line = f"CPU/Load: load1 {l1:.2f} · load5 {l5:.2f}"
    else:
        cpu_line = "CPU/Load: n/a"

    # --- Disks per path ---
    disk_lines: List[str] = []
    for p in paths:
        used_pct   = get_gauge(host, "disk_used_percent", labels={"path": p}, port=port)
        used_bytes = get_gauge(host, "disk_used",         labels={"path": p}, port=port)
        tot_bytes  = get_gauge(host, "disk_total",        labels={"path": p}, port=port)

        # показываем только если есть все три значения
        if not (isinstance(used_pct, (int, float)) and
                isinstance(used_bytes, (int, float)) and
                isinstance(tot_bytes, (int, float))):
            continue

        disk_lines.append("- `{}` — **{}** ({} / {})".format(
            p, _percent(used_pct), _fmt_bytes(used_bytes), _fmt_bytes(tot_bytes)
        ))

    if not disk_lines:
        disk_lines.append("_нет данных по дискам из Telegraf_")

    # --- Формирование вывода ---
    lines: List[str] = []
    lines.append("### SEED · Профиль хоста `{}`".format(host))
    if isinstance(mem_total, (int, float)):
        lines.append("**RAM:** {} / {} (free {})".format(
            _fmt_bytes(mem_used), _fmt_bytes(mem_total), _fmt_bytes(mem_avail)
        ))
    else:
        lines.append("**RAM:** n/a")
    lines.append(cpu_line)
    lines.append("**Диски:**")
    lines.extend(disk_lines)

    # --- Короткий совет от LLM (опционально) ---
    try:
        use_llm = os.getenv("USE_LLM", "0") == "1"
        if use_llm:
            from core.llm import GigaChat

            # Соберём компактный контекст из фактических значений
            disks_ctx = []
            for line in disk_lines:
                # строка: - `/` — **58%** (5.7 GB / 9.9 GB)
                try:
                    path = line.split("`")[1]
                    pct  = line.split("**")[1].strip("*% ")
                    disks_ctx.append("{}:{}%".format(path, pct))
                except Exception:
                    pass

            ctx = []
            if isinstance(mem_total, (int, float)) and isinstance(mem_used, (int, float)):
                ctx.append("RAM_used={}B".format(int(mem_used)))
                ctx.append("RAM_total={}B".format(int(mem_total)))
            if isinstance(load1, (int, float)):
                ctx.append("load1={:.2f}".format(load1))
            if isinstance(load5, (int, float)):
                ctx.append("load5={:.2f}".format(load5))
            if isinstance(ncpu, (int, float)) and ncpu > 0:
                ctx.append("vCPU={}".format(int(ncpu)))
            if disks_ctx:
                ctx.append("disks=" + ",".join(disks_ctx))

            prompt = (
                "Ты SRE/DBA. Дано: {ctx}. "
                "Верни 1–2 коротких практичных рекомендации именно по этим значениям (RAM/нагрузка/диски). "
                "Не приводить примеры и образцы. Без списков. ≤180 символов."
            ).format(ctx="; ".join(ctx) if ctx else "нет метрик")

            tip = GigaChat().ask(prompt, max_tokens=90)
            if tip:
                tip = " ".join(tip.strip().split())
                lines.append("\n**LLM-совет:** " + tip)
    except Exception as e:
        lines.append("\n_(LLM недоступен: {})_".format(e))

    return "\n".join(lines)