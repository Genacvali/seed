#!/bin/bash
# =============================================================================
# Создание базового образа Python с предустановленными зависимостями
# =============================================================================

echo "🐍 Создание базового образа Python с зависимостями SEED Agent..."

# Создаем временный Dockerfile для базового образа
cat > Dockerfile.base << 'EOF'
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Обновляем pip
RUN pip install --upgrade pip

# Устанавливаем Python зависимости
RUN pip install \
    fastapi==0.114.2 \
    uvicorn[standard]==0.30.6 \
    redis==5.3.1 \
    httpx==0.27.2 \
    pydantic==2.5.0 \
    pyyaml==6.0.2 \
    python-dateutil==2.8.2 \
    structlog==23.2.0 \
    requests==2.31.0 \
    aio_pika==9.4.3

# Проверяем что все установилось
RUN python -c "import fastapi, uvicorn, redis, httpx, yaml, aio_pika; print('✅ All packages installed')"

EOF

echo "🔧 Сборка базового образа..."
docker build -f Dockerfile.base -t python:3.11-seed-base .

if [ $? -eq 0 ]; then
    echo "✅ Базовый образ создан: python:3.11-seed-base"
    
    # Удаляем временный файл
    rm Dockerfile.base
    
    echo "🚀 Теперь можно собирать SEED Agent:"
    echo "   ./deploy.sh build-from-base"
else
    echo "❌ Ошибка создания базового образа"
    rm Dockerfile.base
    exit 1
fi