#!/bin/bash
# Cell W1 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# W1 (owner decision 164, knowledge wave item W1) is the retained AGREE arm with ONE key added --
# knowledge_stores.slot-contracts.candidate_supply.solver.candidate_legality_source, the pinned
# intent -> slot-type legality table -- flown on TRAIN Fold A 1,080 as a row-127 no-harm FORM item,
# read at the coordinator's SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16).
# The card route is not an input to the first-phase supply, so the minted supply's output digest
# must equal the AGREE preparation's eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae
# -- anything else means the Perception channel moved: stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
export RD=docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1
export CELL=slurp-native-stage3-w1-cardsel-fold-a-v1
export EXP=slurp-native-stage3-w1-cardsel-fold-a-v1
export PKG=slurp-stage3-w1-cardsel-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w1-cardsel-fold-a-admission-v1
export TAG=w1-arm ARM=1
export MSG=/home/chao/w1-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
