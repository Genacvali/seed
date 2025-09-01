# -*- coding: utf-8 -*-
from typing import Dict, Any
from .common import render_panel, code_table, llm_tip

def render(data: Dict[str, Any]) -> str:
    title = f"SEED · Mongo Hot @ {data.get('host','?')}"
    lines = []
    meta = f"• БД: {data.get('db','?')}; порог: {data.get('min_ms','?')} мс; записи: {data.get('shown',0)} (показано до {data.get('limit','?')})"
    lines.append(meta)

    rows = data.get("rows") or []
    if rows:
        lines.append(code_table(
            ["namespace","op","time","details1","details2","plan"],
            rows
        ))
    if data.get("last_ts"):
        lines.append(f"\nПоследняя запись: {data['last_ts']}")
    if data.get("llm_prompt"):
        lines.append("\n**Советы LLM:**")
        lines.append(llm_tip(data["llm_prompt"]))
    return render_panel(title, lines)