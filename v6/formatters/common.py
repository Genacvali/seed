# -*- coding: utf-8 -*-
from typing import List, Dict, Any
from core.config import CFG
from core.llm import GigaChat

def bullets(lines: List[str]) -> List[str]:
    return [f"• {x}" for x in lines]

def code_table(headers: List[str], rows: List[List[str]]) -> str:
    # выравнивание фикс. шириной столбцов
    cols = len(headers)
    widths = [len(h) for h in headers]
    for r in rows:
        for i in range(cols):
            widths[i] = max(widths[i], len(str(r[i])) if i < len(r) else 0)

    def fmt_row(arr: List[str]) -> str:
        cells = []
        for i, c in enumerate(arr):
            w = widths[i]
            cells.append(str(c).ljust(w))
        return "  ".join(cells)

    lines = []
    lines.append(fmt_row(headers))
    lines.append("  ".join(["-" * w for w in widths]))
    for r in rows:
        lines.append(fmt_row(r))
    return "```\n" + "\n".join(lines) + "\n```"

def render_panel(title: str, lines: List[str]) -> str:
    return f"**{title}**\n" + "\n".join(lines)

def llm_tip(prompt: str) -> str:
    if not CFG.use_llm:
        return ""
    try:
        tip = GigaChat().ask(prompt, max_tokens=90)
        tip = " ".join((tip or "").strip().split())
        return f"\n**Совет:** {tip}" if tip else ""
    except Exception as e:
        return f"\n_(LLM недоступен: {e})_"

def render_generic(data: Dict[str, Any]) -> str:
    title = data.get("title") or f"SEED · {data.get('plugin','event')}"
    lines = []
    for k in ("header","subtitle"):
        if data.get(k): lines.append(data[k])

    table = data.get("table")
    if table and table.get("rows"):
        lines.append(code_table(table.get("headers") or [], table["rows"]))

    for sec in data.get("lines") or []:
        lines.append(f"- {sec}")

    if data.get("llm_prompt"):
        lines.append(llm_tip(data["llm_prompt"]))

    return render_panel(title, lines)