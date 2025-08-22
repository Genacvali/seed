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
    
    if [[ -d "images" ]]; then
        echo "📥 Loading images from tar archives..."
        
        # Load all tar files in images directory
        for tar_file in images/*.tar; do
            if [[ -f "$tar_file" ]]; then
                echo "Loading $(basename "$tar_file")..."
                docker load -i "$tar_file"
            fi
        done
        
        echo "✅ Images loaded successfully"
    else
        echo "⚠️ No images/ directory found. Available options:"
        echo "   1. Run ./export-images.sh on online machine"
        echo "   2. Copy images/*.tar files to this machine"  
        echo "   3. Create images/ directory and put tar files there"
        exit 1
    fi
fi

# Load environment variables from seed.env if it exists
if [[ -f "seed.env" ]]; then
    echo "📁 Loading environment variables from seed.env..."
    set -a
    source seed.env
    set +a
    echo "✅ Environment variables loaded"
else
    echo "⚠️ seed.env not found - copy seed.env.example and fill with real values"
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
echo "🎯 Starting SEED Agent..."

# Check if we have Python and dependencies
if python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml, requests, dotenv" 2>/dev/null; then
    echo "Using Python (recommended)..."
    python3 seed-agent.py > seed-agent.log 2>&1 &
    AGENT_PID=$!
elif [[ -f "dist/seed-agent" ]]; then
    echo "Using binary..."
    ./dist/seed-agent > seed-agent.log 2>&1 &
    AGENT_PID=$!
else
    echo "❌ No Python dependencies and no binary found"
    echo "   Install dependencies: pip3 install -r requirements.txt"
    echo "   Or build binary: ./build-agent.sh"
    exit 1
fi

echo $AGENT_PID > seed-agent.pid

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

# Get hostname
HOSTNAME=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "localhost")

echo ""
echo "🎉 SEED Agent v4 Started Successfully!"
echo "🌐 Web Interface:"
echo "   📊 Health Check:    http://$HOSTNAME:8080/health"
echo "   🚀 Live Dashboard:  http://$HOSTNAME:8080/dashboard"
echo "   📋 Config View:     http://$HOSTNAME:8080/config"
echo "   📈 Metrics:         http://$HOSTNAME:8080/metrics"
echo "   🧪 Test Alerts:     http://$HOSTNAME:8080/alerts/test"
echo "   🐰 RabbitMQ UI:     http://$HOSTNAME:15672 (user: $RABBITMQ_USER)"
echo ""
echo "⚡ Quick Commands:"
echo "   Reload Config:    curl -X POST http://$HOSTNAME:8080/config/reload"
echo "   Health Check:     curl http://$HOSTNAME:8080/health | jq ."
echo "   Live Dashboard:   curl http://$HOSTNAME:8080/dashboard | jq ."
echo "   Available Tests:  curl http://$HOSTNAME:8080/alerts/test | jq ."
echo ""
echo "🧪 Test Alert:"
echo "   curl -X POST http://$HOSTNAME:8080/alert -H 'Content-Type: application/json' -d '{\"alerts\":[{\"labels\":{\"alertname\":\"TestAlert\", \"instance\":\"$HOSTNAME\", \"severity\":\"warning\"}, \"annotations\":{\"summary\":\"Test alert from SEED Agent v4\"}, \"status\":\"firing\"}]}'"
echo ""
echo "📜 Logs: tail -f seed-agent.log"
echo "⏹️ Stop: ./stop.sh"