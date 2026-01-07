#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Activate venv if not already active
if [[ -z "${VIRTUAL_ENV:-}" && -x "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"
# Clear token to avoid auth in tests unless explicitly set by caller
export SECURITY__API_TOKEN=${SECURITY__API_TOKEN-}

exec "$ROOT/.venv/bin/pytest" "$@"
