# 🌌 S.E.E.D. Agent v6.1 - Demo Test Requests
*Final Fantasy стиль мониторинга с эпичными эмодзи и AI диагностикой*

## 🎮 Что демонстрируем в v6.1:
- 💎🔥 **Final Fantasy эмодзи** для всех метрик (CPU/Memory/Disk)
- 🧙‍♂️ **AI диагностика** с улучшенным форматированием
- ⚔️ **Plugin System** с специализированными обработчиками
- 🛡️ **Smart Enrichment** с Prometheus + Telegraf fallback
- ✨ **No Duplicates** - все метрики только в summary line

## 1. 🔍 Базовые тесты системы

### Проверка здоровья агента
```bash
# Health check - покажет статус всех компонентов
curl -s http://p-dba-seed-adv-msk01:8080/health | jq .

# Простой тест уведомлений с Final Fantasy стилем
curl -X POST http://p-dba-seed-adv-msk01:8080/test
```

## 2. Демонстрация плагинов

### 🖥️ OS/System алерты (os_basic plugin)
*Демонстрирует Final Fantasy эмодзи и отсутствие дублирования метрик*

```bash
# 💾 Алерт высокого использования памяти - покажет 🏰 MEM эмодзи
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighMemoryUsage",
        "instance": "nt-smi-mng-sc-msk03",
        "severity": "high"
      },
      "annotations": {
        "summary": "Memory usage is critically high",
        "description": "Memory usage at 88% for 10+ minutes"
      }
    }]
  }'

# ⚔️ Алерт высокой нагрузки CPU - покажет CPU эмодзи прогрессию
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing", 
      "labels": {
        "alertname": "HighCPUUsage",
        "instance": "p-smi-mng-sc-msk06",
        "severity": "high"
      },
      "annotations": {
        "summary": "High CPU usage on database server",
        "description": "CPU usage is above 90% for more than 5 minutes"
      }
    }]
  }'
```

### 🐘 PostgreSQL алерты (pg_slow plugin)  
*Демонстрирует специализированную диагностику БД*

```bash
# 💎🔥 Критичные медленные запросы PostgreSQL
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PostgresSlowQuery",
        "instance": "p-smi-mng-sc-msk07",
        "severity": "critical",
        "database": "main_db"
      },
      "annotations": {
        "summary": "Critical slow queries in main database", 
        "description": "Multiple queries taking >10 seconds"
      }
    }]
  }'
```

### 🍃 MongoDB алерты (mongo_hot plugin)
*Демонстрирует MongoDB анализ и рекомендации*

```bash
# 🛡️ MongoDB медленные операции
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "MongoSlowQuery",
        "instance": "p-smi-mng-sc-msk07:9216",
        "severity": "warning",
        "database": "analytics"
      },
      "annotations": {
        "summary": "Slow MongoDB operations detected",
        "description": "Operations taking >1000ms detected in analytics DB"
      }
    }]
  }'
```

### 🌐 Host алерты (host_inventory plugin)
*Демонстрирует сетевую диагностику*

```bash
# ⚙️ Сервис недоступен  
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "InstanceDown",
        "instance": "p-smi-mng-sc-msk08",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Instance is down",
        "description": "Host is not responding to health checks"
      }
    }]
  }'
```

## 3. 🎮 Комплексная демонстрация Final Fantasy стиля

### 🌟 Мультиалертный инцидент - демонстрирует все фишки v6.1:
```bash
# 💎🔥 Комплексный инцидент: PostgreSQL + CPU + Memory
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "PostgresSlowQuery",
          "instance": "p-smi-mng-sc-msk07",
          "severity": "critical",
          "database": "main_db"
        },
        "annotations": {
          "summary": "Critical slow queries in main database", 
          "description": "Multiple queries taking >10 seconds"
        }
      },
      {
        "status": "firing",
        "labels": {
          "alertname": "HighCPUUsage", 
          "instance": "p-smi-mng-sc-msk06",
          "severity": "high"
        },
        "annotations": {
          "summary": "High CPU usage on database server",
          "description": "CPU usage at 95% for 10+ minutes"
        }
      },
      {
        "status": "firing",
        "labels": {
          "alertname": "HighMemoryUsage",
          "instance": "p-smi-mng-sc-msk07", 
          "severity": "warning"
        },
        "annotations": {
          "summary": "Memory usage approaching limits",
          "description": "Memory usage at 88%"
        }
      }
    ]
  }'
```

## 4. 🧙‍♂️ Что ожидать в демонстрации

### ✨ Final Fantasy эмодзи прогрессии:
- **CPU**: ✨ (0-50%) → ⚔️ (50-70%) → 🗡️ (70-90%) → 💎🔥 (90%+)
- **Memory**: 🌟 (0-50%) → 🛡️ (50-70%) → 🏰 (70-90%) → 💎🔥 (90%+)  
- **Disk**: ✨ (0-60%) → 🛡️ (60-80%) → ⚔️ (80-90%) → 💎🔥 (90%+)

### 🔧 Структура уведомления:
1. **🌌 S.E.E.D. заголовок** с красивой рамкой
2. **⚔️ Алерт с эмодзи** по критичности
3. **📊 Summary line** с Final Fantasy эмодзи для всех метрик
4. **🔧 Детальная диагностика** от плагинов (БЕЗ дублирования метрик)
5. **🧠 Магия кристалла** с AI анализом и структурированными рекомендациями

### 🎯 Ключевые фишки для демо:
- **Нет дублирования** - все метрики только в summary line сверху
- **AI форматирование** - четкие секции "Диагностика" и "Рекомендации"  
- **Telegraf fallback** - работает даже если node_exporter недоступен
- **Plugin specialization** - каждый тип алерта обрабатывается специализированным плагином

## 5. 🚀 Готовность к презентации

```bash
# Проверить что все работает
curl http://p-dba-seed-adv-msk01:8080/health | jq .

# Убедиться что LLM включен для "магии кристалла"  
grep USE_LLM /path/to/configs/seed.env

# Проверить подключение к Prometheus для эмодзи
grep PROM_URL /path/to/configs/seed.env
```

**🎮 Ready for Epic Demo! ⚔️✨**
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighMemoryUsage", 
        "instance": "prod-cache01.example.com",
        "severity": "high"
      },
      "annotations": {
        "summary": "Memory usage is critically high",
        "description": "Memory usage exceeded 85% threshold"
      }
    }]
  }'
```

### PostgreSQL алерты (pg_slow plugin)

```bash
# Медленные запросы PostgreSQL
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PostgresSlowQuery",
        "instance": "prod-postgres01.example.com", 
        "severity": "warning",
        "database": "main_db"
      },
      "annotations": {
        "summary": "Slow queries detected in PostgreSQL",
        "description": "Queries taking more than 5 seconds detected"
      }
    }]
  }'

# Проблемы с подключениями к PostgreSQL
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "PostgresConnections",
        "instance": "prod-postgres01.example.com",
        "severity": "critical",
        "database": "main_db"
      },
      "annotations": {
        "summary": "PostgreSQL connection limit approaching",
        "description": "Active connections: 180/200"
      }
    }]
  }'
```

### MongoDB алерты (mongo_hot plugin)

```bash
# MongoDB медленные запросы
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "MongoSlowQuery",
        "instance": "prod-mongo01.example.com",
        "severity": "warning",
        "database": "analytics"
      },
      "annotations": {
        "summary": "Slow MongoDB operations detected",
        "description": "Operations taking >1000ms detected in analytics DB"
      }
    }]
  }'

# MongoDB Collection Scan
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing", 
      "labels": {
        "alertname": "MongoCollscan",
        "instance": "prod-mongo02.example.com",
        "severity": "high",
        "collection": "users"
      },
      "annotations": {
        "summary": "MongoDB collection scan detected",
        "description": "Full collection scan on users collection affecting performance"
      }
    }]
  }'
```

### Сервисы и сеть (host_inventory plugin)

```bash
# Сервис недоступен
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "InstanceDown",
        "instance": "prod-api03.example.com",
        "severity": "critical",
        "job": "node-exporter"
      },
      "annotations": {
        "summary": "Instance prod-api03 is down",
        "description": "prod-api03.example.com has been down for more than 1 minute"
      }
    }]
  }'

# Проблемы с сервисом
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "ServiceDown",
        "instance": "prod-web01.example.com", 
        "severity": "high",
        "service": "nginx"
      },
      "annotations": {
        "summary": "Nginx service is not responding",
        "description": "HTTP checks failing on port 80"
      }
    }]
  }'
```

## 3. Комплексные сценарии

### Множественные алерты (демонстрация LLM анализа)

```bash
# Комплексный инцидент: проблемы с базой данных и приложением  
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "PostgresSlowQuery",
          "instance": "prod-postgres01.example.com",
          "severity": "critical",
          "database": "main_db"
        },
        "annotations": {
          "summary": "Critical slow queries in main database", 
          "description": "Multiple queries taking >10 seconds"
        }
      },
      {
        "status": "firing",
        "labels": {
          "alertname": "HighCPUUsage", 
          "instance": "prod-postgres01.example.com",
          "severity": "high"
        },
        "annotations": {
          "summary": "High CPU usage on database server",
          "description": "CPU usage at 95% for 10+ minutes"
        }
      },
      {
        "status": "firing",
        "labels": {
          "alertname": "HighMemoryUsage",
          "instance": "prod-postgres01.example.com", 
          "severity": "warning"
        },
        "annotations": {
          "summary": "Memory usage approaching limits",
          "description": "Memory usage at 88%"
        }
      }
    ]
  }'

# Инцидент с сетевыми проблемами
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "InstanceDown", 
          "instance": "prod-app01.example.com",
          "severity": "critical"
        },
        "annotations": {
          "summary": "Application server is unreachable",
          "description": "prod-app01 not responding to health checks"
        }
      },
      {
        "status": "firing",
        "labels": {
          "alertname": "HighNetworkTraffic",
          "instance": "prod-lb01.example.com",
          "severity": "warning"
        },
        "annotations": {
          "summary": "Unusual network traffic patterns",
          "description": "Network throughput 3x normal levels"
        }
      }
    ]
  }'
```

## 4. Тестирование разных уровней severity

```bash
# Critical alerts
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "ServiceOutage",
        "instance": "prod-payment.example.com",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Payment service completely down - CRITICAL",
        "description": "All payment processing has stopped"
      }
    }]
  }'

# Info level
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing", 
      "labels": {
        "alertname": "DeploymentCompleted",
        "instance": "prod-api02.example.com",
        "severity": "info"
      },
      "annotations": {
        "summary": "Application deployment completed successfully",
        "description": "Version 2.1.3 deployed to production"
      }
    }]
  }'
```

## 5. Resolved алерты

```bash
# Resolved alert
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "resolved",
      "labels": {
        "alertname": "DiskSpaceLow", 
        "instance": "prod-db01.example.com",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Disk space issue resolved",
        "description": "Cleanup completed, disk space now at 45% usage"
      }
    }]
  }'
```

## 6. Демонстрация Prometheus обогащения

### Предварительная настройка
Убедитесь, что в `configs/seed.env` настроен:
```bash
PROM_URL=https://prometheus.sberdevices.ru
PROM_VERIFY_SSL=1
PROM_TIMEOUT=10
```

### Диагностика проблем с URL:
Судя по логу `"https://prome"` - URL обрезается. Проверьте:
```bash
# В SEED Agent логах должно быть:
grep "PROM_URL" v6/logs/agent.log

# Проверьте переменные окружения:
python3 -c "import os; print('PROM_URL:', os.getenv('PROM_URL'))"
```

### 🎯 Схема реального тестирования:
```
1. curl → p-dba-seed-adv-msk01:8080 (SEED Agent)
2. SEED Agent → prometheus.sberdevices.ru (Prometheus API) 
3. Prometheus → возвращает метрики с p-smi-mng-sc-msk07:9100/9216 (exporters)
```

### Отладка подключения к Prometheus (ИСПРАВЛЕНО - нужен HTTPS)
```bash
# Сначала проверьте доступность Prometheus API
curl -s "https://prometheus.sberdevices.ru/api/v1/query?query=up" | jq .

# Проверьте какие instance доступны для p-smi-mng-sc-msk07
curl -s "https://prometheus.sberdevices.ru/api/v1/label/instance/values" | jq . | grep "p-smi-mng-sc-msk07"

# Найдите точный instance для вашего хоста
curl -s "https://prometheus.sberdevices.ru/api/v1/query?query=up{instance=~'.*p-smi-mng-sc-msk07.*'}" | jq '.data.result[].metric.instance'

# Проверьте метрики напрямую с хоста:
curl -s "http://p-smi-mng-sc-msk07:9100/metrics" | head -20
curl -s "http://p-smi-mng-sc-msk07:9216/metrics" | head -20
```

### Тест с реальным Prometheus (обогащенные алерты)
```bash
# Используйте ТОЧНО тот instance, который есть в Prometheus
# Сначала узнайте какие есть, потом замените в команде ниже
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighCPUUsage", 
        "instance": "p-smi-mng-adv02:9100",
        "severity": "critical"
      },
      "annotations": {
        "summary": "High CPU usage on p-smi-mng-adv02",
        "description": "CPU usage is above 80% for more than 5 minutes"
      }
    }]
  }'

# Альтернатива - используйте хост который точно есть в Prometheus
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighCPUUsage",
        "instance": "p-smi-mng-sc-msk07:9100", 
        "severity": "critical"
      },
      "annotations": {
        "summary": "High CPU usage on p-smi-mng-sc-msk07",
        "description": "CPU usage is above 80% for more than 5 minutes"
      }
    }]
  }'

# Алерт с проблемами памяти на том же сервере - покажет реальные метрики
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighMemoryUsage",
        "instance": "p-smi-mng-adv02:9100",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Memory usage approaching limits on p-smi-mng-adv02",
        "description": "Memory usage exceeded 75% threshold"
      }
    }]
  }'

# Алерт с диском - тоже с реального сервера
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "DiskSpaceLow",
        "instance": "p-smi-mng-adv02:9100",
        "device": "/dev/sda1",
        "mountpoint": "/",
        "severity": "warning"
      },
      "annotations": {
        "summary": "Disk space running low on p-smi-mng-adv02",
        "description": "Root filesystem is running out of space"
      }
    }]
  }'
```

### Тест без Prometheus (базовое форматирование)
```bash
# Для демонстрации работы без обогащения - используйте несуществующий хост
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing", 
      "labels": {
        "alertname": "HighCPUUsage",
        "instance": "fake-server.example.com",
        "severity": "critical"
      },
      "annotations": {
        "summary": "High CPU usage on fake server (no metrics available)",
        "description": "This will show basic formatting without Prometheus enrichment"
      }
    }]
  }'
```

Алерты будут автоматически обогащаться метриками из Prometheus при их обработке.

## Примечания для демо

1. **Последовательность**: Начните с простых single alerts, затем покажите complex scenarios
2. **LLM**: Для получения LLM рекомендаций установите `USE_LLM=1` в configs/seed.env
3. **Prometheus**: Настройте `PROM_URL=http://p-infra-alertmanager-adv-msk01:9090` для реального обогащения метриками
4. **Mattermost**: Настройте MM_WEBHOOK для визуализации форматированных уведомлений
5. **Плагины**: Каждый тип алерта покажет разные плагины в действии

## Демо-сценарий "Два мира":

### 🟢 С Prometheus (богатые алерты):
- Используйте `instance: "p-smi-mng-adv02:9100"` 
- Получите реальные метрики CPU, память, диск
- Покажите обогащенные уведомления с трендами

### 🟡 Без Prometheus (базовые алерты):
- Используйте `instance: "fake-server.example.com"`
- Покажите как система работает без метрик
- Демонстрируйте fallback поведение

## Мониторинг демо

```bash
# Логи агента в реальном времени
tail -f v6/logs/agent.log

# Статус здоровья
watch -n 2 "curl -s http://p-dba-seed-adv-msk01:8080/health | jq ."
```