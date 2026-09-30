#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for ONE P-SV cell. Model-free.
# The caller exports PSV_CELL (psv1 | psv2 | psv3 | psv4) and PSV_KIND (arm | smoke); repin_loop_generic.sh runs this
# script with no arguments on every pass, so the cell is named by the environment it inherits.
# No ALLOW_OUTPUT_CHANGE: a P-SV cell carries NO committed prepared_phase_supply, so the re-pin tool MINTS the
# cell's own first-phase supply under its own run id (item E16) beside the Fold B agreement-table requirement.
# There is no earlier digest to reproduce (the first Fold B supply at w_agree 1.0 over the whole roster); a
# CHANGED output on a later re-pin means the knowledge channel moved -- stop and report.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
case "${PSV_CELL:-}" in psv1|psv2|psv3|psv4) ;; *) echo "PSV_CELL must be psv1, psv2, psv3 or psv4" >&2; exit 2;; esac
case "$PSV_CELL" in psv4) PKG_DATE=2026-09-30 ;; *) PKG_DATE=2026-09-29 ;; esac
BASE=$PSV_CELL-fold-b
export RD=docs/readiness/$PKG_DATE-slurp-stage3-$BASE-v1
export PKG=slurp-stage3-$BASE-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-stage3-$BASE-admission-v1
case "${PSV_KIND:-}" in
  arm)   export CELL=slurp-native-stage3-$BASE-v1 TAG=$PSV_CELL-arm ;;
  smoke) export CELL=slurp-native-stage3-$BASE-smoke-4-v1 TAG=$PSV_CELL-smoke ;;
  *) echo "PSV_KIND must be arm or smoke" >&2; exit 2;;
esac
export EXP=$CELL ARM=0
export MSG=/home/chao/$PSV_CELL-$PSV_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
