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

exec "$ROOT/.venv/bin/pytest" "${ARGS[@]}"
