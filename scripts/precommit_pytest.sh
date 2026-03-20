#!/usr/bin/env bash
set -euo pipefail

if [[ ! -x .venv/bin/python ]]; then
  echo "Missing .venv. Run: uv venv && uv pip install -e \".[dev]\""
  exit 1
fi

.venv/bin/python -m pytest
