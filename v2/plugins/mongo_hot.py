# -*- coding: utf-8 -*-
"""
MongoDB Performance Analysis Plugin
S.E.E.D. - Smart Event Explainer & Diagnostics
"""
import os
from typing import Dict, Any, List
from core.formatter import SEEDFormatter
from core.llm import GigaChat

def run(host: str, labels: Dict[str,str], annotations: Dict[str,str], payload: Dict[str,Any]) -> str:
    """Анализ производительности MongoDB"""
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
        result = SEEDFormatter.header("MongoDB Analysis", host)
        
        # Информация о запросе
        result += f"🎯 Collection: {ns}\n"
        result += f"⏱️ Duration: {duration} ms\n"
        result += f"📄 Documents: {docs_examined}\n"
        result += f"🔑 Keys: {keys_examined}\n"
        result += f"📋 Plan: {plan_summary}\n\n"
        
        # Определяем серьезность ситуации
        try:
            duration_val = float(duration) if duration != "n/a" else 0
            docs_val = float(docs_examined) if docs_examined != "n/a" else 0
        except:
            duration_val = docs_val = 0
            
        if duration_val > 1000 or docs_val > 100000:
            status_msg = "🔥 Critical performance issue detected"
        elif duration_val > 500 or docs_val > 10000:
            status_msg = "⚠️ Performance degradation detected"
        else:
            status_msg = "✅ Query performance within acceptable range"
            
        result += f"{status_msg}\n\n"
        
        # Получаем умные советы от LLM
        llm_advice = _get_llm_mongo_advice(plan_summary, duration_val, docs_val, ns, host)
        if llm_advice:
            result += f"🤖 Умный совет:\n  • {llm_advice}\n"
        else:
            # Fallback на статические советы
            advice = _get_mongo_advice(plan_summary, duration_val, docs_val, ns)
            result += SEEDFormatter.advice_section(advice)
        
        return result
        
    except Exception as e:
        return SEEDFormatter.error_message(str(e), f"анализ MongoDB на {host}")

def _get_mongo_advice(plan: str, duration: float, docs: float, namespace: str) -> List[str]:
    """Генерирует практические советы DBA"""
    advice = []
    
    if "COLLSCAN" in plan:
        advice.append("🔍 Collection scan detected - создайте индекс для оптимизации")
        advice.append(f"📝 Команда: db.{namespace.split('.')[-1]}.createIndex({{field: 1}})")
        
    if duration > 1000:
        advice.append("🐌 Медленный запрос - проанализируйте план выполнения")
        advice.append("⚡ Рассмотрите составные индексы или изменение запроса")
        
    if docs > 50000:
        advice.append("📊 Сканируется большое количество документов")  
        advice.append("🎯 Добавьте селективные условия или пагинацию")
        
    if not advice:
        advice.append("✅ Запрос работает в приемлемых пределах")
        advice.append("📈 Продолжайте мониторинг производительности")
        
    return advice

def _get_llm_mongo_advice(plan: str, duration: float, docs: float, namespace: str, host: str) -> str:
    """Получает умные советы от LLM для MongoDB"""
    try:
        if os.getenv("USE_LLM", "0") != "1":
            return ""
            
        # Формируем контекст для LLM
        context = f"MongoDB query on {host}: Collection={namespace}, Duration={duration}ms, Documents={docs}, Plan={plan}"
        
        # Определяем тип проблемы
        if "COLLSCAN" in plan:
            problem_type = "полное сканирование коллекции"
        elif duration > 1000:
            problem_type = "медленный запрос"
        elif docs > 50000:
            problem_type = "сканирование большого количества документов"
        else:
            problem_type = "обычный запрос MongoDB"
            
        prompt = f"""Ты опытный MongoDB DBA. Анализируешь производительность запроса.

{context}
Проблема: {problem_type}

Дай ОДИН конкретный практический совет с MongoDB командой (максимум 120 символов).
Отвечай кратко и по делу, без объяснений."""

        llm = GigaChat()
        advice = llm.ask(prompt, max_tokens=100).strip()
        
        # Очищаем ответ
        advice = " ".join(advice.split())
        if len(advice) > 250:
            advice = advice[:250] + "..."
            
        return advice
        
    except Exception as e:
        return ""
