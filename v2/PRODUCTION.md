# SEED v2 - Production Setup

## 1. Установка как systemd сервис

### Быстрая установка:
```bash
chmod +x install_service.sh
./install_service.sh
```

### Ручная установка:
```bash
# Копируем service файлы
sudo cp seed-api.service /etc/systemd/system/
sudo cp seed-worker.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable seed-api.service
sudo systemctl enable seed-worker.service

# Запускаем сервисы
sudo systemctl start seed-api.service
sudo systemctl start seed-worker.service
```

### Управление сервисами:
```bash
# Проверка статуса
sudo systemctl status seed-api
sudo systemctl status seed-worker

# Перезапуск
sudo systemctl restart seed-api
sudo systemctl restart seed-worker

# Логи
sudo journalctl -u seed-api -f
sudo journalctl -u seed-worker -f

# Остановка
sudo systemctl stop seed-api seed-worker
```

## 2. Настройка Alertmanager

### 2.1 Конфигурация для предотвращения спама алертов

**В `alertmanager.yml` добавьте:**

```yaml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@company.com'

# Группировка алертов для уменьшения спама
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s        # Ждем 30 сек перед отправкой первого алерта
  group_interval: 5m     # Группируем новые алерты каждые 5 минут
  repeat_interval: 12h   # Повторяем алерт не чаще раза в 12 часов
  
  # Маршруты для SEED
  routes:
  - match:
      alertname: mongo_collscan
    receiver: seed-mongo
    group_wait: 1m
    group_interval: 10m
    repeat_interval: 1h
    
  - match:
      alertname: host_inventory
    receiver: seed-host
    group_wait: 5m
    group_interval: 30m
    repeat_interval: 6h

receivers:
- name: 'seed-mongo'
  webhook_configs:
  - url: 'http://your-server:8000/alert'
    send_resolved: false
    max_alerts: 5  # Лимит алертов в одном webhook

- name: 'seed-host'
  webhook_configs:
  - url: 'http://your-server:8000/alert'
    send_resolved: false
    max_alerts: 3

# Подавление повторяющихся алертов
inhibit_rules:
- source_match:
    severity: 'critical'
  target_match:
    severity: 'warning'
  equal: ['alertname', 'cluster', 'service']
```

### 2.2 Дополнительные правила фильтрации

**Для Prometheus rules (например в `mongodb.rules.yml`):**

```yaml
groups:
- name: mongodb.collscan
  interval: 60s
  rules:
  - alert: MongoCollscanDetected
    expr: |
      increase(mongodb_metrics_document_total{state="scanned"}[5m]) > 10000
      and
      rate(mongodb_metrics_document_total{state="scanned"}[5m]) > 100
    for: 2m  # Алерт только если проблема длится > 2 минут
    labels:
      severity: warning
      alertname: mongo_collscan
    annotations:
      summary: "MongoDB COLLSCAN detected"
      description: "High document scan rate detected: {{ $value }} docs/sec"

  # Алерт только в рабочее время
  - alert: MongoCollscanBusinessHours
    expr: |
      increase(mongodb_metrics_document_total{state="scanned"}[5m]) > 50000
      and
      hour() >= 9 and hour() <= 18  # 9:00-18:00
      and
      day_of_week() >= 1 and day_of_week() <= 5  # Пн-Пт
    for: 1m
    labels:
      severity: critical
      alertname: mongo_collscan
```

### 2.3 Рекомендуемые настройки для продакшена

1. **Throttling на стороне SEED:**
   - Уже настроен в коде: один алерт в 15 минут по умолчанию
   - Настройка через `ALERT_TTL` в `seed.env`

2. **Группировка в Alertmanager:**
   - `group_wait: 1-5m` - первый алерт
   - `group_interval: 10-30m` - новые алерты в группе
   - `repeat_interval: 1-12h` - повтор того же алерта

3. **Фильтрация по времени:**
   - Критичные алерты - круглосуточно
   - Warning алерты - только в рабочее время
   - Info алерты - раз в день

4. **Лимиты:**
   - `max_alerts: 3-5` в webhook
   - Не более 10 алертов в час на один хост

### 2.4 Тестирование настроек

```bash
# Проверка конфигурации Alertmanager
amtool config show

# Тест webhook
amtool alert add alertname=test_alert instance=test:9090

# Проверка что SEED получает алерты
curl http://your-server:8000/stats
```