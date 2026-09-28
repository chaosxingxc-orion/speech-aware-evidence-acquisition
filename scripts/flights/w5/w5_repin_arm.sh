#!/bin/bash
# Cell W5 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# W5 is the retained AGREE arm with ONE store ADDED -- knowledge_stores.slot-exemplars, nine
# shortlist-scoped, speech-keyed, slot-bearing TRAIN exemplars per row to the Solver from the
# R01-excluded pool (owner decision 170) -- flown on TRAIN Fold A 1,080, read on no harm (SLU-F1
# primary, intent guard) at the knowledge wave's shared in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1.
#
# No ALLOW_OUTPUT_CHANGE: no committed prepared_phase_supply pin, so the re-pin tool MINTS this
# cell's own (item E16). The added store serves the Solver only, so the minted first-phase supply's
# output digest must equal the AGREE arm's
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae -- anything else: stop and report.
export RD=docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1
export CELL=slurp-native-stage3-w5-fold-a-v1
export EXP=slurp-native-stage3-w5-fold-a-v1
export PKG=slurp-stage3-w5-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-w5-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w5-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w5-fold-a-admission-v1
export TAG=w5-arm ARM=1
export MSG=/home/chao/w5-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
