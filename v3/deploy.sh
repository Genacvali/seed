#!/bin/bash
# =============================================================================
# SEED Agent - Deployment Script
# =============================================================================

set -e

echo "🚀 SEED Agent Deployment"
echo "======================="

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Функции
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker не найден. Установите Docker и попробуйте снова."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose не найден. Установите Docker Compose."
        exit 1
    fi
}

load_images() {
    echo "📦 Загрузка Docker образов..."
    
    # Ищем tar файлы с образами
    found_images=false
    for img in *.tar *.tar.gz; do
        if [ -f "$img" ]; then
            echo "   Загружаем $img..."
            docker load < "$img"
            found_images=true
        fi
    done
    
    if [ "$found_images" = false ]; then
        echo "❌ Не найдены tar файлы с образами!"
        echo "   Поместите файлы *.tar или *.tar.gz в текущую директорию"
        echo "   Необходимы образы: python:3.11-slim, redis:7.2-alpine, rabbitmq:3.12-management"
        exit 1
    fi
    
    # Проверяем наличие необходимых образов
    echo "🔍 Проверяем загруженные образы:"
    missing=false
    
    for img in "python:3.11-slim" "redis:7.2-alpine" "rabbitmq:3.12-management"; do
        if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$img"; then
            echo "   ✅ $img"
        else
            echo "   ❌ $img - НЕ НАЙДЕН"
            missing=true
        fi
    done
    
    if [ "$missing" = true ]; then
        echo ""
        echo "❌ Отсутствуют необходимые образы!"
        echo "   Загрузите недостающие образы через 'docker load < file.tar'"
        exit 1
    fi
    
    echo "✅ Все образы загружены"
}

build_seed() {
    echo "🔧 Сборка SEED Agent..."
    
    # Сборка без доступа к интернету
    DOCKER_BUILDKIT=0 docker-compose build --no-cache seed-agent
    
    if [ $? -eq 0 ]; then
        echo "✅ SEED Agent собран"
    else
        echo "❌ Ошибка сборки SEED Agent"
        echo ""
        echo "🔍 Возможные причины:"
        echo "   - Образ python:3.11-slim не загружен"
        echo "   - Нет доступа к pip репозиториям"
        echo ""
        echo "💡 Решение:"
        echo "   1. Убедитесь что python:3.11-slim загружен: docker images | grep python"
        echo "   2. Если нет pip доступа, используйте: ./deploy.sh offline-build"
        exit 1
    fi
}

start_services() {
    echo "🌱 Запуск сервисов..."
    docker-compose up -d
    
    echo "⏳ Ожидание готовности сервисов..."
    sleep 10
    
    # Проверка здоровья
    echo "🔍 Проверка состояния:"
    docker-compose ps
    
    echo ""
    echo "🎉 Развертывание завершено!"
    echo ""
    echo "📊 Доступные сервисы:"
    echo "   🌐 SEED Agent:        http://localhost:8080"
    echo "   🐰 RabbitMQ UI:       http://localhost:15672 (seed/seed123)"
    echo "   🔴 Redis:             localhost:6379"
}

offline_build() {
    echo "🔧 Offline сборка SEED Agent (без pip доступа)..."
    
    # Создаем временный Dockerfile без pip install
    cat > Dockerfile.offline << 'EOF'
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY . .
RUN useradd -r -s /bin/false seed && \
    mkdir -p logs && \
    chown -R seed:seed /app
USER seed
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
CMD ["python", "seed-agent.py", "--mode", "both", "--host", "0.0.0.0", "--port", "8080"]
EOF
    
    echo "⚠️  ВНИМАНИЕ: Python зависимости НЕ будут установлены!"
    echo "   Убедитесь что в образе python:3.11-slim уже есть нужные пакеты"
    echo "   Или установите их на хосте: pip install -r requirements.txt"
    
    DOCKER_BUILDKIT=0 docker build -f Dockerfile.offline -t seed-agent:offline .
    rm Dockerfile.offline
    
    echo "✅ Offline образ собран: seed-agent:offline"
}

# Выбор действия
case "${1:-deploy}" in
    "images")
        check_docker
        load_images
        ;;
    "build")
        check_docker
        build_seed
        ;;
    "offline-build")
        check_docker
        offline_build
        ;;
    "start")
        check_docker
        start_services
        ;;
    "deploy")
        check_docker
        load_images
        build_seed
        start_services
        ;;
    "stop")
        echo "🛑 Остановка сервисов..."
        docker-compose down
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        echo ""
        echo "🌐 SEED Agent Health:"
        curl -s http://localhost:8080/health | python3 -m json.tool 2>/dev/null || echo "Недоступен"
        ;;
    *)
        echo "Использование: $0 {deploy|images|build|offline-build|start|stop|logs|status}"
        echo ""
        echo "  deploy       - Полное развертывание (по умолчанию)"
        echo "  images       - Только загрузка образов из tar файлов"
        echo "  build        - Сборка SEED Agent с pip install"
        echo "  offline-build- Сборка SEED Agent БЕЗ pip install"
        echo "  start        - Только запуск сервисов"
        echo "  stop         - Остановка всех сервисов"
        echo "  logs         - Показать логи"
        echo "  status       - Показать статус"
        ;;
esac