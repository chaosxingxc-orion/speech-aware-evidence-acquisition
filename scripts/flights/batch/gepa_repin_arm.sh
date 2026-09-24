#!/bin/bash
# GEPA arm flip: env for repin_cell_generic.sh. Model-free. No ALLOW_OUTPUT_CHANGE: this cell has
# NO prepared phase supply at all (phase-stage3-gepa-v1 declares knowledge "none" and the baseline
# declares evidence_source "none"), so core.flight.repin has nothing to re-mint and nothing to
# compare. NOTE: this commit moved core/flight/runtime.py, so the CELL-1 family's prepared
# artifacts are stale and must be re-pinned in the same cycle -- never with --allow-output-change.
export RD=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1
export CELL=slurp-native-stage3-gepa-r01-v1
export PKG=slurp-stage3-gepa-r01-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-gepa-r01-admission-v1
export EXP=slurp-native-stage3-gepa-r01-v1
export TAG=gepa-arm ARM=1
export MSG=/home/chao/gepa-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
