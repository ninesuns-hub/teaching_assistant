#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/teaching-assistant/app}"
ENV_FILE="${ENV_FILE:-/etc/teaching-assistant/app.env}"
BACKUP_ROOT="${BACKUP_ROOT:-/srv/teaching-assistant/backups}"
STORAGE_ROOT="${STORAGE_HOST_PATH:-/srv/teaching-assistant/storage}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
COMPOSE_FILE="$APP_DIR/compose.production.yml"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_ROOT/$STAMP"

case "$BACKUP_ROOT" in
  /srv/teaching-assistant/backups|/srv/teaching-assistant/backups/*) ;;
  *)
    echo "Refusing to rotate an unexpected backup root: $BACKUP_ROOT" >&2
    exit 1
    ;;
esac

test -f "$ENV_FILE"
test -f "$COMPOSE_FILE"
test -d "$STORAGE_ROOT"
mkdir -p "$TARGET"
umask 077

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

backend_was_running=false
if compose ps --status running --services | grep -qx backend; then
  backend_was_running=true
  compose stop backend
fi

restore_backend() {
  if "$backend_was_running"; then
    compose start backend
  fi
}
trap restore_backend EXIT

compose exec -T mysql sh -c \
  'exec mysqldump --single-transaction --routines --triggers --default-character-set=utf8mb4 -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' \
  > "$TARGET/database.sql"

tar -C "$(dirname "$STORAGE_ROOT")" -czf "$TARGET/storage.tar.gz" \
  "$(basename "$STORAGE_ROOT")"

sha256sum "$TARGET/database.sql" "$TARGET/storage.tar.gz" \
  > "$TARGET/SHA256SUMS"

restore_backend
backend_was_running=false
trap - EXIT

find "$BACKUP_ROOT" \
  -mindepth 1 -maxdepth 1 -type d \
  -name '20?????????????Z' -mtime "+$RETENTION_DAYS" \
  -print -exec rm -rf -- {} +

echo "Backup completed: $TARGET"
