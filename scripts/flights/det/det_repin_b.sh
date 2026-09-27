#!/bin/bash
# Cell DET pass B flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# Pass B is pass A's request-identical second pass on the same single-slot, prompt-cache-off
# geometry. Its prepared first-phase supply MUST reproduce pass A's byte for byte -- a
# different value means the pair is not request-identical. Stop and report; never pass
# --allow-output-change.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against.
# ARM=1: the pass records its flight commit (the chain's flight commit is THIS one, the last
# flip), prints the check summary and runs the results-ledger gate.
export RD=docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1
export CELL=slurp-native-stage3-det-np1-fold-a-50-b-v1
export EXP=slurp-native-stage3-det-np1-fold-a-50-b-v1
export PKG=slurp-stage3-det-np1-fold-a-50-v1
export PREREG=docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-det-np1-fold-a-50-admission-v1
export TAG=det-b ARM=1
export MSG=/home/chao/det-b-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
