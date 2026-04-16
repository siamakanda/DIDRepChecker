#!/bin/bash
# Minimal bootstrap script to clone and run the full deployment
# Usage: curl -sL https://raw.githubusercontent.com/siamakanda/DIDRepChecker/main/bootstrap.sh | sudo bash

set -e

REPO_URL="https://github.com/siamakanda/DIDRepChecker.git"
REPO_DIR="DIDRepChecker"
BRANCH="main"  # change if your default branch is 'master'

# Install git if not present
if ! command -v git &> /dev/null; then
    echo "Git not found. Installing..."
    sudo apt update && sudo apt install -y git
fi

# Clone or update the repository
if [ -d "$REPO_DIR" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd "$REPO_DIR"
    sudo git pull origin "$BRANCH"
else
    echo "Cloning repository..."
    sudo git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# Enter the server directory (where the actual Flask app lives)
cd server

# Make the deployment script executable and run it
chmod +x deploy_lan.sh
sudo ./deploy_lan.sh