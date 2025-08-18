# -*- coding: utf-8 -*-
"""
SEED Agent Formatter - Final Fantasy Style
Стильное оформление сообщений в духе FF с элементами дружелюбности
"""
import random
from typing import Dict, Any, List

class FFFormatter:
    """Форматировщик в стиле Final Fantasy"""
    
    # Символы и эмодзи в стиле FF
    CRYSTAL_ICONS = ["💎", "💠", "🔮", "✨", "⭐"]
    STATUS_ICONS = {
        "ok": "✅",
        "warning": "⚠️", 
        "critical": "🔥",
        "info": "ℹ️",
        "magic": "🪄"
    }
    
    # Фразы для разных ситуаций в стиле опытного но дружелюбного админа
    GREETING_PHRASES = [
        "Кристалл мониторинга активирован! 💎",
        "Система сканирует горизонт событий... ✨",
        "Магия DevOps пробуждается! 🪄",
        "Древние руны мониторинга говорят..."
    ]
    
    ADVICE_STARTERS = [
        "💡 *Совет от бывалого админа:*",
        "🎯 *Мудрость сервера гласит:*", 
        "⚡ *Заклинание оптимизации:*",
        "🔧 *Древняя техника SRE:*"
    ]
    
    @classmethod
    def header(cls, title: str, host: str, icon: str = "💎") -> str:
        """Создает заголовок в стиле FF"""
        crystal = random.choice(cls.CRYSTAL_ICONS)
        return f"*{crystal} {title} @ {host} {crystal}*\n"
    
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
    def _create_progress_bar(cls, percentage: float, length: int = 8) -> str:
        """Создает прогресс-бар в стиле FF"""
        if percentage < 50:
            fill_char = "🟢"
        elif percentage < 80:
            fill_char = "🟡" 
        else:
            fill_char = "🔴"
            
        empty_char = "⬜"
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
            status = "critical"
            icon = "🔥"
        elif percentage > 80:
            status = "warning" 
            icon = "⚠️"
        else:
            status = "ok"
            icon = "✅"
            
        bar = cls._create_progress_bar(percentage)
        return f"{icon} *{path}* {percentage:.0f}% ({used_gb:.1f} GB / {total_gb:.1f} GB) {bar}"
    
    @classmethod
    def system_summary(cls, cpu_info: str, ram_info: str, disk_info: List[str],
                      host: str) -> str:
        """Создает полную сводку системы"""
        header = cls.header("System Crystal Status", host, "💎")
        
        lines = [header]
        
        # CPU с магической терминологией
        if cpu_info and cpu_info != "n/a":
            lines.append(f"⚡ *Mana Cores:* {cpu_info}")
        else:
            lines.append(f"💤 *Mana Cores:* в режиме сна...")
            
        # RAM 
        if ram_info and ram_info != "n/a":
            lines.append(f"🧙‍♂️ *Memory Crystal:* {ram_info}")
        else:
            lines.append(f"❓ *Memory Crystal:* сканирование...")
            
        # Диски
        if disk_info:
            lines.append(f"💾 *Storage Vaults:*")
            for disk in disk_info:
                lines.append(f"    {disk}")
        else:
            lines.append(f"💾 *Storage Vaults:* исследуются...")
            
        return "\n".join(lines)
    
    @classmethod
    def friendly_advice(cls, situation: str, host: str) -> str:
        """Генерирует дружелюбные советы в зависимости от ситуации"""
        advice_map = {
            "disk_critical": [
                "Пора освободить место! Удали старые логи и временные файлы",
                "Рассмотри архивацию данных или расширение диска", 
                "Настрой ротацию логов - это спасет тебя в будущем"
            ],
            "disk_warning": [
                "Диск заполняется, но паники нет - у нас есть время",
                "Проверь что занимает больше всего места: du -sh /*", 
                "Может стоит настроить автоочистку?"
            ],
            "low_resources": [
                "Система работает в штатном режиме - все спокойно",
                "Мониторь регулярно, но сейчас все хорошо",
                "Отличная работа с оптимизацией ресурсов!"
            ],
            "no_data": [
                f"Telegraf на {host} недоступен - проверь подключение",
                "Возможно нужно поправить конфигурацию мониторинга",
                "Не волнуйся, как наладим связь - данные появятся"
            ]
        }
        
        advice_list = advice_map.get(situation, ["Система работает штатно"])
        return cls.advice_section(advice_list)
    
    @classmethod
    def error_message(cls, error: str, context: str = "") -> str:
        """Дружелюбное сообщение об ошибке"""
        crystal = random.choice(cls.CRYSTAL_ICONS)
        
        msg = f"{crystal} *Упс! Что-то пошло не так...*\n\n"
        msg += f"🔍 *Детали:* {error}\n"
        
        if context:
            msg += f"📍 *Контекст:* {context}\n"
            
        msg += "\n💡 *Не переживай:* я уже работаю над исправлением!"
        msg += "\n🤖 Если проблема повторится - проверь логи или пингани админа"
        
        return msg