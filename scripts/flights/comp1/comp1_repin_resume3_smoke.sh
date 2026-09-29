#!/bin/bash
# COMP-1 RESUME ATTEMPT 3 four-row DRY RUN flip (owner decision 181): env for scripts/flights/batch/repin_cell_generic.sh.
# Model-free.
#
# The dry-run cell SAEA-SLURP-STAGE3-COMP1-FOLD-A-RESUME3-SMOKE-4-V1 carries the parent COMP-1 smoke's bytes except its
# run, attempt and FIT identities and the note. It INHERITS the parent smoke's prepared supply pin
# (prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1/phase-supply-v3.json); core.preparation.artifact_inputs binds the
# cell and attempt identities, so repin_cell.py rebuilds it into prepared/<the dry-run run id>/phase-supply-v1.json and
# ASSERTS the output equals the parent artifact's (1d55ea73...). No ALLOW_OUTPUT_CHANGE, ever.
export RD=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1
export CELL=slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1
export EXP=slurp-native-stage3-comp1-fold-a-resume3-smoke-4-v1
export PKG=slurp-stage3-comp1-fold-a-v1
export PREREG=docs/readiness/2026-09-28-slurp-stage3-comp-1-fold-a-v1-resume-v1-preregistration.md
export DEC_PATH=coordination/slurp-stage3-comp1-fold-a-v1/root-admission-resume-v3.json
export DEC_ID=slurp-stage3-comp1-fold-a-resume-admission-v1
export TAG=comp1-resume3-smoke ARM=0
export MSG=/home/chao/comp1-resume3-smoke-commit.txt
exec bash "$(dirname "$0")/../batch/repin_cell_generic.sh"
