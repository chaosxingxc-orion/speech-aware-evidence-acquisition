#!/bin/bash
# A2T-AA smoke flip (owner decisions 67/68/71/139): env for repin_cell_generic.sh. Prefer a2taa_flip_all.sh
# (one call over the three cells); use this loop form only if root wants the per-cell flips, in the order
# smoke, a, b (repin_loop_generic.sh <this> <RD> <CELL> smoke-generation <msg>).
export RD=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1
export CELL=a2t-stage3-aa-paired-400-smoke-4-v1
export PKG=a2t-stage3-aa-paired-400-v1
export PREREG=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1-preregistration.md
export DEC_PATH=coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json
export DEC_ID=a2t-stage3-aa-paired-400-admission-v1
export TAG=a2taa-smoke ARM=0
export MSG=/home/chao/a2taa-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
