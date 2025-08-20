#!/bin/bash
# =============================================================================
# SEED Agent All-in-One Builder
# Сборка единого образа со всеми сервисами
# =============================================================================

echo "🏗️  Building SEED Agent All-in-One image..."

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден. Установите Docker и попробуйте снова."
    exit 1
fi

echo "📦 Сборка образа seed-allinone..."
docker build -f Dockerfile.allinone -t seed-allinone:latest .

if [ $? -eq 0 ]; then
    echo "✅ Образ успешно собран: seed-allinone:latest"
    echo ""
    echo "🚀 Для запуска:"
    echo "   docker-compose -f docker-compose.allinone.yml up -d"
    echo ""
    echo "📊 Доступные сервисы:"
    echo "   🌐 SEED Agent UI:     http://localhost:8080"
    echo "   🐰 RabbitMQ UI:       http://localhost:15672 (seed/seed123)"
    echo "   🔴 Redis:             localhost:6379"
    echo ""
    echo "📋 Управление:"
    echo "   docker-compose -f docker-compose.allinone.yml logs -f  # Логи"
    echo "   docker-compose -f docker-compose.allinone.yml stop     # Остановка"
    echo "   docker-compose -f docker-compose.allinone.yml down     # Удаление"
else
    echo "❌ Ошибка сборки образа"
    exit 1
fi