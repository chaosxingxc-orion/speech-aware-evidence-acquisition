#!/bin/bash
# Re-pin the COMP-1 in-chain A/A (the locked plan's own bytes at recall k 60) through the generic flip.
# Model-free. Its re-minted prepared supply must again carry output digest ba5e1faa...; a different
# output means the knowledge channel moved -- stop and report (never pass --allow-output-change).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1 \
CELL=slurp-native-stage3-comp1-aa-fold-a-v1 \
PKG=slurp-stage3-comp1-fold-a-v1 \
PREREG=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1-fold-a-admission-v1 \
TAG=comp1-aa MSG=/home/chao/comp1-aa-commit.txt \
bash $SP/repin_cell_generic.sh
