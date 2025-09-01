# -*- coding: utf-8 -*-
import requests, re
from typing import Dict, Optional
from core.config import CFG

# парсим Prometheus exposition format v2 от Telegraf
def _scrape(url: str) -> str:
    r = requests.get(url, timeout=5, verify=False)
    r.raise_for_status()
    return r.text

def _match_line(metric: str, labels: Dict[str,str]) -> str:
    # формируем префикс типа: metric{a="b",c="d"} или без лейблов
    if labels:
      inner = ",".join([f'{k}="{v}"' for k,v in labels.items()])
      return f"{metric}{{{inner}}}"
    return metric

def get_gauge(url_or_none: Optional[str], metric: str, labels: Optional[Dict[str,str]] = None) -> Optional[float]:
    url = url_or_none or CFG.telegraf_url
    try:
        text = _scrape(url)
        target = _match_line(metric, labels or {})
        # точное совпадение строки с числом в конце
        for ln in text.splitlines():
            if ln.startswith(target + " ") or ln.startswith(target + "\t"):
                try:
                    val_str = ln.split()[-1]
                    return float(val_str)
                except Exception:
                    pass
        # если нет точного — попробуем по имени метрики без лейблов (берём первый)
        for ln in text.splitlines():
            if ln.startswith(metric + " "):
                try:
                    return float(ln.split()[-1])
                except Exception:
                    pass
    except Exception:
        return None
    return None