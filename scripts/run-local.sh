#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/.venv/bin/activate" ]]; then
  echo "Missing .venv. Create it with: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

# Activate venv
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"

# Ensure frontend deps and build exist so API can serve /app
if [[ ! -d "$ROOT/frontend-app/node_modules" ]]; then
  (cd "$ROOT/frontend-app" && npm install)
fi
if [[ ! -d "$ROOT/frontend-app/dist" ]]; then
  (cd "$ROOT/frontend-app" && npm run build)
fi

PORT="${PORT:-8000}"
exec "$ROOT/.venv/bin/uvicorn" --app-dir src spearhead.api.main:app --reload --port "$PORT"
