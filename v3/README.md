# SEED Agent - Система мониторинга и алертинга

## Архитектура

- **SEED Agent** - Python приложение, собирается в standalone бинарник
- **RabbitMQ + Redis** - вспомогательные сервисы в Docker контейнере

## Быстрый старт

### 1. Сборка и запуск сервисов (RabbitMQ + Redis)

```bash
# Сборка образа с сервисами
./build-services.sh

# Запуск контейнера с сервисами
docker run -d --name seed-services \
  -p 5672:5672 -p 15672:15672 -p 6379:6379 \
  seed-services:latest

# Проверка статуса
docker ps
docker logs seed-services
```

**Доступные сервисы:**
- RabbitMQ: `localhost:5672`
- RabbitMQ Management UI: http://localhost:15672 (seed/seed_password)
- Redis: `localhost:6379`

### 2. Сборка агента в бинарник

```bash
# Сборка SEED Agent в standalone бинарник
./build-agent.sh

# Результат: dist/seed-agent
```

### 3. Установка агента как системный сервис

```bash
# Установка как systemd сервис
sudo ./install-service.sh

# Запуск сервиса
sudo systemctl start seed-agent

# Проверка статуса
sudo systemctl status seed-agent

# Просмотр логов
sudo journalctl -u seed-agent -f
```

## Структура файлов

```
v3/
├── core/                    # Основные модули агента
├── fetchers/               # Получение данных
├── seed-agent.py           # Главный файл агента
├── seed.yaml              # Конфигурация
├── plugins.py             # Плагины мониторинга
├── requirements.txt       # Python зависимости
├── build-services.sh      # Сборка Docker с сервисами
├── build-agent.sh         # Сборка агента в бинарник
├── install-service.sh     # Установка systemd сервиса
└── Dockerfile.services    # Docker для RabbitMQ + Redis
```

## Экспорт для офлайн установки

### Экспорт Docker образа

```bash
# После сборки сервисов
docker save seed-services:latest > seed-services.tar

# На целевом сервере
docker load < seed-services.tar
```

### Перенос агента

```bash
# Копируем собранный бинарник и конфигурацию
scp dist/seed-agent user@server:/opt/
scp seed.yaml user@server:/opt/
scp plugins.py user@server:/opt/

# На целевом сервере
sudo chmod +x /opt/seed-agent
```

## Управление сервисами

### Docker сервисы

```bash
# Запуск
docker run -d --name seed-services -p 5672:5672 -p 15672:15672 -p 6379:6379 seed-services:latest

# Остановка
docker stop seed-services

# Удаление
docker rm seed-services

# Логи
docker logs seed-services
```

### SEED Agent (systemd)

```bash
# Управление
sudo systemctl start|stop|restart|status seed-agent

# Логи  
sudo journalctl -u seed-agent -f

# Автозапуск
sudo systemctl enable|disable seed-agent
```

## Тестирование

```bash
# Проверка агента
curl http://localhost:8080/health

# Отправка тестового алерта  
curl -X POST http://localhost:8080/alert \
  -H "Content-Type: application/json" \
  -d '{"level": "warning", "message": "Test alert", "source": "test"}'

# Проверка RabbitMQ UI
# http://localhost:15672 (seed/seed_password)

# Проверка Redis
redis-cli ping
```

## Конфигурация

- **seed.yaml** - основная конфигурация системы
- **plugins.py** - плагины для различных источников мониторинга
- Переменные окружения для агента:
  - `REDIS_URL=redis://127.0.0.1:6379/0`
  - `RABBITMQ_URL=amqp://seed:seed_password@127.0.0.1:5672//`