#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DB_PATH="data/ironview.db"
SYNC_TMP="data/input/sync_tmp"
CACHE_DIR="data/sync_cache"

echo "Removing $DB_PATH (if exists)..."
rm -f "$DB_PATH"

echo "Cleaning sync temp/cache dirs (if exist)..."
rm -rf "$SYNC_TMP" "$CACHE_DIR"

echo "Done. Re-import your files to rebuild the database."
