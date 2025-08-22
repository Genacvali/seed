#!/bin/bash
# SEED Agent v4 - Service Installation Script
set -euo pipefail

SERVICE_NAME="seed-agent"
SERVICE_USER="seed"
INSTALL_DIR="/opt/seed-agent"
SERVICE_FILE="/etc/systemd/system/seed-agent.service"

echo "🔧 Installing SEED Agent v4 as system service..."

# Check root privileges
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root"
   exit 1
fi

# Create service user
if ! id "$SERVICE_USER" &>/dev/null; then
    echo "👤 Creating service user: $SERVICE_USER"
    useradd -r -s /bin/false "$SERVICE_USER"
else
    echo "✅ Service user $SERVICE_USER already exists"
fi

# Create installation directory
echo "📁 Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Copy files
echo "📦 Copying SEED Agent files..."
cp -r * "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR"/*.sh

# Set ownership
echo "🔐 Setting permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"

# Create systemd service
echo "⚙️ Creating systemd service..."
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SEED Agent v4 - Monitoring and Alerting System
After=network.target docker.service
Requires=docker.service
StartLimitIntervalSec=0

[Service]
Type=forking
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment=RABBITMQ_DEFAULT_USER=admin
Environment=RABBITMQ_DEFAULT_PASS=admin
ExecStart=$INSTALL_DIR/start.sh
ExecStop=$INSTALL_DIR/stop.sh
Restart=always
RestartSec=10
KillMode=mixed
TimeoutStopSec=30

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=$INSTALL_DIR
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "🔄 Reloading systemd and enabling service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo ""
echo "✅ SEED Agent v4 installed as system service!"
echo ""
echo "📋 Service commands:"
echo "   sudo systemctl start $SERVICE_NAME     # Start service"
echo "   sudo systemctl stop $SERVICE_NAME      # Stop service"  
echo "   sudo systemctl restart $SERVICE_NAME   # Restart service"
echo "   sudo systemctl status $SERVICE_NAME    # Check status"
echo "   sudo systemctl logs -f $SERVICE_NAME   # View logs"
echo ""
echo "🏃 Starting service now..."
if systemctl start "$SERVICE_NAME"; then
    echo "✅ Service started successfully!"
    
    # Wait for startup
    sleep 10
    
    # Check status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "🎉 SEED Agent v4 is running!"
        echo "🌐 Access: http://localhost:8080/health"
    else
        echo "⚠️ Service may be starting up. Check status with:"
        echo "   sudo systemctl status $SERVICE_NAME"
    fi
else
    echo "❌ Failed to start service. Check logs with:"
    echo "   sudo journalctl -u $SERVICE_NAME -f"
fi

echo ""
echo "📁 Installation directory: $INSTALL_DIR"
echo "⚙️ Service file: $SERVICE_FILE"