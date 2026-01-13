#!/usr/bin/env bash
set -euo pipefail

RESET_DB=0

# Parse args
for arg in "$@"; do
    case $arg in
        --reset-db)
            RESET_DB=1
            shift
            ;;
        *)
            ;;
    esac
done

echo "============================================="
echo "   Spearhead Dev Environment - One Click"
echo "============================================="

# 1. Environment Setup
echo ">>> [1/4] Verifying Python Environment..."
./scripts/setup-venv.sh

# 2. Database Reset (Optional)
if [[ "$RESET_DB" -eq 1 ]]; then
    echo ">>> [2/4] Resetting Database & Seeding..."
    ./scripts/clean-db.sh # Explicit clean
    ./scripts/seed-and-export.sh
else
    echo ">>> [2/4] Skipping Database Reset (Use --reset-db to force)..."
fi

# 3. Build UI
echo ">>> [3/4] Building Frontend..."
./scripts/build-ui.sh

# 4. Run Server
echo ">>> [4/4] Starting Server..."
echo "    http://127.0.0.1:8000"
./scripts/run-local.sh
