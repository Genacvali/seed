# SEED Agent v6 🚀

**Simplified Modular Alert Processing System**

Упрощённая архитектура с плагинами для обработки алертов от Alertmanager и RabbitMQ.

## ⚡ Быстрый старт

```bash
# 1. Настройка
cp configs/seed.env.example configs/seed.env
nano configs/seed.env  # Заполнить MM_WEBHOOK и опционально LLM credentials

# 2. Запуск
./start.sh

# 3. Проверка
curl http://localhost:8080/health
curl -X POST http://localhost:8080/test
```

## 📋 Требования

- **Python 3.8+** с зависимостями из requirements.txt
- **Mattermost webhook URL** (обязательно для уведомлений)
- **GigaChat credentials** (опционально для LLM)
- **RabbitMQ** (опционально для agent.py)

## 🏗️ Архитектура

- **FastAPI HTTP server** (app.py) - порт 8080
- **RabbitMQ consumer** (agent.py) - опционально
- **Plugin system** - модульная обработка событий
- **Formatters** - специализированное форматирование для каждого типа
- **Fetchers** - получение метрик из внешних источников (Telegraf)

## 📊 Ключевые эндпоинты

- `GET /health` - статус системы
- `POST /test` - тестовое сообщение (host_inventory demo)
- `POST /alertmanager` - webhook для Alertmanager

## 🧩 Компоненты

### Core Modules
- **config.py** - конфигурация из environment переменных
- **log.py** - логирование в файлы и stdout
- **mm.py** - отправка в Mattermost
- **llm.py** - GigaChat интеграция (опционально)
- **amqp.py** - RabbitMQ consumer
- **dispatcher.py** - маршрутизация событий к плагинам

### Plugins
- **echo.py** - fallback для неизвестных событий
- **host_inventory.py** - системные метрики (CPU, RAM, диски)
- **mongo_hot.py** - MongoDB медленные запросы

### Formatters
- **common.py** - базовые функции форматирования и LLM
- **host_inventory.py** - таблица системных ресурсов
- **mongo_hot.py** - таблица горячих MongoDB операций

### Fetchers
- **telegraf.py** - парсинг Prometheus метрик от Telegraf

## ⚙️ Конфигурация

Все настройки в `configs/seed.env`:

```bash
# Основные
MM_WEBHOOK=https://your-mattermost/hooks/xxx
LISTEN_PORT=8080

# LLM (опционально)
USE_LLM=1
GIGACHAT_CLIENT_ID=xxx
GIGACHAT_CLIENT_SECRET=xxx

# RabbitMQ (опционально для agent.py)
RABBIT_ENABLE=1
RABBIT_HOST=localhost
RABBIT_QUEUE=seed-inbox
```

## 🔄 Работа с Alertmanager

Система принимает стандартные алерты Alertmanager:

```json
{
  "alerts": [
    {
      "labels": {
        "alertname": "host_inventory",
        "instance": "db01"
      },
      "annotations": {
        "seed_plugin": "host_inventory",
        "seed_payload": "{\"paths\": [\"/\", \"/data\"]}"
      },
      "status": "firing"
    }
  ]
}
```

Маппинг:
- **plugin** = `annotations.seed_plugin` или `labels.alertname`
- **host** = `labels.instance` или `labels.hostname`
- **payload** = `annotations.seed_payload` (JSON) + raw labels/annotations

## 🚀 Развертывание

```bash
# Запуск HTTP сервера
./start.sh

# Остановка всех процессов
./stop.sh

# Проверка логов
tail -f logs/http.log
tail -f logs/agent.log  # если RabbitMQ включён
```

## 📈 Мониторинг

- **HTTP сервер**: автоматический рестарт через start.sh
- **Agent**: опциональный RabbitMQ consumer
- **Logs**: в директории `logs/`
- **Health check**: `GET /health`

---
*SEED Agent v6 - модульная простота* ✨