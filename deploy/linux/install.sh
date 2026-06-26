#!/bin/bash
# =============================================================================
# DID Intel — One-command Linux installer
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/deploy/linux/install.sh | sudo bash
#
# What it does:
#   1. Installs system deps (python3, venv, nginx, git, curl)
#   2. Clones repo to /opt/did-intel
#   3. Creates Python virtual environment + installs dependencies
#   4. Creates config.json from template (if missing)
#   5. Installs systemd service (auto-start on boot)
#   6. Configures nginx reverse proxy
#   7. Starts everything + runs health check
# =============================================================================

set -euo pipefail

# ------------------------------------------------------------------
# Configurable — change these if you fork the repo
# ------------------------------------------------------------------
REPO_URL="https://github.com/siamakanda/DIDRepChecker.git"
INSTALL_DIR="/opt/did-intel"
BRANCH="main"
SERVICE_NAME="did-intel"
VENV_DIR="$INSTALL_DIR/venv"

# ------------------------------------------------------------------
# Pretty output
# ------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
log()  { echo -e "${CYAN}[$(date +'%H:%M:%S')]${NC} $1"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()  { echo -e "  ${RED}✗${NC} $1"; }
header() { echo -e "\n${BOLD}${CYAN}━━━ $1 ━━━${NC}"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║       DID Intel — Linux Installer     ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ------------------------------------------------------------------
# 0. Pre-flight checks
# ------------------------------------------------------------------
if [ "$EUID" -ne 0 ]; then
    err "Please run as root:  curl ... | sudo bash"
    exit 1
fi

# ------------------------------------------------------------------
# 1. System dependencies
# ------------------------------------------------------------------
header "Step 1/8 — System packages"

apt update -qq
PACKAGES="python3 python3-pip python3-venv nginx git curl"
log "Installing: $PACKAGES"
apt install -y -qq $PACKAGES
ok "System packages ready"

# ------------------------------------------------------------------
# 2. Clone / update repository
# ------------------------------------------------------------------
header "Step 2/8 — Repository"

if [ -d "$INSTALL_DIR/.git" ]; then
    log "Repository exists — pulling latest from $BRANCH..."
    cd "$INSTALL_DIR"
    git pull origin "$BRANCH" 2>&1 | sed 's/^/  /'
    ok "Repository updated"
else
    if [ -d "$INSTALL_DIR" ]; then
        BACKUP="${INSTALL_DIR}.bak.$(date +%s)"
        warn "Directory exists without .git — moving to $BACKUP"
        mv "$INSTALL_DIR" "$BACKUP"
    fi
    log "Cloning $REPO_URL..."
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR" 2>&1 | sed 's/^/  /'
    cd "$INSTALL_DIR"
    ok "Repository cloned"
fi

# ------------------------------------------------------------------
# 3. Python virtual environment
# ------------------------------------------------------------------
header "Step 3/8 — Python environment"

if [ ! -f "$VENV_DIR/bin/python3" ]; then
    log "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

log "Installing Python packages..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$INSTALL_DIR/requirements.txt" -q 2>&1 | sed 's/^/  /'
deactivate
ok "Python dependencies installed ($($VENV_DIR/bin/python3 --version))"

# ------------------------------------------------------------------
# 4. Configuration
# ------------------------------------------------------------------
header "Step 4/8 — Configuration"

CONFIG_FILE="$INSTALL_DIR/config.json"
CONFIG_EXAMPLE="$INSTALL_DIR/config.example.json"

if [ ! -f "$CONFIG_FILE" ]; then
    if [ -f "$CONFIG_EXAMPLE" ]; then
        cp "$CONFIG_EXAMPLE" "$CONFIG_FILE"
        ok "Config created from config.example.json"
    else
        cat > "$CONFIG_FILE" <<'JSON'
{
    "cache_ttl_days": 3,
    "concurrent_requests": 30,
    "requests_per_second": 5,
    "max_retries": 2,
    "timeout": 15,
    "api_host": "127.0.0.1",
    "api_port": 8000,
    "api_reload": false
}
JSON
        ok "Default config created"
    fi
    echo -e "  ${YELLOW}→ Edit: $CONFIG_FILE${NC}"
else
    ok "Config already exists (not overwritten)"
fi

# ------------------------------------------------------------------
# 5. Directories for cache & logs
# ------------------------------------------------------------------
CACHE_DIR="/var/cache/did-intel"
LOG_DIR="/var/log/did-intel"
mkdir -p "$CACHE_DIR" "$LOG_DIR"
chown www-data:www-data "$CACHE_DIR" "$LOG_DIR" 2>/dev/null || true
ok "Cache/log directories: $CACHE_DIR, $LOG_DIR"

# ------------------------------------------------------------------
# 6. Systemd service
# ------------------------------------------------------------------
header "Step 5/8 — Systemd service"

cat > "/etc/systemd/system/$SERVICE_NAME.service" <<SYSTEMD
[Unit]
Description=DID Intel API Server
Documentation=https://github.com/siamakanda/DIDRepChecker
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$VENV_DIR/bin:/usr/bin"
Environment="DIDINTEL_API_HOST=127.0.0.1"
Environment="DIDINTEL_API_PORT=8000"
ExecStart=$VENV_DIR/bin/uvicorn did_intel.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
ok "Service unit installed: /etc/systemd/system/$SERVICE_NAME.service"

# ------------------------------------------------------------------
# 7. Nginx reverse proxy
# ------------------------------------------------------------------
header "Step 6/8 — Nginx reverse proxy"

cat > "/etc/nginx/sites-available/$SERVICE_NAME" <<'NGINX'
# DID Intel — Nginx reverse proxy
# Proxies :80 → uvicorn on 127.0.0.1:8000

# Rate limit definition (30 req/min per IP, burst of 10)
limit_req_zone $binary_remote_addr zone=didintel:10m rate=30r/m;

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    client_max_body_size 10M;

    # Apply rate limiting
    limit_req zone=didintel burst=10 nodelay;
    limit_req_status 429;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Long timeout for bulk scrape requests
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        proxy_set_header Host $host;
        access_log off;
    }

    # Block access to dot-files
    location ~ /\. {
        deny all;
        access_log off;
    }
}
NGINX

# Enable site, disable default
ln -sf "/etc/nginx/sites-available/$SERVICE_NAME" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx config
if nginx -t 2>&1; then
    ok "Nginx configuration valid"
else
    err "Nginx configuration test FAILED — check /etc/nginx/sites-available/$SERVICE_NAME"
fi

# ------------------------------------------------------------------
# 8. Permissions & Start
# ------------------------------------------------------------------
header "Step 7/8 — Permissions"

# Nginx needs read access to the app directory to serve through the socket/proxy
chown -R www-data:www-data "$INSTALL_DIR" 2>/dev/null || true
chmod 755 "$INSTALL_DIR" "$(dirname "$INSTALL_DIR")"
ok "Permissions set"

header "Step 8/8 — Starting services"

systemctl enable "$SERVICE_NAME" 2>&1 | sed 's/^/  /'
systemctl restart "$SERVICE_NAME" 2>&1 | sed 's/^/  /'
systemctl restart nginx 2>&1 | sed 's/^/  /'

sleep 2

# ------------------------------------------------------------------
# Final — Health check & summary
# ------------------------------------------------------------------
echo ""
echo -e "${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}║         Deployment Summary            ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# Service status
if systemctl is-active --quiet "$SERVICE_NAME"; then
    ok "did-intel service  ${GREEN}RUNNING${NC}"
else
    err "did-intel service  ${RED}FAILED${NC}  →  journalctl -u $SERVICE_NAME -n 30"
fi

if systemctl is-active --quiet nginx; then
    ok "nginx              ${GREEN}RUNNING${NC}"
else
    err "nginx              ${RED}FAILED${NC}  →  nginx -t"
fi

# Detect server IP
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$SERVER_IP" ] && SERVER_IP="YOUR_SERVER_IP"

echo ""
echo -e "  ${BOLD}Endpoints:${NC}"
echo -e "    API          ${CYAN}http://$SERVER_IP/scrape${NC}"
echo -e "    Docs         ${CYAN}http://$SERVER_IP/docs${NC}"
echo -e "    Health       ${CYAN}http://$SERVER_IP/health${NC}"
echo ""
echo -e "  ${BOLD}Management:${NC}"
echo -e "    Status       ${CYAN}systemctl status $SERVICE_NAME${NC}"
echo -e "    Logs         ${CYAN}journalctl -u $SERVICE_NAME -f${NC}"
echo -e "    Restart      ${CYAN}systemctl restart $SERVICE_NAME${NC}"
echo -e "    Config       ${CYAN}$CONFIG_FILE${NC}"
echo ""
echo -e "  ${GREEN}${BOLD}Installation complete.${NC}"
echo ""
echo -e "  ${YELLOW}Tip: Test it:  curl http://$SERVER_IP/health${NC}"
echo ""