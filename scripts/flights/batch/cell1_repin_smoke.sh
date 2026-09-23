#!/bin/bash
# CELL-1 generation-smoke flip (Stage-3 S3-6 / S3-4s, owner decisions 83 / 99 / 101 / 106): env for
# repin_cell_generic.sh. Model-free. No ALLOW_OUTPUT_CHANGE: this cell carries NO committed
# prepared_phase_supply pin at all, so core.flight.repin.ensure_artifact_pinned MINTS this cell's own
# under its own run id (item E16) and has nothing to compare against. If a later re-pin ever reports a
# CHANGED output, the knowledge channel moved -- stop and report, never pass --allow-output-change.
#
# 2026-09-23, THIRD FAILURE: run id SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2 metered 12 contacts on
# the four rows and died at the openJiuwen vertex reviewer_0_input with "acquire must introduce at
# least one new value or facet" -- a node-filtered, candidate-bound delta route that selected nothing
# still returned a supply, and any supply is an acquire transition. Rows 2 and 4 of the roster reach
# no Reviewer-targeted delta at all. The v1 run id before it failed twice. The program rule -- a
# failure is fixed and PROVEN on a four-row dry run before any further contact -- retires the v2 run
# id too, so this script now flips the REPLACEMENT smoke cell
# slurp-native-stage3-delta-cell-smoke-4-v3 (run id ...-SMOKE-4-V3, fit ...-SMOKE-4-V3-FIT-V1) and
# its own plan documents smoke-v3-*-plan-registered-v1.json. The twin smoke keeps its v1 ids and its
# own flip script. See the package README, "Third failure; the v2 smoke run id is retired".
export RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
export CELL=slurp-native-stage3-delta-cell-smoke-4-v3
export EXP=slurp-native-stage3-delta-cell-smoke-4-v3
export PKG=slurp-stage3-delta-cell-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-delta-cell-r01-admission-v1
export TAG=cell1-smoke ARM=0
export MSG=/home/chao/cell1-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
