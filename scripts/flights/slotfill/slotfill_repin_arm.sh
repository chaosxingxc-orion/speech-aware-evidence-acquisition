#!/bin/bash
# Cell SLOTFILL arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# SLOTFILL is the locked PLAN plan with ONE key added -- dispatch (rails.dispatch_slot_fill:
# recall_prefetch, role_input_offload, gc_freeze; owner decision 159) -- flown on TRAIN Fold A
# 1,080 as a row-127 no-harm item with a throughput ceiling, read at the in-chain A/A flown in
# the same chain.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16).
# The dispatch key enters the supply's identity but not its computation, so the minted supply's
# output digest must equal the sealed PLAN preparation's
# ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f -- anything else means the
# knowledge channel moved: stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
# The check attaches to NOTHING; the resident np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1
export CELL=slurp-native-stage3-slotfill-fold-a-v1
export EXP=slurp-native-stage3-slotfill-fold-a-v1
export PKG=slurp-stage3-slotfill-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-slotfill-fold-a-admission-v1
export TAG=slotfill-arm ARM=1
export MSG=/home/chao/slotfill-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
