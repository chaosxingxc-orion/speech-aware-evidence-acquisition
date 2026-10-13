#!/bin/bash
# Per-cell environment for scripts/flights/batch/repin_cell_generic.sh, for NX-T R1 (the per-node thinking-policy column). Model-free.
# The caller exports NXT1_KIND (smoke | arm); repin_loop_generic.sh runs this script with no arguments on every pass.
# No ALLOW_OUTPUT_CHANGE: --allow-output-change must never be passed. The re-pin mints each cell's own first-phase supply (item E16).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SLUG=nxt-r1-thinking-policy-fold-b
SHORT=nxt1
export RD=docs/readiness/2026-10-13-slurp-nxt-r1-thinking-policy-fold-b-v1
export PKG=slurp-nxt-r1-thinking-policy-fold-b-v1
export PREREG=$RD-preregistration.md
export DEC_PATH=coordination/$PKG/root-admission-v1.json
export DEC_ID=slurp-nxt-r1-thinking-policy-fold-b-admission-v1
case "${NXT1_KIND:-}" in
  smoke) export CELL=slurp-native-stage3-$SLUG-smoke-4-v1 ;;
  arm)   export CELL=slurp-native-stage3-$SLUG-v1 ;;
  *) echo "NXT1_KIND must be smoke or arm" >&2; exit 2;;
esac
export TAG=$SHORT-$NXT1_KIND EXP=$CELL ARM=0
export MSG=/home/chao/$SHORT-$NXT1_KIND-commit.txt
unset ALLOW_OUTPUT_CHANGE
exec bash "$MAIN/scripts/flights/batch/repin_cell_generic.sh"
