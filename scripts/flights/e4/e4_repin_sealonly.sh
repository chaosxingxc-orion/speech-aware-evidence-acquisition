#!/bin/bash
# E4-1 SEAL-ONLY completion flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# The seal-only cell (owner decision 194, pending; the COMP-1 shape of decision 189 option A) is the resume cell under
# the arm's SAME run id with the new attempt attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only and
# resume_from the aborted attempt (trace 966613e4..., 1,080 complete rows). It INHERITS the arm's prepared supply pin;
# core.preparation.artifact_inputs binds the cell and attempt identities (and runtime.py's whole-file hash, which the
# seal fix changed), so repin_cell.py rebuilds it into the next phase-supply-v<N>.json under the same run id and
# ASSERTS the output equals eab5c61e... No ALLOW_OUTPUT_CHANGE, ever.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate. The cli check must
# report the resume receipt with seal_only true (kept 1,080, flown 0).
export RD=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1
export CELL=slurp-native-stage3-relisten-fold-a-v1-resume
export EXP=slurp-native-stage3-relisten-fold-a-v1-resume
export PKG=slurp-stage3-relisten-fold-a-v1
export PREREG=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-relisten-fold-a-v1/root-admission-sealonly-v1.json
export DEC_ID=slurp-stage3-relisten-fold-a-sealonly-admission-v1
export TAG=e4-sealonly ARM=1
export MSG=/home/chao/e4-sealonly-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
