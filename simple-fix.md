# Простое исправление для вашего скрипта

## Вариант 1: Минимальное изменение (1 строка)

В вашем оригинальном скрипте найдите строку:
```python
url = 'http://{}:{}/alert'.format(config['instances']['listner']['host'].replace('0.0.0.0','127.0.0.1'), config['instances']['listner']['port'])
```

Замените на:
```python
url = 'http://{}:{}/zabbix'.format(config['instances']['listner']['host'].replace('0.0.0.0','127.0.0.1'), config['instances']['listner']['port'])
```

**Результат:** Теперь ваш скрипт будет отправлять на правильный `/zabbix` эндпоинт, где SEED будет парсить severity из текста.

## Вариант 2: Полная адаптация (новый скрипт)

Используйте `zabbix-script-adapted.py` который:

1. **Правильно парсит severity:**
   - "ПРОЦЕССОВ НЕТ" → `high`
   - "КРИТИЧЕСКАЯ" → `disaster` 
   - "ВЫСОКАЯ" → `high`
   - "СРЕДНЯЯ" → `average`

2. **Извлекает hostname:** `p-homesecurity-mng-adv-msk01`

3. **Создает Zabbix payload:**
```json
{
  "event": {"value": "1", "id": "987654"},
  "trigger": {
    "name": "MongoDB Процессов нет",
    "severity_text": "high",
    "id": "745832"
  },
  "host": {
    "name": "p-homesecurity-mng-adv-msk01",
    "ip": "10.20.30.40"
  }
}
```

## Рекомендация

**Начните с Варианта 1** - изменив только URL. Если severity все еще будет INFO, переходите к Варианту 2.

## Тестирование

После изменения протестируйте:
```bash
python3 your-script.py recipient "SEED Alert: MongoDB Процессов нет" "p-homesecurity-mng-adv-msk01 MongoDB недоступен" mattermost
```

Должно появиться **HIGH** ⚔️ вместо **INFO** ✨.