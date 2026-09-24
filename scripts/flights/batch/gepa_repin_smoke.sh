#!/bin/bash
# GEPA four-row form smoke flip: env for repin_cell_generic.sh. Model-free; same reasoning as
# gepa_repin_arm.sh (no prepared phase supply, nothing to re-mint).
export RD=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1
export CELL=slurp-native-stage3-gepa-r01-smoke-4-v1
export PKG=slurp-stage3-gepa-r01-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-gepa-r01-admission-v1
export EXP=slurp-native-stage3-gepa-r01-smoke-4-v1
export TAG=gepa-smoke
export MSG=/home/chao/gepa-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
