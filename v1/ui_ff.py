# seed/v1/ui_ff.py
# -*- coding: utf-8 -*-
"""
FF-style renderer for Mattermost/Markdown.
Рисует «панель персонажа» в стиле JRPG с рамкой (в код-блоке),
чтобы верстка в Mattermost не «плыла».
"""

from typing import List, Optional

# символы рамки
TL, TR, BL, BR = "╔", "╗", "╚", "╝"
HL, VL = "═", "║"
SEP_T = "╠"
SEP_M = "─"
SEP_TR = "╣"
DOT = "•"

def _visible_len(s: str) -> int:
    # грубо: считаем ширину по len; эмодзи и wide-символы могут «ехать»,
    # но внутри код-блока MM обычно монопробельный шрифт, выглядит ровно.
    return len(s)

def _pad(s: str, width: int) -> str:
    return s + " " * (width - _visible_len(s))

def render_panel(title: str, lines: List[str], subtitle: Optional[str] = None) -> str:
    # вычислим ширину по самым длинным строкам и заголовку
    content = []
    maxw = _visible_len(title)
    if subtitle:
        maxw = max(maxw, _visible_len(subtitle))
    for ln in lines:
        for part in ln.split("\n"):
            maxw = max(maxw, _visible_len(part))
            content.append(part)

    pad = 2  # отступы слева/справа
    inner = maxw + pad * 2
    border_top    = f"{TL}{HL * inner}{TR}"
    border_sep    = f"{SEP_T}{HL * inner}{SEP_TR}"
    border_bottom = f"{BL}{HL * inner}{BR}"

    out = []
    out.append(border_top)
    out.append(f"{VL}{_pad(' ' * pad + title, inner)}{VL}")
    if subtitle:
        out.append(f"{VL}{_pad(' ' * pad + subtitle, inner)}{VL}")
    out.append(border_sep)
    for raw in content:
        out.append(f"{VL}{_pad(' ' * pad + raw, inner)}{VL}")
    out.append(border_bottom)

    # оборачиваем в код-блок, чтобы MM отрисовал моноширинно
    return "```\n" + "\n".join(out) + "\n```"

def bullets(items: List[str], indent: int = 2) -> List[str]:
    return [(" " * indent) + f"{DOT} " + it for it in items]