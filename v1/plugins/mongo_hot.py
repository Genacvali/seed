# seed/v1/plugins/mongo_hot.py
# -*- coding: utf-8 -*-
"""
SEED plugin: mongo_hot — компактная сводка «горячих» операций Mongo из system.profile.
Вывод адаптирован под Mattermost (эмодзи + короткие строки).
"""

import os
from typing import Dict, List, Any
from fetchers.fetch_mongo import aggregate  # обёртка вокруг PyMongo.aggregate()

# --- утилиты ---------------------------------------------------------------

def _to_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default

def _to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default

def _truncate(s: str, maxlen: int = 160) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= maxlen else s[: maxlen - 1] + "…"

# --- основной хэндлер ------------------------------------------------------

def run(host: str, payload: Dict) -> str:
    """
    payload:
      mongo_uri: "mongodb://user:pass@host:27017/?authSource=admin&connect=direct"
      db: "admin"
      min_ms: 50
      limit: 10
    """
    uri   = payload["mongo_uri"]
    db    = payload.get("db", "admin")
    minms = int(payload.get("min_ms", 50))
    limit = int(payload.get("limit", 10))

    pipeline: List[Dict[str, Any]] = [
        {"$match": {"ns": {"$exists": True}, "millis": {"$gte": minms}}},
        {
            "$project": {
                "ns": 1, "op": 1, "millis": 1,
                "docsExamined": 1, "keysExamined": 1, "nreturned": 1,
                "planSummary": 1, "command": 1
            }
        },
        {"$sort": {"millis": -1}},
        {"$limit": limit},
    ]

    docs = aggregate(uri, db, "system.profile", pipeline) or []

    # Заголовок — максимально компактно
    header = f"🗡 MONGO HOT SPOTS | 🍃 {host} | ⏱ {minms}ms | 🔝{limit}"

    lines: List[str] = [header]

    for d in docs:
        ns   = str(d.get("ns", "?"))
        op   = str(d.get("op", "?"))
        ms   = _to_int(d.get("millis", 0))
        de   = _to_int(d.get("docsExamined", 0))
        ke   = _to_int(d.get("keysExamined", 0))
        nr   = _to_int(d.get("nreturned", 0))
        eff  = (_to_float(de) / _to_float(nr)) if (nr and de) else 0.0

        # Попробуем вытащить короткое имя коллекции из ns "<db>.<coll>"
        try:
            _, coll = ns.split(".", 1)
        except ValueError:
            coll = ns

        # compact line: одна строка на операцию
        # пример:  🔥 events · find · 153ms · docs=2300 keys=120 ret=34 · eff=67.6
        line = f"🔥 {coll} · {op} · {ms}ms · docs={de} keys={ke} ret={nr} · eff={eff:.1f}"

        # убираем лишнее, чтобы не разъезжалась ширина в чате
        lines.append(_truncate(line, 160))

    if len(lines) == 1:
        lines.append("✅ горячих операций не найдено (порог не превышен)")

    # Короткий LLM-совет при включенном USE_LLM
    try:
        if os.getenv("USE_LLM", "0") == "1":
            from core.llm import GigaChat
            ctx = f"topN={len(docs)}; min_ms={minms}"
            tip = GigaChat().ask(
                f"Mongo профайлер ({ctx}). Дай 1–2 лаконичных совета по ускорению (индексы/фильтры/лимиты). "
                f"Пиши конкретно и коротко, ≤120 символов.",
                max_tokens=70
            )
            if tip:
                tip = " ".join(tip.strip().split())
                lines.append(f"💡 {tip}")
    except Exception as e:
        lines.append(f"_(LLM недоступен: {e})_")

    return "\n".join(lines)