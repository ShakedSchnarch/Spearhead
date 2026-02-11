#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/2] Setup Python environment"
"$ROOT/scripts/setup-venv.sh"

echo "[2/2] Setup frontend dependencies"
if [[ ! -d "$ROOT/frontend-app/node_modules" ]]; then
  (cd "$ROOT/frontend-app" && npm ci)
fi

cat <<MSG

Environment is ready.
Run tests with:
  ./scripts/test.sh

Run app with:
  ./scripts/dev-one-click.sh
MSG
