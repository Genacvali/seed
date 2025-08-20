#!/bin/bash
# =============================================================================
# Сборка контейнера с RabbitMQ + Redis для SEED Agent
# =============================================================================

echo "🔧 Сборка контейнера SEED Services (RabbitMQ + Redis)..."

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Установите Docker."
    exit 1
fi

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Сборка образа
echo "📦 Сборка образа seed-services:latest..."
docker build -f Dockerfile.services -t seed-services:latest .

if [ $? -eq 0 ]; then
    echo "✅ Образ seed-services:latest собран успешно!"
    echo ""
    echo "🚀 Для запуска:"
    echo "   docker run -d --name seed-services \\"
    echo "     -p 5672:5672 -p 15672:15672 -p 6379:6379 \\"
    echo "     seed-services:latest"
    echo ""
    echo "📊 Доступные сервисы:"
    echo "   🐰 RabbitMQ:      localhost:5672"
    echo "   🌐 RabbitMQ UI:   http://localhost:15672 (seed/seed_password)"
    echo "   🔴 Redis:         localhost:6379"
    echo ""
    echo "💾 Для экспорта в tar:"
    echo "   docker save seed-services:latest > seed-services.tar"
else
    echo "❌ Ошибка сборки образа"
    exit 1
fi