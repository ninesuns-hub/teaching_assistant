#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 1 || "$1" != v* ]]; then
  echo "Usage: bash scripts/deploy-tag.sh <version-tag>" >&2
  exit 2
fi

VERSION="$1"
APP_DIR="${APP_DIR:-/opt/teaching-assistant/app}"
ENV_FILE="${ENV_FILE:-/etc/teaching-assistant/app.env}"
COMPOSE_FILE="$APP_DIR/compose.production.yml"

cd "$APP_DIR"
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to deploy from a dirty server worktree." >&2
  exit 1
fi

git fetch origin --tags --prune
git rev-parse --verify "refs/tags/$VERSION^{commit}" >/dev/null

APP_DIR="$APP_DIR" ENV_FILE="$ENV_FILE" bash scripts/backup.sh

git checkout --detach "$VERSION"
git submodule sync --recursive
git submodule update --init --recursive

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" config >/dev/null
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" run --rm migrate
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --remove-orphans

for _ in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1/api/health/ready >/dev/null; then
    echo "Deployment completed: $VERSION"
    exit 0
  fi
  sleep 2
done

echo "Deployment started, but readiness did not pass within 60 seconds." >&2
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps >&2
exit 1
