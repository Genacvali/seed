#!/bin/bash
# Script to run SberDevices Alertmanager integration with SEED Agent

set -e

echo "🚀 Starting SberDevices Alertmanager Integration"
echo "==============================================="

# Load configuration
if [ -f "sberdevices-integration.env" ]; then
    source sberdevices-integration.env
    echo "✅ Loaded configuration from sberdevices-integration.env"
else
    echo "⚠️  No sberdevices-integration.env found, using defaults"
fi

# Check if SEED Agent is running
SEED_URL=${SEED_AGENT_URL:-http://localhost:8080}
echo "🔍 Checking SEED Agent at $SEED_URL"

if curl -s "$SEED_URL/health" >/dev/null 2>&1; then
    echo "✅ SEED Agent is running"
else
    echo "❌ SEED Agent is not running at $SEED_URL"
    echo "   Please start SEED Agent first:"
    echo "   cd v5/ && ./start.sh   # for v5"
    echo "   cd v6/ && ./start.sh   # for v6"
    exit 1
fi

# Check Python dependencies
echo "🔍 Checking Python dependencies"
python3 -c "import requests, json, time" 2>/dev/null && echo "✅ Dependencies OK" || {
    echo "❌ Missing dependencies, installing..."
    pip3 install requests
}

# Run integration
echo "🔄 Starting integration..."
echo "   Alertmanager: ${SBER_ALERTMANAGER_URL:-https://alertmanager.sberdevices.ru}"
echo "   SEED Agent: $SEED_URL"
echo "   Sync interval: ${SYNC_INTERVAL:-60}s"
echo ""
echo "Press Ctrl+C to stop"
echo "─────────────────────────────────────────────────"

# Run the integration script
python3 alertmanager-integration.py