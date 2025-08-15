# -*- coding: utf-8 -*-
"""
SEED plugin: mongo_hot
Назначение: показать "горячие" запросы MongoDB из system.profile и выдать краткие рекомендации.
Источник коннекта:
  - payload['mongo_uri'] (из configs/seed.yaml) — приоритетно
  - иначе переменная окружения MONGO_URI (из .env)
Настройки payload:
  db:        имя БД для чтения system.profile (str)
  min_ms:    порог медленных операций в миллисекундах (int)
  limit:     максимум записей в выводе (int)
"""

import os
from datetime import datetime
from typing import Dict, Any, List

USE_LLM = os.getenv("USE_LLM", "0") == "1"
if USE_LLM:
    try:
        from core.llm import GigaChat
    except Exception:
        USE_LLM = False

def _fmt_dt(ts) -> str:
    try:
        if isinstance(ts, datetime):
            return ts.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return str(ts)

def _mk_row(doc: Dict[str, Any]) -> str:
    ns  = doc.get("ns", "-")
    op  = doc.get("op", doc.get("command", {}).get("query", {}).get("op", "-"))
    ms  = doc.get("millis", doc.get("durationMillis", "-"))
    de  = doc.get("docsExamined", doc.get("nreturned", "-"))
    ke  = doc.get("keysExamined", "-")
    ps  = doc.get("planSummary", "-")
    # компактная строка для код-блока
    return f"{ns:<28}  {op:<6}  {ms:>6}ms  docs:{de:<7} keys:{ke:<7} plan:{ps}"

def run(host: str, payload: dict) -> str:
    mongo_uri = payload.get("mongo_uri") or os.getenv("MONGO_URI")
    db_name   = str(payload.get("db", "admin"))
    min_ms    = int(payload.get("min_ms", 50))
    limit     = int(payload.get("limit", 10))

    if not mongo_uri:
        return (
            f"**SEED · Mongo Hot @ `{host}`**\n"
            f"• БД: `{db_name}`, порог: {min_ms} мс, лимит: {limit}\n"
            f"• ❌ Не задан `mongo_uri` (ни в payload, ни в .env)."
        )

    # подключаемся к Mongo
    try:
        from pymongo import MongoClient
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        client.admin.command("ping")  # проверка доступности
        db = client[db_name]
    except Exception as e:
        return (
            f"**SEED · Mongo Hot @ `{host}`**\n"
            f"• `{db_name}` (>{min_ms} мс, top {limit})\n"
            f"• ❌ Ошибка подключения к Mongo: {e}"
        )

    # читаем system.profile
    try:
        profile = db["system.profile"]
        cursor = (
            profile.find({"millis": {"$gte": min_ms}})
                   .sort([("ts", -1)])
                   .limit(limit)
        )
        docs: List[Dict[str, Any]] = list(cursor)
    except Exception as e:
        return (
            f"**SEED · Mongo Hot @ `{host}`**\n"
            f"• `{db_name}` (>{min_ms} мс, top {limit})\n"
            f"• ❌ Ошибка чтения system.profile: {e}"
        )

    lines: List[str] = []
    lines.append(f"**SEED · Mongo Hot @ `{host}`**")
    lines.append(f"• БД: `{db_name}`; порог: **{min_ms} мс**; записи: **{len(docs)}** (показано до {limit})")

    if not docs:
        lines.append("• Горячих операций не найдено за недавний период.")
    else:
        # заголовок таблицы (код-блок для Mattermost)
        lines.append("\n```text")
        lines.append(f"{'namespace':<28}  {'op':<6}  {'time':<8}  details")
        lines.append("-" * 80)
        for d in docs:
            lines.append(_mk_row(d))
        lines.append("```")
        # пример конкретики по самой свежей записи
        last_ts = _fmt_dt(docs[0].get("ts"))
        lines.append(f"_Последняя запись: {last_ts}_")

    # LLM-подсказка (опционально)
    if USE_LLM:
        try:
            # небольшой контекст: какие op и planSummary попадались
            ops = {}
            plans = {}
            for d in docs:
                op = d.get("op", "-")
                ps = d.get("planSummary", "-")
                ops[op] = ops.get(op, 0) + 1
                plans[ps] = plans.get(ps, 0) + 1
            ctx = f"ops={list(ops.items())[:5]}, plans={list(plans.items())[:5]}"
            tip = GigaChat().ask(
                f"На MongoDB замечены операции дольше {min_ms} мс в БД {db_name}. "
                f"Контекст: {ctx}. Дай 3-5 кратких, практичных рекомендаций по диагностике и индексации. "
                f"Формат — маркированный список.",
                max_tokens=220
            )
            if tip:
                lines.append("\n**Советы LLM:**\n" + tip)
        except Exception as e:
            lines.append(f"\n_(LLM недоступен: {e})_")

    try:
        client.close()
    except Exception:
        pass

    return "\n".join(lines)