#!/bin/bash
# ROLL-1 smoke flip (Stage-3 S3-2, decisions 80-83/96/101): env for repin_cell_generic.sh
export RD=docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1
export CELL=slurp-native-stage3-rollout-r01-smoke-4-v1
export PKG=slurp-stage3-rollout-r01-v1
export PREREG=docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-rollout-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-rollout-r01-admission-v1
export TAG=roll1-smoke ARM=0
export ALLOW_OUTPUT_CHANGE=1  # 2026-09-23: the R01 -> R01C narrowing legitimately changes the prepared supply
export MSG=/home/chao/roll1-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
