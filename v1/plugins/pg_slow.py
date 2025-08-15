# seed/v1/plugins/pg_slow.py
# -*- coding: utf-8 -*-
import os
from typing import Dict, List, Tuple
from ui_ff import render_panel, bullets
from fetchers.fetch_sql import fetch_sql  # твой уже существующий

def run(host: str, payload: Dict) -> str:
    """
    payload:
      dsn_tpl: "postgresql://user:pass@{host}:5432/postgres"
      limit: 5
    """
    limit = int(payload.get("limit", 5))
    dsn = payload["dsn_tpl"].format(host=host)
    rows: List[Tuple[str, float]] = fetch_sql(
        "postgres", None,
        f"SELECT query, total_exec_time/1000.0 AS sec FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT {limit};",
        {"dsn": dsn}
    ) or []

    items=[]
    for q, sec in rows:
        sec = float(sec)
        items.append(f"{int(sec)}s · {q[:180].replace('\\n',' ')}")

    if not items:
        items.append("_заметных медленных запросов не найдено_")

    # LLM краткий совет
    llm_line = None
    try:
        if os.getenv("USE_LLM","0") == "1":
            from core.llm import GigaChat
            ctx = f"кол-во тяжелых запросов={len(rows)}; топ1 сек={int(rows[0][1]) if rows else 0}"
            tip = GigaChat().ask(
                f"По данным PG ({ctx}) дай 1–2 кратких совета по оптимизации (индексы/батчи/параметры). Без общих фраз. ≤160 символов.",
                max_tokens=90
            )
            if tip:
                llm_line = "💡 " + " ".join(tip.strip().split())
    except Exception as e:
        llm_line = f"_(LLM недоступен: {e})_"

    lines = []
    lines.append(f"🗄  Server: {host}")
    lines.append("🔥 Top slow statements:")
    lines += bullets(items)
    if llm_line:
        lines.append("─" * 40)
        lines.append(llm_line)

    return render_panel("🧙 POSTGRES · SLOW QUERIES", lines, subtitle="SEED · Final Fantasy style")