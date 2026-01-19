#!/bin/bash

# Cotabot Web Panel Service Uninstallation Script
# This script removes the web panel systemd service

set -e

echo "==============================================="
echo "Cotabot Web Panel Service Uninstallation"
echo "==============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Stop the service
echo "🛑 Stopping Cotabot Web Panel service..."
systemctl stop cotabot-panel.service || true

# Disable the service
echo "❌ Disabling service..."
systemctl disable cotabot-panel.service || true

# Remove service file
echo "🗑️  Removing service file..."
rm -f /etc/systemd/system/cotabot-panel.service

# Reload systemd daemon
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Reset failed state
systemctl reset-failed || true

echo ""
echo "==============================================="
echo "✅ Uninstallation Complete!"
echo "==============================================="
echo ""
echo "The Cotabot Web Panel service has been removed."
echo ""
