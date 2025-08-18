# -*- coding: utf-8 -*-
"""
SEED Agent Formatter - Final Fantasy Style
Стильное оформление сообщений в духе FF с элементами дружелюбности
"""
import random
from typing import Dict, Any, List

class SEEDFormatter:
    """S.E.E.D. - Smart Event Explainer & Diagnostics Formatter"""
    
    STATUS_ICONS = {
        "ok": "✓",
        "warning": "⚠", 
        "critical": "✗",
        "info": "ℹ"
    }
    
    ADVICE_STARTERS = [
        "💡 Совет:",
        "⚡ Рекомендация:", 
        "🔧 Действие:"
    ]
    
    @classmethod
    def header(cls, title: str, host: str) -> str:
        """Создает заголовок S.E.E.D."""
        return f"*S.E.E.D. {title} @ {host}*\n"
    
    @classmethod 
    def status_line(cls, label: str, value: str, status: str = "info", 
                   show_bar: bool = False, percentage: float = None) -> str:
        """Форматирует строку статуса с иконкой"""
        icon = cls.STATUS_ICONS.get(status, "•")
        
        if show_bar and percentage is not None:
            bar = cls._create_progress_bar(percentage)
            return f"{icon} *{label}:* {value} {bar}"
        else:
            return f"{icon} *{label}:* {value}"
    
    @classmethod
    def _create_progress_bar(cls, percentage: float, length: int = 10) -> str:
        """Создает простой прогресс-бар"""
        if percentage < 50:
            fill_char = "="
        elif percentage < 80:
            fill_char = "-" 
        else:
            fill_char = "#"
            
        empty_char = "."
        filled = int((percentage / 100) * length)
        empty = length - filled
        
        return f"[{''.join([fill_char] * filled)}{''.join([empty_char] * empty)}]"
    
    @classmethod
    def advice_section(cls, advice_list: List[str]) -> str:
        """Создает секцию с советами"""
        if not advice_list:
            return ""
            
        starter = random.choice(cls.ADVICE_STARTERS)
        advice_text = "\n".join([f"  • {advice}" for advice in advice_list])
        
        return f"\n{starter}\n{advice_text}"
    
    @classmethod
    def disk_status(cls, path: str, used_gb: float, total_gb: float, 
                   percentage: float) -> str:
        """Форматирует информацию о диске"""
        if percentage > 90:
            icon = cls.STATUS_ICONS["critical"]
        elif percentage > 80:
            icon = cls.STATUS_ICONS["warning"]
        else:
            icon = cls.STATUS_ICONS["ok"]
            
        bar = cls._create_progress_bar(percentage)
        return f"{icon} {path}: {percentage:.0f}% ({used_gb:.1f}/{total_gb:.1f} GB) {bar}"
    
    @classmethod
    def system_summary(cls, cpu_info: str, ram_info: str, disk_info: List[str],
                      host: str) -> str:
        """Создает полную сводку системы"""
        header = cls.header("System Status", host)
        
        lines = [header]
        
        # CPU
        if cpu_info and cpu_info != "n/a":
            lines.append(f"CPU: {cpu_info}")
        else:
            lines.append(f"CPU: n/a")
            
        # RAM 
        if ram_info and ram_info != "n/a":
            lines.append(f"Memory: {ram_info}")
        else:
            lines.append(f"Memory: n/a")
            
        # Диски
        if disk_info:
            lines.append(f"Disks:")
            for disk in disk_info:
                lines.append(f"  {disk}")
        else:
            lines.append(f"Disks: n/a")
            
        return "\n".join(lines)
    
    @classmethod
    def friendly_advice(cls, situation: str, host: str) -> str:
        """Генерирует советы в зависимости от ситуации"""
        advice_map = {
            "disk_critical": [
                "Критичное заполнение диска - требуется немедленное действие",
                "Очистите старые логи: find /var/log -name '*.log' -mtime +7 -delete", 
                "Настройте ротацию логов для предотвращения повторения"
            ],
            "disk_warning": [
                "Диск заполняется - мониторьте ситуацию",
                "Проверьте размеры: du -sh /* | sort -hr", 
                "Рассмотрите очистку или расширение диска"
            ],
            "low_resources": [
                "Система работает в нормальном режиме",
                "Продолжайте мониторинг для раннего обнаружения проблем"
            ],
            "no_data": [
                f"Telegraf недоступен на {host} - проверьте подключение",
                "Убедитесь что сервис telegraf запущен и доступен"
            ]
        }
        
        advice_list = advice_map.get(situation, ["Система работает штатно"])
        return cls.advice_section(advice_list)
    
    @classmethod
    def error_message(cls, error: str, context: str = "") -> str:
        """Сообщение об ошибке"""        
        msg = f"*S.E.E.D. Error*\n\n"
        msg += f"Details: {error}\n"
        
        if context:
            msg += f"Context: {context}\n"
            
        msg += "\nПроверьте подключение к источникам данных и конфигурацию"
        
        return msg