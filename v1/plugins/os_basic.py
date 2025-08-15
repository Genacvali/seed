# -*- coding: utf-8 -*-
"""
SEED plugin: os_basic — компактная сводка по ОС из Telegraf (без SSH/локального доступа).
Показывает uptime, load, cpu, память. Подходит как «быстрый пинг» хоста.

payload:
  port: 9216
  telegraf_url: "http://host:9216"  # имеет приоритет
"""

import os
import re
from typing import Dict, Optional, Union, List

from fetchers.telegraf import get_gauge
from ui_format import header, cli_table, tips_block

Number = Union[int, float]

def _fmt_sec(s: Optional[Number]) -> str:
    if not isinstance(s, (int, float)):
        return "n/a"
    s = int(s)
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    if d:
        return f"{d}d {h}h {m}m"
    return f"{h}h {m}m"

def _pick_host_port(host: str, port: int, telegraf_url: Optional[str]):
    if telegraf_url:
        m = re.match(r"https?://([^:]+):(\d+)", telegraf_url)
        if m:
            return m.group(1), int(m.group(2))
    return host, port

def run(host: str, payload: Dict) -> str:
    port = int(payload.get("port") or os.getenv("TELEGRAF_PORT", 9216))
    host, port = _pick_host_port(host, port, payload.get("telegraf_url"))

    load1  = get_gauge(host, "system_load1", port=port)
    load5  = get_gauge(host, "system_load5", port=port)
    ncpu   = get_gauge(host, "system_n_cpus", port=port)
    upsec  = get_gauge(host, "system_uptime", port=port) or get_gauge(host, "system_uptime_seconds", port=port)

    meta = []
    if isinstance(ncpu, (int, float)): meta.append(f"vCPU: {int(ncpu)}")
    if isinstance(load1, (int, float)): meta.append(f"load1: {load1:.2f}")
    if isinstance(load5, (int, float)): meta.append(f"load5: {load5:.2f}")
    if isinstance(upsec, (int, float)):  meta.append(f"uptime: {_fmt_sec(upsec)}")

    parts: List[str] = [header("OS Basic", host, " • ".join(meta) if meta else None)]

    # минимальная таблица показателей
    rows = [
        ["load1", f"{load1:.2f}" if isinstance(load1,(int,float)) else "n/a"],
        ["load5", f"{load5:.2f}" if isinstance(load5,(int,float)) else "n/a"],
        ["vCPU",  f"{int(ncpu)}" if isinstance(ncpu,(int,float)) else "n/a"],
        ["uptime", _fmt_sec(upsec)],
    ]
    parts.append(cli_table(rows, headers=["metric", "value"], align=['l','r']))

    # короткий совет (опционально)
    tips = []
    try:
        if os.getenv("USE_LLM", "0") == "1":
            from core.llm import GigaChat
            ctx = f"vCPU={int(ncpu) if isinstance(ncpu,(int,float)) else 'n/a'} load1={load1} load5={load5} uptime={_fmt_sec(upsec)}"
            txt = GigaChat().ask(
                f"Дано: {ctx}. Дай 1 краткий совет по стабильности/нагрузке (≤120 символов), без общих фраз.",
                max_tokens=60
            ) or ""
            short = " ".join(txt.strip().split())
            if short:
                tips.append(short)
    except Exception as e:
        tips = [f"LLM недоступен: {e}"]

    tips_md = tips_block(tips, title="Совет")
    if tips_md:
        parts.append(tips_md)

    return "\n".join(parts)