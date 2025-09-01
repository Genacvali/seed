# -*- coding: utf-8 -*-
from typing import Dict, Any
from .common import render_panel, code_table, llm_tip

def render(data: Dict[str, Any]) -> str:
    title = f"SEED · Host Inventory @ {data.get('host','?')}"
    lines = []
    if data.get("header"):
        lines.append(data["header"])
    tbl = data.get("table")
    if tbl and tbl.get("rows"):
        lines.append(code_table(tbl["headers"], tbl["rows"]))
    if data.get("llm_prompt"):
        lines.append(llm_tip(data["llm_prompt"]))
    return render_panel(title, lines)