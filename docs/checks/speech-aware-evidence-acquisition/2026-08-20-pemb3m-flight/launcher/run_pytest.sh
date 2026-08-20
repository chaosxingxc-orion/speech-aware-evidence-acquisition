#!/usr/bin/env bash
source "$(dirname "$0")/env.sh"
cd "$REPO"
mkdir -p "$SCRATCH"
python -m pytest -q -p no:cacheprovider 2>&1 | tee "$SCRATCH/pytest.log" | tail -25
echo "PYTEST_EXIT=${PIPESTATUS[0]}"
