#!/bin/bash
# VAR-1 flip: the four-row family smoke (the VAR1-PER-K16C5 form on the first four R01C rows).
# Env for repin_cell_generic.sh. Model-free.
#
# The smoke exists for ONE item: that the widened contract shape walks a real flight -- five
# Perception candidates instead of three, sixteen intent cards instead of eight, the same
# 28-value slot-contract budget spread over five candidates. The three exemplar variants change a
# retrieval budget and no contract byte, and VAR1-PLAN / VAR1-PLANR are the locked plan's own
# sealed form, so this is the family's only smoke.
#
# No ALLOW_OUTPUT_CHANGE: this cell carries NO committed prepared_phase_supply pin at all, so
# core.flight.repin.ensure_artifact_pinned MINTS its own under its own run id (harness item E16).
export RD=docs/readiness/2026-09-24-slurp-stage3-var1-v1
export CELL=slurp-native-stage3-var1-smoke-4-v1
export EXP=slurp-native-stage3-var1-smoke-4-v1
export PKG=slurp-stage3-var1-v1
export PREREG=docs/readiness/2026-09-24-slurp-stage3-var1-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-var1-v1/root-admission-v1.json
export DEC_ID=slurp-stage3-var1-admission-v1
export TAG=var1-smoke
export MSG=/home/chao/var1-smoke-commit.txt
exec bash "$(dirname "$0")/repin_cell_generic.sh"
