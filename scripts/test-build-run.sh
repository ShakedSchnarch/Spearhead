#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# 1) Tests
echo "Running backend tests..."
"$ROOT/scripts/test.sh"

# 2) Build UI (ensures dist/ is fresh for run-local)
echo "Building frontend..."
"$ROOT/scripts/build-ui.sh"

# 3) Run full stack locally (FastAPI + built UI)
echo "Starting API with built UI..."
exec "$ROOT/scripts/run-local.sh"
