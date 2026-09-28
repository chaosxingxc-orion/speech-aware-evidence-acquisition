#!/bin/bash
# Cell W4-SV four-row form smoke flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
# The same base and arm group on the first four rows of the unchanged TRAIN Fold A roster; structural form proof
# only, never scored, never read. No ALLOW_OUTPUT_CHANGE; the minted supply's output digest must equal the AGREE
# smoke's 308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9.
export RD=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1
export CELL=slurp-native-stage3-w4sv-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-w4sv-fold-a-smoke-4-v1
export PKG=slurp-stage3-w4sv-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w4sv-fold-a-admission-v1
export TAG=w4sv-smoke
export MSG=/home/chao/w4sv-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
