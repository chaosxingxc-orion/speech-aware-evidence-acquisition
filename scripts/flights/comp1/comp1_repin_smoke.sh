#!/bin/bash
# Re-pin the COMP-1 four-row form smoke through the generic flip (the cell carries the agreement
# table beside its own supply; the re-pin tool's preparation-requirement fix keeps both). Model-free.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1 \
CELL=slurp-native-stage3-comp1-fold-a-smoke-4-v1 \
PKG=slurp-stage3-comp1-fold-a-v1 \
PREREG=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1-fold-a-admission-v1 \
TAG=comp1-smoke MSG=/home/chao/comp1-smoke-commit.txt \
bash $SP/repin_cell_generic.sh
