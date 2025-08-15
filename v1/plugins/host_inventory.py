# seed/v1/plugins/host_inventory.py
# -*- coding: utf-8 -*-
import os, re
from typing import Dict, List, Union, Optional
from fetchers.telegraf import get_gauge
from ui_ff import render_panel, bullets

def _fmt_bytes(n: Optional[Union[float, int]]) -> str:
    if n is None: return "n/a"
    n = float(n)
    for u in ("B","KB","MB","GB","TB","PB"):
        if n < 1024: return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} EB"

def _percent(v: Optional[float]) -> str:
    return f"{v:.0f}%" if isinstance(v,(int,float)) else "n/a"

def run(host: str, payload: Dict) -> str:
    port  = int(payload.get("port") or os.getenv("TELEGRAF_PORT", 9216))
    paths: List[str] = payload.get("paths") or ["/", "/data"]
    telegraf_url = payload.get("telegraf_url")
    if telegraf_url:
        m = re.match(r"https?://([^:/]+):(\d+)", telegraf_url.strip())
        if m:
            host = m.group(1); port = int(m.group(2))

    # RAM
    mem_total = get_gauge(host, "mem_total", port=port)
    mem_avail = get_gauge(host, "mem_available", port=port)
    mem_used  = (mem_total - mem_avail) if (
        isinstance(mem_total,(int,float)) and isinstance(mem_avail,(int,float))
    ) else None

    # CPU/Load
    load1  = get_gauge(host, "system_load1", port=port)
    load5  = get_gauge(host, "system_load5", port=port)
    ncpu   = get_gauge(host, "system_n_cpus", port=port)
    if (load1 is not None) or (load5 is not None):
        l1 = load1 if isinstance(load1,(int,float)) else 0.0
        l5 = load5 if isinstance(load5,(int,float)) else 0.0
        cpu_line = f"🧮 CPU: {int(ncpu)} vCPU · load1 {l1:.2f} · load5 {l5:.2f}" if isinstance(ncpu,(int,float)) and ncpu>0 \
                   else f"🧮 CPU: load1 {l1:.2f} · load5 {l5:.2f}"
    else:
        cpu_line = "🧮 CPU: n/a"

    # Disks
    disk_items = []
    for p in paths:
        used_pct   = get_gauge(host, "disk_used_percent", labels={"path": p}, port=port)
        used_bytes = get_gauge(host, "disk_used",         labels={"path": p}, port=port)
        tot_bytes  = get_gauge(host, "disk_total",        labels={"path": p}, port=port)
        if not (isinstance(used_pct,(int,float)) and isinstance(used_bytes,(int,float)) and isinstance(tot_bytes,(int,float))):
            continue
        disk_items.append(f"`{p}` — **{_percent(used_pct)}** ({_fmt_bytes(used_bytes)} / {_fmt_bytes(tot_bytes)})")

    if not disk_items:
        disk_items.append("_нет данных по дискам из Telegraf_")

    # LLM совет (по делу, коротко)
    llm_line = None
    try:
        if os.getenv("USE_LLM","0") == "1":
            from core.llm import GigaChat
            ctx = []
            if isinstance(mem_total,(int,float)) and isinstance(mem_used,(int,float)):
                ctx.append(f"RAM_used={int(mem_used)}B; RAM_total={int(mem_total)}B")
            if isinstance(load1,(int,float)): ctx.append(f"load1={load1:.2f}")
            if isinstance(load5,(int,float)): ctx.append(f"load5={load5:.2f}")
            if isinstance(ncpu,(int,float)) and ncpu>0: ctx.append(f"vCPU={int(ncpu)}")
            if disk_items:
                # вытащим /path:percent
                pairs=[]
                for d in disk_items:
                    try:
                        path = d.split("`")[1]
                        pct  = d.split("**")[1].strip("*% ")
                        pairs.append(f"{path}:{pct}%")
                    except Exception:
                        pass
                if pairs: ctx.append("disks=" + ",".join(pairs))
            prompt = (
                "Ты SRE/DBA. По метрикам [{ctx}] дай 1–2 коротких практичных рекомендации "
                "именно по этим значениям (RAM/нагрузка/диски). Без примеров и общих фраз. ≤160 символов."
            ).format(ctx="; ".join(ctx) if ctx else "нет метрик")
            tip = GigaChat().ask(prompt, max_tokens=90)
            if tip:
                llm_line = "💡 " + " ".join(tip.strip().split())
    except Exception as e:
        llm_line = f"_(LLM недоступен: {e})_"

    # Собираем панель
    lines = []
    lines.append(f"🏷 Host: {host}")
    if isinstance(mem_total,(int,float)):
        lines.append(f"💾 RAM: {_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)} (free {_fmt_bytes(mem_avail)})")
    else:
        lines.append("💾 RAM: n/a")
    lines.append(cpu_line)
    lines.append("─" * 40)
    lines.append("💽 Disks:")
    lines += bullets(disk_items)
    if llm_line:
        lines.append("─" * 40)
        lines.append(llm_line)

    return render_panel("🖥  HOST STATUS PANEL", lines, subtitle="SEED · Final Fantasy style")