# Требования к сетевым доступам для SEED Agent

## Схема сетевых подключений:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Alertmanager  │───▶│  SEED Agent      │───▶│   Mattermost        │
│   (любой хост)  │    │ p-dba-seed-adv-  │    │   (webhook URL)     │
│                 │    │ msk01:8080       │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │   Prometheus API     │
                    │ prometheus.sber      │
                    │ devices.ru:443       │
                    └──────────────────────┘
                              │
                              ▼
                    ┌──────────────────────┐
                    │   Exporters          │
                    │ p-smi-mng-sc-msk07   │
                    │ :9100, :9216         │
                    └──────────────────────┘
```

## Требуемые доступы для SEED Agent:

### 1. **ВХОДЯЩИЕ подключения (кто подключается К агенту):**
- **Alertmanager** → `p-dba-seed-adv-msk01:8080`
- **Пользователи для тестов** → `p-dba-seed-adv-msk01:8080`

### 2. **ИСХОДЯЩИЕ подключения (агент подключается К кому):**

#### A) **Prometheus API** (ОБЯЗАТЕЛЬНО для обогащения):
- `p-dba-seed-adv-msk01` → `https://prometheus.sberdevices.ru:443`
- **Протокол:** HTTPS
- **Тип трафика:** REST API запросы
- **Частота:** При каждом алерте (1-5 запросов за раз)

#### B) **Mattermost/Slack** (для уведомлений):
- `p-dba-seed-adv-msk01` → `ВАШ_MATTERMOST_URL`
- **Протокол:** HTTPS
- **Тип трафика:** Webhook POST запросы
- **Частота:** При каждом алерте

#### C) **GigaChat LLM** (опционально, для AI анализа):
- `p-dba-seed-adv-msk01` → `ngw.devices.sberbank.ru:9443` (OAuth)
- `p-dba-seed-adv-msk01` → `gigachat.devices.sberbank.ru:443` (API)
- **Протокол:** HTTPS
- **Тип трафика:** REST API для LLM запросов

#### D) **Exporters** (НЕ нужно агенту, только для прямой проверки):
- `p-smi-mng-sc-msk07:9100/metrics` - для диагностики
- `p-smi-mng-sc-msk07:9216/metrics` - для диагностики

## Доступы которые НЕ нужны:

❌ **SEED Agent НЕ подключается напрямую к exporters**
- Prometheus сам собирает метрики с exporters
- SEED просит данные только у Prometheus API

❌ **Exporters НЕ подключаются к SEED**
- Это односторонний сбор через Prometheus

## Критичные доступы для работы:

### **Минимум для базовой работы:**
1. ✅ **Входящий:** `*` → `p-dba-seed-adv-msk01:8080`
2. ✅ **Исходящий:** `p-dba-seed-adv-msk01` → `MM_WEBHOOK_URL`

### **Для полной функциональности:**
3. ✅ **Исходящий:** `p-dba-seed-adv-msk01` → `https://prometheus.sberdevices.ru:443`
4. ⚠️ **Исходящий:** `p-dba-seed-adv-msk01` → GigaChat URLs (опционально)

## Проверка доступности:

```bash
# Проверьте доступ к Prometheus
curl -I "https://prometheus.sberdevices.ru"

# Проверьте доступ к Mattermost  
curl -X POST "$MM_WEBHOOK" -d '{"text":"test"}'

# Проверьте доступ к GigaChat (если используете)
curl -I "https://ngw.devices.sberbank.ru:9443"
```

## Возможные проблемы с доступами:

### **Prometheus недоступен:**
- ✅ **Симптом:** `CPU ~ n/a · MEM ~ n/a`
- ✅ **Решение:** Откройте доступ или временно отключите (`PROM_URL=`)

### **Mattermost недоступен:**  
- ❌ **Симптом:** Алерты обрабатываются, но не приходят уведомления
- ✅ **Решение:** Откройте доступ к webhook URL

### **GigaChat недоступен:**
- ⚠️ **Симптом:** Нет секции "🧠 Магия кристалла"
- ✅ **Решение:** Откройте доступ или отключите (`USE_LLM=0`)

## Резюме:

**ОБЯЗАТЕЛЬНО нужен доступ:**
- К Prometheus API: `https://prometheus.sberdevices.ru:443`
- К Mattermost webhook

**НЕ нужен прямой доступ:**
- К exporters (9100, 9216) - это делает Prometheus