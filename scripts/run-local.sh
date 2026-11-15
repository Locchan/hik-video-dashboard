#!/usr/bin/env bash
# Local HVD: poetry backend (5480/5481) + nginx frontend (5482) with /api/ strip.
# Does not touch prod. Ctrl+C stops both.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${HVD_DATA_DIR:-$ROOT/data}"
mkdir -p "$DATA_DIR"

FRONT_CID=""
BACKEND_PID=""

cleanup() {
  if [[ -n "${FRONT_CID}" ]]; then
    docker stop "${FRONT_CID}" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID}" ]] && kill -0 "${BACKEND_PID}" 2>/dev/null; then
    kill "${BACKEND_PID}" 2>/dev/null || true
    wait "${BACKEND_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Ensuring backend deps + sibling purest..."
cd "$ROOT/backend"
poetry install --no-interaction --no-ansi >/dev/null
# After poetry (path=submodule), force editable sibling purest for local edits.
"$ROOT/scripts/use-local-purest.sh"

export HVD_VERSION="${HVD_VERSION:-dev-local}"
export REST_PORT="${REST_PORT:-5480}"
export WS_PORT="${WS_PORT:-5481}"
export REST_WORKERS="${REST_WORKERS:-4}"
export DB_TYPE="${DB_TYPE:-sqlite}"
export DB_URL="${DB_URL:-$DATA_DIR/hvd.sqlite}"
export ROOT_PASSWORD="${ROOT_PASSWORD:-root}"
export DEBUG="${DEBUG:-1}"

echo "Starting backend on :${REST_PORT} (WS :${WS_PORT}, sqlite ${DB_URL})..."
poetry run hvd &
BACKEND_PID=$!

for _ in $(seq 1 40); do
  if curl -sf -o /dev/null -X POST "http://127.0.0.1:${REST_PORT}/auth/login" \
    -H 'Content-Type: application/json' \
    -d "{\"username\":\"root\",\"password\":\"${ROOT_PASSWORD}\"}"; then
    break
  fi
  if ! kill -0 "${BACKEND_PID}" 2>/dev/null; then
    echo "Backend exited early."
    exit 1
  fi
  sleep 0.25
done

echo "Starting frontend nginx on :5482 (proxy /api/ → :${REST_PORT})..."
FRONT_CID="$(docker run -d --rm --network host \
  -v "$ROOT/frontend:/usr/share/nginx/html:ro" \
  -v "$ROOT/frontend/nginx.dev.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:stable-alpine)"

echo
echo "Local HVD ready:"
echo "  UI:  http://127.0.0.1:5482/"
echo "  API: http://127.0.0.1:${REST_PORT}/  (via UI as /api/...)"
echo "  DB:  ${DB_URL}"
echo "  root / ${ROOT_PASSWORD}"
echo
wait "${BACKEND_PID}"
