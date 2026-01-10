#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/frontend-app"

# Install deps if missing
if [[ ! -d node_modules ]]; then
  npm install
fi

npm run dev
