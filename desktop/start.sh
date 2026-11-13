#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Virtual environment missing. Run: python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt' >&2
  exit 1
fi
exec .venv/bin/python main.py
