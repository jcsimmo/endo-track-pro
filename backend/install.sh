#!/bin/bash

# Get the directory of the script
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Change to the script's directory
cd "$SCRIPT_DIR" || exit

echo "Creating virtual environment in $(pwd)/.venv..."
uv venv
echo "Activating virtual environment..."
source .venv/bin/activate # Now correctly refers to backend/.venv/bin/activate
echo "Installing dependencies from requirements.txt..."
uv pip install -r requirements.txt
echo "Backend installation complete."
