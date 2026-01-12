#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Activate venv if not already active
if [[ -z "${VIRTUAL_ENV:-}" && -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"
exec "$ROOT/.venv/bin/uvicorn" --app-dir src spearhead.api.main:app --reload --port 8000
