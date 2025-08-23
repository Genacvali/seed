# -*- coding: utf-8 -*-
"""
SEED Agent v5 Message Formatter
Единообразное форматирование уведомлений для Mattermost/Slack
"""
import re
import datetime
from typing import Dict, Any, List, Optional

def _strip_code_fences(text: str) -> str:
    """Убираем все ```...``` (с любым языком) из входа"""
    return re.sub(r"```[a-zA-Z]*\s*([\s\S]*?)```", r"\1", text)

def _pick_commands(lines, limit=5):
    """Берём до N уникальных командных строк, без мусора"""
    cmd_re = re.compile(r"^\s*(sudo\s+|systemctl|journalctl|mongo\b|mongosh\b|kubectl|docker|grep\b|find\b|ps\b|df\b|du\b|ss\b|netstat\b|curl\b)\b.*")
    seen, cmds = set(), []
    for ln in lines:
        m = cmd_re.match(ln)
        if m:
            s = ln.strip()
            if s.lower() in ("bash",):  # выкидываем одиночные "bash"
                continue
            if s not in seen:
                seen.add(s)
                cmds.append(s)
            if len(cmds) >= limit:
                break
    return cmds

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
        """Коротко: 2–3 возможные причины + чистый блок команд"""
        if not llm_response or not llm_response.strip():
            return "Нет анализа от LLM", "Нет команд"
        
        if "LLM недоступен" in llm_response or "Ошибка LLM" in llm_response:
            return llm_response, "LLM недоступен"

        # 1) убираем все тройные бэктики и языки
        clean = _strip_code_fences(llm_response)

        # 2) разобьём на строки
        lines = [l.rstrip() for l in clean.splitlines() if l.strip()]

        # 3) возможные проблемы: берём первые 3 содержательных пункта
        problems = []
        for l in lines:
            low = l.lower()
            # фильтруем «воду»
            if any(t in low for t in ("критичност", "описани", "приоритет")):
                continue
            if len(l) < 6:
                continue
            # берём либо буллеты, либо короткие предложения
            if l.lstrip().startswith(("•", "-", "*")) or l.endswith((".", "!", "?")):
                problems.append(l.lstrip("•-* ").strip())
            else:
                # допустим как гипотезу, но не длиннее 120
                problems.append(l.strip()[:120])
            if len(problems) >= 3:
                break
        problems_block = "\n".join(f"• {p}" for p in problems) if problems else "Нет информации"

        # 4) команды: ищем до 5 уникальных командных строк
        cmds = _pick_commands(lines, limit=5)
        commands_block = "\n".join(cmds) if cmds else "Нет команд"

        return problems_block, commands_block
    
    
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