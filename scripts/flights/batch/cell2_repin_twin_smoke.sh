#!/bin/bash
# CELL-2 twin-smoke flip (Stage-3 S3-6 ITERATION 2, owner decisions 83 / 99 / 101 / 106): env for
# repin_cell_generic.sh. Model-free. CELL-2 is CELL-1 with knowledge_stores.stage3-deltas
# re-pointed from version 1r (379 values) to the released version 2 (200 values, the
# owner-decision-83 retention over CELL-1's own read); every run, attempt and fit identity is NEW,
# because CELL-1's are consumed and a plan budget is run-cumulative per run id.
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
export RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1
export CELL=slurp-native-stage3-delta-cell-r02-smoke-4-twin-v1
export EXP=slurp-native-stage3-delta-cell-r02-smoke-4-v1
export PKG=slurp-stage3-delta-cell-r02-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r02-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r02-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r02-admission-v1
export TAG=cell2-twin-smoke ARM=0
export MSG=/home/chao/cell2-twin-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
