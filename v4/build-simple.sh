#!/bin/bash
# SEED Agent v4 - Simple Build (no PyInstaller issues)
set -euo pipefail

echo "🔧 Creating simple SEED Agent wrapper..."

# Create wrapper script
cat > seed-agent << 'EOF'
#!/bin/bash
# SEED Agent v4 - Python Wrapper
cd "$(dirname "$0")"

# Check dependencies
if ! python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml" 2>/dev/null; then
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
fi

# Run agent
exec python3 seed-agent.py "$@"
EOF

chmod +x seed-agent

echo "✅ Simple wrapper created: ./seed-agent"
echo ""
echo "🚀 Usage:"
echo "   ./seed-agent --config seed.yaml"
echo "   ./seed-agent --host 0.0.0.0 --port 8080"
echo ""
echo "📋 Install: sudo cp seed-agent /usr/local/bin/"