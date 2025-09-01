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
python3 test_llm.py  # Полнофункциональный тест с LLM
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

## 🧪 Тестирование

### Быстрые тесты
```bash
# Проверка системы
curl http://localhost:8080/health | jq .

# Простой тест алерт
curl -X POST http://localhost:8080/test

# Полнофункциональный LLM тест  
python3 test_llm.py

# Тест Prometheus интеграции (обогащение алертов)
python3 test_prometheus.py

# Тест с реальными Prometheus метриками
python3 test_realistic.py
```

### Что тестируется
- ✅ **Final Fantasy стилизация** с эмодзи 💎🔥⚔️🛡️✨
- ✅ **Цветные уведомления** по severity (красный/оранжевый/желтый/синий)  
- ✅ **LLM рекомендации** "🧠 Магия кристалла"
- ✅ **Prometheus обогащение** - реальные метрики в алертах
- ✅ **Комплексные инциденты** с множественными алертами

## 🚀 Развертывание

```bash
# Запуск
./start.sh

# Остановка  
./stop.sh

# Мониторинг логов
tail -f logs/agent.log
```

## 📈 Мониторинг

- **Health check**: `GET /health` - статус LLM, Mattermost, RabbitMQ
- **Logs**: `logs/agent.log` с эмодзи маркерами
- **Test endpoints**: `/test` для быстрой проверки
- **Real metrics**: integration с Prometheus API

---
*SEED Agent v6.1 - Final Fantasy powered alerts* 🌌✨