# -*- coding: utf-8 -*-
"""
Плагин для алёрта «mongo_collscan» (или аналогичного).
Источник правды — сам алерт (labels/annotations). При наличии — добираем контекст из Telegraf.
Ожидаемые аннотации (желательно):
  - summary: "COLLSCAN > 100ms on db.coll"
  - hotspots (опционально): многострочный текст таблицей
  - last_ts (опционально): ISO-время последней записи
Лейблы:
  - host, alertname, db (опционально), ns/collection/plan/millis (если одиночный случай)
"""
import os
from typing import Dict, Any
from core.llm import GigaChat

def run(host: str, labels: Dict[str,str], annotations: Dict[str,str], payload: Dict[str,Any]) -> str:
    threshold = int(payload.get("min_ms", 50))
    limit     = int(payload.get("limit", 10))
    title = f"**SEED · Mongo Hot @ {host}**"
    header = f"• порог: {threshold} мс; показываем до {limit}"

    # Попробуем взять уже агрегированный список из annotations['hotspots']
    hotspots = annotations.get("hotspots","").strip()
    if not hotspots:
        # Сконструируем минимум из лейблов, если что-то прилетело
        ns     = labels.get("ns") or labels.get("collection") or "n/a"
        op     = labels.get("op") or "n/a"
        millis = labels.get("millis") or labels.get("time_ms") or "n/a"
        plan   = labels.get("plan") or labels.get("planSummary") or "n/a"
        hotspots = f"{'namespace':26} {'op':8} {'time':>8}  details\n" \
                   f"{'-'*60}\n" \
                   f"{ns:26} {op:8} {str(millis)+'ms':>8}  plan:{plan}"

    last_ts = annotations.get("last_ts") or ""

    # LLM совет
    tip = ""
    try:
        if os.getenv("USE_LLM","0") == "1":
            ctx = hotspots.splitlines()[:5]
            prompt = (
                "Дано несколько медленных операций Mongo (возможно COLLSCAN). "
                "Сформулируй 1–2 коротких конкретных совета по индексам/фильтрам, ≤160 символов."
                f"\nПримеры строк:\n{chr(10).join(ctx)}"
            )
            tip = GigaChat().ask(prompt, max_tokens=90).strip()
            tip = " ".join(tip.split())
    except Exception as e:
        tip = f"(LLM недоступен: {e})"

    lines = [title, header, "```", hotspots, "```"]
    if last_ts:
        lines.append(f"_Последняя запись: {last_ts}_")
    if tip:
        lines.append("\n**Совет:** " + tip)
    return "\n".join(lines)
