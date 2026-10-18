#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for the carrier base on the Thinking core. Model-free.
# The caller exports CARRIERTHINK_KEY (<carrier>-<smoke|alloff|direct>); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: --allow-output-change must never be passed. The program declares no supplied first phase, so the re-pin creates no prepared artifact.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SHORT=carrierthink
export RD=docs/readiness/2026-10-18-carrier-base-thinking-v1
export PKG=carrier-base-thinking-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=carrier-base-thinking-admission-v1
case "${CARRIERTHINK_KEY:-}" in
  a2t-smoke) export CELL=carrier-think-base-a2t-smoke-4-v1 ;;
  a2t-alloff) export CELL=carrier-think-base-a2t-alloff-v1 ;;
  a2t-direct) export CELL=carrier-think-base-a2t-direct-v1 ;;
  e21-smoke) export CELL=carrier-think-base-e21-smoke-4-v1 ;;
  e21-alloff) export CELL=carrier-think-base-e21-alloff-v1 ;;
  e21-direct) export CELL=carrier-think-base-e21-direct-v1 ;;
  e22-smoke) export CELL=carrier-think-base-e22-smoke-4-v1 ;;
  e22-alloff) export CELL=carrier-think-base-e22-alloff-v1 ;;
  e22-direct) export CELL=carrier-think-base-e22-direct-v1 ;;
  *) echo "CARRIERTHINK_KEY must be <a2t|e21|e22>-<smoke|alloff|direct>" >&2; exit 2;;
esac
export TAG=$SHORT-$CARRIERTHINK_KEY EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$CARRIERTHINK_KEY-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
