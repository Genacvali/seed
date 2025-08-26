#!/bin/bash
# Fix Docker temporary directory issue after migration

set -euo pipefail

echo "🔧 Fixing Docker temporary directory issue..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   echo "Usage: sudo ./fix-docker-tmp.sh"
   exit 1
fi

# Create all necessary Docker directories
echo "📁 Creating Docker directories..."
mkdir -p /data/docker
mkdir -p /data/docker/tmp
mkdir -p /data/docker/containers
mkdir -p /data/docker/image
mkdir -p /data/docker/volumes
mkdir -p /data/docker/network
mkdir -p /data/logs
mkdir -p /data/redis
mkdir -p /data/rabbitmq

# Set proper ownership and permissions
chown -R root:root /data/docker
chmod -R 755 /data/docker
chmod 755 /data/logs /data/redis /data/rabbitmq

# Stop Docker if running
echo "⏹️ Stopping Docker..."
systemctl stop docker || true

# Start Docker
echo "🚀 Starting Docker..."
systemctl start docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker daemon..."
sleep 10

# Verify Docker is working
echo "✅ Testing Docker..."
if docker version &>/dev/null; then
    echo "✅ Docker is working correctly"
else
    echo "❌ Docker failed to start properly"
    echo "Check logs: journalctl -u docker -f"
    exit 1
fi

# Show Docker info
echo "📊 Docker system info:"
docker system info | grep -E "(Docker Root Dir|Storage Driver)"

echo ""
echo "🎉 Docker temporary directory issue fixed!"
echo ""
echo "💡 Now you can load Docker images:"
echo "  docker load -i images/redis_7.2-alpine.tar"
echo "  docker load -i images/rabbitmq_3.13-management.tar"
echo ""
echo "🚀 Or run SEED Agent:"
echo "  cd v5/ && ./start.sh"