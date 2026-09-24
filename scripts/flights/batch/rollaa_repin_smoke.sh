#!/bin/bash
# Cell ROLL-AA generation-smoke flip (board route F2, the Stage-3 within-flight A/A null): env for
# repin_cell_generic.sh. Model-free. ROLL-AA is cell ROLL-1 with the Solver group changed to the
# E2b greedy-repeat twin form at N = 2 -- the locked v2.0 plan's Solver answering the IDENTICAL
# prompt twice per row, greedy -- on the first 200 rows of R01C (the smoke flies the first 4).
# Every run, attempt and fit identity is NEW.
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
export RD=docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1
export CELL=slurp-native-stage3-roll-aa-smoke-4-v1
export EXP=slurp-native-stage3-roll-aa-smoke-4-v1
export PKG=slurp-stage3-roll-aa-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-roll-aa-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-roll-aa-admission-v1
export TAG=rollaa-smoke ARM=0
export MSG=/home/chao/rollaa-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
