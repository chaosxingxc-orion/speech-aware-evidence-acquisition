#!/bin/bash
# Cell ROLL-2 generation-smoke flip (the Stage-3 sealed-sample-pool asset on the v2.0 lock roster): env for
# repin_cell_generic.sh. Model-free. ROLL-2 is cell ROLL-1's grouped-Solver form -- samples 5,
# temperature 0.7, seed_offset 0, plurality commit at min_support 3 -- re-pointed from the 625-row
# R01C construction subset onto TRAIN Fold A, 1,080 rows: the roster the v2.0 lock lives on. ZERO
# factors change in the form; only the roster moves. Every run, attempt and fit identity is NEW.
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
export RD=docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1
export CELL=slurp-native-stage3-roll-2-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-roll-2-fold-a-smoke-4-v1
export PKG=slurp-stage3-roll-2-fold-a-v1
export PREREG=docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-roll-2-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-roll-2-fold-a-admission-v1
export TAG=roll2-smoke ARM=0
export MSG=/home/chao/roll2-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
