# -*- coding: utf-8 -*-
"""
MongoDB Performance Analysis Plugin - Final Fantasy Style
Анализирует медленные запросы и COLLSCAN операции с дружелюбными советами
"""
import os
from typing import Dict, Any, List
from core.formatter import FFFormatter

def run(host: str, labels: Dict[str,str], annotations: Dict[str,str], payload: Dict[str,Any]) -> str:
    """Анализ производительности MongoDB в стиле FF"""
    try:
        threshold = int(payload.get("min_ms", 50))
        limit = int(payload.get("limit", 10))
        
        # Извлекаем данные запроса
        ns = labels.get("ns") or labels.get("namespace") or "unknown.collection"
        duration = labels.get("durationMillis") or annotations.get("duration", "n/a")
        docs_examined = labels.get("docsExamined") or "n/a" 
        keys_examined = labels.get("keysExamined") or "n/a"
        plan_summary = labels.get("planSummary") or "UNKNOWN"
        
        # Создаем заголовок
        result = FFFormatter.header("MongoDB Performance Crystal", host, "🔮")
        
        # Информация о запросе
        result += f"🎯 *Quest Target:* `{ns}`\n"
        result += f"⏱️ *Casting Time:* {duration} ms\n"
        result += f"📊 *Documents Scanned:* {docs_examined}\n"
        result += f"🗝️ *Keys Examined:* {keys_examined}\n"
        result += f"📋 *Spell Pattern:* {plan_summary}\n\n"
        
        # Определяем серьезность ситуации
        try:
            duration_val = float(duration) if duration != "n/a" else 0
            docs_val = float(docs_examined) if docs_examined != "n/a" else 0
        except:
            duration_val = docs_val = 0
            
        if duration_val > 1000 or docs_val > 100000:
            severity = "critical"
            status_msg = "🔥 *Критическая ситуация!* Запрос требует немедленного внимания"
        elif duration_val > 500 or docs_val > 10000:
            severity = "warning"  
            status_msg = "⚠️ *Подозрительная активность* - стоит разобраться"
        else:
            severity = "info"
            status_msg = "✅ *Все под контролем* - но мониторим дальше"
            
        result += f"{status_msg}\n\n"
        
        # Дружелюбные советы от опытного DBA
        advice = _get_mongo_advice(plan_summary, duration_val, docs_val, ns)
        result += FFFormatter.advice_section(advice)
        
        return result
        
    except Exception as e:
        return FFFormatter.error_message(str(e), f"анализ MongoDB на {host}")

def _get_mongo_advice(plan: str, duration: float, docs: float, namespace: str) -> List[str]:
    """Генерирует дружелюбные советы от опытного DBA"""
    advice = []
    
    if "COLLSCAN" in plan:
        advice.append("📝 Обнаружен полный скан коллекции - самое время создать индекс!")
        advice.append(f"💡 Попробуй: db.{namespace.split('.')[-1]}.createIndex({{field: 1}})")
        
    if duration > 1000:
        advice.append("🐌 Запрос работает медленно - проверь план выполнения через explain()")
        advice.append("⚡ Возможно стоит добавить составной индекс или оптимизировать запрос")
        
    if docs > 50000:
        advice.append("📚 Сканируется слишком много документов")  
        advice.append("🎯 Добавь более селективные условия в запрос или пагинацию")
        
    if not advice:
        advice.append("👍 Запрос выглядит нормально, но всегда есть что улучшить")
        advice.append("📊 Регулярно анализируй медленные запросы через db.runCommand({profile: 2})")
        
    return advice
