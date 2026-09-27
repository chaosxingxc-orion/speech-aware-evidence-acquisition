#!/bin/bash
# Cell ROLL-3 arm flip (the Stage-3 sealed-sample-pool asset on DEV-2000-ADDED): env for repin_cell_generic.sh.
# Model-free.
# ROLL-3 is cell ROLL-2's grouped-Solver form -- samples 5, temperature 0.7, seed_offset 0, plurality commit at
# min_support 3 -- re-pointed from TRAIN Fold A (1,080 rows) onto DEV-2000-ADDED, 1,000 rows: the evaluation roster
# where every admitted policy must later be replicated. ZERO factors change in the form; only the roster moves.
# Every run, attempt and fit identity is NEW. No ALLOW_OUTPUT_CHANGE: this cell carries NO committed
# prepared_phase_supply pin at all, so core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own
# run id (item E16) and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
# ARM=1, so the pass records the flight commit, prints the check summary and runs the results-ledger gate.
export RD=docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1
export CELL=slurp-native-stage3-roll-3-dev2000-added-v1
export EXP=slurp-native-stage3-roll-3-dev2000-added-v1
export PKG=slurp-stage3-roll-3-dev2000-added-v1
export PREREG=docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-roll-3-dev2000-added-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-roll-3-dev2000-added-admission-v1
export TAG=roll3-arm ARM=1
export MSG=/home/chao/roll3-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
