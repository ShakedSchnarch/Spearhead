#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
RECREATE="${RECREATE:-false}"

if [[ "$RECREATE" == "true" && -d "$ROOT/.venv" ]]; then
  BACKUP_DIR="$ROOT/.venv.backup.$(date +%Y%m%d%H%M%S)"
  mv "$ROOT/.venv" "$BACKUP_DIR"
  echo "Moved existing .venv to: $BACKUP_DIR"
fi

if [[ ! -x "$ROOT/.venv/bin/python" ]]; then
  "$PYTHON_BIN" -m venv "$ROOT/.venv"
  echo "Created virtualenv: $ROOT/.venv"
fi

"$ROOT/.venv/bin/python" -m pip install --upgrade pip
"$ROOT/.venv/bin/python" -m pip install -r requirements.txt

cat <<MSG

Environment is ready.
Run tests with:
  ./scripts/test.sh

Run app with:
  ./scripts/dev-one-click.sh
MSG
