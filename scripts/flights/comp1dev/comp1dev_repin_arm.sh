#!/bin/bash
# Re-pin the COMP-1 DEV-2000-ADDED arm (this roster's agreement table + the centroid key + the citation contract on
# the sealed DEV plan arm) through the generic flip. Model-free. ARM=1: records the flight commit, prints the check
# summary and runs the results-ledger gate. The check attaches to NOTHING.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1 \
CELL=slurp-native-stage3-comp1-dev2000-added-v1 \
PKG=slurp-stage3-comp1-dev2000-added-v1 \
PREREG=docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1-dev2000-added-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1-dev2000-added-admission-v1 \
TAG=comp1dev-arm ARM=1 MSG=/home/chao/comp1dev-arm-commit.txt \
bash $SP/repin_cell_generic.sh
