#!/bin/bash
# Cell KPROBE flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# KPROBE is the locked PLAN plan with ONE pin moved -- the intent-boundary Perception
# facet_source, from the written-key file to the centroid-key file (owner decision 145) --
# flown on exactly the TRAIN Fold A rows whose gold boundary entry that key newly delivers,
# to read P(correct given newly delivered). Treatment only; the comparator is the sealed PLAN arm.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16)
# and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
# The check attaches to NOTHING; the resident np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1
export CELL=slurp-native-stage3-kprobe-fold-a-55-v1
export EXP=slurp-native-stage3-kprobe-fold-a-55-v1
export PKG=slurp-stage3-kprobe-fold-a-55-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-kprobe-fold-a-55-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-kprobe-fold-a-55-admission-v1
export TAG=kprobe-arm ARM=1
export MSG=/home/chao/kprobe-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
