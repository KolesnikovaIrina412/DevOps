#!/bin/bash

set -euo pipefail

DUMP_FILE="${DUMP:-}"
DB_NAME="${DB:-library}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; exit 1; }

if [[ -z "$DUMP_FILE" ]]; then
    error "DUMP is not set. Example: make restore DUMP=/var/backups/library/library_20261002.sql DB=library"
fi

if [[ ! -f "$DUMP_FILE" ]]; then
    error "File not found: $DUMP_FILE"
fi

log "WARNING: database '$DB_NAME' will be RECREATED."
read -p "Continue? (yes/no): " confirm

if [[ "$confirm" != "yes" ]]; then
    log "Cancelled."
    exit 0
fi

log "Dropping database '$DB_NAME'..."
sudo -u postgres dropdb --if-exists "$DB_NAME"

log "Creating database '$DB_NAME'..."
sudo -u postgres createdb "$DB_NAME"

log "Loading dump..."
sudo -u postgres psql -d "$DB_NAME" -f "$DUMP_FILE" > /dev/null

log "Restore completed."
sudo -u postgres psql -d "$DB_NAME" -c "\dt"