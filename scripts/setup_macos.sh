#!/usr/bin/env bash
set -euo pipefail

if [ ! -d ".venv" ]; then
  python3.12 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip

if [ "${1:-}" = "--dev" ]; then
  python -m pip install -e '.[dev]'
else
  python -m pip install -e .
fi

echo "Done. Activate with: source .venv/bin/activate"
