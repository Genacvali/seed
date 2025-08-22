# SEED Agent v5 🚀

**Universal LLM-powered Alert Processing System**

Компактная система мониторинга и уведомлений с LLM-анализом алертов для production окружений.

## ⚡ Быстрый старт

```bash
# 1. Настройка
cp seed.env.example seed.env
nano seed.env  # Заполнить GIGACHAT_CLIENT_ID и CLIENT_SECRET

# 2. Запуск
./start.sh

# 3. Проверка
./smoke-test.sh
```

## 📋 Требования

- **Python 3.8+** с зависимостями из requirements.txt
- **Docker/Podman** для Redis и RabbitMQ
- **GigaChat credentials** (обязательно для LLM)
- **Webhook URL** для Mattermost/Slack (опционально)

## 🏗️ Архитектура

- **FastAPI** - HTTP API на порту 8080
- **GigaChat** - LLM анализ алертов 
- **Redis** - кеширование и throttling
- **RabbitMQ** - очереди сообщений
- **Mattermost/Slack** - уведомления

## 📊 Ключевые эндпоинты

- `POST /alert` - прием алертов от Alertmanager
- `GET /health` - статус системы
- `GET /llm/selftest` - диагностика LLM
- `GET /dashboard` - живые метрики
- `POST /config/reload` - горячая перезагрузка

## 🔧 Конфигурация

Вся настройка в двух файлах:
- **`seed.yaml`** - основная конфигурация
- **`seed.env`** - переменные окружения (credentials)

## 📈 Производительность

- **RAM**: ~100MB агент + 450MB инфраструктура
- **CPU**: <1% в простое
- **Пропускная способность**: >1000 алертов/сек
- **Время отклика**: <100ms

## 📚 Документация

- **[QUICKSTART.md](QUICKSTART.md)** - подробная настройка и диагностика
- **[smoke-test.sh](smoke-test.sh)** - автоматическая проверка системы

## 🆘 Поддержка

При проблемах:
1. Запустите `./smoke-test.sh` для диагностики
2. Проверьте логи: `tail -f seed-agent.log | grep -E "(📁|✅|❌|📤)"`
3. Используйте `/llm/selftest` для диагностики LLM

---
*SEED Agent v5 - готов к production* ✨