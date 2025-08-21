#!/bin/bash
# SEED Agent v4 - Simplified Startup Script
set -euo pipefail

echo "🚀 Starting SEED Agent v4..."

# Default credentials
RABBITMQ_USER=${RABBITMQ_USER:-admin}
RABBITMQ_PASS=${RABBITMQ_PASS:-admin}

# Start infrastructure
echo "📦 Starting Docker services..."
export RABBITMQ_DEFAULT_USER="$RABBITMQ_USER"
export RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASS"

docker compose up -d 2>/dev/null || docker-compose up -d

# Wait for services
echo "⏳ Waiting for services..."
sleep 10

# Start SEED Agent
if [[ -f "dist/seed-agent" ]]; then
    echo "🎯 Starting SEED Agent..."
    ./dist/seed-agent &
    AGENT_PID=$!
    echo $AGENT_PID > seed-agent.pid
else
    echo "🔨 Building and starting SEED Agent..."
    ./build-agent.sh
    ./dist/seed-agent &
    AGENT_PID=$!
    echo $AGENT_PID > seed-agent.pid
fi

# Wait for startup
sleep 5

echo ""
echo "✅ SEED Agent v4 Started!"
echo "🌐 URLs:"
echo "   Agent: http://localhost:8080"
echo "   RabbitMQ: http://localhost:15672 ($RABBITMQ_USER/$RABBITMQ_PASS)"
echo ""
echo "🧪 Test: curl -X POST http://localhost:8080/alert -H 'Content-Type: application/json' -d '{\"alertname\":\"Test\", \"instance\":\"localhost\"}'"
echo "⏹️ Stop: ./stop.sh"