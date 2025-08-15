# seed/v1/plugins/mongo_hot.py
# -*- coding: utf-8 -*-
import os
from typing import Dict, List
from ui_ff import render_panel, bullets
from fetchers.fetch_mongo import aggregate  # твой общий аггрегатор

PIPELINE = [
    {"$match": {"ns": {"$exists": True}, "millis": {"$gte": 50}}},  # переопред. в payload
    {"$project": {"ns": 1, "op": 1, "millis": 1, "docsExamined": 1, "keysExamined": 1, "nreturned": 1}},
    {"$sort": {"millis": -1}},
    {"$limit": 10},
]

def run(host: str, payload: Dict) -> str:
    """
    payload:
      mongo_uri: "mongodb://user:pass@host:27017/?authSource=admin&connect=direct"
      db: "admin"
      min_ms: 50
      limit: 10
    """
    uri   = payload["mongo_uri"]
    db    = payload.get("db","admin")
    minms = int(payload.get("min_ms", 50))
    limit = int(payload.get("limit", 10))

    # подставим параметры в pipeline
    pipeline = list(PIPELINE)
    pipeline[0]["$match"]["millis"]["$gte"] = minms
    pipeline[3]["$limit"] = limit

    docs = aggregate(uri, db, "system.profile", pipeline) or []
    items: List[str] = []
    for d in docs:
        ns   = d.get("ns","?")
        op   = d.get("op","?")
        ms   = d.get("millis",0)
        de   = d.get("docsExamined",0)
        ke   = d.get("keysExamined",0)
        nr   = d.get("nreturned",0)
        eff  = (float(de)/float(nr)) if (nr and de) else 0.0
        items.append(f"{ns} · {op} · {ms}ms · docs={de} keys={ke} ret={nr} · scanEff≈{eff:.1f}")

    if not items:
        items.append("_hot spots не найдены_")

    # LLM
    llm_line = None
    try:
        if os.getenv("USE_LLM","0") == "1":
            from core.llm import GigaChat
            ctx = f"topN={len(docs)}; min_ms={minms}"
            tip = GigaChat().ask(
                f"Mongo профилировщик: {ctx}. Дай 1–2 кратких совета по индексации/фильтрам/лимитам. Без общих фраз. ≤160 символов.",
                max_tokens=90
            )
            if tip:
                llm_line = "💡 " + " ".join(tip.strip().split())
    except Exception as e:
        llm_line = f"_(LLM недоступен: {e})_"

    lines = []
    lines.append(f"🍃 Server: {host}")
    lines.append(f"⏱  Threshold: {minms} ms · Limit: {limit}")
    lines.append("🔥 Hot spots:")
    lines += bullets(items)
    if llm_line:
        lines.append("─" * 40)
        lines.append(llm_line)

    return render_panel("🗡  MONGO · HOT SPOTS", lines, subtitle="SEED · Final Fantasy style")