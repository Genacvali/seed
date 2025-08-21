# CLAUDE.md - SEED Agent v4

## Project Overview

SEED Agent v4 - компактная система мониторинга и уведомлений с единой архитектурой.

## Ключевые файлы

- **seed-agent.py**: Главный HTTP-сервер агента
- **seed.yaml**: Единая конфигурация системы  
- **start.sh / stop.sh**: Скрипты управления
- **build-agent.sh**: Сборка в бинарный файл
- **BUILD.md**: Полные инструкции по сборке и развертыванию

## Быстрый старт

```bash
cd v4/
./start.sh    # Запуск всего стека
./stop.sh     # Остановка
```

## Сборка и развертывание

```bash
# Сборка в бинарник
./build-agent.sh

# Установка как сервис (Linux)
sudo ./install-service.sh

# Установка как сервис (Windows) 
./install-service.ps1

# Экспорт Docker-образов
./export-images.sh

# Импорт Docker-образов
./load-images.sh
```

## Тестирование

```bash
# Проверка здоровья
curl http://localhost:8080/health

# Тест алерта
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{"alertname": "Test", "instance": "localhost"}'
```

## Компоненты

- **Агент**: FastAPI сервер на порту 8080
- **Redis**: Кеширование и троттлинг (порт 6379)
- **RabbitMQ**: Очереди сообщений (порт 5672/15672)
- **Плагины**: host_inventory, mongo_hot
- **Уведомления**: Mattermost, Slack, Email

## Производительность

- RAM: ~100MB агент + 450MB инфраструктура
- CPU: <1% в простое
- Пропускная способность: >1000 алертов/сек

Все настройки в `seed.yaml`. Система готова к production.