# 🧪 Тестирование SEED Agent

## Быстрый тест

**1. Замените Mattermost webhook в seed.yaml:**
```yaml
notifications:
  mattermost:
    webhook_url: "https://your-mattermost.com/hooks/xxxxxxxxxx"
```

**2. Перезапустите агент:**
```bash
./deploy.sh stop
./deploy.sh start
```

**3. Запустите тестовые алерты:**
```bash
chmod +x test-alerts.sh
./test-alerts.sh
```

## Что тестируется:

### 🔥 1. MongoDB High CPU
- Критический алерт о высокой нагрузке CPU на MongoDB
- Тест LLM анализа производительности

### 💾 2. Disk Space Low  
- Предупреждение о заканчивающемся месте на диске
- Тест рекомендаций по очистке

### 🐌 3. MongoDB Slow Queries
- Медленные запросы в базе данных
- Тест анализа индексов и оптимизации

### ✅ 4. Service Recovery
- Восстановление сервиса (resolved alert)
- Тест обработки resolved статуса

### 🔴 5. Redis High Memory
- Высокое использование памяти в Redis
- Тест анализа кэш политик

## Проверка результатов:

```bash
# Статистика обработки
curl http://localhost:8080/stats | jq

# Логи в реальном времени  
./deploy.sh logs

# Health check
curl http://localhost:8080/health
```

## Ожидаемый результат:

В Mattermost должны прийти умные уведомления с:
- 🤖 LLM анализом каждого алерта
- 📋 Рекомендациями по устранению  
- 🔗 Ссылками на дашборды
- ⚡ Оценкой критичности

Если уведомления не приходят - проверьте webhook URL и логи агента!