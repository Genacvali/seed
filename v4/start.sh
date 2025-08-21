#!/bin/bash
# SEED Agent v4 - Simplified Startup Script
set -euo pipefail

echo "🚀 Starting SEED Agent v4..."

# RabbitMQ credentials
if [[ -z "${RABBITMQ_USER:-}" ]]; then
    read -p "RabbitMQ Username [admin]: " RABBITMQ_USER
    RABBITMQ_USER=${RABBITMQ_USER:-admin}
fi

if [[ -z "${RABBITMQ_PASS:-}" ]]; then
    read -s -p "RabbitMQ Password [admin]: " RABBITMQ_PASS
    echo ""
    RABBITMQ_PASS=${RABBITMQ_PASS:-admin}
fi

echo "✅ Using RabbitMQ credentials: $RABBITMQ_USER/*****"

# Check if Docker images are available
echo "🔍 Checking Docker images..."
if ! docker image inspect redis:7.2-alpine &>/dev/null || ! docker image inspect rabbitmq:3.13-management &>/dev/null; then
    echo "❌ Required Docker images not found"
    
    if [[ -d "images" ]] && [[ -f "images/redis_7.2-alpine.tar" ]] && [[ -f "images/rabbitmq_3.13-management.tar" ]]; then
        echo "📥 Loading images from tar archives..."
        ./load-images.sh
    else
        echo "⚠️ No offline images found. Available options:"
        echo "   1. Run ./export-images.sh on online machine"
        echo "   2. Copy images/*.tar files to this machine"
        echo "   3. Manually load: docker pull redis:7.2-alpine && docker pull rabbitmq:3.13-management"
        exit 1
    fi
fi

# Start infrastructure
echo "📦 Starting Docker services..."
export RABBITMQ_DEFAULT_USER="$RABBITMQ_USER"
export RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASS"

docker compose up -d 2>/dev/null || docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."

# Wait for Redis
echo -n "Redis: "
for i in {1..30}; do
    if docker exec seed-redis redis-cli ping &>/dev/null 2>&1; then
        echo "✅"
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "❌ Redis timeout"
        exit 1
    fi
    sleep 1
    echo -n "."
done

# Wait for RabbitMQ
echo -n "RabbitMQ: "
for i in {1..60}; do
    if docker exec seed-rabbitmq rabbitmq-diagnostics check_port_connectivity &>/dev/null 2>&1; then
        echo "✅"
        break
    fi
    if [[ $i -eq 60 ]]; then
        echo "❌ RabbitMQ timeout"
        exit 1
    fi
    sleep 2
    echo -n "."
done

echo "🎉 All services ready!"

# Start SEED Agent
if [[ -f "dist/seed-agent" ]]; then
    echo "🎯 Starting SEED Agent..."
    ./dist/seed-agent > seed-agent.log 2>&1 &
    AGENT_PID=$!
    echo $AGENT_PID > seed-agent.pid
else
    echo "🔨 Building and starting SEED Agent..."
    ./build-agent.sh
    ./dist/seed-agent > seed-agent.log 2>&1 &
    AGENT_PID=$!
    echo $AGENT_PID > seed-agent.pid
fi

# Wait for SEED Agent to start
echo -n "SEED Agent: "
for i in {1..30}; do
    if curl -s http://localhost:8080/health &>/dev/null; then
        echo "✅"
        break
    fi
    # Check if process is still running
    if ! kill -0 $AGENT_PID 2>/dev/null; then
        echo "❌ Process died. Check logs:"
        tail -10 seed-agent.log
        exit 1
    fi
    if [[ $i -eq 30 ]]; then
        echo "❌ Agent timeout. Check logs:"
        tail -10 seed-agent.log
        exit 1
    fi
    sleep 1
    echo -n "."
done

echo ""
echo "🎉 SEED Agent v4 Started Successfully!"
echo "🌐 URLs:"
echo "   Agent: http://localhost:8080/health"
echo "   RabbitMQ: http://localhost:15672 ($RABBITMQ_USER/$RABBITMQ_PASS)"
echo ""
echo "🧪 Test: curl -X POST http://localhost:8080/alert -H 'Content-Type: application/json' -d '{\"alertname\":\"Test\", \"instance\":\"localhost\"}'"
echo "📜 Logs: tail -f seed-agent.log"
echo "⏹️ Stop: ./stop.sh"