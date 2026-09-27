#!/bin/bash
# Cell DET pass A flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# DET is the locked v2.0 plan, byte-identical, flown twice in one chain on a single-slot,
# prompt-cache-off serving geometry (np1 x 24,576, --no-cache-prompt) to test whether the
# programme's between-flight offset is an artefact of batch composition and cache state.
# Pass A flips FIRST: pass B is its request-identical second pass, and B's prepared
# first-phase supply must reproduce A's byte for byte.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
# ARM=1: the pass records its flight commit, prints the check summary and runs the
# results-ledger gate. The check attaches to NOTHING; it needs the resident np4 session to be
# stopped only at LAUNCH time, not at flip time.
export RD=docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1
export CELL=slurp-native-stage3-det-np1-fold-a-50-a-v1
export EXP=slurp-native-stage3-det-np1-fold-a-50-a-v1
export PKG=slurp-stage3-det-np1-fold-a-50-v1
export PREREG=docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-det-np1-fold-a-50-admission-v1
export TAG=det-a ARM=1
export MSG=/home/chao/det-a-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
