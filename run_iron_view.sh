#!/bin/bash

# Iron-View One-Click Runner
# Automatically detects latest Excel/CSV in mvp/files or data/input
# Runs the Iron-View build pipeline
# Opens the report

set -e

# 0. Setup Environment
# Assuming script is run from project root or iron-view dir
cd "$(dirname "$0")"
PROJECT_ROOT=$(pwd)
PYTHON_EXEC="../.venv/bin/python"
export PYTHONPATH=src

echo "========================================"
echo "   IRON-VIEW: TACTICAL REPORT SYSTEM    "
echo "========================================"

# 1. Detect Input File
# Priority: mvp/files/*.xlsx -> data/input/*.csv
INPUT_FILE=""

# Check mvp/files for Excel
LATEST_XLSX=$(ls -t ../mvp/files/*.xlsx 2>/dev/null | head -n 1)
if [ ! -z "$LATEST_XLSX" ]; then
    INPUT_FILE="$LATEST_XLSX"
else
    # Check data/input for CSV
    LATEST_CSV=$(ls -t data/input/*.csv 2>/dev/null | head -n 1)
    if [ ! -z "$LATEST_CSV" ]; then
        INPUT_FILE="$LATEST_CSV"
    fi
fi

if [ -z "$INPUT_FILE" ]; then
    echo "ERROR: No input files found in ../mvp/files or data/input"
    exit 1
fi

echo "[*] Detected Input: $INPUT_FILE"

# 2. Run Build
echo "[*] Initializing Intelligence Engine..."
OUTPUT_FILE="reports/report_latest.html"

$PYTHON_EXEC -m iron_view.main build --input "$INPUT_FILE" --output "$OUTPUT_FILE"

# 3. Open Report
if [ -f "$OUTPUT_FILE" ]; then
    echo "[*] Build Successful. Opening Report..."
    open "$OUTPUT_FILE"
else
    echo "ERROR: Build failed to produce output."
    exit 1
fi
