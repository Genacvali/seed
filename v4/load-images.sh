#!/bin/bash
# SEED Agent v4 - Docker Images Load Script
set -euo pipefail

echo "📥 Loading Docker images from archives..."

# Check Docker
if ! command -v docker &>/dev/null; then
    echo "❌ Docker not found"
    exit 1
fi

# Check images directory
if [[ ! -d "images" ]]; then
    echo "❌ Images directory not found. Run ./export-images.sh first."
    exit 1
fi

# Load all tar files in images directory
loaded_count=0
for tar_file in images/*.tar; do
    if [[ -f "$tar_file" ]]; then
        echo "Loading $(basename "$tar_file")..."
        docker load -i "$tar_file"
        ((loaded_count++))
    fi
done

if [[ $loaded_count -eq 0 ]]; then
    echo "❌ No tar files found in images/ directory"
    exit 1
fi

echo ""
echo "✅ Loaded $loaded_count Docker images!"

# Show available images
echo ""
echo "📋 Available images:"
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" | grep -E "(redis|rabbitmq|REPOSITORY)"

echo ""
echo "🚀 Ready to start SEED Agent:"
echo "   ./start.sh"