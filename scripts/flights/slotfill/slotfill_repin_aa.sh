#!/bin/bash
# Cell SLOTFILL in-chain A/A flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
# The locked PLAN form unchanged and WITHOUT the dispatch key, its own run / attempt / fit ids,
# flown in the same campaign chain as the SLOTFILL arm as the within-chain null and throughput
# baseline. No ALLOW_OUTPUT_CHANGE (item E16: the flip mints this cell's own supply; its output
# digest must equal the sealed PLAN's ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f).
export RD=docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1
export CELL=slurp-native-stage3-slotfill-aa-fold-a-v1
export EXP=slurp-native-stage3-slotfill-aa-fold-a-v1
export PKG=slurp-stage3-slotfill-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-slotfill-fold-a-admission-v1
export TAG=slotfill-aa
export MSG=/home/chao/slotfill-aa-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
