#!/bin/bash
# One-command package launch (efficiency measure M7). See package_launch.py for the steps, the rules and the exit codes.
#   bash scripts/flights/batch/package_launch.sh <spec.json> [--from STEP] [--until STEP] [--dry-run] [--root-countersign] [--redo STEP]
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PY=${PACKAGE_LAUNCH_PY:-$HOME/.venvs/speechrl/bin/python}
[ -x "$PY" ] || PY=python3
export PYTHONDONTWRITEBYTECODE=1
exec "$PY" -B "$HERE/package_launch.py" "$@"
