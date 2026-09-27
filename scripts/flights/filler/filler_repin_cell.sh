#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for ONE filler cell. Model-free.
# The caller exports FILLER_CHUNK (1..99) and FILLER_KIND (arm | smoke); repin_loop_generic.sh runs this
# script with no arguments on every pass, so the cell is named by the environment it inherits.
# No ALLOW_OUTPUT_CHANGE: a filler cell carries NO committed prepared_phase_supply, so
# core.flight.repin.ensure_artifact_pinned MINTS the cell's own under its own run id (item E16) and keeps
# the agreement-table preparation requirement beside it (relpath identity, fixed 2026-09-27). A CHANGED
# output on a later re-pin means the knowledge channel moved -- stop and report.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
case "${FILLER_CHUNK:-}" in ''|*[!0-9]*) echo "FILLER_CHUNK must be a chunk number" >&2; exit 2;; esac
K2=$(printf %02d "$((10#$FILLER_CHUNK))")
BASE=filler-fold-b-c$K2
export RD=docs/readiness/2026-09-27-slurp-stage3-$BASE-v1
export PKG=slurp-stage3-$BASE-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-stage3-$BASE-admission-v1
case "${FILLER_KIND:-}" in
  arm)   export CELL=slurp-native-stage3-$BASE-v1 TAG=filler-c$K2-arm ARM=1 ;;
  smoke) export CELL=slurp-native-stage3-$BASE-smoke-4-v1 TAG=filler-c$K2-smoke ARM=0 ;;
  *) echo "FILLER_KIND must be arm or smoke" >&2; exit 2;;
esac
export EXP=$CELL
export MSG=/home/chao/filler-c$K2-$FILLER_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
