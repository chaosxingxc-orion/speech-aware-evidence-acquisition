#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip cell E4-1 (dry run, then arm) to ready on master: model-free, in LOOP FORM -- one convergence loop
# over both cycles, re-run until one whole pass commits nothing (a later flip rewrites shared files such as
# the exposure ledger after an earlier cycle reported "satisfied"), and only then is HEAD recorded as the
# E4-1 flight commit. Root runs this ONLY after:
#   1. countersigning E4-1's four DRAFT flight rows (SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-V1 and its -FIT-V1); the READ row
#      SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1 stays a draft until the seal and is countersigned
#      before any column score is opened;
#   2. minting coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-relisten-fold-a-admission-v1, four eligible run ids) with scripts/flights/e4/e4_mint_receipt.py;
#   3. merging the E4 engineering branch (the outputs.jsonl relisten persistence and the
#      scripts/analysis/stage3_rollout_score.py --mode relisten wiring) into master.
# --allow-output-change must never be passed: the flip mints each cell's own first-phase supply (item E16);
# the arm's minted digest must be the AGREE arm's (eab5c61e...).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
WS=$MAIN/scripts/flights/e4
RD=docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-stage3-relisten-fold-a-v1/root-admission-v1.json" ]; then
  echo "refusing: the E4-1 decision receipt is not minted (scripts/flights/e4/e4_mint_receipt.py)"; exit 6
fi
msg() {  # $1 file, $2 subject
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' "$2" > "$1"
}
for K in smoke arm; do
  msg "/home/chao/e4-$K-commit.txt" "research: flip E4-1 ($K) to ready (owner decision 185, the core-native targeted re-listen: the retained AGREE arm under the 17-ceiling relisten program with a post-accept blind + forced-choice relisten stage in shadow, read as two shadow columns against the same flight's delivered column, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-relisten-fold-a-admission-v1)"
done
CYCLES=(
  "$WS/e4_repin_smoke.sh $RD slurp-native-stage3-relisten-fold-a-smoke-4-v1 smoke-generation /home/chao/e4-smoke-commit.txt"
  "$WS/e4_repin_arm.sh $RD slurp-native-stage3-relisten-fold-a-v1 generation /home/chao/e4-arm-commit.txt"
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
echo "$CONVERGED" > /home/chao/e4-flight-commit.txt
echo "flight commit $CONVERGED (E4-1 dry run and arm ready at it)"
