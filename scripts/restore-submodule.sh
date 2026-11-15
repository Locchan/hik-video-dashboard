#!/usr/bin/env bash
# Re-sync the purest git submodule and reinstall it into the backend venv
# (undoes use-local-purest.sh).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

git submodule sync --recursive
git submodule update --init --recursive purest

cd "$ROOT/backend"
poetry install
echo "Restored submodule at ${ROOT}/purest -> $(git -C "$ROOT/purest" rev-parse --short HEAD)"
poetry run python -c "import purest; print(purest.__file__)"
