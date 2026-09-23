#!/bin/bash
# CELL-1 arm flip (the locked v2.0 plan plus the per-node stage3-deltas store on TRAIN Fold A;
# Stage-3 S3-6 / S3-4s, owner decisions 83 / 99 / 101 / 106): env for repin_cell_generic.sh.
# Model-free. ARM=1, so the pass records the flight commit, prints the check summary and runs the
# results-ledger gate. No ALLOW_OUTPUT_CHANGE: the flip mints this cell's OWN prepared supply under
# its own run id (item E16); a CHANGED output means the knowledge channel moved -- stop and report.
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-r01-v1
export EXP=slurp-native-stage3-delta-cell-r01-v1
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-arm ARM=1
export MSG=/home/chao/cell1-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
