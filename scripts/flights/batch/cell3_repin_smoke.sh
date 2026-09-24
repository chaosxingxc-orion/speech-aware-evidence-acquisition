#!/bin/bash
# CELL-3 generation-smoke flip (Stage-3 S3-6 ITERATION 3, the coverage-gated application policy; owner
# decisions 83 / 99 / 101 / 106 and 110 PENDING): env for repin_cell_generic.sh. Model-free.
#
# CELL-3 is cell B6's plan arm plus the released stage3-deltas-v2 store applied under a COVERAGE
# GATE: the three candidate-bound routes each declare scenario_gate
# majority-candidate-scenario-not-in-v1 over general, alarm, music, social, iot, play and news, and
# CELL-2's Perception unconditional route is REMOVED. The store itself is the one CELL-2 flew,
# pinned unchanged. Every run, attempt and fit identity is NEW, because CELL-2's are consumed and a
# plan budget is run-cumulative per run id.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
export RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1
export CELL=slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1
export EXP=slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1
export PKG=slurp-stage3-delta-cell-r03-gate-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r03-gate-admission-v1
export TAG=cell3-smoke ARM=0
export MSG=/home/chao/cell3-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
