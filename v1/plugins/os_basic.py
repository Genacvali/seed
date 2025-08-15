# -*- coding: utf-8 -*-
import os, re, requests
from core.llm import GigaChat
USE_LLM = os.getenv("USE_LLM","0") == "1"

TELEGRAF_URL = os.getenv("TELEGRAF_URL")  # например http://<host>:9216/metrics

def _get_metric(name: str, text: str, label=None):
    pat = rf'^{re.escape(name)}(?:\{{[^}}]*\}})?\s+([0-9.eE+-]+)$'
    for line in text.splitlines():
        if name not in line: 
            continue
        if label and label not in line:
            continue
        m = re.match(pat, line)
        if m:
            try: return float(m.group(1))
            except: pass
    return None

def run(host: str, payload: dict) -> str:
    # 1) тянем метрики
    r = requests.get(TELEGRAF_URL, timeout=10, verify=False)
    txt = r.text

    mem_total = _get_metric("node_memory_MemTotal_bytes", txt)
    mem_avail = _get_metric("node_memory_MemAvailable_bytes", txt)
    used_pct  = None
    if mem_total and mem_avail:
        used_pct = (mem_total - mem_avail) / mem_total * 100.0

    # 2) готовим короткий паспорт
    lines = [f"**SEED · Сервер {host} — краткий паспорт**"]
    if used_pct is not None:
        lines.append(f"• Память: **~{used_pct:.0f}%** занято")
    cpu_user = _get_metric("node_cpu_seconds_total", txt, 'mode="user"')
    if cpu_user is not None:
        lines.append(f"• CPU user counter: {cpu_user:.0f} сек")
    root_used = _get_metric("node_filesystem_usage_bytes", txt, 'mountpoint="/"') or None
    if root_used:
        lines.append(f"• Диск `/`: usage_bytes ≈ {root_used/1e9:.1f} ГБ")
    lines.append("_(метрики расширяются плагином; Telegraf отдаёт /metrics)_")

    # 3) необязательный совет LLM
    if USE_LLM:
        ctx = f"mem_used_pct={used_pct:.0f if used_pct else 0}; cpu_user={cpu_user}"
        try:
            tip = GigaChat().ask(
                f"Дай 3 коротких практичных совета по наблюдаемости и чистке хоста {host}. Контекст: {ctx}",
                max_tokens=180
            )
            if tip:
                lines.append("\n**Совет LLM:**\n" + tip)
        except Exception as e:
            lines.append(f"\n_(LLM недоступен: {e})_")

    return "\n".join(lines)