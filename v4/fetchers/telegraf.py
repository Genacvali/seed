# -*- coding: utf-8 -*-
import re
import httpx
import asyncio
import time
from typing import Dict, Optional, List, Tuple, Any
from functools import lru_cache

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

async def _get_cached_metrics(url: str, timeout: float = 3.0) -> Optional[Dict[str, float]]:
    """Получает метрики с кэшированием"""
    current_time = time.time()
    
    # Проверяем кэш
    if url in _metrics_cache:
        cache_time, cached_data = _metrics_cache[url]
        if current_time - cache_time < _CACHE_TTL:
            return cached_data
    
    # Запрашиваем новые данные
    try:
        timeout_config = httpx.Timeout(timeout)
        async with httpx.AsyncClient(
            timeout=timeout_config,
            verify=False,
            headers={'Connection': 'close'}
        ) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                return None
                
            metrics = _parse_metrics_response(response.text)
            _metrics_cache[url] = (current_time, metrics)
            return metrics
        
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        # При любой ошибке сети - возвращаем None быстро
        return None
    except Exception:
        return None

class TelegrafFetcher:
    """Класс для работы с Telegraf metrics"""
    
    def __init__(self, config):
        self.config = config
    
    async def fetch_metrics(self, url: str, timeout: float = 30.0) -> List[Dict[str, Any]]:
        """Получает метрики в формате словарей для pluginов"""
        try:
            raw_metrics = await _get_cached_metrics(url, timeout)
            if not raw_metrics:
                return []
            
            # Преобразуем в формат, ожидаемый pluginами
            metrics = []
            for metric_line, value in raw_metrics.items():
                # Парсим строку метрики
                parts = metric_line.split()
                if not parts:
                    continue
                
                metric_name_with_labels = parts[0]
                
                # Разделяем имя метрики и лейблы
                if '{' in metric_name_with_labels:
                    metric_name = metric_name_with_labels.split('{')[0]
                    labels_part = metric_name_with_labels.split('{', 1)[1].rstrip('}')
                    
                    # Парсим лейблы
                    tags = {}
                    if labels_part:
                        for pair in PAIR_RE.findall(labels_part):
                            if len(pair) == 2:
                                tags[pair[0]] = pair[1]
                else:
                    metric_name = metric_name_with_labels
                    tags = {}
                
                metrics.append({
                    "name": metric_name,
                    "tags": tags,
                    "fields": {metric_name: value},
                    "timestamp": int(time.time())
                })
            
            return metrics
            
        except Exception as e:
            print(f"Error fetching Telegraf metrics from {url}: {e}")
            return []
    
    async def get_gauge(self, host: str, metric: str, labels: Optional[Dict[str,str]]=None, 
                       telegraf_url: Optional[str]=None) -> Optional[float]:
        """Получает значение gauge метрики от Telegraf"""
        url = telegraf_url or self.config.get_telegraf_url(host)
        
        all_metrics = await _get_cached_metrics(url)
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

    async def get_multiple_gauges(self, host: str, metrics: List[str], 
                                telegraf_url: Optional[str]=None) -> Dict[str, Optional[float]]:
        """Получает несколько метрик одним запросом"""
        url = telegraf_url or self.config.get_telegraf_url(host)
        result = {metric: None for metric in metrics}
        
        all_metrics = await _get_cached_metrics(url)
        if not all_metrics:
            return result
        
        for metric_name in metrics:
            for metric_line, value in all_metrics.items():
                if metric_line.startswith(metric_name):
                    result[metric_name] = value
                    break
        
        return result


# Legacy compatibility functions (deprecated)
async def get_gauge(host: str, metric: str, labels: Optional[Dict[str,str]]=None, 
                   telegraf_url: Optional[str]=None) -> Optional[float]:
    """Легаси функция для совместимости"""
    # Для совместимости - создаем временный fetcher
    from core.config import Config
    config = Config()
    fetcher = TelegrafFetcher(config)
    return await fetcher.get_gauge(host, metric, labels, telegraf_url)


async def get_multiple_gauges(host: str, metrics: List[str], 
                             telegraf_url: Optional[str]=None) -> Dict[str, Optional[float]]:
    """Легаси функция для совместимости"""
    from core.config import Config
    config = Config()
    fetcher = TelegrafFetcher(config)
    return await fetcher.get_multiple_gauges(host, metrics, telegraf_url)
