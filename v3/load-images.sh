#!/bin/bash
# =============================================================================
# SEED Agent - Docker Images Loader
# Скрипт для загрузки предустановленных Docker образов
# =============================================================================

echo "🐳 Loading Docker images for SEED Agent..."

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Установите Docker и попробуйте снова."
    exit 1
fi

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Путь к образам
IMAGES_DIR="docker-images"

if [ ! -d "$IMAGES_DIR" ]; then
    echo "❌ Директория $IMAGES_DIR не найдена"
    exit 1
fi

echo "📦 Загружаем Docker образы из $IMAGES_DIR..."

# Загрузка RabbitMQ
if [ -f "$IMAGES_DIR/rabbitmq.tar" ]; then
    echo "🐰 Загружаем RabbitMQ..."
    docker load -i "$IMAGES_DIR/rabbitmq.tar"
    echo "✅ RabbitMQ загружен"
else
    echo "⚠️  Файл rabbitmq.tar не найден, образ будет скачан из Docker Hub"
fi

# Загрузка Redis
if [ -f "$IMAGES_DIR/redis.tar" ]; then
    echo "🔴 Загружаем Redis..."
    docker load -i "$IMAGES_DIR/redis.tar"
    echo "✅ Redis загружен"
else
    echo "⚠️  Файл redis.tar не найден, образ будет скачан из Docker Hub"
fi

# Загрузка дополнительных образов
for img_file in "$IMAGES_DIR"/*.tar; do
    if [ -f "$img_file" ] && [ "$(basename "$img_file")" != "rabbitmq.tar" ] && [ "$(basename "$img_file")" != "redis.tar" ]; then
        echo "📦 Загружаем $(basename "$img_file")..."
        docker load -i "$img_file"
        echo "✅ $(basename "$img_file") загружен"
    fi
done

echo ""
echo "🎉 Загрузка образов завершена!"
echo ""
echo "📋 Загруженные образы:"
docker images | head -1  # header
docker images | grep -E "(rabbitmq|redis|seed)" || echo "   (образы SEED будут показаны после сборки)"

echo ""
echo "🚀 Теперь можно запустить систему:"
echo "   make up          # Запуск продакшн окружения"
echo "   make dev         # Запуск для разработки"  
echo "   make build       # Собрать SEED Agent образ"
echo ""