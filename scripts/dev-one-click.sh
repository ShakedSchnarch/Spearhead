#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  echo "Setting up Python environment..."
  "$ROOT/scripts/setup-venv.sh"
fi

PORT="${PORT:-8000}"
echo "Starting Spearhead on http://127.0.0.1:${PORT}/spearhead/"
exec "$ROOT/scripts/run-local.sh"
