#!/bin/bash

# Get the directory of the script
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Change to the script's directory
cd "$SCRIPT_DIR" || exit

source .venv/bin/activate

uvicorn main:app --port 8123
