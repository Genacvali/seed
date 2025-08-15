# -*- coding: utf-8 -*-
"""
Единый форматтер для SEED:
- заголовок/метаданные
- монотаблицы «как в CLI»
- блок "Советы"
Все функции возвращают готовый Markdown/текст для Mattermost.
"""

from typing import List, Dict, Iterable, Optional, Sequence

def _to_str(x) -> str:
    if x is None:
        return "n/a"
    if isinstance(x, float):
        # убираем лишние .0
        return f"{x:.0f}" if abs(x - int(x)) < 1e-9 else f"{x:.2f}"
    return str(x)

def header(title: str, host: str, meta: Optional[str] = None) -> str:
    """
    Заголовок вида:
    SEED · <title> @ <host>
    <meta>
    """
    lines = [f"SEED · {title} @ {host}"]
    if meta:
        lines.append(meta)
    return "\n".join(lines)

def cli_table(
    rows: Iterable[Sequence[str]],
    headers: Sequence[str],
    align: Optional[Sequence[str]] = None,
) -> str:
    """
    Рендер монотаблицы (пробелами), удобно смотрится в MM в ```блоке.
    align: список из 'l'|'c'|'r' (по умолчанию 'l')
    """
    rows = [[_to_str(c) for c in r] for r in rows]
    headers = [str(h) for h in headers]
    ncol = len(headers)
    align = align or ['l'] * ncol

    # ширины колонок
    widths = [len(h) for h in headers]
    for r in rows:
        for i, cell in enumerate(r):
            widths[i] = max(widths[i], len(cell))

    def _pad(text: str, w: int, a: str) -> str:
        if a == 'r':
            return text.rjust(w)
        if a == 'c':
            pad = w - len(text)
            left = pad // 2
            right = pad - left
            return (" " * left) + text + (" " * right)
        return text.ljust(w)

    # заголовок
    out = []
    head = "  ".join(_pad(h, widths[i], align[i]) for i, h in enumerate(headers))
    sep  = "  ".join("-" * widths[i] for i in range(ncol))
    out.append(head)
    out.append(sep)

    # строки
    for r in rows:
        line = "  ".join(_pad(r[i], widths[i], align[i]) for i in range(ncol))
        out.append(line)

    return "```\n" + "\n".join(out) + "\n```"

def tips_block(tips: List[str], title: str = "Советы") -> str:
    """
    Сжатый список рекомендаций. Пустой — не выводим.
    """
    if not tips:
        return ""
    lines = [f"**{title}:**"]
    for t in tips:
        lines.append(f"- {t}")
    return "\n".join(lines)

def small_note(text: str) -> str:
    return f"_ {text} _"