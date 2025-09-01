# -*- coding: utf-8 -*-
from typing import Dict, Any, List

def run(host: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ожидаем в payload:
      db: "seed_demo"
      min_ms: 50
      limit: 10
      hotspots: [ { ns, op, millis, docsExamined, keysExamined, planSummary, ts? }, ... ]
    Агент в БД не ходит: данные сюда приносит Alertmanager/внешний сборщик.
    """
    db      = payload.get("db","?")
    min_ms  = int(payload.get("min_ms", 50))
    limit   = int(payload.get("limit", 10))
    items: List[Dict[str, Any]] = payload.get("hotspots") or []

    rows: List[List[str]] = []
    last_ts = None
    for d in items[:limit]:
        ns   = d.get("ns","?")
        op   = d.get("op","?")
        ms   = d.get("millis",0)
        de   = d.get("docsExamined",0)
        ke   = d.get("keysExamined",0)
        plan = d.get("planSummary","?")
        if d.get("ts"):
            last_ts = d["ts"]
        rows.append([ns, op, f"{int(ms)}ms", f"docs:{de}", f"keys:{ke}", f"plan:{plan}"])

    # Короткий LLM prompt (по желанию)
    top_plan = {}
    for r in rows:
        plan = r[-1].split(":",1)[-1]
        top_plan[plan] = top_plan.get(plan, 0) + 1
    hot = ", ".join([f"{k}:{v}" for k,v in sorted(top_plan.items(), key=lambda x: -x[1])])

    llm_prompt = (
        f"MongoDB hot ops (db={db}, min_ms={min_ms}): plans={hot or 'n/a'}. "
        f"Дай 1–2 кратких рекомендаций (индексы/фильтры/лимиты). Без воды."
    )

    return {
        "plugin": "mongo_hot",
        "host": host,
        "db": db,
        "min_ms": min_ms,
        "limit": limit,
        "shown": len(rows),
        "rows": rows,
        "last_ts": last_ts,
        "llm_prompt": llm_prompt
    }