#!/bin/bash
# Re-pin the AGREE four-row form smoke through the generic flip (requires the repin tool's
# preparation-requirement fix: this cell carries the agreement table beside its own supply).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1 \
CELL=slurp-native-stage3-agree-w1-fold-a-smoke-4-v1 \
PKG=slurp-stage3-agree-w1-fold-a-v1 \
PREREG=docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-agree-w1-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-agree-w1-fold-a-admission-v1 \
TAG=agree-smoke MSG=/home/chao/agree-smoke-commit.txt \
bash $SP/repin_cell_generic.sh
