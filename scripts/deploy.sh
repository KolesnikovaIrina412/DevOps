#!/bin/bash

set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/home/appuser/DevOps}"
VENV_DIR="$PROJECT_DIR/.venv"
SERVICE_NAME="library.service"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; exit 1; }

log "Deploying application to $PROJECT_DIR"

cd "$PROJECT_DIR" || error "Directory not found: $PROJECT_DIR"

if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        log "Creating .env from .env.example..."
        cp .env.example .env
        log "  WARNING: edit .env (SECRET_KEY, DATABASE_URL)"
    else
        error ".env and .env.example not found"
    fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating venv..."
    python3 -m venv "$VENV_DIR"
fi

log "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip > /dev/null
"$VENV_DIR/bin/pip" install -r requirements.txt > /dev/null

log "Checking application import..."
"$VENV_DIR/bin/python" -c "from app import app; print('OK')" || error "Import failed"

if systemctl list-unit-files | grep -q "$SERVICE_NAME"; then
    log "Restarting $SERVICE_NAME..."
    sudo systemctl restart "$SERVICE_NAME"
    sleep 2
    sudo systemctl status "$SERVICE_NAME" --no-pager | head -10
else
    log "WARNING: $SERVICE_NAME not found. Start manually:"
    log "   python app.py"
fi

log "Deployment completed."