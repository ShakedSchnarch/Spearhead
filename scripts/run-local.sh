#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUILD_UI=1
RELOAD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build-ui)
      BUILD_UI=0
      shift
      ;;
    --no-reload)
      RELOAD=0
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--no-build-ui] [--no-reload]"
      exit 1
      ;;
  esac
done

resolve_python_bin() {
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    echo "$ROOT/.venv/bin/python"
    return 0
  fi
  return 1
}

PYTHON_BIN="$(resolve_python_bin || true)"
if [[ -z "$PYTHON_BIN" ]]; then
  echo "Missing Python environment. Run: ./scripts/setup-venv.sh"
  exit 1
fi
VENV_BIN="$(dirname "$PYTHON_BIN")"

# Activate venv
if [[ -z "${VIRTUAL_ENV:-}" && -f "$VENV_BIN/activate" ]]; then
  # shellcheck disable=SC1091
  source "$VENV_BIN/activate"
fi

export PYTHONPATH="$ROOT/src"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export OPENBLAS_NUM_THREADS=1

# Local-first default: keep dashboard usable without OAuth/API token.
# Set LOCAL_DEV_ENFORCE_AUTH=true to test full auth locally.
if [[ "${LOCAL_DEV_ENFORCE_AUTH:-false}" != "true" ]]; then
  export SECURITY__API_TOKEN=
  export SECURITY__BASIC_USER=
  export SECURITY__BASIC_PASS=
  export SECURITY__REQUIRE_AUTH_ON_QUERIES=false
fi

needs_ui_build() {
  if [[ ! -f "$ROOT/frontend-app/dist/index.html" ]]; then
    return 0
  fi
  if find "$ROOT/frontend-app/src" "$ROOT/frontend-app/public" "$ROOT/frontend-app/index.html" \
    -type f -newer "$ROOT/frontend-app/dist/index.html" | grep -q .; then
    return 0
  fi
  return 1
}

if [[ "$BUILD_UI" -eq 1 ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required to build the frontend. Install Node.js LTS and retry."
    exit 1
  fi

  if [[ ! -d "$ROOT/frontend-app/node_modules" ]]; then
    echo "Installing frontend dependencies..."
    (cd "$ROOT/frontend-app" && npm ci)
  fi

  if needs_ui_build; then
    echo "Building frontend..."
    (cd "$ROOT/frontend-app" && npm run build)
  fi
fi

PORT="${PORT:-8000}"
echo "Serving Spearhead at http://127.0.0.1:${PORT}/spearhead/"
if [[ "$RELOAD" -eq 1 ]]; then
  exec "$PYTHON_BIN" -m uvicorn --app-dir src spearhead.api.main:app --reload --port "$PORT"
fi
exec "$PYTHON_BIN" -m uvicorn --app-dir src spearhead.api.main:app --port "$PORT"
