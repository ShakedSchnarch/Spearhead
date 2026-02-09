#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/5] Validate shell scripts syntax"
bash -n scripts/run-local.sh scripts/dev-one-click.sh scripts/build-ui.sh scripts/setup-venv.sh scripts/test.sh \
  scripts/cloud/enable-gcp-apis.sh scripts/cloud/deploy-api-cloudrun.sh scripts/cloud/deploy-worker-cloudrun.sh scripts/cloud/deploy-stage-a.sh

echo "[2/5] Validate Python bytecode compile"
python3 -m compileall -q src

echo "[3/5] Run backend test suite (non-legacy)"
./scripts/test.sh -q

echo "[4/5] Build frontend"
cd "$ROOT/frontend-app"
npm run build
cd "$ROOT"

echo "[5/5] Validate API app import"
PYTHONPATH=src ./.venv/bin/python -c "from spearhead.api.main import create_app; app=create_app(); print(app.version)"

echo "Release check passed."
