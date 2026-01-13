#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV_DIR=".venv"

echo "=== Setup Virtual Environment ==="

ensure_python() {
    if ! command -v python3 &> /dev/null; then
        echo "Error: python3 could not be found."
        exit 1
    fi
}

create_venv() {
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "Creating new venv in $VENV_DIR..."
        python3 -m venv "$VENV_DIR"
    else
        echo "Virtual environment exists at $VENV_DIR."
    fi
}

install_deps() {
    echo "Installing/Updating dependencies..."
    "$VENV_DIR/bin/pip" install --upgrade pip
    "$VENV_DIR/bin/pip" install -e ".[test]"
}

verify_venv() {
    echo "Verifying environment integrity..."
    # Check if basic imports work (catches corruption like importlib freeze)
    if "$VENV_DIR/bin/python3" -c "import pydantic; import pydantic_settings; print('Integrity OK')" &> /dev/null; then
        echo "Environment Verified."
        return 0
    else
        echo "WARNING: Environment corruption detected (Import check failed)."
        return 1
    fi
}

ensure_python
create_venv
install_deps

if ! verify_venv; then
    echo "Attempting self-healing: Recreating venv..."
    rm -rf "$VENV_DIR"
    create_venv
    install_deps
    if ! verify_venv; then
        echo "CRITICAL: Environment creation failed even after retry. Please check your python installation."
        exit 1
    fi
fi

echo "=== Setup Complete ==="
echo "Activate with: source $VENV_DIR/bin/activate"
