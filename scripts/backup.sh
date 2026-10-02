#!/bin/bash

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/library}"
RETENTION_DAYS=7

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
error() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2; exit 1; }

if ! command -v pg_dump &>/dev/null; then
    error "pg_dump not found. Install postgresql-client"
fi

mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

log "Backup database 'library'..."
sudo -u postgres pg_dump -d library -f "$BACKUP_DIR/library_${TIMESTAMP}.sql"
log "  -> $BACKUP_DIR/library_${TIMESTAMP}.sql"

log "Backup database 'users'..."
sudo -u postgres pg_dump -d users -f "$BACKUP_DIR/users_${TIMESTAMP}.sql"
log "  -> $BACKUP_DIR/users_${TIMESTAMP}.sql"

log "Removing backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql" -type f -mtime +$RETENTION_DAYS -delete

log "Backup completed successfully."
ls -lh "$BACKUP_DIR"/*_${TIMESTAMP}.sql