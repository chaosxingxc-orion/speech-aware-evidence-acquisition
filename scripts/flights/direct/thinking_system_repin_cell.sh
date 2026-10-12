#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the 268-B read (the locked system on the Thinking core). Model-free.
# The caller exports TSYS_KIND (smoke | lock | aa); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: --allow-output-change must never be passed. The re-pin mints each cell's own first-phase supply (item E16).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SLUG=thinking-system-fold-b
SHORT=tsys
export RD=docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1
export PKG=slurp-system-thinking-core-fold-b-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-system-thinking-core-fold-b-admission-v1
case "${TSYS_KIND:-}" in
  smoke) export CELL=slurp-native-stage3-$SLUG-smoke-4-v1 ;;
  lock)  export CELL=slurp-native-stage3-$SLUG-lock-v1 ;;
  aa)    export CELL=slurp-native-stage3-$SLUG-aa-v1 ;;
  *) echo "TSYS_KIND must be smoke, lock or aa" >&2; exit 2;;
esac
export TAG=$SHORT-$TSYS_KIND EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$TSYS_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
