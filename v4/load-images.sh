#!/bin/bash
# =============================================================================
# SEED Agent v4 - Docker Images Load Script
# Loads Redis and RabbitMQ images from tar archives for offline deployment
# =============================================================================

set -e

echo "📥 Loading SEED Agent Docker Images"
echo "=================================="

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

# Check if images directory exists
if [ ! -d "images" ]; then
    echo "❌ Images directory not found. Run ./export-images.sh first."
    exit 1
fi

# Load Redis image
echo ""
echo "📦 Loading Redis image..."
if [ -f "images/redis-7.2-alpine.tar" ]; then
    echo "   Loading: images/redis-7.2-alpine.tar"
    docker load -i images/redis-7.2-alpine.tar
    echo "   ✅ Redis image loaded"
else
    echo "   ❌ Redis tar file not found: images/redis-7.2-alpine.tar"
    exit 1
fi

# Load RabbitMQ image
echo ""
echo "📦 Loading RabbitMQ image..."
if [ -f "images/rabbitmq-3.13-management.tar" ]; then
    echo "   Loading: images/rabbitmq-3.13-management.tar"
    docker load -i images/rabbitmq-3.13-management.tar
    echo "   ✅ RabbitMQ image loaded"
else
    echo "   ❌ RabbitMQ tar file not found: images/rabbitmq-3.13-management.tar"
    exit 1
fi

# Verify loaded images
echo ""
echo "🔍 Verifying loaded images..."
echo ""

if docker image inspect redis:7.2-alpine >/dev/null 2>&1; then
    echo "   ✅ redis:7.2-alpine - Available"
    docker image inspect redis:7.2-alpine --format "      Size: {{.Size}} bytes ({{.VirtualSize}} virtual)"
else
    echo "   ❌ redis:7.2-alpine - Not found"
fi

if docker image inspect rabbitmq:3.13-management >/dev/null 2>&1; then
    echo "   ✅ rabbitmq:3.13-management - Available"  
    docker image inspect rabbitmq:3.13-management --format "      Size: {{.Size}} bytes ({{.VirtualSize}} virtual)"
else
    echo "   ❌ rabbitmq:3.13-management - Not found"
fi

echo ""
echo "🎉 Image Loading Complete!"
echo ""
echo "🚀 Ready to start SEED Agent:"
echo "   ./start.sh"
echo ""
echo "📋 Available commands:"
echo "   docker images                    # List all images"
echo "   docker-compose up -d            # Start infrastructure"
echo "   docker system df                # Show disk usage"