#!/usr/bin/env bash
set -euo pipefail

# Create and activate venv
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# Install deps
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run
python run.py
