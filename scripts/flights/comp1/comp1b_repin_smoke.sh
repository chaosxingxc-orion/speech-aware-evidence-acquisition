#!/bin/bash
# Re-pin the COMP-1b four-row form smoke through the generic flip (the cell carries the agreement
# table beside its own supply; the re-pin tool's preparation-requirement fix keeps both). Model-free.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1 \
CELL=slurp-native-stage3-comp1b-fold-a-smoke-4-v1 \
PKG=slurp-stage3-comp1b-fold-a-v1 \
PREREG=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1b-fold-a-admission-v1 \
TAG=comp1b-smoke MSG=/home/chao/comp1b-smoke-commit.txt \
bash $SP/repin_cell_generic.sh
