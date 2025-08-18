# S.E.E.D. v2 - Smart Event Explainer & Diagnostics

**Smart Event Explainer & Diagnostics** - интеллектуальный помощник для анализа событий мониторинга.

## ✨ Возможности

### 🎯 Умный анализ
- Автоматическое определение типа проблемы
- Контекстуальные рекомендации
- Практические команды для решения проблем
- Минималистичный но информативный интерфейс

### 🚀 Производительность
- **Кэширование метрик** - Telegraf данные кэшируются на 30 секунд
- **Быстрые таймауты** - 3 секунды на запрос, предотвращает залипание
- **Batch запросы** - получение нескольких метрик одним запросом
- **Оптимизированный парсинг** - быстрая обработка ответов

### 🛡️ Надежность
- Graceful обработка недоступности источников данных
- Retry логика с Dead Letter Queue
- Автоматическое восстановление соединений

## 📋 Компоненты

```
v2/
├── app.py                 # FastAPI webhook receiver
├── worker.py              # Background alert processor  
├── core/formatter.py      # S.E.E.D. message formatting
├── plugins/
│   ├── host_inventory.py  # System monitoring
│   └── mongo_hot.py       # MongoDB performance analysis
├── fetchers/telegraf.py   # Optimized metrics fetcher
└── ⚙️ configs/
    ├── routing.yaml       # Alert routing rules
    └── hosts.yaml         # Host configurations
```

## 📊 Примеры сообщений

### System Status
```
*S.E.E.D. System Status @ server-01*

🖥️ CPU: 4 cores • LA: 0.15/0.23
🧠 Memory: 2.1 GB / 8.0 GB  
💾 Storage:
  ✅ /: 45% (4.5/10.0 GB) [████░░░░░░]
  🔥 /data: 92% (18.4/20.0 GB) [█████████░]

💡 Совет:
  • Критичное заполнение диска - требуется немедленное действие
  • Очистите старые логи: find /var/log -name '*.log' -mtime +7 -delete
```

### MongoDB Analysis
```
*S.E.E.D. MongoDB Analysis @ db-server*

🎯 Collection: myapp.users
⏱️ Duration: 1247 ms
📄 Documents: 156823
🔑 Keys: 0
📋 Plan: COLLSCAN

🔥 Critical performance issue detected

🔧 Действие:
  • 🔍 Collection scan detected - создайте индекс для оптимизации
  • 📝 Команда: db.users.createIndex({field: 1})
  • 🐌 Медленный запрос - проанализируйте план выполнения
```

## ⚙️ Настройка

### 1. Конфигурация алертов
Добавь новые алерты в `configs/routing.yaml`:

```yaml
alerts:
  DiskSpaceHigh:
    plugin: host_inventory
    payload:
      paths: ["/", "/data"]
      alert_type: "disk_space" 
      priority: "high"
```

### 2. Prometheus Rules  
```yaml
- alert: DiskSpaceHigh
  expr: (disk_used / disk_total) * 100 > 85
  labels:
    severity: warning
    alertname: "DiskSpaceHigh"
```

### 3. Alertmanager Receiver
```yaml
receivers:
  - name: "seed_agent"
    webhook_configs:
      - url: "http://your-server:8000/alert"
        send_resolved: true
```

## 🚀 Запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск API (прием алертов)
uvicorn app:app --host 0.0.0.0 --port 8000

# Запуск Worker (обработка алертов)  
python worker.py

# Или через systemd
systemctl start seed-api
systemctl start seed-worker
```

## 🔧 Оптимизации

- **Кэш метрик**: Telegraf данные кэшируются 30 сек
- **Таймауты**: Увеличены до 8 сек для стабильности
- **Batch операции**: Можно получить несколько метрик сразу
- **Async плагины**: Поддержка асинхронных операций

## 🎯 Тестирование

Отправь тестовый алерт:
```bash
curl -X POST http://your-server:8000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "DiskSpaceHigh",
        "instance": "server-01"
      },
      "annotations": {
        "summary": "Disk space 87% full"
      }
    }]
  }'
```

## 🎯 Философия дизайна

S.E.E.D. v2 создан как **умный диагностический помощник**:
- 🎯 Фокус на практических действиях
- 📊 Минималистичный но информативный интерфейс  
- 🔧 Конкретные команды для решения проблем
- ⚡ Быстрая работа без залипаний
- 🛡️ Надежная обработка ошибок

---
*S.E.E.D. - Smart Event Explainer & Diagnostics*