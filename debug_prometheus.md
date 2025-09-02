# Отладка Prometheus подключения

## Проблема: parse error: Invalid numeric literal at line 1, column 7

Это означает что Prometheus возвращает не JSON, а HTML страницу с ошибкой или редирект.

## Шаг 1: Посмотрите сырой ответ
```bash
# Без jq - посмотрите что возвращается
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=up{instance=~'p-smi-mng-sc-msk07.*'}"

# Или проще запрос
curl -s "http://prometheus.sberdevices.ru/api/v1/query?query=up"
```

## Шаг 2: Проверьте базовую доступность
```bash
# Проверка доступности главной страницы
curl -I "http://prometheus.sberdevices.ru"

# Проверка API endpoint
curl -I "http://prometheus.sberdevices.ru/api/v1/query"
```

## Шаг 3: Возможные проблемы

### Проблема 1: Нужна аутентификация
```bash
# Если требуется токен авторизации
curl -s -H "Authorization: Bearer YOUR_TOKEN" "http://prometheus.sberdevices.ru/api/v1/query?query=up"
```

### Проблема 2: Редирект на HTTPS
```bash
# Попробуйте HTTPS
curl -s "https://prometheus.sberdevices.ru/api/v1/query?query=up"
```

### Проблема 3: Другой порт или путь
```bash
# Возможно нужен порт
curl -s "http://prometheus.sberdevices.ru:9090/api/v1/query?query=up"

# Или другой путь
curl -s "http://prometheus.sberdevices.ru/prometheus/api/v1/query?query=up"
```

## Шаг 4: Проверьте метрики напрямую
```bash
# Проверьте доступны ли exporters
curl -s "http://p-smi-mng-sc-msk07:9100/metrics" | head -10
curl -s "http://p-smi-mng-sc-msk07:9216/metrics" | head -10
```

## Быстрое решение для демо

Если Prometheus недоступен, можно временно настроить на локальные метрики:

```bash
# В configs/seed.env временно отключите Prometheus
PROM_URL=
# или
PROM_URL=http://p-smi-mng-sc-msk07:9216
```

Тогда система будет работать без обогащения метриками, но показывать базовые алерты.