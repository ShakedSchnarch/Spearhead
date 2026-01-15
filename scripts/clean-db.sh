#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Resolve DB path from settings (falls back if unavailable)
DB_PATH="$("$ROOT/.venv/bin/python" - <<'PY' 2>/dev/null || echo "data/spearhead.db"
from spearhead.config import settings
print(settings.paths.db_path)
PY
)"
ALT_DB="data/ironview.db"
SYNC_TMP="data/input/sync_tmp"
CACHE_DIR="data/sync_cache"

echo "Removing $DB_PATH (if exists)..."
rm -f "$DB_PATH"
if [[ "$ALT_DB" != "$DB_PATH" ]]; then
  echo "Removing $ALT_DB (if exists)..."
  rm -f "$ALT_DB"
fi

echo "Cleaning sync temp/cache dirs (if exist)..."
rm -rf "$SYNC_TMP" "$CACHE_DIR"

echo "Done. Re-import your files to rebuild the database."
