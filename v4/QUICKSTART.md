# SEED Agent v4 - Быстрый старт

## Исправленные проблемы

✅ **LLM конфигурация** - исправлена проверка на непустые значения  
✅ **Загрузка переменных окружения** - start.sh теперь автоматически загружает seed.env  
✅ **Перезагрузка конфигурации** - /config/reload теперь пересоздает LLM и уведомления  
✅ **Mattermost уведомления** - улучшено логирование ошибок и статуса отправки  
✅ **Версионные несоответствия** - приведено к единому v4  
✅ **Безопасность** - убран хардкод credentials из конфигурации  

## Настройка для RedHat сервера

### 1. Подготовка окружения

```bash
# Скопируйте пример переменных окружения
cp seed.env.example seed.env

# Отредактируйте seed.env и укажите РЕАЛЬНЫЕ credentials GigaChat
nano seed.env
```

Обязательно заполните в `seed.env`:
```bash
GIGACHAT_CLIENT_ID=ваш-настоящий-client-id
GIGACHAT_CLIENT_SECRET=ваш-настоящий-client-secret
```

### 2. Запуск

```bash
cd v4/
./start.sh
```

### 3. Диагностика проблем

Если `llm: false` в health check:

```bash
# Проверьте конфигурацию LLM
curl http://localhost:8080/llm/selftest | jq .

# Должно показать present: true для всех GIGACHAT_* переменных
# Если present: false - проверьте seed.env файл
```

Если не приходят уведомления в Mattermost:

```bash
# Проверьте детальные логи отправки (теперь с эмодзи и подробностями)
tail -f seed-agent.log | grep -E "(📤|✅|❌).*[Mm]attermost"

# Проверьте конфигурацию уведомлений
curl http://localhost:8080/config | jq .notifications

# Перезагрузите конфиг без рестарта (теперь пересоздает клиентов)
curl -X POST http://localhost:8080/config/reload
```

### 4. Быстрые тесты

```bash
# Тест здоровья системы
curl http://localhost:8080/health | jq .

# Тест алерта (замените hostname на реальный)
curl -X POST http://localhost:8080/alert \\
  -H 'Content-Type: application/json' \\
  -d '{"alerts":[{"labels":{"alertname":"TestAlert","instance":"hostname","severity":"warning"},"annotations":{"summary":"Тестовый алерт"},"status":"firing"}]}'

# Живая панель статистики
curl http://localhost:8080/dashboard | jq .
```

## Ключевые эндпоинты

- `GET /health` - статус системы
- `GET /llm/selftest` - диагностика LLM
- `GET /config` - просмотр конфигурации (без секретов)
- `GET /dashboard` - живые метрики
- `POST /alert` - прием алертов от Alertmanager

## Структура логов

- `seed-agent.log` - основные логи приложения
- `📁 Loading environment variables` - загрузка seed.env
- `📊 LLM config values` - диагностика LLM конфига
- `❌ GigaChat disabled` - если LLM не работает
- `📤 Sending notification` - начало отправки уведомлений
- `✅ Mattermost message sent` - успешная отправка в Mattermost
- `❌ Mattermost API error` - ошибки Mattermost с кодами и описанием

## Новые возможности

- **Горячая перезагрузка**: `curl -X POST /config/reload` теперь пересоздает все клиенты
- **Автозагрузка .env**: start.sh автоматически загружает переменные из seed.env  
- **Улучшенная диагностика**: подробные логи с эмодзи для быстрого поиска проблем