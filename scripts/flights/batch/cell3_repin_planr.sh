#!/bin/bash
# PLANr-DEV2000 flip (Stage-3 S3-6 ITERATION 3, owner decisions 83 / 99 / 101 / 106 / 110 pending):
# env for repin_cell_generic.sh. Model-free.
#
# PLANr-DEV2000 is cell B6's plan arm flown a SECOND time, request-identical, to give the
# DEV-2000-ADDED roster its OWN NULL. Every run, attempt and fit identity is NEW, because cell B6's
# are consumed and a plan budget is run-cumulative per run id. It flies FIRST of the family: CELL-3
# has no margin until this cell's read has sealed.
#
# No ALLOW_OUTPUT_CHANGE. This cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS its own under its own run id (item E16). Because
# the cell is request-identical to cell B6's plan arm, the minted artifact MUST reproduce
# 36463545fa791723c2adee82db9fb8c78420c72d0ebc07d4ec179cc0ddb2e179 exactly; a different value means
# the knowledge channel moved and the replicate is not a replicate -- stop and report.
#
# ARM=1, so the pass records the flight commit, prints the check summary and runs the
# results-ledger gate.
export RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1
export CELL=slurp-native-default-plan-dev2000-added-replicate-v1
export EXP=slurp-native-default-plan-dev2000-added-replicate-v1
export PKG=slurp-stage3-delta-cell-r03-gate-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r03-gate-admission-v1
export TAG=cell3-planr ARM=1
export MSG=/home/chao/cell3-planr-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
