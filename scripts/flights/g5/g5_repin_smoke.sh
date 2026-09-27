#!/bin/bash
# Cell G5 four-row form smoke flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
# The same one pin (the repaired Reviewer instruction) on the first four rows of the unchanged
# TRAIN Fold A roster; structural form proof only, never scored, never read. No ALLOW_OUTPUT_CHANGE.
export RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
export CELL=slurp-native-stage3-g5-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-g5-fold-a-smoke-4-v1
export PKG=slurp-stage3-g5-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-g5-fold-a-admission-v1
export TAG=g5-smoke
export MSG=/home/chao/g5-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
