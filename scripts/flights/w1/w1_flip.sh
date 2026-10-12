#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the W1 family (smoke, arm) to ready on master: model-free, two cells in the per-cell
# repin_loop_generic.sh form, converged at ONE HEAD, which becomes the flight commit.
# Root runs this ONLY after:
#   1. the branch fable/w1 is merged to master;
#   2. countersigning the six DRAFT rows SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1 and its -FIT-V1, SAEA-SLURP-INTENT-SLOT-LEGALITY-POOL-V1
#      and SAEA-SLURP-W1-CARD-SELECTION-MEASUREMENT-V1 (the READ row
#      SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1 stays DRAFT until the seal);
#   3. minting coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-w1-cardsel-fold-a-admission-v1, FOUR eligible run ids) with
#      scripts/flights/w1/w1_mint_receipt.py;
#   4. registering the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 (the coordinator's own
#      cell and receipt): the W1 arm never flies without it in the same chain.
# --allow-output-change must never be passed. Untracked files count as dirt for core.flight.cli check.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
W1=$MAIN/scripts/flights/w1
RD=docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1
cd "$MAIN" || exit 1
[ -f "$DATA/coordination/slurp-stage3-w1-cardsel-fold-a-v1/root-admission-v1.json" ] || { echo "refusing: the W1 receipt is not minted (scripts/flights/w1/w1_mint_receipt.py)"; exit 6; }
grep -q "| SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 |" docs/exposure-ledger.md || { echo "refusing: the shared in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 is not registered"; exit 6; }
for K in smoke arm; do
cat > /home/chao/w1-$K-commit.txt <<M
research: flip W1 ($K) to ready (knowledge wave item W1, slot-card selection -- the retained AGREE arm with the slot-contract card route narrowed by the pinned intent -> slot-type legality table, 286 of the 402 authored bindings, those the released exemplar store carries in at least two utterances -- read on no harm at the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1; owner decisions 127, 161 and 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w1-cardsel-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CYCLES=(
  "$W1/w1_repin_smoke.sh $RD slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1 smoke-generation /home/chao/w1-smoke-commit.txt"
  "$W1/w1_repin_arm.sh $RD slurp-native-stage3-w1-cardsel-fold-a-v1 generation /home/chao/w1-arm-commit.txt"
)
CONVERGED=""
for pass in 1 2 3; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash $SP/repin_loop_generic.sh $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after three passes"; exit 5; }
echo "$CONVERGED" > /home/chao/w1-flight-commit.txt
echo "flight commit $CONVERGED (W1 smoke and arm ready at it)"
