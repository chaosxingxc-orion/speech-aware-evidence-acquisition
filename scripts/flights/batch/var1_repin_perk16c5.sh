#!/bin/bash
# VAR-1 flip: cell VAR1-PER-K16C5. Env for repin_cell_generic.sh. Model-free.
#
# Stage-3 VAR-1 is the FIRST construction-variant rollout of the locked v2.0 plan (owner
# directive 2026-09-24): six cells on the 625-row SLURP-STAGE3-CONSTRUCTION-R01C construction
# roster -- the locked plan re-pointed at R01C, its request-identical replicate (the roster's own
# null), and four single-knob construction variants of its knowledge supply.
# VAR1-PER-K16C5 moves the intent-coverage lever: Perception intent cards k 8 -> 16 with fuse_coverage 1/16/16, and the candidate bound 3 -> 5 at BOTH the Perception fill contract and the slot-contracts candidate supply. It is the only VAR-1 form whose contract shape changes, and the only one with a four-row smoke.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS this cell's own under its own run id (harness item
# E16) and has nothing to compare against. A CHANGED output on a later re-pin means the knowledge
# channel moved -- stop and report.
# ARM=1 on every VAR-1 flight cell: each one is a 625-row arm, so the pass records its flight
# commit, prints the check summary and runs the results-ledger gate.
export RD=docs/readiness/2026-09-24-slurp-stage3-var1-v1
export CELL=slurp-native-stage3-var1-per-k16c5-r01c-v1
export EXP=slurp-native-stage3-var1-per-k16c5-r01c-v1
export PKG=slurp-stage3-var1-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-var1-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-var1-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-var1-admission-v1
export TAG=var1-perk16c5 ARM=1
export MSG=/home/chao/var1-perk16c5-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
