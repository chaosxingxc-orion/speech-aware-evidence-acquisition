#!/bin/bash
# Re-pin the COMP-1b arm (COMP-1's own agreement term + centroid key, the citation contract reverted)
# through the generic flip. Model-free. ARM=1: records the flight commit, prints the check summary and
# runs the results-ledger gate. The check attaches to NOTHING; the resident np4 session is untouched at
# flip time. No AA repin sibling: the comparator is the EXISTING SEALED in-chain A/A cell COMP-1 already
# flew (SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1), reused cross-flight and never re-flown or re-pinned here.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1 \
CELL=slurp-native-stage3-comp1b-fold-a-v1 \
PKG=slurp-stage3-comp1b-fold-a-v1 \
PREREG=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1-preregistration.md \
DEC_PATH=coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json \
DEC_ID=slurp-stage3-comp1b-fold-a-admission-v1 \
TAG=comp1b-arm ARM=1 MSG=/home/chao/comp1b-arm-commit.txt \
bash $SP/repin_cell_generic.sh
