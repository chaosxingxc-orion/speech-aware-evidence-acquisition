#!/bin/bash
# Re-pin the COMP-1 arm (agreement term + centroid key + citation contract on the locked plan) through
# the generic flip. Model-free. ARM=1: records the flight commit, prints the check summary and runs the
# results-ledger gate. The check attaches to NOTHING; the resident np4 session is untouched at flip time.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1 \
CELL=slurp-native-stage3-comp1-fold-a-v1 \
PKG=slurp-stage3-comp1-fold-a-v1 \
PREREG=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1-fold-a-admission-v1 \
TAG=comp1-arm ARM=1 MSG=/home/chao/comp1-arm-commit.txt \
bash $SP/repin_cell_generic.sh
