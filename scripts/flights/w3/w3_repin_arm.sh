#!/bin/bash
# Cell W3 arm flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# W3 is W3a ALONE (owner decision 164; coordinator ruling 2026-09-27, the per-intent exemplar cap W3b
# dropped): the retained AGREE arm with one knowledge-content pin -- the intent-boundaries store moves
# to the contrast-card release intent-boundaries-contrast-v1; the Solver's exemplar supply stays the
# AGREE arm's. Read on no harm at the SHARED wave-1 in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1
# flown in the same chain.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (item E16).
# The first-phase (Perception) supply reads keys and value ids, which W3 does not move, so the
# minted supply's output digest must equal the AGREE arm's
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae -- anything else means the
# boundary retrieval moved: stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
# The check attaches to NOTHING; the resident np4 session is untouched at flip time.
export RD=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1
export CELL=slurp-native-stage3-w3-fold-a-v1
export EXP=slurp-native-stage3-w3-fold-a-v1
export PKG=slurp-stage3-w3-contrast-fold-a-v1
export PREREG=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-w3-contrast-fold-a-admission-v1
export TAG=w3-arm ARM=1
export MSG=/home/chao/w3-arm-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
