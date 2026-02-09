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

if [[ ! -x "$ROOT/.venv/bin/uvicorn" ]]; then
  echo "Missing Python environment. Run: ./scripts/setup-venv.sh"
  exit 1
fi

# Activate venv
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export OPENBLAS_NUM_THREADS=1

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
  exec "$ROOT/.venv/bin/uvicorn" --app-dir src spearhead.api.main:app --reload --port "$PORT"
fi
exec "$ROOT/.venv/bin/uvicorn" --app-dir src spearhead.api.main:app --port "$PORT"
