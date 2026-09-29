#!/bin/bash
# Cell W-SV-1 four-row form smoke flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
# The same program switch and Solver supply_variants block on the first four rows of the unchanged
# TRAIN Fold A roster; structural form proof only, never scored, never read. No ALLOW_OUTPUT_CHANGE;
# the minted supply's output digest must equal the AGREE smoke's
# 308601c52b54ec49013422349e045dd3a4d621c530bf3d2be730fdfe1fdd2fc9.
export RD=docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1
export CELL=slurp-native-stage3-wsv1-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-wsv1-fold-a-smoke-4-v1
export PKG=slurp-stage3-wsv1-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-wsv1-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-wsv1-fold-a-admission-v1
export TAG=wsv1-smoke
export MSG=/home/chao/wsv1-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
