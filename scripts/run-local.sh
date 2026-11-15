#!/usr/bin/env bash
# Local HVD: postgres + docker backend (5480/5481) + nginx frontend (5482).
# Does not touch prod. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${HVD_DATA_DIR:-$ROOT/data}"
ALERTS_HOST="${ALERTS_HOST:-/mnt/secondary/backups/dacha/dacha_alerts}"
mkdir -p "$DATA_DIR/postgres"

if [[ ! -d "$ALERTS_HOST" ]]; then
  echo "Alerts dir missing: $ALERTS_HOST"
  exit 1
fi

FRONT_CID=""

cleanup() {
  if [[ -n "${FRONT_CID}" ]]; then
    docker stop "${FRONT_CID}" >/dev/null 2>&1 || true
  fi
  docker compose -f "$ROOT/docker-compose.dev.yaml" down >/dev/null 2>&1 || true
}
trap cleanup EXIT INT TERM

if ! docker image inspect hvd:latest >/dev/null 2>&1; then
  echo "No hvd:latest image. Build once from LocInfra/infra/hvd or:"
  echo "  docker build -t hvd:latest -f backend/Dockerfile ."
  exit 1
fi

echo "Starting postgres + backend (alerts: ${ALERTS_HOST} → /alerts)..."
docker compose -f "$ROOT/docker-compose.dev.yaml" up -d --force-recreate

for _ in $(seq 1 90); do
  if curl -sf -o /dev/null -X POST "http://127.0.0.1:5480/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"username":"root","password":"root"}'; then
    break
  fi
  sleep 0.5
done

if ! curl -sf -o /dev/null -X POST "http://127.0.0.1:5480/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"root","password":"root"}'; then
  echo "Backend did not become ready."
  docker compose -f "$ROOT/docker-compose.dev.yaml" logs --tail 60 || true
  exit 1
fi

echo "Checking /alerts inside container..."
docker exec hvd-local ls /alerts >/dev/null
docker exec hvd-local sh -c 'test -d /alerts/J_HikAlertClip && test -d /alerts/J_HikAlertSnap'

echo "Starting frontend nginx on :5482 (proxy /api/ → :5480)..."
docker ps -q --filter ancestor=nginx:stable-alpine | while read -r cid; do
  docker stop "$cid" >/dev/null 2>&1 || true
done
FRONT_CID="$(docker run -d --rm --network host \
  -v "$ROOT/frontend:/usr/share/nginx/html:ro" \
  -v "$ROOT/frontend/nginx.dev.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:stable-alpine)"

echo
echo "Local HVD ready:"
echo "  UI:     http://127.0.0.1:5482/"
echo "  API:    http://127.0.0.1:5480/  (via UI as /api/...)"
echo "  Alerts: ${ALERTS_HOST} → /alerts (ALERTS_DIR)"
echo "  DB:     postgresql://hvd:hvd@127.0.0.1:5433/hvd  (data: ${DATA_DIR}/postgres)"
echo "  root / root"
echo
docker compose -f "$ROOT/docker-compose.dev.yaml" logs -f hvd
