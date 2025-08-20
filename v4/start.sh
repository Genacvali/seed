#!/bin/bash
# =============================================================================
# SEED Agent v4 - Complete Startup Script
# Starts all services and SEED Agent with one command
# =============================================================================

set -e

echo "🚀 Starting SEED Agent v4 Complete Stack"
echo "=========================================="

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo "📄 Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
    echo "✅ Environment variables loaded"
fi

# RabbitMQ credentials configuration
echo ""
echo "🔐 RabbitMQ Configuration"
echo "You can provide credentials via environment variables or interactive input:"
echo "   Environment variables: RABBITMQ_USER, RABBITMQ_PASS"
echo ""

# Get RabbitMQ credentials
if [ -z "$RABBITMQ_USER" ]; then
    read -p "RabbitMQ Username [admin]: " RABBITMQ_USER
    RABBITMQ_USER=${RABBITMQ_USER:-admin}
fi

if [ -z "$RABBITMQ_PASS" ]; then
    read -s -p "RabbitMQ Password [admin]: " RABBITMQ_PASS
    echo ""
    RABBITMQ_PASS=${RABBITMQ_PASS:-admin}
fi

echo "✅ Using RabbitMQ credentials: $RABBITMQ_USER/*****"

# Check if we're in the right directory
if [ ! -f "seed.yaml" ] || [ ! -f "docker-compose.yml" ]; then
    echo "❌ Please run this script from the v4 directory"
    echo "   cd v4/ && ./start.sh"
    exit 1
fi

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Start infrastructure services
echo ""
echo "📦 Starting infrastructure services..."
echo "   - Redis (port 6379)"
echo "   - RabbitMQ (ports 5672, 15672)"
echo "   - RabbitMQ User: $RABBITMQ_USER"

# Use docker compose (new syntax) or docker-compose (old syntax)
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Export credentials for docker-compose
export RABBITMQ_DEFAULT_USER="$RABBITMQ_USER"
export RABBITMQ_DEFAULT_PASS="$RABBITMQ_PASS"

$COMPOSE_CMD up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."

# Wait for Redis
echo -n "   Redis: "
for i in {1..30}; do
    if docker exec seed-redis redis-cli ping &>/dev/null; then
        echo "✅ Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Timeout"
        exit 1
    fi
    sleep 1
done

# Wait for RabbitMQ
echo -n "   RabbitMQ: "
for i in {1..60}; do
    if docker exec seed-rabbitmq rabbitmq-diagnostics -q ping &>/dev/null; then
        echo "✅ Ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Timeout"
        exit 1
    fi
    sleep 1
done

# Wait for RabbitMQ management to be fully ready
echo -n "   RabbitMQ Management: "
for i in {1..30}; do
    if docker exec seed-rabbitmq rabbitmqctl list_users &>/dev/null; then
        echo "✅ Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Timeout"
        exit 1
    fi
    sleep 2
done

# Setup RabbitMQ user if needed
echo ""
echo "🔐 Configuring RabbitMQ user..."

# Check if user already exists
if docker exec seed-rabbitmq rabbitmqctl list_users | grep -q "^$RABBITMQ_USER"; then
    echo "✅ RabbitMQ user $RABBITMQ_USER already exists"
else
    echo "📝 Creating RabbitMQ user $RABBITMQ_USER..."
    
    # Create user
    if docker exec seed-rabbitmq rabbitmqctl add_user "$RABBITMQ_USER" "$RABBITMQ_PASS"; then
        echo "   ✅ User created"
    else
        echo "   ❌ Failed to create user"
        exit 1
    fi
    
    # Set administrator tag
    if docker exec seed-rabbitmq rabbitmqctl set_user_tags "$RABBITMQ_USER" administrator; then
        echo "   ✅ Administrator privileges granted"
    else
        echo "   ❌ Failed to set administrator privileges"
        exit 1
    fi
    
    # Set permissions
    if docker exec seed-rabbitmq rabbitmqctl set_permissions -p / "$RABBITMQ_USER" ".*" ".*" ".*"; then
        echo "   ✅ Permissions configured"
    else
        echo "   ❌ Failed to set permissions"
        exit 1
    fi
    
    echo "✅ RabbitMQ user $RABBITMQ_USER configured successfully"
fi

# Check if SEED Agent binary exists
if [ ! -f "dist/seed-agent" ]; then
    echo ""
    echo "🔨 Building SEED Agent binary..."
    if [ -f "build-agent.sh" ]; then
        ./build-agent.sh
    else
        echo "❌ build-agent.sh not found. Please build manually."
        exit 1
    fi
fi

# Check if port 8080 is available
if check_port 8080; then
    echo ""
    echo "⚠️  Port 8080 is already in use. Trying to stop existing SEED Agent..."
    pkill -f "seed-agent" 2>/dev/null || true
    sleep 2
    
    if check_port 8080; then
        echo "❌ Port 8080 is still in use. Please stop the service manually."
        exit 1
    fi
fi

# Start SEED Agent
echo ""
echo "🎯 Starting SEED Agent..."
echo "   Config: seed.yaml"
echo "   URL: http://localhost:8080"
echo "   RabbitMQ Management: http://localhost:15672 ($RABBITMQ_USER/*****)"

# Update seed.yaml with current RabbitMQ credentials
echo "📝 Updating SEED Agent configuration..."
if command -v sed &> /dev/null; then
    # Use sed if available (Linux/macOS)
    sed -i.bak "s/username: \".*\"/username: \"$RABBITMQ_USER\"/" seed.yaml
    sed -i.bak "s/password: \".*\"/password: \"$RABBITMQ_PASS\"/" seed.yaml
    rm -f seed.yaml.bak
else
    # Fallback method using temporary file
    awk -v user="$RABBITMQ_USER" -v pass="$RABBITMQ_PASS" '
        /username:/ { print "    username: \"" user "\""; next }
        /password:/ { print "    password: \"" pass "\""; next }
        { print }
    ' seed.yaml > seed.yaml.tmp && mv seed.yaml.tmp seed.yaml
fi

# Start in background with logging
./dist/seed-agent --config seed.yaml > seed-agent.log 2>&1 &
SEED_PID=$!

# Wait for SEED Agent to start
echo ""
echo "⏳ Waiting for SEED Agent to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8080/health &>/dev/null; then
        echo "✅ SEED Agent is ready!"
        break
    fi
    
    # Check if process is still running
    if ! kill -0 $SEED_PID 2>/dev/null; then
        echo "❌ SEED Agent failed to start. Check logs:"
        tail -20 seed-agent.log
        exit 1
    fi
    
    if [ $i -eq 30 ]; then
        echo "❌ SEED Agent startup timeout. Check logs:"
        tail -20 seed-agent.log
        exit 1
    fi
    
    sleep 1
    echo -n "."
done

# Show status
echo ""
echo "🎉 SEED Agent v4 Stack Started Successfully!"
echo ""
echo "📊 Service Status:"
echo "   ✅ Redis:      localhost:6379"
echo "   ✅ RabbitMQ:   localhost:5672"
echo "   ✅ SEED Agent: http://localhost:8080"
echo ""
echo "🔗 Web Interfaces:"
echo "   📈 SEED Health:  http://localhost:8080/health"
echo "   📊 SEED Config:  http://localhost:8080/config" 
echo "   📋 SEED Metrics: http://localhost:8080/metrics"
echo "   🐰 RabbitMQ UI:  http://localhost:15672 ($RABBITMQ_USER/*****)"
echo ""
echo "🧪 Testing:"
echo "   Run test alerts: python3 test_alerts.py"
echo "   Send custom alert: curl -X POST http://localhost:8080/alert -H 'Content-Type: application/json' -d '{\"alertname\":\"TestAlert\", \"instance\":\"localhost\"}'"
echo ""
echo "📜 Logs:"
echo "   SEED Agent: tail -f seed-agent.log"
echo "   RabbitMQ:   docker logs seed-rabbitmq"
echo "   Redis:      docker logs seed-redis"
echo ""
echo "⏹️  To stop everything: ./stop.sh"

# Save PID for stop script
echo $SEED_PID > seed-agent.pid

echo ""
echo "✨ Ready to receive alerts! SEED Agent is running in background."
echo "   Process ID: $SEED_PID"