#!/bin/bash
# Настройка для работы с предзагруженными Docker образами

echo "🐳 Настройка оффлайн Docker окружения..."

# Проверяем есть ли локальные образы
echo "📦 Проверяем доступные образы:"
docker images | grep -E "(redis|rabbitmq)"

# Если образов нет, показываем как их загрузить
if ! docker images | grep -q redis; then
    echo ""
    echo "❌ Образ Redis не найден"
    echo "💡 На машине с интернетом выполните:"
    echo "   docker pull redis:7-alpine"
    echo "   docker save redis:7-alpine | gzip > redis.tar.gz"
    echo "   # Скопируйте redis.tar.gz на этот сервер"
    echo "   docker load < redis.tar.gz"
    echo ""
fi

if ! docker images | grep -q rabbitmq; then
    echo "❌ Образ RabbitMQ не найден"
    echo "💡 На машине с интернетом выполните:"
    echo "   docker pull rabbitmq:3-management-alpine"
    echo "   docker save rabbitmq:3-management-alpine | gzip > rabbitmq.tar.gz"
    echo "   # Скопируйте rabbitmq.tar.gz на этот сервер"
    echo "   docker load < rabbitmq.tar.gz"
    echo ""
fi

# Создаем docker-compose для оффлайн режима
cat > docker-compose.offline.yml << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: seed_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - seed_network

  rabbitmq:
    image: rabbitmq:3-management-alpine
    container_name: seed_rabbitmq
    restart: unless-stopped
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: seed
      RABBITMQ_DEFAULT_PASS: seed_password
    volumes:
      - rabbitmq_data:/var/lib/rabbitmq
    networks:
      - seed_network

volumes:
  redis_data:
  rabbitmq_data:

networks:
  seed_network:
    driver: bridge
EOF

echo "✅ Создан docker-compose.offline.yml"
echo ""
echo "🚀 Запуск контейнеров:"
echo "   docker-compose -f docker-compose.offline.yml up -d"