# -*- coding: utf-8 -*-
"""
SEED Agent v5 Message Formatter
Единообразное форматирование уведомлений для Mattermost/Slack
"""
import re
import datetime
from typing import Dict, Any, List, Optional

class AlertMessageFormatter:
    """Форматтер сообщений алертов для красивого Markdown"""
    
    # Иконки статусов в Final Fantasy стиле
    SEVERITY_ICONS = {
        "critical": "💎🔥",   # crystal + danger
        "high": "⚔️",        # crossed blades
        "warning": "🛡️",     # shield
        "info": "✨",         # sparkle
        "unknown": "❔"       # fancy question
    }
    
    # Цветовые коды для Mattermost attachments
    SEVERITY_COLORS = {
        "critical": "#FF0000",   # красный
        "high": "#FF4500",      # оранжево-красный
        "warning": "#FFA500",   # жёлтый
        "info": "#36A2EB",      # синий
        "unknown": "#808080"    # серый
    }
    
    # Приоритеты
    PRIORITY_LABELS = {
        3: "🚨 КРИТИЧЕСКИЙ", 
        2: "⚠️ ВЫСОКИЙ", 
        1: "📊 СРЕДНИЙ", 
        0: "ℹ️ НИЗКИЙ"
    }
    
    @classmethod
    def format_alert_message(
        cls, 
        alertname: str,
        instance: str,
        severity: str,
        priority: int,
        labels: Dict[str, str],
        annotations: Dict[str, str],
        llm_response: str,
        time_context: str = "",
        status: str = "firing"
    ) -> str:
        """
        Форматирует сообщение в лаконичный красивый Markdown
        """
        if status == "resolved":
            return cls._format_resolved_message(alertname, instance)
        
        # Получаем иконки 
        severity_icon = cls.SEVERITY_ICONS.get(severity.lower(), "📋")
        
        # Время
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d %H:%M')
        
        # Описание
        description = (
            annotations.get('summary') or 
            annotations.get('description') or 
            'Описание отсутствует'
        )
        
        # Парсим LLM-ответ на проблемы и команды
        problems, commands = cls._extract_brief_info_from_llm(llm_response)
        
        # Компактные рекомендации
        compact_problems = cls._format_compact_recommendations(problems)
        compact_commands = cls._format_compact_recommendations(commands, max_length=300)
        
        # Собираем лаконичное сообщение
        message = f"""{severity_icon} **{alertname} ({severity.upper()})**

📍 **Сервер:** {instance}  
⏰ **Время:** {time_str}{time_context}  
📝 **Описание:** {description}

---

### 🔍 Возможные проблемы:
{compact_problems}

### 🛠 Рекомендации:
```bash
{compact_commands}
```

— Powered by 🌌 SEED ✨"""
        return message.strip()
    
    @classmethod
    def _format_resolved_message(cls, alertname: str, instance: str) -> str:
        """Форматирует сообщение о решении алерта"""
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return f"""✅ **АЛЕРТ РЕШЕН: {alertname}**

**Сервер:** {instance}  
**Время решения:** {current_time}  

🎉 Проблема автоматически устранена или решена администратором.

— SEED ✨"""
    
    @classmethod
    def _extract_brief_info_from_llm(cls, llm_response: str) -> tuple:
        """
        Извлекает из LLM ответа максимум 3 пункта проблем + команды
        Возвращает (problems_text, commands_text)
        """
        if not llm_response or llm_response.strip() == "":
            return "Нет анализа от LLM", "# Анализ недоступен"
        
        if "LLM недоступен" in llm_response or "Ошибка LLM" in llm_response:
            return llm_response, "# LLM недоступен"
        
        # Ищем команды в тексте
        commands = cls._extract_commands_from_text(llm_response)
        commands_block = commands if commands.strip() else "# Нет команд для диагностики"
        
        # Ищем возможные проблемы (первые содержательные строки)
        problems = cls._extract_problems_from_text(llm_response)
        problems_block = problems if problems.strip() else "• Нет информации о проблемах"
        
        return problems_block, commands_block
    
    @classmethod
    def _extract_commands_from_text(cls, text: str) -> str:
        """Извлекает команды из текста LLM"""
        # Паттерны команд
        command_patterns = [
            r'systemctl\s+\w+\s+[\w\-\.]+',
            r'journalctl\s+[^\n]+',
            r'sudo\s+[^\n]+',
            r'docker\s+[^\n]+',
            r'kubectl\s+[^\n]+',
            r'mongo\s+[^\n]+',
            r'find\s+[^\n]+',
            r'grep\s+[^\n]+',
            r'ps\s+[^\n]+',
            r'du\s+[^\n]+',
            r'df\s+[^\n]*',
            r'ls\s+[^\n]*',
            r'cat\s+[^\n]+',
            r'tail\s+[^\n]+',
            r'head\s+[^\n]+',
            r'service\s+\w+\s+\w+'
        ]
        
        found_commands = []
        
        # Ищем команды по всем паттернам
        for pattern in command_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            found_commands.extend(matches)
        
        # Убираем дубликаты и ограничиваем количество
        unique_commands = list(dict.fromkeys(found_commands))[:5]  # Максимум 5 команд
        
        return '\n'.join(unique_commands) if unique_commands else "# Команды не найдены"
    
    @classmethod 
    def _extract_problems_from_text(cls, text: str) -> str:
        """Извлекает возможные проблемы из текста LLM"""
        lines = text.split('\n')
        problems = []
        
        for line in lines:
            line = line.strip()
            
            # Пропускаем короткие строки, заголовки, команды
            if (len(line) < 20 or 
                line.startswith('#') or 
                line.startswith('```') or
                any(cmd in line.lower() for cmd in ['systemctl', 'journalctl', 'sudo', 'docker'])):
                continue
            
            # Ищем строки, описывающие проблемы
            if any(word in line.lower() for word in [
                'проблем', 'ошибк', 'недоступ', 'критич', 'заполн', 'нагрузк', 
                'остановлен', 'упал', 'неисправ', 'некорректн'
            ]):
                # Очищаем от лишних символов
                clean_line = re.sub(r'^[•\-\*\d\.\s]+', '', line).strip()
                if clean_line and len(clean_line) > 15:
                    problems.append(f"• {clean_line}")
                
                if len(problems) >= 3:  # Максимум 3 проблемы
                    break
        
        return '\n'.join(problems) if problems else "• Анализ проблем недоступен"
    
    @classmethod
    def _format_compact_recommendations(cls, text: str, max_length: int = 500) -> str:
        """Сжимает рекомендации от LLM, чтобы не захламлять Mattermost"""
        if not text or text.strip() == "":
            return "• Нет рекомендаций"
        
        # Если текст короткий, возвращаем как есть
        if len(text) <= max_length:
            return text.strip()
        
        # Обрезаем по словам, чтобы не порвать предложение
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:  # Если пробел не слишком близко к началу
            truncated = truncated[:last_space]
        
        return truncated + "\n\n... 🔎 *Полный текст в seed-agent.log*"
    
    @classmethod
    def get_severity_color(cls, severity: str) -> str:
        """Возвращает цветовой код для severity"""
        return cls.SEVERITY_COLORS.get(severity.lower(), "#808080")
    
    @classmethod
    def format_system_status(cls, host: str, cpu_info: str, ram_info: str, disk_info: List[str]) -> str:
        """Форматирует статус системы (для совместимости со старым кодом)"""
        message = f"### 📊 Статус системы {host}\n\n"
        
        if cpu_info and cpu_info != "n/a":
            message += f"🖥️ **CPU:** {cpu_info}\n"
        
        if ram_info and ram_info != "n/a":
            message += f"🧠 **Memory:** {ram_info}\n"
        
        if disk_info:
            message += f"💾 **Storage:**\n"
            for disk in disk_info:
                message += f"  • {disk}\n"
        
        return message
    
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
            
        return f"{icon} {path}: {percentage:.0f}% ({used_gb:.1f}/{total_gb:.1f} GB)"
    
    @classmethod
    def system_summary(cls, cpu_info: str, ram_info: str, disk_info: List[str],
                      host: str) -> str:
        """Создает полную сводку системы"""
        header = cls.header("System Status", host)
        
        lines = [header]
        
        # CPU
        if cpu_info and cpu_info != "n/a":
            lines.append(f"🖥️ CPU: {cpu_info}")
        else:
            lines.append(f"🖥️ CPU: n/a")
            
        # RAM 
        if ram_info and ram_info != "n/a":
            lines.append(f"🧠 Memory: {ram_info}")
        else:
            lines.append(f"🧠 Memory: n/a")
            
        # Диски
        if disk_info:
            lines.append(f"💾 Storage:")
            for disk in disk_info:
                lines.append(f"  {disk}")
        else:
            lines.append(f"💾 Storage: n/a")
            
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