# -*- coding: utf-8 -*-
"""
SEED plugin: host_inventory (через Telegraf Prometheus exporter).
Ничего локально не читает — только HTTP-эндпойнт Telegraf.

payload:
  paths: ["/", "/data"]        # какие тома показать
  port:  9216                  # если нестандартный
  telegraf_url: "http://host:9216"  # имеет приоритет над host+port
"""

import os
import re
from typing import Dict, List, Optional, Union

from fetchers.telegraf import get_gauge
from ui_format import header, cli_table, tips_block

Number = Union[int, float]

def _fmt_bytes(n: Optional[Number]) -> str:
    if n is None:
        return "n/a"
    n = float(n)
    for u in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} EB"

def _pct(x: Optional[Number]) -> str:
    return f"{float(x):.0f}%" if isinstance(x, (int, float)) else "n/a"

def _pick_host_port(host: str, port: int, telegraf_url: Optional[str]):
    if telegraf_url:
        m = re.match(r"https?://([^:]+):(\d+)", telegraf_url)
        if m:
            return m.group(1), int(m.group(2))
    return host, port

def run(host: str, payload: Dict) -> str:
    # --- входные параметры ---
    port  = int(payload.get("port") or os.getenv("TELEGRAF_PORT", 9216))
    paths: List[str] = payload.get("paths") or ["/", "/data"]
    host, port = _pick_host_port(host, port, payload.get("telegraf_url"))

    # --- RAM ---
    mem_total = get_gauge(host, "mem_total", port=port)
    mem_avail = get_gauge(host, "mem_available", port=port)
    mem_used  = (mem_total - mem_avail) if isinstance(mem_total, (int, float)) and isinstance(mem_avail, (int, float)) else None

    # --- CPU/Load (если есть) ---
    load1  = get_gauge(host, "system_load1", port=port)
    load5  = get_gauge(host, "system_load5", port=port)
    ncpu   = get_gauge(host, "system_n_cpus", port=port)

    # --- Диски по указанным path ---
    disk_rows = []
    for p in paths:
        used_pct   = get_gauge(host, "disk_used_percent", labels={"path": p}, port=port)
        used_bytes = get_gauge(host, "disk_used",         labels={"path": p}, port=port)
        tot_bytes  = get_gauge(host, "disk_total",        labels={"path": p}, port=port)
        free_bytes = (tot_bytes - used_bytes) if isinstance(tot_bytes, (int, float)) and isinstance(used_bytes, (int, float)) else None

        # показываем только если Telegraf реально отдаёт метрики по этому path
        if all(isinstance(v, (int, float)) for v in (used_pct, used_bytes, tot_bytes)):
            disk_rows.append([
                p,
                _fmt_bytes(tot_bytes),
                _fmt_bytes(used_bytes),
                _fmt_bytes(free_bytes),
                _pct(used_pct),
            ])

    # --- Заголовок и мета ---
    meta_bits = []
    if isinstance(ncpu, (int, float)):
        meta_bits.append(f"vCPU: {int(ncpu)}")
    if isinstance(load1, (int, float)):
        meta_bits.append(f"load1: {load1:.2f}")
    if isinstance(load5, (int, float)):
        meta_bits.append(f"load5: {load5:.2f}")
    if isinstance(mem_total, (int, float)) and isinstance(mem_used, (int, float)):
        meta_bits.append(f"RAM: {_fmt_bytes(mem_used)} / {_fmt_bytes(mem_total)}")
    meta = " • ".join(meta_bits) if meta_bits else None

    parts: List[str] = [header("Host Inventory", host, meta)]

    # --- Таблица дисков ---
    if disk_rows:
        parts.append(
            cli_table(
                disk_rows,
                headers=["mount", "total", "used", "free", "%"],
                align=['l', 'r', 'r', 'r', 'r'],
            )
        )
    else:
        parts.append("_нет данных по дискам из Telegraf_")

    # --- LLM: короткая рекомендация (опционально) ---
    tips: List[str] = []
    try:
        if os.getenv("USE_LLM", "0") == "1":
            from core.llm import GigaChat
            ctx = []
            if isinstance(mem_used, (int, float)) and isinstance(mem_total, (int, float)):
                ctx.append(f"ram_used={int(mem_used)}B ram_total={int(mem_total)}B")
            if isinstance(load1, (int, float)):
                ctx.append(f"load1={load1:.2f}")
            if disk_rows:
                # включим проблемные path (>=85%)
                hot = [r[0] for r in disk_rows if r[4] != "n/a" and float(r[4].rstrip('%')) >= 85]
                if hot:
                    ctx.append("hot=" + ",".join(hot))
            prompt = (
                "Ты SRE. Дано: {ctx}. Сформулируй 1–2 очень кратких совета по RAM/нагрузке/дискам, "
                "исходя из фактических значений. Без общих фраз, ≤140 символов."
            ).format(ctx="; ".join(ctx) if ctx else "нет метрик")
            txt = GigaChat().ask(prompt, max_tokens=90) or ""
            short = " ".join(txt.strip().split())
            if short:
                # разобьём максимум на 2 пункта
                for s in short.replace("\n", " ").split(". "):
                    s = s.strip(" •-–—.\n\t")
                    if s:
                        tips.append(s)
                    if len(tips) >= 2:
                        break
    except Exception as e:
        tips = [f"LLM недоступен: {e}"]

    tips_md = tips_block(tips, title="Советы")
    if tips_md:
        parts.append(tips_md)

    return "\n".join(parts)