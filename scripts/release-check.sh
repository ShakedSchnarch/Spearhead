#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[1/8] Validate shell scripts syntax"
bash -n scripts/run-local.sh scripts/local-dev.sh scripts/dev-one-click.sh scripts/build-ui.sh scripts/setup-venv.sh scripts/test.sh \
  scripts/cloud/enable-gcp-apis.sh scripts/cloud/deploy-api-cloudrun.sh scripts/cloud/deploy-worker-cloudrun.sh scripts/cloud/deploy-stage-a.sh

echo "[2/8] Validate Python bytecode compile"
python3 -m compileall -q src

echo "[3/8] Validate frontend lint"
cd "$ROOT/frontend-app"
npm run lint
cd "$ROOT"

echo "[4/8] Ensure no unresolved merge markers"
if rg -n '^(<<<<<<<|=======|>>>>>>>)' . >/tmp/spearhead_release_merge_markers.txt 2>/dev/null; then
  echo "Unresolved merge markers found:"
  cat /tmp/spearhead_release_merge_markers.txt
  exit 1
fi

echo "[5/8] Ensure no TODO/FIXME in active runtime/docs"
if rg -n 'TODO|FIXME|XXX|HACK' src frontend-app scripts docs --glob '!docs/archive/**' --glob '!scripts/release-check.sh' >/tmp/spearhead_release_todos.txt 2>/dev/null; then
  echo "Active TODO/FIXME markers found:"
  cat /tmp/spearhead_release_todos.txt
  exit 1
fi

echo "[6/8] Run backend test suite (non-legacy)"
./scripts/test.sh -q

echo "[7/8] Build frontend"
cd "$ROOT/frontend-app"
npm run build
cd "$ROOT"

echo "[8/8] Validate API app import"
PYTHONPATH=src ./.venv/bin/python -c "from spearhead.api.main import create_app; app=create_app(); print(app.version)"

echo "Release check passed."
