#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip cell W4-SV (smoke, then arm) to ready on master in LOOP FORM: one convergence loop over both cycles,
# re-run until one whole pass commits nothing (a later flip rewrites shared files such as the exposure ledger
# and the package's protocol document after an earlier cycle reported "satisfied"), bound 4 passes; only then
# is HEAD recorded as the W4-SV flight commit in /home/chao/w4sv-flight-commit.txt (the W-SV-1 queue reads it).
# Supersedes the one-shot scripts/flights/w4sv/w4sv_flip.sh, whose two cycles ran once each with no
# convergence pass. Preconditions are the same as that script's:
#   0. the committed arm-A proof reads arm_b_verdict ARM-B-VARIES (arm b-w4 varies, arm A matches AGREE);
#   1. the four DRAFT flight rows and the two model-free rows are countersigned; the READ row
#      SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1 stays a draft until the seal;
#   2. coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json is minted (w4sv_mint_receipt.py).
# --allow-output-change must never be passed: the minted digests must be the AGREE arm's / smoke's
# (eab5c61e... / 308601c5...). Untracked files count as dirt. Model-free; spawns core.flight.cli, so run it only
# while a flying driver is mid-step (never between chain steps).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
WS=$MAIN/scripts/flights/w4sv
PY=/home/chao/.venvs/speechrl/bin/python
RD=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json" ]; then
  echo "refusing: the W4-SV decision receipt is not minted (scripts/flights/w4sv/w4sv_mint_receipt.py)"; exit 6
fi
VERDICT=$($PY -c "import json;d=json.load(open('$MAIN/$RD/arm-a-byte-identity-proof-v1.json'));print(d.get('arm_b_verdict'),d.get('verdict'))") || exit 8
case "$VERDICT" in
  "ARM-B-VARIES IDENTICAL"|"ARM-B-VARIES IDENTICAL-MODULO-PROGRAM-FIELDS") ;;
  *) echo "refusing: the committed arm-A proof reads [$VERDICT]; arm b-w4 must vary and arm A must match AGREE"; exit 7 ;;
esac
msg() {  # $1 file, $2 subject
  printf '%s\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n' "$2" > "$1"
}
for K in smoke arm; do
  msg "/home/chao/w4sv-$K-commit.txt" "research: flip W4-SV ($K) to ready (the W4 slot conventions as a same-flight supply-variant cell, owner decision 172: the retained AGREE arm with three first-visit Solver arms -- b-w4 release swap to slot-contracts-w4-v1, t-twin replicate of a-agree, a-agree delivering -- read as first-visit columns b-w4 vs a-agree against the twin null, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w4sv-fold-a-admission-v1)"
done
CYCLES=(
  "$WS/w4sv_repin_smoke.sh $RD slurp-native-stage3-w4sv-fold-a-smoke-4-v1 smoke-generation /home/chao/w4sv-smoke-commit.txt"
  "$WS/w4sv_repin_arm.sh $RD slurp-native-stage3-w4sv-fold-a-v1 generation /home/chao/w4sv-arm-commit.txt"
)
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash "$SP/repin_loop_generic.sh" $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/w4sv-flight-commit.txt
echo "flight commit $CONVERGED (W4-SV smoke and arm ready at it)"
