#!/bin/bash
# CELL-1 generation-smoke flip (Stage-3 S3-6 / S3-4s, owner decisions 83 / 99 / 101 / 106): env for
# repin_cell_generic.sh. Model-free. No ALLOW_OUTPUT_CHANGE: this cell carries NO committed
# prepared_phase_supply pin at all, so core.flight.repin.ensure_artifact_pinned MINTS this cell's own
# under its own run id (item E16) and has nothing to compare against. If a later re-pin ever reports a
# CHANGED output, the knowledge channel moved -- stop and report, never pass --allow-output-change.
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-smoke-4-v1
export EXP=slurp-native-stage3-delta-cell-smoke-4-v1
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-smoke ARM=0
export MSG=/home/chao/cell1-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
