#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Resetting DB and frontend build..."
"$ROOT/scripts/clean-db.sh"
"$ROOT/scripts/clean-ui.sh"

echo "Reset complete. Re-run sync/import and build when ready."
