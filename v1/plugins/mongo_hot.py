# -*- coding: utf-8 -*-
"""
Плагин 'mongo_hot': берёт профайлер MongoDB (system.profile) и
печатает «CLI-таблицу» через единый форматтер.
Плагин занимается только данными; оформление — в ui_format.py.
"""

import os
from typing import Dict, List
from fetchers.fetch_mongo import aggregate
from ui_format import header, cli_table, tips_block, small_note

# Базовый pipeline (min_ms и limit подставим в рантайме)
BASE_PIPELINE = [
    {"$match": {"ns": {"$exists": True}, "millis": {"$gte": 50}}},
    {"$project": {"ns": 1, "op": 1, "millis": 1, "docsExamined": 1, "keysExamined": 1, "nreturned": 1, "planSummary": 1, "ts": 1}},
    {"$sort": {"millis": -1}},
    {"$limit": 10},
]

def _row(doc: dict):
    ns   = doc.get("ns", "?")
    op   = doc.get("op", "?")
    ms   = doc.get("millis", 0)
    docs = doc.get("docsExamined", 0)
    keys = doc.get("keysExamined", 0)
    plan = doc.get("planSummary", "")
    # нормализуем time
    time = f"{int(ms)}ms"
    return [ns, op, time, str(docs), str(keys), plan or ""]

def run(host: str, payload: Dict) -> str:
    """
    payload:
      mongo_uri: mongodb://user:pass@host:27017/?authSource=admin&connect=direct
      db:        admin
      min_ms:    50
      limit:     10
    """
    uri   = payload["mongo_uri"]
    db    = payload.get("db", "admin")
    minms = int(payload.get("min_ms", 50))
    limit = int(payload.get("limit", 10))

    # подставляем параметры
    pipeline = list(BASE_PIPELINE)
    pipeline[0]["$match"]["millis"]["$gte"] = minms
    pipeline[3]["$limit"] = limit

    docs = aggregate(uri, db, "system.profile", pipeline) or []

    # ---- заголовок + мета
    meta = f"• БД: {db}  • порог: {minms} мс  • найдено: {len(docs)}  • лимит: {limit}"
    parts: List[str] = [header("Mongo Hot", host, meta)]

    # ---- таблица
    rows = [_row(d) for d in docs]
    table_md = cli_table(
        rows,
        headers=["namespace", "op", "time", "docs", "keys", "plan"],
        align=['l', 'l', 'r', 'r', 'r', 'l'],
    )
    parts.append(table_md)

    # ---- хвост: timestamp последней записи, если есть
    try:
        last_ts = max(d.get("ts") for d in docs if d.get("ts"))
        parts.append(small_note(f"Последняя запись профайлера: {last_ts}"))
    except Exception:
        pass

    # ---- LLM (опционально)
    tips: List[str] = []
    try:
        if os.getenv("USE_LLM", "0") == "1":
            from core.llm import GigaChat
            # контекст: первые N строк, min_ms
            ctx = f"min_ms={minms}; topN={min(len(rows), 5)}; sample={'; '.join(r[0] + '/' + r[1] for r in rows[:5])}"
            prompt = (
                "Ты DBA по MongoDB. Дано из профайлера: {ctx}. "
                "Сформулируй 2 кратких и практичных совета по индексации/фильтрам/лимитам. "
                "Без общих фраз, без кода, ≤120 символов каждый."
            ).format(ctx=ctx)
            txt = GigaChat().ask(prompt, max_tokens=120) or ""
            # распилим на 1–2 коротких предложения
            for s in (txt.replace("\n", " ").split(". ")):
                s = s.strip(" •-–—\n\t. ")
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