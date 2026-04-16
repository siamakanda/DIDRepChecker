#!/bin/bash
# One‑command installer for DID Reputation API
# Usage: curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/bootstrap.sh | sudo bash

set -e

REPO_URL="https://github.com/siamakanda/DIDRepChecker.git"
REPO_DIR="/opt/did-reputation-api"
BRANCH="main"

# Ensure curl is available (though we are already using curl to fetch this script)
if ! command -v curl &> /dev/null; then
    apt update && apt install -y curl
fi

# Install git if missing
if ! command -v git &> /dev/null; then
    apt update && apt install -y git
fi

# Clone or update the repository
if [ -d "$REPO_DIR" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd "$REPO_DIR"
    git pull origin "$BRANCH"
else
    echo "Cloning repository into $REPO_DIR..."
    git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# Enter the server directory and run the deployment script
cd server
chmod +x deploy_lan.sh
./deploy_lan.sh