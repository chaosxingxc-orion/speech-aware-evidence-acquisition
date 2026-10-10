#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the SLURP test-sample SUCCESSOR-2 composed cell
# (slurp-milestone-successor2-composed-v1; owner decisions 233, 241, 250 A, 251 A). Model-free. ONE cell, NO smoke (the allowance
# lists a test-sample smoke as not authorised). repin_loop_generic.sh runs this script with no arguments on every pass.
# ARM=0: the flip wrapper records the flight commit itself, on convergence at one HEAD.
# No ALLOW_OUTPUT_CHANGE: the cell carries NO committed prepared_phase_supply, so the re-pin tool MINTS the cell's own first-phase
# supply under its own run id (item E16) beside the sample's pinned agreement table and segment vectors. A CHANGED output on a later
# re-pin means the knowledge channel moved -- stop and report; --allow-output-change must never be passed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export RD=docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1
export PKG=slurp-milestone-successor2-composed-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-milestone-successor2-admission-v1
export CELL=slurp-milestone-successor2-composed-v1 EXP=slurp-milestone-successor2-composed-v1 TAG=ms2 ARM=0
export MSG=/home/chao/ms2-arm-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
