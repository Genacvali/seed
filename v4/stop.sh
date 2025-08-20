#!/bin/bash
# =============================================================================
# SEED Agent v4 - Stop Script  
# Stops SEED Agent and infrastructure services
# =============================================================================

echo "🛑 Stopping SEED Agent v4 Stack"
echo "==============================="

# Stop SEED Agent
if [ -f "seed-agent.pid" ]; then
    PID=$(cat seed-agent.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "🎯 Stopping SEED Agent (PID: $PID)..."
        kill $PID
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! kill -0 $PID 2>/dev/null; then
                echo "✅ SEED Agent stopped"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            echo "⚡ Force stopping SEED Agent..."
            kill -9 $PID
        fi
    else
        echo "❌ SEED Agent process not running"
    fi
    rm -f seed-agent.pid
else
    # Try to find and kill any running SEED Agent processes
    PIDS=$(pgrep -f "seed-agent" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        echo "🎯 Found running SEED Agent processes: $PIDS"
        for PID in $PIDS; do
            kill $PID 2>/dev/null || true
        done
        sleep 2
        # Force kill any remaining
        pkill -9 -f "seed-agent" 2>/dev/null || true
        echo "✅ SEED Agent processes stopped"
    else
        echo "ℹ️  No SEED Agent processes found"
    fi
fi

# Stop Docker services
echo ""
echo "📦 Stopping infrastructure services..."

# Use docker compose (new syntax) or docker-compose (old syntax)  
if docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

if [ -f "docker-compose.yml" ]; then
    $COMPOSE_CMD down
    echo "✅ Infrastructure services stopped"
else
    echo "⚠️  docker-compose.yml not found, stopping containers manually..."
    docker stop seed-rabbitmq seed-redis 2>/dev/null || true
    docker rm seed-rabbitmq seed-redis 2>/dev/null || true
fi

# Clean up log files (optional)
read -p "🗑️  Remove log files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f seed-agent.log
    echo "✅ Log files removed"
fi

echo ""
echo "✅ SEED Agent v4 Stack Stopped"
echo ""
echo "📊 Final Status:"

# Check if any processes are still running
if pgrep -f "seed-agent" >/dev/null; then
    echo "   ⚠️  SEED Agent: Still running (check manually)"
else
    echo "   ✅ SEED Agent: Stopped"
fi

if docker ps --format "table {{.Names}}" | grep -E "(seed-rabbitmq|seed-redis)" >/dev/null 2>&1; then
    echo "   ⚠️  Docker services: Some containers still running"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(seed-rabbitmq|seed-redis)"
else
    echo "   ✅ Docker services: Stopped"
fi

echo ""
echo "🔄 To start again: ./start.sh"