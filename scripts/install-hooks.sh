#!/usr/bin/env bash
# Install repo hooks into .git/hooks (no git config changes).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/.git/hooks"
install -m 755 "$ROOT/.githooks/pre-push" "$ROOT/.git/hooks/pre-push"
echo "Installed pre-push hook (updates purest submodule before push)."
