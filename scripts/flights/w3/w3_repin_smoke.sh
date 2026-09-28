#!/bin/bash
# Cell W3 four-row form smoke flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
# The same one pin (W3a alone: the contrast-card release; no exemplar cap) on the first four rows of
# the unchanged TRAIN Fold A roster; structural form proof only, never scored, never read. No
# ALLOW_OUTPUT_CHANGE; the minted supply must carry the AGREE smoke's own output digest.
export RD=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1
export CELL=slurp-native-stage3-w3-fold-a-smoke-4-v1
export EXP=slurp-native-stage3-w3-fold-a-smoke-4-v1
export PKG=slurp-stage3-w3-contrast-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w3-contrast-fold-a-admission-v1
export TAG=w3-smoke
export MSG=/home/chao/w3-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
