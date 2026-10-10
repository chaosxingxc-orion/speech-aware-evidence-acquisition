#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the VER-1b cell. Model-free.
# The caller exports VER_KIND (arm | smoke); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: the cell carries NO committed prepared_phase_supply, so the re-pin tool MINTS the cell's own
# first-phase supply under its own run id (item E16) beside the Fold A agreement-table requirement. The knowledge channel is the
# COMP-1b / A2 Fold A cells' own (the Fold A supply at w_agree 1.0 with the centroid key), so the output digest is expected to equal
# theirs; a CHANGED output on a later re-pin means the knowledge channel moved -- stop and report.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SLUG=ver1b-samples-fold-a
SHORT=ver1b
export RD=docs/readiness/2026-10-10-slurp-$SLUG-v1
export PKG=slurp-$SLUG-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-$SLUG-admission-v1
case "${VER_KIND:-}" in
  arm)   export CELL=slurp-native-stage3-$SLUG-v1 TAG=$SHORT-arm ;;
  smoke) export CELL=slurp-native-stage3-$SLUG-smoke-4-v1 TAG=$SHORT-smoke ;;
  *) echo "VER_KIND must be arm or smoke" >&2; exit 2;;
esac
export EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$VER_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
