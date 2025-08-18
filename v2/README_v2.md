# SEED v2 - Asynchronous Alert Processing

## Архитектурные улучшения

v2 добавляет асинхронную обработку алертов через RabbitMQ с Redis-based throttling:

```
Alertmanager → FastAPI → RabbitMQ → Worker(s) → Plugins → Mattermost
```

## Новые компоненты

- **RabbitMQ** - очереди для алертов, retry, DLQ
- **Redis** - persistent throttling (с fallback на memory)
- **Worker процесс** - асинхронная обработка алертов
- **Docker Compose** - полный стек для разработки

## Быстрый старт

```bash
# 1. Запуск инфраструктуры
docker-compose up -d rabbitmq redis

# 2. Установка зависимостей
pip install -r requirements.txt

# 3. Запуск приложения
uvicorn app:app --reload

# 4. Запуск worker'а
python worker.py
```

## Или полный стек в Docker:

```bash
docker-compose up --build
```

## API Endpoints

- `GET /health` - проверка здоровья
- `GET /stats` - статистика throttling и очередей
- `POST /alert` - webhook для Alertmanager

## Мониторинг

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **App Stats**: http://localhost:8000/stats

## Конфигурация

Переменные окружения в `seed.env`:
- `RABBITMQ_URL` - подключение к RabbitMQ
- `REDIS_URL` - подключение к Redis
- `ALERT_SUPPRESS_SECONDS` - TTL для throttling

## Очереди RabbitMQ

- `seed.alerts.incoming` - входящие алерты
- `seed.alerts.retry` - повторная обработка (30s TTL)
- `seed.alerts.dead` - алерты с ошибками после 3 попыток

## Масштабирование

Worker процессы легко масштабируются:
```bash
docker-compose up --scale worker=5
```