# -*- coding: utf-8 -*-
from typing import Dict, Any, List
from fetchers.telegraf import get_gauge
from core import config
from core.formatter import FFFormatter

def _fmt_gb(bytes_val: float) -> float:
    """Конвертирует байты в ГБ"""
    return bytes_val / (1024**3)

def _determine_system_situation(cpu_info: str, ram_info: str, 
                               disk_percentages: List[float]) -> str:
    """Определяет общую ситуацию с системой"""
    max_disk = max(disk_percentages) if disk_percentages else 0
    
    if max_disk > 90:
        return "disk_critical"
    elif max_disk > 80:
        return "disk_warning"
    elif not disk_percentages or ram_info == "n/a":
        return "no_data"
    else:
        return "low_resources"


def run(host: str, labels: Dict[str,str], annotations: Dict[str,str], payload: Dict[str,Any]) -> str:
    """Синхронная версия плагина"""
    telegraf_url = payload.get("telegraf_url") or config.default_telegraf_url(host)
    paths: List[str] = payload.get("paths") or ["/", "/data"]
    
    try:
        # Получаем CPU информацию
        load1 = get_gauge(host, "system_load1", telegraf_url=telegraf_url)
        load5 = get_gauge(host, "system_load5", telegraf_url=telegraf_url)
        ncpu = get_gauge(host, "system_n_cpus", telegraf_url=telegraf_url)
        
        if isinstance(load1, float) or isinstance(load5, float):
            if isinstance(ncpu, float):
                cpu_info = f"{int(ncpu)} cores • LA: {load1 or 0:.2f}/{load5 or 0:.2f}"
            else:
                cpu_info = f"LA: {load1 or 0:.2f}/{load5 or 0:.2f}"
        else:
            cpu_info = "n/a"

        # Получаем RAM информацию  
        mem_total = get_gauge(host, "mem_total", telegraf_url=telegraf_url)
        mem_avail = get_gauge(host, "mem_available", telegraf_url=telegraf_url)
        
        if isinstance(mem_total, float) and isinstance(mem_avail, float):
            mem_used = mem_total - mem_avail
            mem_used_gb = _fmt_gb(mem_used)
            mem_total_gb = _fmt_gb(mem_total)
            ram_info = f"{mem_used_gb:.1f} GB / {mem_total_gb:.1f} GB"
        else:
            ram_info = "n/a"

        # Получаем информацию о дисках
        disk_info = []
        disk_percentages = []
        
        for path in paths:
            used_pct = get_gauge(host, "disk_used_percent", labels={"path": path}, telegraf_url=telegraf_url)
            used = get_gauge(host, "disk_used", labels={"path": path}, telegraf_url=telegraf_url)
            total = get_gauge(host, "disk_total", labels={"path": path}, telegraf_url=telegraf_url)
            
            if isinstance(used_pct, float) and isinstance(used, float) and isinstance(total, float):
                used_gb = _fmt_gb(used)
                total_gb = _fmt_gb(total)
                disk_info.append(FFFormatter.disk_status(path, used_gb, total_gb, used_pct))
                disk_percentages.append(used_pct)

        # Формируем красивый вывод
        result = FFFormatter.system_summary(cpu_info, ram_info, disk_info, host)
        
        # Определяем ситуацию и добавляем дружелюбный совет
        situation = _determine_system_situation(cpu_info, ram_info, disk_percentages)
        advice = FFFormatter.friendly_advice(situation, host)
        
        return result + advice

    except Exception as e:
        return FFFormatter.error_message(str(e), f"мониторинг хоста {host}")
