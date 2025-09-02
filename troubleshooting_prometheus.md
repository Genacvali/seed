# Диагностика проблемы "CPU ~ n/a · MEM ~ n/a"

## Проблема: Система подключается к Prometheus, но метрики возвращают `n/a`

## Чек-лист диагностики:

### 1. Проверьте подключение к Prometheus
```bash
# Базовая проверка API (ИСПРАВЛЕНО на реальный URL)
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=up" | jq .

# Ответ должен быть примерно:
# {"status":"success","data":{"resultType":"vector","result":[...]}}
```

### 2. Проверьте существование instance в Prometheus
```bash
# Узнайте все доступные instance
curl -s "http://prometheus.sberdevices.ru/api/v1/label/instance/values" | jq .

# Должен быть в списке: "p-smi-mng-sc-msk07:9100"
```

### 3. Проверьте конкретные метрики для этого instance
```bash
# CPU метрика (node-exporter)
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=node_cpu_seconds_total{instance=\"p-smi-mng-sc-msk07:9100\"}" | jq .

# Memory метрика
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=node_memory_MemAvailable_bytes{instance=\"p-smi-mng-sc-msk07:9100\"}" | jq .
```

### 4. Проверьте точные запросы которые делает SEED
```bash
# CPU запрос который использует enrich.py:
curl -s "http://prometheus.sberdevices.ru/api/v1/query" \
  --data-urlencode 'query=100 * (1 - avg(rate(node_cpu_seconds_total{instance="p-smi-mng-sc-msk07:9100",mode="idle"}[5m])))' | jq .

# Memory запрос:
curl -s "http://prometheus.sberdevices.ru/api/v1/query" \
  --data-urlencode 'query=100 * (1 - (node_memory_MemAvailable_bytes{instance="p-smi-mng-sc-msk07:9100"} / node_memory_MemTotal_bytes{instance="p-smi-mng-sc-msk07:9100"}))' | jq .
```

### 5. Проверьте логи SEED Agent
```bash
# Ищите ошибки Prometheus запросов
tail -f v6/logs/agent.log | grep -E "(ENRICH|PROM|ERROR)"

# Должны быть строки типа:
# [ENRICH] HighCPUUsage: CPU: 45%, Memory: 67%
```

### 6. Проверьте конфигурацию SEED
```bash
# Проверьте переменные окружения
python3 -c "
import os
print('PROM_URL:', os.getenv('PROM_URL'))
print('PROM_VERIFY_SSL:', os.getenv('PROM_VERIFY_SSL'))
print('PROM_TIMEOUT:', os.getenv('PROM_TIMEOUT'))
print('PROM_BEARER:', os.getenv('PROM_BEARER'))
"
```

### 7. Тест модуля обогащения напрямую
```bash
# Перейдите в директорию v6 и запустите:
cd v6
python3 -c "
from enrich import enrich_alert
alert = {'labels': {'instance': 'p-smi-mng-sc-msk07:9100'}}
result = enrich_alert(alert)
print('Enrichment result:', result)
"
```

## Возможные причины и решения:

### Причина 1: Неправильный формат instance
- **Проблема**: В Prometheus instance может быть `p-smi-mng-sc-msk07:9100` или просто `p-smi-mng-sc-msk07`
- **Решение**: Проверьте точный формат через API и используйте его

### Причина 2: Другие названия метрик  
- **Проблема**: Вместо `node_cpu_seconds_total` могут быть другие названия
- **Решение**: Узнайте доступные метрики:
```bash
curl -s "http://p-infra-alertmanager-adv-msk01:9090/api/v1/label/__name__/values" | jq . | grep cpu
```

### Причина 3: Нет данных за последние 5 минут
- **Проблема**: Запросы используют `[5m]` range, но данных нет
- **Решение**: Проверьте последние значения:
```bash
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=node_cpu_seconds_total{instance=\"p-smi-mng-sc-msk07:9100\"}" | jq '.data.result[0].value'
```

### Причина 4: Права доступа
- **Проблема**: Prometheus требует аутентификацию
- **Решение**: Настройте `PROM_BEARER` токен если нужен

## Специфичная диагностика для вашей инфраструктуры:

```bash
# 1. Проверьте доступность внешнего Prometheus
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=up{instance=~'p-smi-mng-sc-msk07.*'}" | jq .

# 2. Проверьте метрики напрямую с exporters
curl -s "http://p-smi-mng-sc-msk07:9100/metrics" | grep "node_cpu_seconds_total" | head -5
curl -s "http://p-smi-mng-sc-msk07:9216/metrics" | grep "cpu" | head -5

# 3. Узнайте как именно instance зарегистрирован в Prometheus
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=node_cpu_seconds_total" | jq '.data.result[].metric.instance' | grep "p-smi-mng-sc-msk07" | head -3

# 4. Проверьте Telegraf метрики (порт 9216)
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=cpu_usage_active" | jq '.data.result[].metric.instance' | grep "p-smi-mng-sc-msk07"
```

## Быстрая диагностика для презентации:

```bash
# 1. Найдите рабочий instance
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=up" | jq -r '.data.result[0].metric.instance'

# 2. Используйте его в тесте
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {
        "alertname": "HighCPUUsage",
        "instance": "НАЙДЕННЫЙ_INSTANCE_ЗДЕСЬ",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Test alert with real metrics"
      }
    }]
  }'
```