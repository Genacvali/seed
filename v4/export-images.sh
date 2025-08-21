#!/bin/bash
# SEED Agent v4 - Docker Images Export Script
set -euo pipefail

echo "📦 Exporting Docker images for offline deployment..."

# Check Docker
if ! command -v docker &>/dev/null; then
    echo "❌ Docker not found"
    exit 1
fi

mkdir -p images

# Images to export
IMAGES=(
    "redis:7.2-alpine"
    "rabbitmq:3.13-management"
)

# Export each image
for image in "${IMAGES[@]}"; do
    echo "Exporting $image..."
    
    # Pull if not exists
    docker image inspect "$image" &>/dev/null || docker pull "$image"
    
    # Export
    filename=$(echo "$image" | tr '/:' '_').tar
    docker save "$image" -o "images/$filename"
    
    echo "✅ $image -> images/$filename ($(du -h images/$filename | cut -f1))"
done

echo ""
echo "✅ Export complete!"
echo "📁 Files in images/:"
ls -lh images/*.tar

echo ""
echo "💾 Total: $(du -ch images/*.tar 2>/dev/null | tail -1 | cut -f1 || echo 'N/A')"
echo "🚚 Load with: ./load-images.sh"