#!/bin/bash
# SEED Agent - Docker Configuration Setup Script
# Configures Docker with new network settings and data directory

set -euo pipefail

echo "🐋 Setting up Docker configuration for SEED Agent..."

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   echo "Usage: sudo ./setup-docker-config.sh"
   exit 1
fi

# Create /data directory and subdirectories
echo "📁 Creating /data directory structure..."
mkdir -p /data/docker
mkdir -p /data/logs
chmod 755 /data
chmod 755 /data/docker
chmod 755 /data/logs

# Stop Docker service
echo "⏹️ Stopping Docker service..."
systemctl stop docker

# Backup existing Docker data if it exists
if [[ -d /var/lib/docker ]] && [[ ! -d /data/docker-backup ]]; then
    echo "💾 Backing up existing Docker data..."
    mv /var/lib/docker /data/docker-backup
    echo "✅ Docker data backed up to /data/docker-backup"
fi

# Copy daemon.json to Docker config directory
echo "📝 Installing Docker daemon configuration..."
mkdir -p /etc/docker
cp docker-daemon.json /etc/docker/daemon.json
chmod 644 /etc/docker/daemon.json

# Create systemd drop-in directory for Docker service
echo "⚙️ Creating systemd configuration..."
mkdir -p /etc/systemd/system/docker.service.d

# Create override configuration for Docker service
cat > /etc/systemd/system/docker.service.d/override.conf << 'EOF'
[Service]
# Set proxy environment variables for Docker daemon
Environment="HTTP_PROXY=http://proxy.sberdevices.ru:3128"
Environment="HTTPS_PROXY=http://proxy.sberdevices.ru:3128"
Environment="NO_PROXY=*.sberdevices.ru,vcd.sbercloud.ru,172.16.*,api.cloud.gcorelabs.com*,api.gcdn.co*,gitlab.sberdevices.ru:5050,localhost,127.0.0.1,172.31.*"

# Ensure Docker data directory is writable
ExecStartPre=/bin/mkdir -p /data/docker
ExecStartPre=/bin/chown root:root /data/docker
ExecStartPre=/bin/chmod 755 /data/docker
EOF

# Reload systemd and start Docker
echo "🔄 Reloading systemd configuration..."
systemctl daemon-reload

echo "🚀 Starting Docker service..."
systemctl start docker
systemctl enable docker

# Wait for Docker to be ready
echo "⏳ Waiting for Docker to be ready..."
sleep 5

# Verify Docker configuration
echo "✅ Verifying Docker configuration..."
docker version
echo ""
echo "📊 Docker system info:"
docker system info | grep -E "(Docker Root Dir|Network|Default Address Pools)"

echo ""
echo "🎉 Docker configuration completed successfully!"
echo ""
echo "📋 Summary of changes:"
echo "  • Docker data directory: /data/docker"
echo "  • Bridge network: 172.31.255.1/24"
echo "  • Address pools: 172.31.0.0/16 (size /24)"  
echo "  • Proxy: proxy.sberdevices.ru:3128"
echo "  • Logs directory: /data/logs"
echo ""
echo "⚠️  Network changes:"
echo "  Old: 172.17.0.0/16, 172.18.0.0/16"
echo "  New: 172.31.0.0/16 (no conflicts with 172.20.15.0/24)"
echo ""
echo "🔧 Next steps:"
echo "  1. cd v4/ && ./start.sh    # Start SEED Agent v4"
echo "  2. cd v5/ && ./start.sh    # Start SEED Agent v5"
echo "  3. ./smoke-test.sh         # Test the system"