# fetchers/telegraf.py
# -*- coding: utf-8 -*-
import os, re, requests
from functools import lru_cache
from typing import Optional, Union, Dict

TELEGRAF_PORT = int(os.getenv("TELEGRAF_PORT", "9216"))
VERIFY = False  # Упрощено для работы в локальной сети

def _metrics_url(host: str, port: Optional[int] = None) -> str:
    p = port or TELEGRAF_PORT
    # обычно это http, если у тебя https — поправь тут
    return f"http://{host}:{p}/metrics"

@lru_cache(maxsize=64)
def _scrape(host: str, port: Optional[int] = None) -> str:
    url = _metrics_url(host, port)
    r = requests.get(url, timeout=5, verify=VERIFY)
    r.raise_for_status()
    return r.text

def _labels_match(line: str, labels: Optional[Dict]) -> bool:
    if not labels: 
        return "{" not in line or True  # допускаем строки без лейблов
    for k, v in labels.items():
        # ищем k="v" внутри { ... }
        if f'{k}="{v}"' not in line:
            return False
    return True

def get_gauge(host: str, metric: str, labels: Optional[Dict] = None, port: Optional[int] = None) -> Optional[float]:
    """
    Возвращает ПЕРВОЕ подходящее значение метрики.
    Пример:
      get_gauge("host","disk_total", labels={"path":"/"})
    """
    text = _scrape(host, port)
    val = None
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        # ожидание формата: <metric>{label1="..",...} <value>
        if not line.startswith(metric):
            continue
        if labels and "{" in line:
            if not _labels_match(line, labels):
                continue
        # выцепим число в конце строки
        try:
            num_str = line.strip().split()[-1]
            val = float(num_str)
            return val
        except Exception:
            continue
    return None