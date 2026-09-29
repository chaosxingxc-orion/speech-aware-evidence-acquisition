#!/bin/bash
# COMP-1 RESUME-RECOVERY flip: env for scripts/flights/batch/repin_cell_generic.sh. Model-free.
#
# The resume cell (owner decision 22, harness item E10) flies under the arm's SAME run id with a new attempt
# and resume_from = the aborted attempt + its trace sha256. It INHERITS the arm's prepared supply pin
# (prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1/phase-supply-v3.json); core.preparation.artifact_inputs binds the
# cell and attempt identities, so repin_cell.py rebuilds it into the next phase-supply-v<N>.json under the same
# run id and ASSERTS the output equals ce68bebc... No ALLOW_OUTPUT_CHANGE, ever: a moved output means the
# knowledge channel moved and the resume is no longer a resume -- stop and report.
# ARM=1: records the flight commit, prints the check summary and runs the results-ledger gate.
export RD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1
export CELL=slurp-native-stage3-comp1-fold-a-v1-resume
export EXP=slurp-native-stage3-comp1-fold-a-v1-resume
export PKG=slurp-stage3-comp1-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json
export DEC_ID=slurp-stage3-comp1-fold-a-resume-admission-v1
export TAG=comp1-resume ARM=1
export MSG=/home/chao/comp1-resume-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
