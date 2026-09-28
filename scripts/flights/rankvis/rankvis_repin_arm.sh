#!/bin/bash
# Cell RANKVIS flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# RANKVIS is the registered AGREE arm with ONE native_episode key added (knowledge_value_rendering:
# order retrieval-rank, rank_visible true, stores intent-boundaries and train-exemplars; owner decision
# 171), flown on the 119 TRAIN Fold A rows AGREE delivered the gold boundary entry for and still got
# wrong. Treatment only; the comparator is the sealed AGREE arm.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16).
# A CHANGED output on a later re-pin means the knowledge channel moved -- stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
# The check attaches to NOTHING; the resident np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1
export CELL=slurp-native-stage3-rankvis-fold-a-119-v1
export EXP=slurp-native-stage3-rankvis-fold-a-119-v1
export PKG=slurp-stage3-rankvis-fold-a-119-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-rankvis-fold-a-119-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-rankvis-fold-a-119-admission-v1
export TAG=rankvis-arm ARM=1
export MSG=/home/chao/rankvis-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
