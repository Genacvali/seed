# -*- coding: utf-8 -*-
import re
import requests
import time
from typing import Dict, Optional, List, Tuple
from functools import lru_cache
from core import config

LABEL_RE = re.compile(r'\{([^}]*)\}')
PAIR_RE = re.compile(r'(\w+)\s*=\s*"(.*?)"')

# Простой кэш для метрик (TTL = 30 секунд)
_metrics_cache: Dict[str, Tuple[float, Dict[str, float]]] = {}
_CACHE_TTL = 30

def _matches(line: str, labels: Dict[str,str]) -> bool:
    """Проверяет соответствие лейблов в метрике"""
    m = LABEL_RE.search(line)
    if not m:
        return not labels
    raw = m.group(1)
    d = dict(PAIR_RE.findall(raw))
    for k,v in labels.items():
        if d.get(k) != str(v):
            return False
    return True

def _parse_metrics_response(text: str) -> Dict[str, float]:
    """Парсит ответ от Telegraf и возвращает словарь метрик"""
    metrics = {}
    for line in text.splitlines():
        if line.startswith('#') or not line.strip():
            continue
        try:
            # Находим последнее число в строке (значение метрики)
            value = float(line.strip().split()[-1])
            # Берем имя метрики (до первого пробела или {)
            metric_name = line.split()[0].split('{')[0]
            full_line = line.strip()
            metrics[full_line] = value
        except (ValueError, IndexError):
            continue
    return metrics

def _get_cached_metrics(url: str) -> Optional[Dict[str, float]]:
    """Получает метрики с кэшированием"""
    current_time = time.time()
    
    # Проверяем кэш
    if url in _metrics_cache:
        cache_time, cached_data = _metrics_cache[url]
        if current_time - cache_time < _CACHE_TTL:
            return cached_data
    
    # Запрашиваем новые данные
    try:
        response = requests.get(
            url, 
            timeout=3,  # Жесткий таймаут 3 секунды
            verify=False,
            headers={'Connection': 'close'}  # Не держим соединение
        )
        if response.status_code != 200:
            return None
            
        metrics = _parse_metrics_response(response.text)
        _metrics_cache[url] = (current_time, metrics)
        return metrics
        
    except (requests.exceptions.Timeout, 
            requests.exceptions.ConnectionError,
            requests.exceptions.RequestException):
        # При любой ошибке сети - возвращаем None быстро
        return None
    except Exception:
        return None

def get_gauge(host: str, metric: str, labels: Optional[Dict[str,str]]=None, 
              telegraf_url: Optional[str]=None) -> Optional[float]:
    """Получает значение gauge метрики от Telegraf с кэшированием"""
    url = telegraf_url or config.default_telegraf_url(host)
    
    # Получаем все метрики разом
    all_metrics = _get_cached_metrics(url)
    if not all_metrics:
        return None
    
    # Ищем нужную метрику
    for metric_line, value in all_metrics.items():
        if not metric_line.startswith(metric):
            continue
        if labels and not _matches(metric_line, labels):
            continue
        return value
    
    return None

def get_multiple_gauges(host: str, metrics: List[str], 
                       telegraf_url: Optional[str]=None) -> Dict[str, Optional[float]]:
    """Получает несколько метрик одним запросом (оптимизация)"""
    url = telegraf_url or config.default_telegraf_url(host)
    result = {metric: None for metric in metrics}
    
    all_metrics = _get_cached_metrics(url)
    if not all_metrics:
        return result
    
    for metric_name in metrics:
        for metric_line, value in all_metrics.items():
            if metric_line.startswith(metric_name):
                result[metric_name] = value
                break
    
    return result
