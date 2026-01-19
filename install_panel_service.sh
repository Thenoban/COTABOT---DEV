#!/bin/bash

# Cotabot Web Panel Service Installation Script
# This script installs the web panel as a systemd service

set -e

echo "==============================================="
echo "Cotabot Web Panel Service Installation"
echo "==============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get the current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_FILE="$SCRIPT_DIR/cotabot-panel.service"

# Check if service file exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ Service file not found: $SERVICE_FILE"
    exit 1
fi

echo "📁 Service file: $SERVICE_FILE"
echo ""

# Update the WorkingDirectory and ExecStart paths in the service file
echo "🔧 Updating service file paths..."
CURRENT_USER=$(logname)
sed -i "s|User=.*|User=$CURRENT_USER|g" "$SERVICE_FILE"
sed -i "s|WorkingDirectory=.*|WorkingDirectory=$SCRIPT_DIR|g" "$SERVICE_FILE"
sed -i "s|ExecStart=.*|ExecStart=/usr/bin/python3 $SCRIPT_DIR/web_admin/api.py|g" "$SERVICE_FILE"

# Copy service file to systemd directory
echo "📋 Copying service file to /etc/systemd/system/..."
cp "$SERVICE_FILE" /etc/systemd/system/cotabot-panel.service

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "✅ Enabling service to start on boot..."
systemctl enable cotabot-panel.service

# Start the service
echo "🚀 Starting Cotabot Web Panel service..."
systemctl start cotabot-panel.service

# Wait a moment for service to start
sleep 2

# Check service status
echo ""
echo "==============================================="
echo "Service Status:"
echo "==============================================="
systemctl status cotabot-panel.service --no-pager

echo ""
echo "==============================================="
echo "✅ Installation Complete!"
echo "==============================================="
echo ""
echo "Service Management Commands:"
echo "  - Check status:  sudo systemctl status cotabot-panel"
echo "  - Start:         sudo systemctl start cotabot-panel"
echo "  - Stop:          sudo systemctl stop cotabot-panel"
echo "  - Restart:       sudo systemctl restart cotabot-panel"
echo "  - View logs:     sudo journalctl -u cotabot-panel -f"
echo ""
echo "Panel should be accessible at: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
