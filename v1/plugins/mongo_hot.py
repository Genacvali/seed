# seed/v1/plugins/mongo_hot.py
# -*- coding: utf-8 -*-
import os
from typing import Dict, List, Any
from ui_ff import render_panel, bullets
from fetchers.fetch_mongo import aggregate

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
                "planSummary": 1,
                "command": 1  # тут могут быть query/filter/sort и т.д.
            }
        },
        {"$sort": {"millis": -1}},
        {"$limit": limit},
    ]

    docs = aggregate(uri, db, "system.profile", pipeline) or []

    items: List[str] = []
    for d in docs:
        ns   = str(d.get("ns", "?"))
        op   = str(d.get("op", "?"))
        ms   = _to_int(d.get("millis", 0))
        de   = _to_int(d.get("docsExamined", 0))
        ke   = _to_int(d.get("keysExamined", 0))
        nr   = _to_int(d.get("nreturned", 0))
        eff  = (_to_float(de) / _to_float(nr)) if (nr and de) else 0.0
        plan = d.get("planSummary")
        if not isinstance(plan, str):
            plan = None

        # попытаемся понять коллекцию из ns: "<db>.<coll>"
        try:
            ns_parts = ns.split(".", 1)
            coll = ns_parts[1] if len(ns_parts) == 2 else ns
        except Exception:
            coll = ns

        # подцепим кусочек фильтра/сортировки, если есть
        cmd = d.get("command") or {}
        qshape = None
        # разные версии драйверов кладут либо filter, либо query
        for k in ("filter", "query", "q"):
            if k in cmd:
                qshape = str(cmd[k])
                break
        if not qshape and "pipeline" in cmd:
            qshape = "[agg pipeline]"
        if "sort" in cmd:
            qshape = (qshape or "") + f" sort={cmd['sort']}"

        line = f"{ns} · {op} · {ms}ms · docs={de} keys={ke} ret={nr}"
        if plan:
            line += f" · plan={plan}"
        if qshape:
            line += f" · {qshape}"

        # компактная метрика эффективности скана
        line += f" · scanEff≈{eff:.1f}"

        items.append(_truncate(line, 180))

    if not items:
        items.append("_заметных горячих запросов не найдено_")

    # LLM (короткий, по делу)
    llm_line = None
    try:
        if os.getenv("USE_LLM", "0") == "1":
            from core.llm import GigaChat
            ctx = f"topN={len(docs)}; min_ms={minms}; limit={limit}"
            tip = GigaChat().ask(
                f"Mongo профайлер ({ctx}). Дай 1–2 кратких совета по индексации/фильтрам/лимитам. "
                f"Пиши по делу, ≤160 симв., без общих фраз.",
                max_tokens=90
            )
            if tip:
                llm_line = "💡 " + " ".join(tip.strip().split())
    except Exception as e:
        llm_line = f"_(LLM недоступен: {e})_"

    title = f"🗡  MONGO · HOT SPOTS · {db}"
    lines = [
        f"🍃 Server: {host}",
        f"⏱  Threshold: {minms} ms · Limit: {limit}",
        "🔥 Hot spots:",
        *bullets(items)
    ]
    if llm_line:
        lines += ["─" * 40, llm_line]

    return render_panel(title, lines, subtitle="SEED")