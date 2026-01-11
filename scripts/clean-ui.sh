#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DIST_DIR="$ROOT/frontend-app/dist"

echo "Cleaning frontend build artifacts..."
rm -rf "$DIST_DIR"

echo "Done. Next build will recreate dist/ automatically."
echo "Note: to fully reset browser state, clear Local Storage for http://127.0.0.1:8000/app (DevTools → Application → Local Storage → Clear)."
