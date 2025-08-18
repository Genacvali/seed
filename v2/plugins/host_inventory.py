# -*- coding: utf-8 -*-
import os
from typing import Dict, Any, List
from fetchers.telegraf import get_gauge
from core import config
from core.formatter import SEEDFormatter
from core.llm import GigaChat

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
                disk_info.append(SEEDFormatter.disk_status(path, used_gb, total_gb, used_pct))
                disk_percentages.append(used_pct)

        # Формируем красивый вывод
        result = SEEDFormatter.system_summary(cpu_info, ram_info, disk_info, host)
        
        # Получаем умные советы от LLM
        llm_advice = _get_llm_advice(cpu_info, ram_info, disk_percentages, host)
        if llm_advice:
            result += f"\n🤖 Умный совет:\n  • {llm_advice}"
        else:
            # Fallback на статические советы
            situation = _determine_system_situation(cpu_info, ram_info, disk_percentages)
            advice = SEEDFormatter.friendly_advice(situation, host)
            result += advice
        
        return result

    except Exception as e:
        return SEEDFormatter.error_message(str(e), f"мониторинг хоста {host}")

def _get_llm_advice(cpu_info: str, ram_info: str, disk_percentages: List[float], host: str) -> str:
    """Получает умные советы от LLM на основе состояния системы"""
    try:
        if os.getenv("USE_LLM", "0") != "1":
            return ""
            
        max_disk = max(disk_percentages) if disk_percentages else 0
        
        # Формируем контекст для LLM
        context_parts = []
        if cpu_info != "n/a":
            context_parts.append(f"CPU: {cpu_info}")
        if ram_info != "n/a":
            context_parts.append(f"Memory: {ram_info}")
        if disk_percentages:
            context_parts.append(f"Max disk usage: {max_disk:.1f}%")
            
        context = ", ".join(context_parts)
        
        # Определяем уровень проблемы
        if max_disk > 90:
            problem_level = "критическое заполнение диска"
        elif max_disk > 80:
            problem_level = "предупреждение о заполнении диска"
        else:
            problem_level = "нормальная работа системы"
            
        prompt = f"""Ты опытный DevOps инженер. Анализируешь состояние сервера {host}.

Текущее состояние: {context}
Основная проблема: {problem_level}

Дай ОДИН конкретный практический совет с командой Linux (максимум 100 символов). 
Отвечай кратко и по делу, без общих фраз."""

        llm = GigaChat()
        advice = llm.ask(prompt, max_tokens=80).strip()
        
        # Очищаем ответ от лишнего
        advice = " ".join(advice.split())
        if len(advice) > 200:
            advice = advice[:200] + "..."
            
        return advice
        
    except Exception as e:
        # При ошибке LLM возвращаем пустую строку - будет fallback
        return ""
