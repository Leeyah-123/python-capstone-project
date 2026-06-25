#!/bin/bash

# Install dependencies into a virtual environment if not already present,
# then run main.py using that environment's Python interpreter.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Create the venv on first run (idempotent).
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

# Install / upgrade dependencies from requirements.txt.
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

# Run the main script.
"$VENV_DIR/bin/python" "$SCRIPT_DIR/main.py"
