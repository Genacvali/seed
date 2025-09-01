# SEED v6 Plugin System

Система маршрутизации алертов к специализированным плагинам для детальной диагностики.

## 🚀 Быстрый старт

1. **Настройка маппинга**: Редактируйте `configs/alerts.yaml`
2. **Создание плагинов**: Добавляйте файлы в `plugins/`  
3. **Тестирование**: Запустите `python test_plugin_system.py`

## 📋 Структура файлов

```
v6/
├── configs/alerts.yaml          # Маппинг алертов к плагинам
├── plugins/                     # Директория плагинов
│   ├── __init__.py
│   ├── echo.py                 # Базовый плагин (fallback)
│   ├── os_basic.py             # Системные метрики (CPU/Mem/Disk)
│   ├── pg_slow.py              # PostgreSQL анализ
│   ├── mongo_hot.py            # MongoDB анализ  
│   └── host_inventory.py       # Инвентаризация хостов
├── plugin_router.py            # Система маршрутизации
└── test_plugin_system.py       # Тестирование плагинов
```

## ⚙️ Конфигурация alerts.yaml

```yaml
routes:
  # Точное совпадение alertname
  - match: { alertname: "DiskSpaceLow" }
    plugin: "os_basic"
    params: { show_paths: ["/", "/data"], lookback: "15m" }

  # Совпадение по severity для fallback
  - match: { severity: "critical" }  
    plugin: "os_basic"
    params: { show_host_metrics: true }

# Плагин по умолчанию если ничего не подошло
default_plugin: "echo"
default_params: { show_basic_info: true }
```

## 🔧 Создание плагина

**Минимальная структура плагина:**

```python
# plugins/my_plugin.py
def run(alert: dict, prom, params: dict) -> dict:
    """
    Args:
        alert: Алерт из Alertmanager
        prom: Prometheus клиент (prom.query, prom.last_value)  
        params: Параметры из alerts.yaml
    
    Returns:
        {"title": "Plugin Name", "lines": ["line1", "line2"]}
    """
    labels = alert.get("labels", {})
    inst = labels.get("instance", "unknown")
    
    # Получаем метрики
    cpu = prom.last_value(f'node_cpu_seconds_total{{instance="{inst}"}}')
    
    lines = [
        f"Instance: {inst}",
        f"CPU: {cpu:.1f}%" if isinstance(cpu, (int, float)) else "CPU: n/a"
    ]
    
    return {"title": "My Plugin", "lines": lines}
```

## 📊 Доступные плагины

### os_basic
- **Назначение**: Системные метрики (CPU, Memory, Disk, Load Average)
- **Алерты**: `DiskSpaceLow`, `HighCPUUsage`, `HighMemoryUsage`, `LoadAverage`
- **Параметры**: `show_paths`, `show_processes`, `show_network`, `lookback`

### pg_slow  
- **Назначение**: PostgreSQL анализ
- **Алерты**: `PostgresSlowQuery`, `PG_IdleInTransaction_Storm`, `PostgresDeadlocks`
- **Параметры**: `show_idle_transactions`, `show_connections`, `show_locks`, `top`

### mongo_hot
- **Назначение**: MongoDB анализ
- **Алерты**: `MongoCollscan`, `MongoSlowQuery`, `MongoReplicaLag`
- **Параметры**: `show_host_metrics`, `lookback`, `top_collections`

### host_inventory
- **Назначение**: Инвентаризация и статус хостов
- **Алерты**: `InstanceDown`, `ServiceDown`
- **Параметры**: `show_services`, `ping_test`, `check_ports`

## 🧪 Тестирование

```bash
# Тест всей системы плагинов
python test_plugin_system.py

# Проверка состояния плагинов
curl http://localhost:8080/health | jq .plugins_enabled

# Отправка тестового алерта для конкретного плагина
curl -X POST http://localhost:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{"alerts":[{"labels":{"alertname":"DiskSpaceHigh","instance":"server-01","severity":"critical"}}]}'
```

## 📝 Логи плагинов

```bash
# Отслеживание работы плагинов
tail -f logs/agent.log | grep -E "(PLUGIN|ENRICH)"

# Конкретные события
tail -f logs/agent.log | grep "PLUGIN.*→"  # Маршрутизация
tail -f logs/agent.log | grep "PLUGIN.*Success"  # Успешное выполнение
```

## 🔍 Результат работы

Плагины добавляют секцию **🔧 Детальная диагностика** в уведомления:

```
🌌 S.E.E.D. - Smart Event Explainer & Diagnostics
═══════════════════════════════════════════════════════

🛡️ DiskSpaceHigh 🔴
└── Host: web-server-01 | Severity: CRITICAL  
└── 📊 CPU ~ 23.4% · MEM ~ 78.1% · Disk /var/lib/postgresql ~ 94.2%

🔧 Детальная диагностика:

**System Metrics - web-server-01**
🔥 CPU: 23.4%
💾 Memory: 78.1% 
🔴 Disk /var/lib/postgresql: 94.2%
🟢 Disk /: 45.3%

🛠️ Рекомендации:
• Find large files: du -sh /var/lib/postgresql/* | sort -rh | head -10
• Clean temp files: find /tmp -type f -atime +7 -delete  
• Check log rotation and cleanup old logs

🧠 Магия кристалла: [LLM рекомендации...]
```

## ⚡ Производительность

- **Параллельность**: Плагины работают для каждого алерта независимо
- **Кеширование**: Загруженные плагины кешируются в памяти  
- **Ограничения**: Максимум 8 строк и 2 плагина на сообщение
- **Timeout**: Плагины должны выполняться быстро (< 5 секунд)

## 🛠️ Отладка

**Плагин не запускается:**
1. Проверить синтаксис Python в файле плагина
2. Убедиться что функция `run()` существует  
3. Проверить права доступа к файлу плагина

**Алерт не попадает в плагин:**
1. Проверить match правила в `alerts.yaml`
2. Посмотреть логи маршрутизации: `grep "PLUGIN.*→" logs/agent.log`
3. Убедиться что `alertname` точно совпадает

**Prometheus метрики возвращают n/a:**
1. Проверить `PROM_URL` в `configs/seed.env`  
2. Убедиться что instance нормализуется правильно
3. Проверить наличие метрик: `curl "http://prometheus:9090/api/v1/query?query=up"`