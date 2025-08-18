# 🔮 SEED v2 - Final Fantasy Style Monitoring Agent

**System Enhancement & Event Detection** - твой дружелюбный но профессиональный DBA/DevOps/SRE помощник в стиле Final Fantasy!

## ✨ Что нового?

### 🎨 Final Fantasy Style Interface
- Красочные эмодзи и магическая терминология
- Прогресс-бары для дисков в стиле FF
- Кристаллы статуса и магические символы
- Дружелюбные но профессиональные советы

### 🚀 Производительность
- **Кэширование метрик** - Telegraf данные кэшируются на 30 секунд
- **Асинхронная обработка** - плагины работают быстрее
- **Batch запросы** - получение нескольких метрик одним запросом
- **Оптимизированный парсинг** - быстрее обрабатываем ответы

### 🤖 Дружелюбный Agent
- Менее формальный, более человечный тон
- Практические советы от "бывалого админа"
- Контекстные подсказки в зависимости от ситуации
- Эмпатичные сообщения об ошибках

## 📋 Компоненты

```
v2/
├── 🎯 app.py              # FastAPI webhook receiver
├── 🔄 worker.py           # Background alert processor  
├── 🎨 core/formatter.py   # FF-style message formatting
├── 📊 plugins/
│   ├── host_inventory.py  # System monitoring (FF style)
│   └── mongo_hot.py       # MongoDB performance (FF style)
├── 🔗 fetchers/telegraf.py # Optimized metrics fetcher
└── ⚙️ configs/
    ├── routing.yaml       # Alert routing rules
    └── hosts.yaml         # Host configurations
```

## 🎮 Примеры сообщений

### 💎 System Crystal Status
```
💎 System Crystal Status @ server-01 💎

⚡ Mana Cores: 4 cores • LA: 0.15/0.23
🧙‍♂️ Memory Crystal: 2.1 GB / 8.0 GB  
💾 Storage Vaults:
    ✅ / 45% (4.5 GB / 10.0 GB) [🟢🟢🟢🟢⬜⬜⬜⬜]
    🔥 /data 92% (18.4 GB / 20.0 GB) [🔴🔴🔴🔴🔴🔴🔴🔴]

💡 Совет от бывалого админа:
  • Пора освободить место! Удали старые логи и временные файлы
  • Рассмотри архивацию данных или расширение диска
```

### 🔮 MongoDB Performance Crystal
```
🔮 MongoDB Performance Crystal @ db-server 🔮

🎯 Quest Target: `myapp.users`
⏱️ Casting Time: 1247 ms
📊 Documents Scanned: 156823
🗝️ Keys Examined: 0
📋 Spell Pattern: COLLSCAN

🔥 Критическая ситуация! Запрос требует немедленного внимания

🔧 Древняя техника SRE:
  • 📝 Обнаружен полный скан коллекции - самое время создать индекс!
  • 💡 Попробуй: db.users.createIndex({field: 1})
  • 🐌 Запрос работает медленно - проверь план выполнения через explain()
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

## 🤝 Философия дизайна

SEED v2 создан как **дружелюбный наставник** - он:
- 🎯 Дает практические советы, а не абстракции
- 🎨 Использует визуальные элементы для лучшего восприятия  
- 🤖 Говорит человеческим языком, не сухим техническим
- ⚡ Работает быстро и не создает задержек
- 🔮 Добавляет немного магии в рутинную работу!

---
*Создано с ❤️ для админов, которые заслуживают красивый мониторинг*