#!/usr/bin/env bash
# h5-shell-pipeline: H5 Shell batch production entry (macOS/Linux)
# Usage: ./run.sh for interactive menu, or ./run.sh <command> [args]

set -e
cd "$(dirname "$0")"

VENV_PYTHON=".venv/bin/python"
VENV_PIP=".venv/bin/pip"

if [ ! -d ".venv" ]; then
    echo ""
    echo "============================================================"
    echo "  First run, initializing environment..."
    echo "============================================================"
    echo ""

    echo "  [1/3] Creating virtual environment..."
    python3 -m venv .venv
    echo "  OK venv created"

    echo ""
    echo "  [2/3] Installing dependencies..."
    "$VENV_PIP" install -r requirements.txt -q
    echo "  OK dependencies installed"
    echo ""
    echo "  Environment initialization complete!"
    echo ""
    sleep 1
fi

export PYTHONPATH="$(pwd)/scripts:${PYTHONPATH}"

# No args → interactive menu (handled by Python)
# With args → direct command execution
exec "$VENV_PYTHON" -m batch "$@"
