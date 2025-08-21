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