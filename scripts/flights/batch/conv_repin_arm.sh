#!/bin/bash
# Re-pin the 70-row conversion probe (cell CONV, decisions 133/134) through the generic flip.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1 \
CELL=slurp-native-stage3-conv-fold-a-70-v1 \
PKG=slurp-stage3-conv-fold-a-70-v1 \
PREREG=docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-conv-fold-a-70-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-conv-fold-a-70-admission-v1 \
TAG=conv-arm ARM=1 MSG=/home/chao/conv-arm-commit.txt \
bash $SP/repin_cell_generic.sh
