# -*- coding: utf-8 -*-
import os
from typing import Dict, Any, List
from fetchers.telegraf import get_gauge
from core import config
from core.llm import GigaChat

def _fmt_bytes(n):
    try:
        n = float(n)
    except:
        return "n/a"
    units = ["B","KB","MB","GB","TB","PB"]
    i=0
    while n>=1024 and i<len(units)-1:
        n/=1024; i+=1
    return f"{n:.1f} {units[i]}"

def run(host: str, labels: Dict[str,str], annotations: Dict[str,str], payload: Dict[str,Any]) -> str:
    telegraf_url = payload.get("telegraf_url") or config.default_telegraf_url(host)
    paths: List[str] = payload.get("paths") or ["/", "/data"]

    # RAM
    mem_total = get_gauge(host, "mem_total", telegraf_url=telegraf_url)
    mem_avail = get_gauge(host, "mem_available", telegraf_url=telegraf_url)
    if isinstance(mem_total, float) and isinstance(mem_avail, float):
        mem_used = mem_total - mem_avail
        ram_line = f"vRAM: {_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)}"
    else:
        ram_line = "vRAM: n/a"

    # CPU/Load
    load1 = get_gauge(host, "system_load1", telegraf_url=telegraf_url)
    load5 = get_gauge(host, "system_load5", telegraf_url=telegraf_url)
    ncpu  = get_gauge(host, "system_n_cpus", telegraf_url=telegraf_url)
    if isinstance(load1, float) or isinstance(load5, float):
        if isinstance(ncpu, float):
            cpu_line = f"CPU: {int(ncpu)} vCPU • load1 {load1 or 0:.2f} • load5 {load5 or 0:.2f}"
        else:
            cpu_line = f"CPU: load1 {load1 or 0:.2f} • load5 {load5 or 0:.2f}"
    else:
        cpu_line = "CPU: n/a"

    # Disks
    disk_lines = []
    for p in paths:
        used_pct = get_gauge(host, "disk_used_percent", labels={"path": p}, telegraf_url=telegraf_url)
        used     = get_gauge(host, "disk_used",         labels={"path": p}, telegraf_url=telegraf_url)
        total    = get_gauge(host, "disk_total",        labels={"path": p}, telegraf_url=telegraf_url)
        if not (isinstance(used_pct, float) and isinstance(used, float) and isinstance(total, float)):
            continue
        disk_lines.append(f"{p:6} {used_pct:5.0f}% ({_fmt_bytes(used)} / {_fmt_bytes(total)})")
    if not disk_lines:
        disk_lines.append("(нет данных по дискам)")

    # LLM совет (кратко)
    tip = ""
    try:
        if os.getenv("USE_LLM","0") == "1":
            ctx = f"load1={load1} load5={load5} disks={';'.join(disk_lines[:2])}"
            tip = GigaChat().ask(
                f"Коротко оцени хост: {ctx}. Дай 1–2 практичных совета (<=160 символов), без общих фраз.",
                max_tokens=90
            ).strip()
            tip = " ".join(tip.split())
    except Exception as e:
        tip = f"(LLM недоступен: {e})"

    # Красивый компактный вывод
    lines = []
    lines.append(f"**SEED · Host Inventory @ {host}**")
    lines.append(f"- {cpu_line}")
    lines.append(f"- {ram_line}")
    lines.append("**Disks:**")
    lines += [f"  • {x}" for x in disk_lines]
    if tip:
        lines.append("\n**Совет:** " + tip)
    return "\n".join(lines)
