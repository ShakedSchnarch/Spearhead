#!/usr/bin/env bash
set -euo pipefail

RESET_DB=0

# Parse args
FORCE_REBUILD=0

for arg in "$@"; do
    case $arg in
        --reset-db)
            RESET_DB=1
            shift
            ;;
        --rebuild-ui|--force)
            FORCE_REBUILD=1
            shift
            ;;
        *)
            ;;
    esac
done

echo "============================================="
echo "   Spearhead Dev Environment - One Click"
echo "============================================="

# 1. Environment Setup (Skipped if valid)
if [[ -d ".venv" ]] && [[ "$FORCE_REBUILD" -eq 0 ]]; then
    echo ">>> [1/4] Python Environment found. Skipping setup (Use --force to reinstall)..."
else
    echo ">>> [1/4] Setting up Python Environment..."
    ./scripts/setup-venv.sh
fi

# 2. Database Reset (Optional)
if [[ "$RESET_DB" -eq 1 ]]; then
    echo ">>> [2/4] Resetting Database & Seeding..."
    ./scripts/clean-db.sh
    bash ./scripts/seed-and-export.sh
else
    echo ">>> [2/4] Skipping Database Reset (Use --reset-db to force)..."
fi

# 3. Build UI (Skipped if dist exists)
DIST_DIR="frontend-app/dist"
if [[ -d "$DIST_DIR" ]] && [[ "$(ls -A $DIST_DIR)" ]] && [[ "$FORCE_REBUILD" -eq 0 ]]; then
    echo ">>> [3/4] UI Build found. Skipping build (Use --rebuild-ui to force)..."
else
    echo ">>> [3/4] Building Frontend..."
    ./scripts/build-ui.sh
fi

# 4. Run Server
echo ">>> [4/4] Starting Server..."
echo "    http://127.0.0.1:8000"

# Use exec to replace shell, ensuring signals like Ctrl+C work
exec ./scripts/run-local.sh
