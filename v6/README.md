# SEED Agent v6.1 🚀

**Simplified Monolithic Alert Processing System**

Упрощённая монолитная архитектура в одном файле для обработки алертов от Alertmanager и RabbitMQ.

## ⚡ Быстрый старт

```bash
# 1. Запуск (интерактивная настройка)
./start.sh

# 2. Или создать конфиг вручную
cp configs/seed.env.example configs/seed.env
nano configs/seed.env  # Заполнить MM_WEBHOOK и опционально LLM credentials
./start.sh

# 3. Проверка
curl http://localhost:8080/health
curl -X POST http://localhost:8080/test
```

## 📋 Требования

- **Python 3.8+** с зависимостями из requirements.txt
- **Mattermost webhook URL** (обязательно для уведомлений)  
- **GigaChat credentials** (опционально для LLM)
- **RabbitMQ server** (опционально для consumer)

## 🏗️ Архитектура

- **seed-agent.py** - единый HTTP сервер + RabbitMQ consumer
- **FastAPI endpoints** - `/health`, `/test`, `/alertmanager`
- **Встроенный GigaChat LLM** - умные рекомендации
- **Интерактивная настройка** - через start.sh
- **Секретная конфигурация** - в `configs/secrets.env` (600)

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