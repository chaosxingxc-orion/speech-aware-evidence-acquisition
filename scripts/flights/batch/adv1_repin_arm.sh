#!/bin/bash
# ADV-1 arm flip (Stage-3 S3-4 / S3-4s, owner decisions 82 / 101 / 106; decision 102 provisional):
# env for repin_cell_generic.sh. Model-free. No ALLOW_OUTPUT_CHANGE: this cell has NO prepared
# phase supply at all (phase-stage3-advantage-v2 declares knowledge "none" and the baseline
# declares evidence_source "none"), so core.flight.repin has nothing to re-mint and nothing to
# compare.
export RD=docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1
export CELL=slurp-native-stage3-advantage-r01-v1
export PKG=slurp-stage3-advantage-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-advantage-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-advantage-r01-admission-v1
export EXP=slurp-native-stage3-advantage-r01-v1
export TAG=adv1-arm ARM=1
export MSG=/home/chao/adv1-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
