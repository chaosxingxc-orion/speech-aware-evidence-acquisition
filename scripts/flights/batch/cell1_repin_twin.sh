#!/bin/bash
# CELL-1 twin-arm flip (the derangement form control on TRAIN Fold A; Stage-3 S3-6 / S3-4s, owner
# decisions 83 / 99 / 101 / 106): env for repin_cell_generic.sh. Model-free. ARM=1, so the pass
# records the flight commit, prints the check summary and runs the results-ledger gate. This is the
# LAST flip of the family, so /home/chao/cell1-twin-flight-commit.txt is the commit both chain steps
# fly. No ALLOW_OUTPUT_CHANGE.
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-r01-twin-v1
export EXP=slurp-native-stage3-delta-cell-r01-v1
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-twin ARM=1
export MSG=/home/chao/cell1-twin-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
