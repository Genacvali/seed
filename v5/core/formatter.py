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
    
    # Иконки статусов
    SEVERITY_ICONS = {
        "critical": "🚨",
        "high": "⚠️", 
        "warning": "📊",
        "info": "ℹ️",
        "unknown": "❓"
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
        Форматирует сообщение алерта в красивый единообразный Markdown
        """
        if status == "resolved":
            return cls._format_resolved_message(alertname, instance)
        
        # Получаем иконки и приоритет
        severity_icon = cls.SEVERITY_ICONS.get(severity.lower(), "📋")
        priority_text = cls.PRIORITY_LABELS.get(priority, "📋 ОБЫЧНЫЙ")
        
        # Время
        current_time = datetime.datetime.now()
        time_str = current_time.strftime('%Y-%m-%d %H:%M')
        
        # Фильтруем метки (убираем основные)
        filtered_labels = {
            k: v for k, v in labels.items() 
            if k not in ['alertname', 'instance', '__name__']
        }
        labels_str = ', '.join([f"{k}={v}" for k, v in filtered_labels.items()]) if filtered_labels else "нет"
        
        # Описание
        description = (
            annotations.get('summary') or 
            annotations.get('description') or 
            'Описание отсутствует'
        )
        
        # Анализируем и форматируем LLM ответ
        analysis_section = cls._format_llm_analysis(llm_response)
        
        # Собираем финальное сообщение
        message = f"""{severity_icon} **{alertname}**

**Сервер:** {instance}  
**Время:** {time_str}{time_context}  
**Метки:** {labels_str}  
**Описание:** {description}

---

### 🧠 AI Анализ
{analysis_section}

---
"""
        return message.strip()
    
    @classmethod
    def _format_resolved_message(cls, alertname: str, instance: str) -> str:
        """Форматирует сообщение о решении алерта"""
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return f"""✅ **АЛЕРТ РЕШЕН: {alertname}**

**Сервер:** {instance}  
**Время решения:** {current_time}  

🎉 Проблема автоматически устранена или решена администратором."""
    
    @classmethod
    def _format_llm_analysis(cls, llm_response: str) -> str:
        """
        Форматирует LLM ответ, выделяя команды в код-блоки
        """
        if not llm_response or llm_response.strip() == "":
            return "Анализ недоступен - LLM не ответил"
        
        if "LLM недоступен" in llm_response or "Ошибка LLM" in llm_response:
            return llm_response
        
        # Разбираем ответ на секции
        sections = cls._parse_llm_sections(llm_response)
        
        if not sections:
            # Если не удалось разобрать, возвращаем как есть с минимальной обработкой
            return cls._extract_commands_to_blocks(llm_response)
        
        # Форматируем секции
        formatted_parts = []
        
        for section in sections:
            if section['type'] == 'analysis':
                formatted_parts.append(section['content'])
            elif section['type'] == 'recommendations':
                formatted_parts.append("### 🛠 Рекомендации")
                formatted_parts.append(section['content'])
            elif section['type'] == 'commands':
                formatted_parts.append("### 📋 Команды для диагностики")
                formatted_parts.append(section['content'])
            elif section['type'] == 'next_steps':
                formatted_parts.append("### 📍 Следующие шаги")
                formatted_parts.append(section['content'])
        
        return "\n\n".join(formatted_parts)
    
    @classmethod
    def _parse_llm_sections(cls, text: str) -> List[Dict[str, str]]:
        """
        Пытается разобрать LLM ответ на логические секции
        """
        sections = []
        
        # Попробуем найти разделы по ключевым словам
        current_section = ""
        current_type = "analysis"
        
        lines = text.split('\n')
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Определяем тип секции
            if any(word in line_lower for word in ['рекомендац', 'совет', 'действи', 'решени']):
                if current_section.strip():
                    sections.append({'type': current_type, 'content': current_section.strip()})
                current_section = ""
                current_type = "recommendations"
            elif any(word in line_lower for word in ['команд', 'проверк', 'запуск']):
                if current_section.strip():
                    sections.append({'type': current_type, 'content': current_section.strip()})
                current_section = ""
                current_type = "commands"
            elif any(word in line_lower for word in ['далее', 'следующ', 'шаги']):
                if current_section.strip():
                    sections.append({'type': current_type, 'content': current_section.strip()})
                current_section = ""
                current_type = "next_steps"
            
            current_section += line + "\n"
        
        # Добавляем последнюю секцию
        if current_section.strip():
            sections.append({'type': current_type, 'content': current_section.strip()})
        
        return sections
    
    @classmethod
    def _extract_commands_to_blocks(cls, text: str) -> str:
        """
        Находит команды в тексте и оборачивает их в код-блоки
        """
        # Паттерны для поиска команд
        command_patterns = [
            r'(systemctl\s+\w+\s+\w+)',
            r'(journalctl\s+[^\n]+)',
            r'(sudo\s+[^\n]+)',
            r'(docker\s+[^\n]+)',
            r'(kubectl\s+[^\n]+)',
            r'(mongo\s+[^\n]+)',
            r'(find\s+[^\n]+)',
            r'(grep\s+[^\n]+)',
            r'(ps\s+[^\n]+)',
            r'(top\s*$)',
            r'(htop\s*$)',
            r'(df\s+[^\n]*)',
            r'(du\s+[^\n]+)',
        ]
        
        formatted_text = text
        
        # Находим и форматируем команды
        for pattern in command_patterns:
            formatted_text = re.sub(
                pattern, 
                lambda m: f"\n```bash\n{m.group(1)}\n```\n", 
                formatted_text, 
                flags=re.MULTILINE
            )
        
        # Убираем множественные переносы строк
        formatted_text = re.sub(r'\n\n\n+', '\n\n', formatted_text)
        
        return formatted_text.strip()
    
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