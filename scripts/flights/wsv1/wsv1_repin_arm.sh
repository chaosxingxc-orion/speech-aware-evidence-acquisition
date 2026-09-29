#!/bin/bash
# Cell W-SV-1 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# W-SV-1 (owner decision 172) is the retained AGREE arm under the 13-ceiling uncited program
# phase-native-candidates-review-revise-variants3first-v1 with a Solver supply_variants group
# (arm_visits first: b-exk30, t-twin, a-base delivering), flown on TRAIN Fold A 1,080 and read as
# Solver-local columns in the same flight.
#
# No ALLOW_OUTPUT_CHANGE: no committed prepared_phase_supply pin, so the re-pin tool MINTS this
# cell's own (item E16). The first-phase supply is upstream of the Solver arm group and of the
# program id, so the minted supply's output digest must equal the AGREE arm's
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae -- anything else: stop and report.
# Not ARM=1: the flight commit is recorded by scripts/flights/wsv1/wsv1_flip.sh once BOTH cycles converge.
export RD=docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1
export CELL=slurp-native-stage3-wsv1-fold-a-v1
export EXP=slurp-native-stage3-wsv1-fold-a-v1
export PKG=slurp-stage3-wsv1-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-wsv1-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-wsv1-fold-a-admission-v1
export TAG=wsv1-arm
export MSG=/home/chao/wsv1-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
