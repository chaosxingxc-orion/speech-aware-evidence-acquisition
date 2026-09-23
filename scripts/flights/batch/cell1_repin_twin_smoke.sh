#!/bin/bash
# CELL-1 twin-smoke flip (the derangement form control's four-row smoke; Stage-3 S3-6 / S3-4s, owner
# decisions 83 / 99 / 101 / 106): env for repin_cell_generic.sh. Model-free. Same discipline as
# cell1_repin_smoke.sh -- the flip mints this cell's OWN prepared supply under its own run id (item
# E16) and --allow-output-change is never passed.
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-smoke-4-twin-v1
export EXP=slurp-native-stage3-delta-cell-smoke-4-v1
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-twin-smoke ARM=0
export MSG=/home/chao/cell1-twin-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
