# 🎭 SEED v2 Демонстрация

## Подготовка к демо

### 1. Запуск инфраструктуры

```bash
# В каталоге v2/
cd v2/

# Запуск RabbitMQ и Redis
docker-compose up -d rabbitmq redis

# Проверка готовности
docker-compose ps
```

### 2. Запуск приложения

```bash
# Terminal 1: API сервер
uvicorn app:app --reload --port 8000

# Terminal 2: Worker процесс  
python worker.py

# Terminal 3: Мониторинг логов
tail -f /var/log/mongodb/mongod.log  # или другой путь к логам
```

### 3. Проверка работоспособности

```bash
# Health check
curl http://localhost:8000/health

# Статистика системы
curl http://localhost:8000/stats | jq
```

## 🧪 Сценарии демонстрации

### Сценарий 1: Автоматические тесты

```bash
# Запуск полного набора тестов
python test_integration.py
```

**Что демонстрируется:**
- ✅ Асинхронная обработка алертов через RabbitMQ
- ✅ Redis-based throttling с подавлением дублей  
- ✅ Масштабируемость (можно добавить worker'ов)
- ✅ Мониторинг очередей и статистики

### Сценарий 2: Ручные тесты через curl

```bash
# Отправка host_inventory алерта
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "host_inventory",
        "host": "demo-server-01",
        "instance": "demo-server-01:9216"
      },
      "annotations": {
        "summary": "Host inventory check needed"
      }
    }]
  }'

# Проверка статистики
curl http://localhost:8000/stats | jq '.queues'
```

### Сценарий 3: MongoDB COLLSCAN демо

```bash
# 1. Обновить telegraf.conf
sudo cp telegraf_mongodb_collscan.conf /etc/telegraf/telegraf.conf
sudo systemctl restart telegraf

# 2. Создать медленные запросы
bash scripts/simulate_collscan.sh

# 3. Отправить алерт о COLLSCAN
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "mongo_collscan",
        "host": "centos-s-1vcpu-512mb-10gb-fra1-01",
        "db": "testdb",
        "ns": "testdb.users"
      },
      "annotations": {
        "summary": "COLLSCAN detected on testdb.users",
        "hotspots": "testdb.users  find  1234ms  plan:COLLSCAN",
        "last_ts": "2024-01-15T10:30:18.456+0000"
      }
    }]
  }'
```

## 📊 Мониторинг во время демо

### Web интерфейсы:
- **API Stats**: http://localhost:8000/stats
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Health Check**: http://localhost:8000/health

### Командная строка:
```bash
# Статистика очередей
curl -s http://localhost:8000/stats | jq '.queues'

# Мониторинг RabbitMQ
docker exec seed-rabbitmq rabbitmqctl list_queues

# Redis ключи throttling
docker exec seed-redis redis-cli keys "seed:throttle:*"

# Логи worker'а
docker-compose logs -f worker
```

## 🎯 Ключевые моменты для демо

### До внедрения RabbitMQ (v1):
- ❌ Синхронная обработка блокировала webhook
- ❌ Потеря алертов при перезапуске (in-memory throttling)
- ❌ Невозможность масштабирования
- ❌ Нет retry механизма

### После внедрения RabbitMQ (v2):
- ✅ Асинхронная обработка - webhook отвечает мгновенно
- ✅ Persistent throttling в Redis 
- ✅ Горизонтальное масштабирование worker'ов
- ✅ Retry логика + Dead Letter Queue
- ✅ Мониторинг всех компонентов

## 🚨 Troubleshooting

### Если RabbitMQ недоступен:
```bash
docker-compose restart rabbitmq
# Ждать ~30 секунд для полной инициализации
```

### Если Redis недоступен:
```bash
docker-compose restart redis
# Система автоматически переключится на in-memory throttling
```

### Если worker не обрабатывает:
```bash
# Проверить логи
python worker.py
# Должно быть: "[WORKER] Worker started, waiting for alerts..."
```

### Если нет сообщений в Mattermost:
```bash
# Проверить MM_WEBHOOK в seed.env
grep MM_WEBHOOK seed.env
```

## 📈 Демонстрация производительности

```bash
# Массовая отправка алертов
for i in {1..50}; do
  curl -X POST http://localhost:8000/alert \
    -H "Content-Type: application/json" \
    -d "{\"alerts\":[{\"status\":\"firing\",\"labels\":{\"alertname\":\"host_inventory\",\"host\":\"server-$i\"}}]}" &
done

# Мониторинг обработки
watch -n 1 "curl -s http://localhost:8000/stats | jq '.queues'"
```

Это покажет как система справляется с пиковой нагрузкой и автоматически распределяет работу между worker'ами.