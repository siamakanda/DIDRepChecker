#!/bin/bash
# =============================================================================
# DID Intel — Linux uninstaller
#
# Usage:  sudo bash deploy/linux/uninstall.sh
#
# Removes: systemd service, nginx config, application files, cache, logs
# =============================================================================

set -euo pipefail

SERVICE_NAME="did-intel"
INSTALL_DIR="/opt/did-intel"
CACHE_DIR="/var/cache/did-intel"
LOG_DIR="/var/log/did-intel"

if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo bash deploy/linux/uninstall.sh"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════╗"
echo "║      DID Intel — Uninstaller          ║"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. Stop & disable systemd service
echo "[1/5] Stopping service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true
rm -f "/etc/systemd/system/$SERVICE_NAME.service"
systemctl daemon-reload
echo "  ✓ Service removed"

# 2. Remove nginx config
echo "[2/5] Removing nginx configuration..."
rm -f "/etc/nginx/sites-available/$SERVICE_NAME"
rm -f "/etc/nginx/sites-enabled/$SERVICE_NAME"
systemctl reload nginx 2>/dev/null || true
echo "  ✓ Nginx config removed"

# 3. Remove application directory
echo "[3/5] Removing application files..."
rm -rf "$INSTALL_DIR"
echo "  ✓ $INSTALL_DIR removed"

# 4. Remove cache & logs
echo "[4/5] Cleaning up cache and logs..."
rm -rf "$CACHE_DIR" "$LOG_DIR"
echo "  ✓ Cache and logs removed"

# 5. Optional: remove nginx if it was only installed for this
echo "[5/5] Done."

echo ""
echo "Uninstall complete."
echo ""
echo "  Note: python3, nginx, and git were NOT removed"
echo "  (they may be used by other applications)."
echo "  To remove them:  apt remove python3 nginx git"
echo ""