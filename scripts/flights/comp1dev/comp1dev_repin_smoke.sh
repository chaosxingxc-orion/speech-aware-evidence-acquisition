#!/bin/bash
# Re-pin the COMP-1 DEV-2000-ADDED four-row form smoke through the generic flip (the cell carries this roster's
# agreement table beside its own supply; the re-pin tool's preparation-requirement fix keeps both). Model-free.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1 \
CELL=slurp-native-stage3-comp1-dev2000-added-smoke-4-v1 \
PKG=slurp-stage3-comp1-dev2000-added-v1 \
PREREG=docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1-dev2000-added-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1-dev2000-added-admission-v1 \
TAG=comp1dev-smoke MSG=/home/chao/comp1dev-smoke-commit.txt \
bash $SP/repin_cell_generic.sh
