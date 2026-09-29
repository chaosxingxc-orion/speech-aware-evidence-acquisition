#!/bin/bash
# Cell E4-1 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# E4-1 (owner decision 185) is the retained AGREE arm under the 17-ceiling program
# phase-native-candidates-review-revise-relisten-v1 with a post-accept native_episode.relisten block
# (blind + forced-choice contacts on up to 3 delivered entities per row, shadow delivery), flown on
# TRAIN Fold A 1,080 and read as two shadow columns against the same flight's delivered column.
#
# No ALLOW_OUTPUT_CHANGE: no committed prepared_phase_supply pin, so the re-pin tool MINTS this
# cell's own (item E16). The first-phase supply is upstream of the program id and of the post-accept
# stage, so the minted supply's output digest must equal the AGREE arm's
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae -- anything else: stop and report.
# Not ARM=1: the flight commit is recorded by scripts/flights/e4/e4_flip.sh once BOTH cycles converge.
export RD=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1
export CELL=slurp-native-stage3-relisten-fold-a-v1
export EXP=slurp-native-stage3-relisten-fold-a-v1
export PKG=slurp-stage3-relisten-fold-a-v1
export PREREG=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-relisten-fold-a-admission-v1
export TAG=e4-arm
export MSG=/home/chao/e4-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
