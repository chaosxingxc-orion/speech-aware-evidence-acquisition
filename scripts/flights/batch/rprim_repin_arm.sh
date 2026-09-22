#!/bin/bash
# R-PRIM 1,080-row arm flip (item E37, decision 84): env for repin_cell_generic.sh
export RD=docs/readiness/2026-09-22-slurp-review-primitives-v1
export CELL=slurp-native-review-primitives-v1
export PKG=slurp-review-primitives-v1
export PREREG=docs/readiness/2026-09-22-slurp-review-primitives-v1-preregistration.md
export DEC_PATH=coordination/slurp-review-primitives-v1/root-admission-v1.json
export DEC_ID=slurp-review-primitives-admission-v1
export TAG=rprim-arm ARM=1
export MSG=/home/chao/rprim-arm-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
