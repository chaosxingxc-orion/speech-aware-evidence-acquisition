#!/bin/bash
# Cell W4-SV arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# W4-SV is the retained AGREE arm with a three-arm first-visit Solver supply-variant group (owner decision 172):
# b-w4 (release_swap slot-contracts -> slot-contracts-w4-v1), t-twin (replicate_of a-agree), a-agree (delivering),
# program phase-native-candidates-review-revise-variants3first-v1 (ceiling 13), flown on TRAIN Fold A 1,080 and
# read as first-visit columns b-w4 vs a-agree against the twin null.
#
# No ALLOW_OUTPUT_CHANGE: no committed prepared_phase_supply pin, so the re-pin tool MINTS this cell's own
# (item E16). Neither the alternate nor the arm group is an input to the first-phase supply, so the minted
# supply's output digest must equal the AGREE arm's
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae -- anything else: stop and report.
export RD=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1
export CELL=slurp-native-stage3-w4sv-fold-a-v1
export EXP=slurp-native-stage3-w4sv-fold-a-v1
export PKG=slurp-stage3-w4sv-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w4sv-fold-a-admission-v1
export TAG=w4sv-arm ARM=1
export MSG=/home/chao/w4sv-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
