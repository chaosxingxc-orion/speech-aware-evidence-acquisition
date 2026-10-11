#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the 266-E bare-core read. Model-free.
# The caller exports DIRECT_KIND (smoke | thinking | instruct | replicate); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: the direct-only program declares no supplied first phase (item E38), so the re-pin creates no prepared artifact and no
# preparation requirement; --allow-output-change must never be passed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SLUG=direct-only-fold-b-thinking-vs-instruct
SHORT=direct-fb
export RD=docs/readiness/2026-10-11-slurp-$SLUG-v1
export PKG=slurp-$SLUG-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-$SLUG-admission-v1
case "${DIRECT_KIND:-}" in
  smoke)     export CELL=slurp-direct-only-fold-b-thinking-smoke-4-v1 ;;
  thinking)  export CELL=slurp-direct-only-fold-b-thinking-v1 ;;
  instruct)  export CELL=slurp-direct-only-fold-b-instruct-v1 ;;
  replicate) export CELL=slurp-direct-only-fold-b-instruct-replicate-v1 ;;
  *) echo "DIRECT_KIND must be smoke, thinking, instruct or replicate" >&2; exit 2;;
esac
export TAG=$SHORT-$DIRECT_KIND EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$DIRECT_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
