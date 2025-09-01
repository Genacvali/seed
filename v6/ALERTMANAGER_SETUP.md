# 🚨 Настройка Alertmanager для SEED v6

Подробная инструкция по интеграции Prometheus Alertmanager с SEED Agent v6.

---

## 🎯 Цель интеграции

Настроить Alertmanager для отправки алертов в SEED v6, где они будут:
- ✅ Обработаны соответствующими плагинами  
- ✅ Обогащены метриками Prometheus
- ✅ Проанализированы LLM (GigaChat)
- ✅ Отправлены в Mattermost с цветным форматированием

---

## 📋 Предварительные требования

### 1. **SEED Agent v6 готов к работе**
```bash
# Проверить статус SEED Agent
curl http://p-dba-seed-adv-msk01:8080/health | jq .

# Ожидаемый результат:
{
  "status": "ok",
  "plugins_enabled": true,
  "plugin_routes": 15,
  "prometheus_enrichment": true,
  "prometheus_url": "http://your-prometheus:9090"
}
```

### 2. **Доступ к конфигурации Alertmanager**
- Права на редактирование `alertmanager.yml`
- Возможность перезапуска Alertmanager

---

## ⚙️ Конфигурация Alertmanager

### 1. **Базовая конфигурация `alertmanager.yml`**

```yaml
# /etc/alertmanager/alertmanager.yml
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alertmanager@your-domain.com'
  
# Маршрутизация алертов  
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s  
  repeat_interval: 12h
  receiver: 'seed-webhook'
  
  # Специальные маршруты для разных типов алертов
  routes:
    # Критические алерты - немедленно в SEED
    - match:
        severity: critical
      receiver: 'seed-critical'
      group_wait: 0s
      group_interval: 30s
      repeat_interval: 5m
      
    # PostgreSQL алерты - в специальный канал  
    - match_re:
        alertname: '^(PG_|PostgreSQL|Postgres).*'
      receiver: 'seed-database'
      group_by: ['alertname', 'instance']
      
    # MongoDB алерты
    - match_re:
        alertname: '^(Mongo|MongoDB).*'
      receiver: 'seed-database' 
      
    # Системные алерты (CPU/Memory/Disk)
    - match_re:
        alertname: '^(High|Low|Disk|CPU|Memory|Load).*'
      receiver: 'seed-system'

# Получатели (receivers) - веб-хуки в SEED
receivers:
  # Основной канал SEED
  - name: 'seed-webhook'
    webhook_configs:
    - url: 'http://p-dba-seed-adv-msk01:8080/alertmanager'
      send_resolved: true
      http_config:
        bearer_token: 'optional-auth-token'  # если нужна авторизация
      title: 'SEED Alert - {{ .GroupLabels.alertname }}'
      
  # Критические алерты - быстрая отправка  
  - name: 'seed-critical'
    webhook_configs:
    - url: 'http://p-dba-seed-adv-msk01:8080/alertmanager'
      send_resolved: true
      title: 'CRITICAL - {{ .GroupLabels.alertname }}'
      
  # Алерты БД - с дополнительным контекстом
  - name: 'seed-database'
    webhook_configs:
    - url: 'http://p-dba-seed-adv-msk01:8080/alertmanager'
      send_resolved: true
      title: 'DATABASE - {{ .GroupLabels.alertname }}'
      
  # Системные алерты
  - name: 'seed-system' 
    webhook_configs:
    - url: 'http://p-dba-seed-adv-msk01:8080/alertmanager'
      send_resolved: true
      title: 'SYSTEM - {{ .GroupLabels.alertname }}'

# Подавление дублированных алертов
inhibit_rules:
  # Если есть критический алерт - подавляем предупреждения
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
```

### 2. **Расширенная конфигурация с темплейтами**

```yaml
# Дополнительно в alertmanager.yml
templates:
  - '/etc/alertmanager/templates/*.tmpl'

receivers:
  - name: 'seed-webhook'
    webhook_configs:
    - url: 'http://p-dba-seed-adv-msk01:8080/alertmanager'
      send_resolved: true
      # Дополнительные поля для лучшего контекста
      title: '{{ .GroupLabels.alertname }}'  
      text: |
        {{ range .Alerts -}}
        Alert: {{ .Annotations.summary }}
        Instance: {{ .Labels.instance }}
        Severity: {{ .Labels.severity }}
        Started: {{ .StartsAt.Format "2006-01-02 15:04:05" }}
        {{ if .Annotations.description }}
        Description: {{ .Annotations.description }}
        {{ end }}
        {{ end -}}
```

---

## 🎛️ Prometheus Rules для лучшей интеграции

### 1. **Создайте правила с правильными лейблами**

```yaml
# /etc/prometheus/rules/seed-integration.yml
groups:
- name: seed.database.postgresql
  rules:
  # PostgreSQL алерты с правильными именами для плагинов
  - alert: PG_IdleInTransaction_Storm
    expr: |
      pg_stat_activity_count{state="idle in transaction"} > 10
    for: 5m
    labels:
      severity: warning
      service: postgresql
      component: database
    annotations:
      summary: "Много сеансов idle in transaction на {{ $labels.instance }}"
      description: "{{ $value }} idle in transaction сессий больше 10 минут"

  - alert: PostgresSlowQuery
    expr: |
      rate(pg_stat_statements_mean_time[5m]) > 1000
    for: 2m  
    labels:
      severity: high
      service: postgresql
      component: database
    annotations:
      summary: "Медленные запросы PostgreSQL на {{ $labels.instance }}"
      description: "Среднее время выполнения запросов {{ $value }}ms"

- name: seed.system.resources  
  rules:
  # Системные алерты с правильными именами
  - alert: DiskSpaceHigh
    expr: |
      100 * (node_filesystem_size_bytes - node_filesystem_avail_bytes) 
      / node_filesystem_size_bytes > 90
    for: 5m
    labels:
      severity: critical
      service: system
      component: disk
    annotations:
      summary: "Диск {{ $labels.mountpoint }} заполнен на {{ $value | printf \"%.1f\" }}%"
      description: "Свободного места меньше 10% на {{ $labels.instance }}:{{ $labels.mountpoint }}"

  - alert: HighCPUUsage
    expr: |
      100 * (1 - avg by(instance)(rate(node_cpu_seconds_total{mode="idle"}[5m]))) > 80
    for: 10m
    labels:
      severity: warning  
      service: system
      component: cpu
    annotations:
      summary: "Высокая нагрузка CPU на {{ $labels.instance }}"
      description: "CPU usage {{ $value | printf \"%.1f\" }}% больше 5 минут"

- name: seed.mongodb
  rules:
  - alert: MongoCollscan  
    expr: |
      rate(mongodb_metrics_operation_scan_total[5m]) > 100
    for: 3m
    labels:
      severity: high
      service: mongodb
      component: database  
    annotations:
      summary: "MongoDB выполняет много collection scans"
      description: "{{ $value }} collection scans в секунду на {{ $labels.instance }}"
```

### 2. **Обязательные лейблы для правильной работы плагинов**

Убедитесь что все алерты содержат:
- ✅ `alertname` - для маршрутизации к плагинам
- ✅ `instance` - для Prometheus запросов 
- ✅ `severity` - для цветового кодирования
- ✅ `mountpoint` - для disk алертов (если применимо)

---

## 🧪 Тестирование интеграции

### 1. **Проверка конфигурации Alertmanager**
```bash
# Проверить синтаксис конфигурации
amtool config check /etc/alertmanager/alertmanager.yml

# Перезапустить Alertmanager  
sudo systemctl reload alertmanager

# Проверить статус
sudo systemctl status alertmanager
```

### 2. **Тестовые алерты**
```bash
# Отправить тестовый алерт напрямую в Alertmanager
curl -X POST http://your-alertmanager:9093/api/v1/alerts \
  -H 'Content-Type: application/json' \
  -d '[{
    "labels": {
      "alertname": "TestDiskAlert",
      "instance": "db-server-01", 
      "severity": "critical",
      "mountpoint": "/var/lib/postgresql"
    },
    "annotations": {
      "summary": "Test disk space alert for SEED integration",
      "description": "This is a test alert to verify SEED plugin routing"
    },
    "startsAt": "'$(date -Iseconds)'",
    "endsAt": "'$(date -d '+1 hour' -Iseconds)'"
  }]'

# Ожидаемый результат в SEED:
# 1. Алерт попадет в os_basic плагин (DiskSpaceHigh не точно, но по severity: critical)
# 2. Покажет системные метрики с Prometheus
# 3. LLM даст рекомендации по очистке диска
```

### 3. **Проверка через Prometheus**
```bash
# Вызвать алерт вручную через Prometheus
# Создайте временное правило:
- alert: TestSEEDIntegration
  expr: up == 1  # всегда срабатывает
  labels:
    severity: warning
    alertname: TestSEEDIntegration
  annotations:
    summary: "Test SEED integration alert"
```

---

## 🔧 Устранение проблем

### 1. **Алерты не доходят до SEED**
```bash
# Проверить логи Alertmanager
sudo journalctl -u alertmanager -f

# Проверить доступность SEED endpoint  
curl -X POST http://p-dba-seed-adv-msk01:8080/alertmanager \
  -H 'Content-Type: application/json' \
  -d '{"alerts": [{"labels": {"alertname": "test"}}]}'

# Проверить сеть
telnet p-dba-seed-adv-msk01 8080
```

### 2. **Плагины не активируются**
```bash
# Проверить маппинг в SEED
curl http://p-dba-seed-adv-msk01:8080/health | jq .

# Проверить логи SEED
tail -f /data/seed/v6/logs/agent.log | grep -E "(PLUGIN|ENRICH)"

# Убедиться что alertname точно совпадает с configs/alerts.yaml
```

### 3. **Prometheus enrichment не работает** 
```bash
# Проверить что SEED может достучаться до Prometheus
curl -v http://your-prometheus:9090/api/v1/query?query=up

# Проверить PROM_URL в configs/seed.env
cat /data/seed/v6/configs/seed.env | grep PROM_URL
```

---

## 📊 Мониторинг интеграции

### 1. **Метрики Alertmanager**
```promql
# Количество отправленных webhook'ов в SEED
alertmanager_notifications_total{integration="webhook"}

# Ошибки отправки
alertmanager_notifications_failed_total{integration="webhook"}

# Время отклика SEED
alertmanager_notification_duration_seconds{integration="webhook"}
```

### 2. **Dashboard для мониторинга**
Создайте Grafana dashboard с панелями:
- Количество алертов по типам
- Время обработки в SEED  
- Успешность доставки в Mattermost
- Активность плагинов

---

## 🎯 Лучшие практики

### 1. **Группировка алертов**
- Группируйте по `alertname` + `instance` для системных
- Группируйте по `alertname` + `database` для БД
- Используйте короткие интервалы для критических

### 2. **Naming convention**
```yaml
# Хорошие имена алертов (точно соответствуют plugins)
alertname: "DiskSpaceHigh"        # → os_basic plugin
alertname: "PG_IdleInTransaction_Storm" # → pg_slow plugin  
alertname: "MongoCollscan"        # → mongo_hot plugin
alertname: "InstanceDown"         # → host_inventory plugin

# Плохие имена (не попадут в специальные плагины)
alertname: "disk_usage_critical"  # → echo plugin (default)
alertname: "postgres_problem"     # → echo plugin (default)
```

### 3. **Annotations для LLM**
```yaml
annotations:
  summary: "Краткое описание проблемы"
  description: "Детальное описание с контекстом для LLM"
  runbook_url: "https://wiki.company.com/runbooks/disk-cleanup"
```

---

## 🚀 Итоговая проверка

После настройки выполните:

```bash
# 1. Перезапустить Alertmanager
sudo systemctl reload alertmanager

# 2. Проверить SEED Agent  
curl http://p-dba-seed-adv-msk01:8080/health

# 3. Отправить тестовый алерт
curl -X POST http://your-alertmanager:9093/api/v1/alerts -d '[...]'

# 4. Проверить Mattermost канал на получение уведомления

# 5. Проверить логи SEED  
tail -f /data/seed/v6/logs/agent.log
```

**Готово!** 🎉 Alertmanager интегрирован с SEED v6 и будет отправлять алерты для обработки плагинами, обогащения метриками и анализа LLM!