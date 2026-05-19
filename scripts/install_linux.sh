#!/bin/bash
# Production installer for DID Reputation Checker on Debian/Ubuntu
# Usage: curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/scripts/install_linux.sh | sudo bash
#   or: export DIDREP_INSTALL_DIR=/custom/path && curl ... | sudo bash

set -e
LOGFILE="/var/log/did-reputation-install.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "[$(date)] Starting installation"

# Trap errors to rollback
cleanup() {
    echo "[ERROR] Installation failed. Rolling back..."
    systemctl stop did-api 2>/dev/null || true
    systemctl disable did-api 2>/dev/null || true
    rm -f /etc/systemd/system/did-api.service
    rm -f /etc/nginx/sites-available/did-api
    rm -f /etc/nginx/sites-enabled/did-api
    systemctl reload nginx 2>/dev/null || true
    [ -d "$REPO_DIR" ] && rm -rf "$REPO_DIR"
    echo "Rollback complete. Check $LOGFILE for details."
    exit 1
}
trap cleanup ERR

REPO_URL="https://github.com/siamakanda/DIDRepChecker.git"
BRANCH="main"
SERVICE_NAME="did-api"
CACHE_DIR="/var/cache/DIDRepChecker"

# Allow custom installation directory via environment variable
if [ -n "$DIDREP_INSTALL_DIR" ]; then
    REPO_DIR="$DIDREP_INSTALL_DIR"
else
    REPO_DIR="/opt/DIDRepChecker"
fi

SOCKET_PATH="$REPO_DIR/$SERVICE_NAME.sock"
VENV_DIR="$REPO_DIR/venv"

echo "Installation directory: $REPO_DIR"
echo "Cache directory: $CACHE_DIR"

# Ensure Debian/Ubuntu
if ! command -v apt &> /dev/null; then
    echo "This script requires apt (Debian/Ubuntu). Exiting."
    exit 1
}

# System dependencies
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx curl git

# Clone or update repository
if [ -d "$REPO_DIR/.git" ]; then
    cd "$REPO_DIR"
    git fetch origin
    git reset --hard "origin/$BRANCH"
else
    rm -rf "$REPO_DIR" 2>/dev/null || true
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# Create default .env configuration file
cat > "$REPO_DIR/.env" <<EOF
# DID Reputation Checker Configuration
# Edit this file to change settings, then restart the service.

# Cache directory (must be writable by www-data)
REPUTATION_CACHE_DIR=$CACHE_DIR

# How many days to keep reputation data in cache (default: 3)
REPUTATION_CACHE_DAYS=3
EOF
chown www-data:www-data "$REPO_DIR/.env"

# Python virtual environment
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "$REPO_DIR/requirements.txt" ]; then
    pip install -r "$REPO_DIR/requirements.txt"
else
    pip install fastapi uvicorn aiohttp lxml aiosqlite python-dotenv
fi
pip install gunicorn uvicorn
deactivate

# Create cache directory owned by www-data
mkdir -p "$CACHE_DIR"
chown www-data:www-data "$CACHE_DIR"

# Create systemd service (no hardcoded cache days – uses .env)
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Gunicorn instance for FastAPI DID Reputation Checker
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$REPO_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONPATH=$REPO_DIR"
ExecStart=$VENV_DIR/bin/gunicorn -k uvicorn.workers.UvicornWorker --workers 4 --bind unix:$SOCKET_PATH server.api_server:app

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
SERVER_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
[ -z "$SERVER_IP" ] && SERVER_IP="localhost"

cat > /etc/nginx/sites-available/$SERVICE_NAME <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$SOCKET_PATH;
    }
}
EOF

# Enable site (backup default if exists)
if [ -f /etc/nginx/sites-enabled/default ]; then
    mv /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.backup
fi
ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/

nginx -t
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME
systemctl restart nginx

# Health check
sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Service $SERVICE_NAME is running."
else
    echo "❌ Service failed to start. Check journalctl -u $SERVICE_NAME"
    exit 1
fi

echo "Deployment complete!"
echo "API accessible at http://$SERVER_IP/scrape"
echo "Cache directory: $CACHE_DIR"
echo "Configuration file: $REPO_DIR/.env"
echo "Logs: $LOGFILE"