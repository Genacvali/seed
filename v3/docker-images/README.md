# 🐳 Docker Images

Эта папка содержит заранее подготовленные Docker образы для offline развертывания.

## 📦 Содержимое

- **rabbitmq.tar** - RabbitMQ 3.12 with Management
- **redis.tar** - Redis 7.2 Alpine
- (Добавь свои образы сюда)

## 🚀 Использование

### 1. Загрузка образов

```bash
# Загрузить RabbitMQ образ
docker load -i docker-images/rabbitmq.tar

# Загрузить Redis образ  
docker load -i docker-images/redis.tar

# Проверить загруженные образы
docker images | grep -E "(rabbitmq|redis)"
```

### 2. Запуск системы

```bash
# Запуск с предзагруженными образами
make up

# Или напрямую через docker-compose
docker-compose up -d
```

## 💾 Создание образов (для справки)

Если нужно пересоздать образы:

```bash
# Скачать и сохранить RabbitMQ
docker pull rabbitmq:3.12-management
docker save rabbitmq:3.12-management > docker-images/rabbitmq.tar

# Скачать и сохранить Redis
docker pull redis:7.2-alpine
docker save redis:7.2-alpine > docker-images/redis.tar

# Проверить размеры файлов
ls -lh docker-images/
```

## 📋 Образы в системе

| Сервис | Образ | Размер | Описание |
|--------|-------|--------|----------|
| RabbitMQ | `rabbitmq:3.12-management` | ~180MB | Message broker + Web UI |
| Redis | `redis:7.2-alpine` | ~30MB | Cache/throttling |
| SEED Agent | `seed-agent:latest` | ~200MB | Собирается локально |

## 🔧 Troubleshooting

### Образ не найден
```bash
# Проверить доступные образы
docker images

# Перезагрузить образ
docker load -i docker-images/rabbitmq.tar
```

### Проблемы с размером
```bash
# Очистить неиспользуемые образы
docker system prune

# Проверить место на диске
df -h
```

### Обновление образов
```bash
# Обновить до новых версий
docker pull rabbitmq:3.12-management
docker pull redis:7.2-alpine

# Пересохранить
docker save rabbitmq:3.12-management > docker-images/rabbitmq.tar
docker save redis:7.2-alpine > docker-images/redis.tar
```

---

**Примечание**: Образы загружены для offline развертывания на VM без интернета.