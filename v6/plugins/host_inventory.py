# -*- coding: utf-8 -*-
from typing import Dict, Any, List, Optional
from core.config import CFG
from fetchers.telegraf import get_gauge

def _fmt_bytes(n: Optional[float]) -> str:
    if n is None: return "n/a"
    n = float(n)
    units = ["B","KB","MB","GB","TB","PB"]
    for u in units:
        if n < 1024.0: return f"{n:.1f} {u}"
        n /= 1024.0
    return f"{n:.1f} EB"

def run(host: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload:
      paths: ["/", "/data"]
      telegraf_url: override (иначе CFG.telegraf_url)
    """
    tg = payload.get("telegraf_url") or CFG.telegraf_url
    paths: List[str] = payload.get("paths") or ["/", "/data"]

    # RAM
    mem_total = get_gauge(tg, "mem_total")
    mem_avail = get_gauge(tg, "mem_available")
    mem_used  = (mem_total - mem_avail) if (isinstance(mem_total,(int,float)) and isinstance(mem_avail,(int,float))) else None

    # LOAD / CPU
    load1  = get_gauge(tg, "system_load1")
    load5  = get_gauge(tg, "system_load5")
    ncpu   = get_gauge(tg, "system_n_cpus")

    header = f"vCPU: {int(ncpu) if ncpu else 'n/a'} • load1: {load1 if load1 is not None else 'n/a'} • load5: {load5 if load5 is not None else 'n/a'} • RAM: {_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)}"

    rows = []
    for p in paths:
        used_pct   = get_gauge(tg, "disk_used_percent", labels={"path": p})
        used_bytes = get_gauge(tg, "disk_used",         labels={"path": p})
        tot_bytes  = get_gauge(tg, "disk_total",        labels={"path": p})
        free_bytes = (tot_bytes - used_bytes) if (isinstance(tot_bytes,(int,float)) and isinstance(used_bytes,(int,float))) else None
        if used_pct is None or tot_bytes is None:
            continue
        rows.append([
            p,
            _fmt_bytes(tot_bytes),
            _fmt_bytes(used_bytes),
            _fmt_bytes(free_bytes if free_bytes is not None else 0.0),
            f"{used_pct:.0f}%" if isinstance(used_pct,(int,float)) else "n/a"
        ])

    # LLM prompt (опционально)
    llm_prompt = None
    if rows:
        top = ", ".join([f"{r[0]}:{r[-1]}" for r in rows[:3]])
        llm_prompt = f"Хост {host}. Нагрузка: load1={load1}, vCPU={ncpu}. Диски: {top}. Дай 1–2 коротких рекомендации по оптимизации."

    return {
        "plugin": "host_inventory",
        "host": host,
        "header": header,
        "table": {
            "headers": ["mount","total","used","free","%"],
            "rows": rows,
        },
        "llm_prompt": llm_prompt,
    }