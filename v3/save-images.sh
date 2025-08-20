#!/bin/bash
# =============================================================================
# SEED Agent - Docker Images Saver
# Скрипт для сохранения Docker образов для offline развертывания
# =============================================================================

echo "💾 Saving Docker images for offline deployment..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Установите Docker и попробуйте снова."
    exit 1
fi

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Создаем директорию для образов
IMAGES_DIR="docker-images"
mkdir -p "$IMAGES_DIR"

echo "📦 Скачиваем и сохраняем образы в $IMAGES_DIR..."

# Сохранение RabbitMQ
echo "🐰 Скачиваем и сохраняем RabbitMQ..."
docker pull rabbitmq:3.12-management
docker save rabbitmq:3.12-management > "$IMAGES_DIR/rabbitmq.tar"
echo "✅ RabbitMQ сохранен в $IMAGES_DIR/rabbitmq.tar"

# Сохранение Redis  
echo "🔴 Скачиваем и сохраняем Redis..."
docker pull redis:7.2-alpine
docker save redis:7.2-alpine > "$IMAGES_DIR/redis.tar"
echo "✅ Redis сохранен в $IMAGES_DIR/redis.tar"

# Сохранение Python base image для SEED Agent
echo "🐍 Скачиваем и сохраняем Python..."
docker pull python:3.11-slim
docker save python:3.11-slim > "$IMAGES_DIR/python.tar"
echo "✅ Python сохранен в $IMAGES_DIR/python.tar"

# Опционально: Prometheus и Grafana для метрик
read -p "💭 Сохранить также Prometheus и Grafana для метрик? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📊 Скачиваем и сохраняем Prometheus..."
    docker pull prom/prometheus:latest
    docker save prom/prometheus:latest > "$IMAGES_DIR/prometheus.tar"
    echo "✅ Prometheus сохранен"
    
    echo "📈 Скачиваем и сохраняем Grafana..."  
    docker pull grafana/grafana:latest
    docker save grafana/grafana:latest > "$IMAGES_DIR/grafana.tar"
    echo "✅ Grafana сохранен"
fi

echo ""
echo "🎉 Сохранение образов завершено!"
echo ""
echo "📊 Размеры файлов:"
ls -lh "$IMAGES_DIR"/*.tar

echo ""
echo "📋 Сохраненные образы:"
echo "   rabbitmq.tar     - RabbitMQ 3.12 with Management UI"
echo "   redis.tar        - Redis 7.2 Alpine"  
echo "   python.tar       - Python 3.11 Slim (для сборки SEED Agent)"
if [ -f "$IMAGES_DIR/prometheus.tar" ]; then
    echo "   prometheus.tar   - Prometheus (метрики)"
fi
if [ -f "$IMAGES_DIR/grafana.tar" ]; then
    echo "   grafana.tar      - Grafana (дашборды)"
fi

echo ""
echo "🚀 Для загрузки на другой машине:"
echo "   1. Скопируйте всю папку v3/ на целевую машину"
echo "   2. Выполните: ./load-images.sh"
echo "   3. Запустите: make up"
echo ""