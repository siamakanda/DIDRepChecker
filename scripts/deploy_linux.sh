#!/bin/bash
# Production deployment for DID Reputation API (Local LAN)
# Designed to run from the scripts directory (but will work from anywhere)

set -e

# Find the project root (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$PROJECT_ROOT"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="did-api"
SOCKET_PATH="$APP_DIR/$SERVICE_NAME.sock"

log() {
    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# 1. System dependencies
log "Updating system packages..."
apt update && apt upgrade -y

log "Installing required packages..."
apt install -y python3 python3-pip python3-venv nginx curl

# 2. Python virtual environment
if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

log "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
    pip install -r "$PROJECT_ROOT/requirements.txt"
else
    log "⚠️ requirements.txt not found in $PROJECT_ROOT. Skipping."
fi
pip install gunicorn uvicorn
deactivate

# 3. Create systemd service (Gunicorn with Uvicorn workers)
log "Creating systemd service: /etc/systemd/system/$SERVICE_NAME.service"
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Gunicorn instance for FastAPI DID Reputation API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
Environment="PYTHONPATH=$APP_DIR"
ExecStart=$VENV_DIR/bin/gunicorn -k uvicorn.workers.UvicornWorker --workers 4 --bind unix:$SOCKET_PATH server.api_server:app

[Install]
WantedBy=multi-user.target
EOF

# 4. Configure Nginx reverse proxy
log "Configuring Nginx..."
SERVER_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
[ -z "$SERVER_IP" ] && SERVER_IP="localhost"
log "Server IP detected as: $SERVER_IP"

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

# Enable site and remove default
ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t

# 5. Fix permissions for socket directory
log "Setting directory permissions for Nginx access..."
chown -R www-data:www-data "$APP_DIR"
chmod 755 "$APP_DIR"
chmod 755 "$PROJECT_ROOT"

# 6. Start services
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME
systemctl restart nginx

# 7. Health check
sleep 3
if systemctl is-active --quiet $SERVICE_NAME; then
    log "✅ $SERVICE_NAME service is running."
else
    log "❌ $SERVICE_NAME service failed to start. Check logs: sudo journalctl -u $SERVICE_NAME"
fi

if systemctl is-active --quiet nginx; then
    log "✅ Nginx is running."
else
    log "❌ Nginx failed to start. Check configuration: sudo nginx -t"
fi

log "Deployment complete!"
log "API is accessible at http://$SERVER_IP/scrape"
log "Interactive API docs at http://$SERVER_IP/docs"