#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYTHONPATH="$ROOT/src" python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests scripts
python3 scripts/check_public_safety.py
