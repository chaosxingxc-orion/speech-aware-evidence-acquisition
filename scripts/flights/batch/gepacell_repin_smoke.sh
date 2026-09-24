#!/bin/bash
# CELL-1-GEPA generation-smoke flip (Stage-3 S3-6, the GEPA delta store; owner decisions 83 / 99 / 101 / 106): env for
# repin_cell_generic.sh. Model-free. CELL-1-GEPA is CELL-1 with knowledge_stores.stage3-deltas
# re-pointed from version 1r (379 values) to the released GEPA store stage3-deltas-gepa-v1
# (448 values: 248 rows the GEPA proposer cell authored over the sealed ROLL-1 trajectories of
# R01C, appended to the 200 iteration-1 rows the owner-decision-83 retention over CELL-1's own
# read kept); every run, attempt and fit identity is NEW,
# because CELL-1's are consumed and a plan budget is run-cumulative per run id.
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
export RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1
export CELL=slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1
export EXP=slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1
export PKG=slurp-stage3-delta-cell-gepa-r01-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-gepa-r01-v1/cell-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-gepa-r01-admission-v1
export TAG=gepacell-smoke ARM=0
export MSG=/home/chao/gepacell-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
