#!/usr/bin/env bash
# Prefer the sibling hik-web-dev/purest checkout for local poetry/tests.
# Keeps the git submodule directory intact (git forbids replacing it with a symlink).
# Installs the sibling tree editable into the backend venv so imports resolve there.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOCAL="$(cd "$ROOT/../purest" 2>/dev/null && pwd || true)"

if [[ -z "${LOCAL}" || ! -d "${LOCAL}/purest" ]]; then
  echo "Local purest checkout not found at ${ROOT}/../purest"
  echo "Expected layout: hik-web-dev/{purest,hik-video-dashboard}"
  exit 1
fi

# Ensure submodule path exists so poetry path deps / Docker still make sense.
if [[ ! -d "$ROOT/purest/purest" ]]; then
  git -C "$ROOT" submodule update --init purest
fi

cd "$ROOT/backend"
poetry install --no-root >/dev/null
poetry run pip install -e "${LOCAL}" >/dev/null
echo "Backend venv now uses local purest: ${LOCAL}"
poetry run python -c "import purest, inspect; print(purest.__file__)"
