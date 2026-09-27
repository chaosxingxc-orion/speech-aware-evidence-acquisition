#!/bin/bash
# Cell G5 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# G5 is the locked PLAN plan with ONE pin moved -- phase_material.reviewer.instruction_template,
# from the v1 file to the g5_v1 file that deletes the retired-tool order (owner decisions 135 and
# 153; item E25) -- flown on TRAIN Fold A 1,080 as a row-127 no-harm item, read at the in-chain
# A/A flown in the same chain.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16).
# The Reviewer instruction is not an input to the first-phase supply, so the minted supply's
# output digest must equal the sealed PLAN preparation's
# ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f -- anything else means the
# knowledge channel moved: stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
# The check attaches to NOTHING; the resident np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
export CELL=slurp-native-stage3-g5-fold-a-v1
export EXP=slurp-native-stage3-g5-fold-a-v1
export PKG=slurp-stage3-g5-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-g5-fold-a-admission-v1
export TAG=g5-arm ARM=1
export MSG=/home/chao/g5-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
