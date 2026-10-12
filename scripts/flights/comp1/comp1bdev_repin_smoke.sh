#!/bin/bash
# Re-pin the A2 four-row form smoke through the generic flip. Model-free. Owner decision 198 (A2 = COMP-1b on DEV-2000-ADDED).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1 CELL=slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1 PKG=slurp-stage3-comp1b-dev2000-added-v1 PREREG=docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1-preregistration.md DEC_PATH=coordination/slurp-stage3-comp1b-dev2000-added-v1/root-admission-v1.json DEC_ID=slurp-stage3-comp1b-dev2000-added-admission-v1 TAG=comp1bdev-smoke MSG=/home/chao/comp1bdev-smoke-commit.txt bash $SP/repin_cell_generic.sh
