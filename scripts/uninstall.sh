#!/bin/bash
# Uninstall the DID Reputation API service and remove files

set -e

SERVICE_NAME="did-api"
APP_DIR="/opt/did-reputation-api"

# Stop and disable service
systemctl stop $SERVICE_NAME 2>/dev/null || true
systemctl disable $SERVICE_NAME 2>/dev/null || true

# Remove systemd service file
rm -f /etc/systemd/system/$SERVICE_NAME.service
systemctl daemon-reload

# Remove Nginx site configuration
rm -f /etc/nginx/sites-available/$SERVICE_NAME
rm -f /etc/nginx/sites-enabled/$SERVICE_NAME
systemctl reload nginx

# Remove application directory
rm -rf "$APP_DIR"

echo "Uninstall complete."