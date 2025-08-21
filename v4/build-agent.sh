#!/bin/bash
# SEED Agent v4 Build Script - Simplified

set -euo pipefail

echo "🔨 Building SEED Agent v4 binary..."

# Verify dependencies
python3 -c "import fastapi, uvicorn, aio_pika, redis, pymongo, yaml" 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
}

# Clean previous builds
rm -rf dist/ build/ *.spec

# Install PyInstaller
pip3 install -q pyinstaller

# Create binary
pyinstaller \
    --onefile \
    --name=seed-agent \
    --add-data="seed.yaml:." \
    --add-data="core:core" \
    --add-data="fetchers:fetchers" \
    --add-data="plugins.py:." \
    --hidden-import=uvloop \
    --hidden-import=aio_pika \
    --hidden-import=aio_pika.abc \
    --hidden-import=aio_pika.connection \
    --hidden-import=aio_pika.robust_connection \
    --hidden-import=aiormq \
    --hidden-import=aiormq.connection \
    --collect-all=aio_pika \
    --collect-all=aiormq \
    --clean \
    --noconfirm \
    seed-agent.py

# Test binary
if [[ -f "dist/seed-agent" ]]; then
    chmod +x dist/seed-agent
    echo "✅ Binary created: $(ls -lh dist/seed-agent | awk '{print $5}') dist/seed-agent"
    
    echo ""
    echo "🚀 Usage: ./dist/seed-agent"
    echo "📋 Install: sudo cp dist/seed-agent /usr/local/bin/"
else
    echo "❌ Build failed"
    exit 1
fi