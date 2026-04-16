#!/bin/bash
# Production deployment for DID Reputation API (Local LAN)
# Designed to run from /opt/did-reputation-api/server

set -e

APP_DIR="$(pwd)"                     # e.g., /opt/did-reputation-api/server
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="did-api"
SOCKET_PATH="$APP_DIR/$SERVICE_NAME.sock"

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
log() {
    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# ----------------------------------------------------------------------
# 1. System dependencies
# ----------------------------------------------------------------------
log "Updating system packages..."
apt update && apt upgrade -y

log "Installing required packages..."
apt install -y python3 python3-pip python3-venv nginx curl

# ----------------------------------------------------------------------
# 2. Python virtual environment
# ----------------------------------------------------------------------
if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

log "Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "../requirements.txt" ]; then
    pip install -r "../requirements.txt"
else
    log "⚠️ requirements.txt not found in parent directory. Skipping."
fi
pip install gunicorn
deactivate

# ----------------------------------------------------------------------
# 3. Create systemd service
# ----------------------------------------------------------------------
log "Creating systemd service: /etc/systemd/system/$SERVICE_NAME.service"
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=Gunicorn instance for DID Reputation API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind unix:$SOCKET_PATH api_server:app

[Install]
WantedBy=multi-user.target
EOF

# ----------------------------------------------------------------------
# 4. Configure Nginx reverse proxy
# ----------------------------------------------------------------------
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

# Test Nginx configuration
nginx -t

# ----------------------------------------------------------------------
# 5. Fix permissions for socket directory (critical for Nginx)
# ----------------------------------------------------------------------
log "Setting directory permissions for Nginx access..."
# The socket will be created by Gunicorn under $APP_DIR.
# Ensure the directory is readable and executable by www-data.
chown -R www-data:www-data "$APP_DIR"
chmod 755 "$APP_DIR"
# The parent /opt/did-reputation-api also needs execute permission for others
chmod 755 /opt/did-reputation-api

# ----------------------------------------------------------------------
# 6. Start services
# ----------------------------------------------------------------------
log "Starting systemd service and Nginx..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME
systemctl restart nginx

# ----------------------------------------------------------------------
# 7. Health check
# ----------------------------------------------------------------------
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
log "From other devices on the same LAN, use the same IP."