#!/bin/bash
# CELL-1 generation-smoke flip (Stage-3 S3-6 / S3-4s, owner decisions 83 / 99 / 101 / 106): env for
# repin_cell_generic.sh. Model-free. No ALLOW_OUTPUT_CHANGE: this cell carries NO committed
# prepared_phase_supply pin at all, so core.flight.repin.ensure_artifact_pinned MINTS this cell's own
# under its own run id (item E16) and has nothing to compare against. If a later re-pin ever reports a
# CHANGED output, the knowledge channel moved -- stop and report, never pass --allow-output-change.
#
# 2026-09-23, SECOND FAILURE: run id SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1 failed twice (refused
# before contact, then 4 contacts / 10.6 s and a refusal at solver_0_input on the sealed Perception
# state's shape). The program rule -- "a second failure stops the flight and the fix is proven on a
# 4-row dry run" -- retires that run id, so this script now flips the REPLACEMENT smoke cell
# slurp-native-stage3-delta-cell-smoke-4-v2 (run id ...-SMOKE-4-V2, fit ...-SMOKE-4-V2-FIT-V1) and
# its own plan documents smoke-v2-*-plan-registered-v1.json. The twin smoke keeps its v1 ids and its
# own flip script. See the package README, "Second failure; the v1 smoke run id is retired".
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-smoke-4-v2
export EXP=slurp-native-stage3-delta-cell-smoke-4-v2
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-smoke ARM=0
export MSG=/home/chao/cell1-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
