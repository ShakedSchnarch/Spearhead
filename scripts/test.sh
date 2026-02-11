#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Prefer repo-local .venv, then currently activated virtualenv, then system python.
PYTHON_BIN="python3"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON_BIN="$ROOT/.venv/bin/python"
elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
  PYTHON_BIN="${VIRTUAL_ENV}/bin/python"
fi

export PYTHONPATH="$ROOT/src"
# Clear token to avoid auth in tests unless explicitly set by caller
export SECURITY__API_TOKEN=${SECURITY__API_TOKEN-}

INCLUDE_LEGACY=0
ARGS=()

for arg in "$@"; do
  if [[ "$arg" == "--include-legacy" ]]; then
    INCLUDE_LEGACY=1
    continue
  fi
  ARGS+=("$arg")
done

if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(tests)
fi

if [[ "$INCLUDE_LEGACY" -eq 0 ]]; then
  ARGS+=(--ignore=tests/legacy)
fi

exec "$PYTHON_BIN" -m pytest "${ARGS[@]}"
