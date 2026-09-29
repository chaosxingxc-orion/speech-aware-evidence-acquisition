#!/bin/bash
# COMP-1 SEAL-ONLY completion flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# The seal-only cell (owner decision 189 option A) is the resume cell under the arm's SAME run id with the new
# attempt attempt-slurp-native-stage3-comp1-fold-a-generation-v1-seal-only and a resume_from LIST (the original
# aborted attempt + resume attempt 3). It INHERITS the arm's prepared supply pin; core.preparation.artifact_inputs
# binds the cell and attempt identities (and runtime.py's whole-file hash, which fable/sealonly changed), so
# repin_cell.py rebuilds it into the next phase-supply-v<N>.json under the same run id and ASSERTS the output equals
# ce68bebc... No ALLOW_OUTPUT_CHANGE, ever: a moved output means the knowledge channel moved.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate. The cli check must
# report the resume receipt with seal_only true (counts: kept 1,080, flown 0).
export RD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1
export CELL=slurp-native-stage3-comp1-fold-a-v1-resume
export EXP=slurp-native-stage3-comp1-fold-a-v1-resume
export PKG=slurp-stage3-comp1-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-sealonly-v1.json
export DEC_ID=slurp-stage3-comp1-fold-a-sealonly-admission-v1
export TAG=comp1-sealonly ARM=1
export MSG=/home/chao/comp1-sealonly-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
