#!/bin/bash
# Production Deployment Script for DID Reputation API (Local LAN)
# Run as: sudo bash deploy.sh

set -e

# --- Configuration (EDIT THESE) ---
REPO_URL="https://github.com/siamakanda/DIDRepChecker.git"
REPO_BRANCH="main"                # change if your default branch is 'master'
APP_DIR="/opt/did-reputation-api"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="did-api"
# No domain, no SSL – we'll use the server's IP

# --- Helper Functions ---
log() {
    echo -e "\n[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# --- 1. System Dependencies ---
log "Updating system packages..."
sudo apt update && sudo apt upgrade -y

log "Installing required system packages..."
sudo apt install -y python3 python3-pip python3-venv git nginx curl

# --- 2. Clone / Update Application ---
if [ -d "$APP_DIR" ]; then
    log "Application directory exists. Pulling latest changes..."
    cd "$APP_DIR"
    sudo git pull origin "$REPO_BRANCH"
else
    log "Cloning repository into $APP_DIR..."
    sudo git clone --branch "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
fi

# Ensure correct ownership (optional, but clean)
sudo chown -R $USER:$USER "$APP_DIR"

# --- 3. Python Virtual Environment & Dependencies ---
if [ ! -d "$VENV_DIR" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

log "Activating virtual environment and installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip

if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt"
else
    log "⚠️ requirements.txt not found. Skipping."
fi

# Install Gunicorn (production WSGI server)
pip install gunicorn

deactivate

# --- 4. Create systemd Service for Gunicorn ---
log "Creating systemd service file: /etc/systemd/system/$SERVICE_NAME.service"
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Gunicorn instance for DID Reputation API
After=network.target

[Service]
User=$USER
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/gunicorn --workers 4 --bind unix:$APP_DIR/$SERVICE_NAME.sock api_server:app

[Install]
WantedBy=multi-user.target
EOF

# --- 5. Configure Nginx Reverse Proxy (LAN, no SSL) ---
log "Configuring Nginx..."

# Get the server's local IP (first non-loopback)
SERVER_IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -1)
if [ -z "$SERVER_IP" ]; then
    SERVER_IP="localhost"
fi

log "Server IP will be: $SERVER_IP"

sudo tee /etc/nginx/sites-available/$SERVICE_NAME > /dev/null <<EOF
server {
    listen 80;
    listen [::]:80;
    server_name $SERVER_IP _;

    location / {
        include proxy_params;
        proxy_pass http://unix:$APP_DIR/$SERVICE_NAME.sock;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/$SERVICE_NAME /etc/nginx/sites-enabled/
# Optional: remove default site to avoid conflict
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# --- 6. Start Services ---
log "Reloading systemd, starting Gunicorn and Nginx..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME
sudo systemctl restart nginx

# --- 7. Health Check ---
log "Waiting 3 seconds for services to start..."
sleep 3

if systemctl is-active --quiet $SERVICE_NAME; then
    log "✅ $SERVICE_NAME service is running."
else
    log "❌ $SERVICE_NAME service failed to start. Check logs with: sudo journalctl -u $SERVICE_NAME"
fi

if systemctl is-active --quiet nginx; then
    log "✅ Nginx is running."
else
    log "❌ Nginx failed to start. Check configuration with: sudo nginx -t"
fi

log "Deployment complete!"
log "API is accessible at http://$SERVER_IP/scrape"
log "From other devices on the same LAN, use the same IP."