# SEED Agent v4 - Быстрый старт

## Исправленные проблемы

✅ **LLM конфигурация** - исправлена проверка на непустые значения  
✅ **Mattermost уведомления** - корректное формирование сообщений  
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
curl http://localhost:8080/llm/selftest

# Должно показать present: true для всех GIGACHAT_* переменных
```

Если не приходят уведомления в Mattermost:

```bash
# Проверьте логи отправки
tail -f seed-agent.log | grep -i mattermost

# Проверьте конфигурацию уведомлений
curl http://localhost:8080/config
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
- Ищите строки с `📊 LLM config values` для диагностики LLM
- Ищите `❌ GigaChat disabled` если LLM не работает
- Ищите `Mattermost message sent` для уведомлений