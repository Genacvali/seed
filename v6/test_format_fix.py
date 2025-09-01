#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест улучшенного форматирования LLM ответов
"""

def clean_llm_response(text: str) -> str:
    """Очищает LLM ответ от блоков кода и форматирует для Mattermost"""
    import re
    
    # Убираем блоки кода ```sql, ```bash и т.д.
    text = re.sub(r'```\w*\n.*?\n```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Убираем лишние ключевые слова
    text = re.sub(r'\b(sql|bash|plpgsql)\b', '', text, flags=re.IGNORECASE)
    
    # Заменяем нумерацию на переносы строк для лучшего форматирования
    text = re.sub(r'\b(\d+)\.\s*', r'\n• ', text)
    text = re.sub(r'\b(Диагностика:|Рекомендации:)', r'\n**\1**', text)
    
    # Чистим лишние пробелы и пустые строки
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line and line != '•']
    
    return '\n'.join(lines).strip()

# Тестовый LLM ответ (как пример из проблемы)
test_response = """Диагностика: 1. Проверьте логи PostgreSQL на наличие длительных транзакций. 2. Используйте pg_stat_activity для поиска активных транзакций старше 600 секунд. 3. Убедитесь в отсутствии аномальных запросов или блокировок. Рекомендации: 1. Настройте автоматическое завершение старых транзакций через PL/pgSQL: sql CREATE OR REPLACE FUNCTION cleanup_idle_transactions() RETURNS void AS $ DECLARE v_query text; BEGIN FOR r IN SELECT pid FROM pg_stat_activity WHERE state = 'idle in transaction' AND age( NOW() - xact_start ) > interval '600 seconds' LOOP v_query := format('SELECT pg_terminate_backend(%s)', r.pid); EXECUTE v_query; END LOOP; END;$ LANGUAGE plpgsql; PERFORM cleanup_idle_transactions(); 2. Установите ограничение времени ожидания транзакции через параметр конфигурации: sql SET statement_timeout TO '600000 ms'; 3. Рассмотрите возможность использования пула соединений с настройкой таймаута подключения: bash pgbouncer 4. Обновите версию PostgreSQL до актуальной, чтобы использовать встроенные механизмы управления транзакциями."""

def test_format():
    print("🧪 Тест форматирования LLM ответа")
    print("=" * 50)
    
    print("📥 Исходный ответ:")
    print(f"{test_response[:200]}...")
    print()
    
    print("📤 После обработки:")
    cleaned = clean_llm_response(test_response)
    print(cleaned)
    print()
    
    print("📊 Статистика:")
    print(f"  Исходная длина: {len(test_response)} символов")
    print(f"  После очистки: {len(cleaned)} символов")
    print(f"  Строк: {len(cleaned.split('\n'))}")

if __name__ == "__main__":
    test_format()