#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the NX R1 cell. Model-free.
# The caller exports NX_KIND (arm | smoke) and, for iteration 2, NX_ITER=2 (default 1); repin_loop_generic.sh runs this script
# with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: the cell carries NO committed prepared_phase_supply, so the re-pin tool MINTS the cell's own
# first-phase supply under its own run id (item E16) beside the Fold B agreement-table requirement. There is no earlier
# digest to reproduce (the first Fold B supply at w_agree 1.0 with the centroid key); a CHANGED output on a later re-pin
# means the knowledge channel moved -- stop and report.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
case "${NX_ITER:-1}" in
  1) SLUG=nx-r1-solver-fold-b; SHORT=nxr1 ;;
  2) SLUG=nx-r1-i2-solver-fold-b; SHORT=nxr1i2 ;;
  *) echo "NX_ITER must be 1 or 2" >&2; exit 2 ;;
esac
export RD=docs/readiness/2026-10-09-slurp-$SLUG-v1
export PKG=slurp-$SLUG-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-$SLUG-admission-v1
case "${NX_KIND:-}" in
  arm)   export CELL=slurp-native-stage3-$SLUG-v1 TAG=$SHORT-arm ;;
  smoke) export CELL=slurp-native-stage3-$SLUG-smoke-4-v1 TAG=$SHORT-smoke ;;
  *) echo "NX_KIND must be arm or smoke" >&2; exit 2;;
esac
export EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$NX_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
