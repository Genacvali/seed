#!/bin/bash
# =============================================================================
# SEED Agent v4 - Docker Images Export Script
# Exports Redis and RabbitMQ images to tar archives for offline deployment
# =============================================================================

set -e

echo "🚀 Exporting SEED Agent Docker Images"
echo "====================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Create images directory if it doesn't exist
mkdir -p images

# Export Redis image
echo ""
echo "📦 Exporting Redis image..."
echo "   Image: redis:7.2-alpine"
echo "   Output: images/redis-7.2-alpine.tar"

if docker image inspect redis:7.2-alpine >/dev/null 2>&1; then
    docker save redis:7.2-alpine -o images/redis-7.2-alpine.tar
    echo "   ✅ Redis image exported ($(du -h images/redis-7.2-alpine.tar | cut -f1))"
else
    echo "   ⚠️  Redis image not found locally. Pulling..."
    docker pull redis:7.2-alpine
    docker save redis:7.2-alpine -o images/redis-7.2-alpine.tar
    echo "   ✅ Redis image pulled and exported ($(du -h images/redis-7.2-alpine.tar | cut -f1))"
fi

# Export RabbitMQ image
echo ""
echo "📦 Exporting RabbitMQ image..."
echo "   Image: rabbitmq:3.13-management"
echo "   Output: images/rabbitmq-3.13-management.tar"

if docker image inspect rabbitmq:3.13-management >/dev/null 2>&1; then
    docker save rabbitmq:3.13-management -o images/rabbitmq-3.13-management.tar
    echo "   ✅ RabbitMQ image exported ($(du -h images/rabbitmq-3.13-management.tar | cut -f1))"
else
    echo "   ⚠️  RabbitMQ image not found locally. Pulling..."
    docker pull rabbitmq:3.13-management
    docker save rabbitmq:3.13-management -o images/rabbitmq-3.13-management.tar
    echo "   ✅ RabbitMQ image pulled and exported ($(du -h images/rabbitmq-3.13-management.tar | cut -f1))"
fi

# Show results
echo ""
echo "🎉 Image Export Complete!"
echo ""
echo "📁 Exported Files:"
ls -lah images/*.tar | while read -r line; do
    echo "   $line"
done

echo ""
echo "📋 Summary:"
echo "   Redis:    images/redis-7.2-alpine.tar"
echo "   RabbitMQ: images/rabbitmq-3.13-management.tar"
echo ""
echo "💾 Total Size: $(du -ch images/*.tar | tail -1 | cut -f1)"
echo ""
echo "🚚 To load these images on another system:"
echo "   ./load-images.sh"