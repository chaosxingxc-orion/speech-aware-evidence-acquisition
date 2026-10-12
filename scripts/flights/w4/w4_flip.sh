#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip cell W4 (smoke, then arm) to ready on master: model-free, two cells in two cycles converging
# at ONE HEAD, which becomes the W4 flight commit. Root runs this ONLY after:
#   1. the coordinator has registered the knowledge wave's shared in-chain A/A
#      SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 (W4's replicate_run_id) and the wave's campaign plan;
#   2. countersigning W4's four DRAFT flight rows (SAEA-SLURP-STAGE3-W4-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1 and its -FIT-V1) and the two model-free rows
#      (SAEA-SLURP-SLOT-CONVENTIONS-W4-PREPARE-V1, SAEA-SLURP-W4-FOLD-A-OFFLINE-ESTIMATE-V1); the READ
#      row SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1 stays a draft until the seal;
#   3. minting coordination/slurp-stage3-w4-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-w4-fold-a-admission-v1, four eligible run ids) with scripts/flights/w4/w4_mint_receipt.py.
# --allow-output-change must never be passed: the flip mints each cell's own supply (item E16) and
# the slot store is not an input to it, so the minted digests must be the AGREE arm's / smoke's
# (eab5c61e... / 308601c5...). Sibling flips move this package's hashes: repin_loop_generic.sh
# re-runs each cycle until it converges; re-run once more and require zero "committed" lines.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SP=$MAIN/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1
if [ ! -f $SAEA_DATA_ROOT/coordination/slurp-stage3-w4-fold-a-v1/root-admission-v1.json ]; then
  echo "refusing: the W4 decision receipt is not minted (scripts/flights/w4/w4_mint_receipt.py)"; exit 6
fi
if ! grep -rqs "SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1" "$MAIN/configs/experiment/"; then
  echo "refusing: the shared in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 is not registered yet"; exit 7
fi
W4=$(dirname "$0")
for K in smoke arm; do
  {
    echo "research: flip W4 ($K) to ready (knowledge-wave item W4, slot conventions: the retained AGREE arm with knowledge_stores.slot-contracts re-pinned to slot-contracts-w4-v1 -- TRAIN-mined value vocabulary, annotation scope and span-extent conventions appended to 19 existing slot-contract cards -- read on no harm, SLU-F1 primary and intent the guard, at the shared in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1; owner decision 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w4-fold-a-admission-v1)"
    echo
    echo "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
  } > /home/chao/w4-$K-commit.txt
done
bash "$SP/repin_loop_generic.sh" "$W4/w4_repin_smoke.sh" $RD slurp-native-stage3-w4-fold-a-smoke-4-v1 smoke-generation /home/chao/w4-smoke-commit.txt || exit $?
bash "$SP/repin_loop_generic.sh" "$W4/w4_repin_arm.sh"   $RD slurp-native-stage3-w4-fold-a-v1         generation       /home/chao/w4-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/w4-flight-commit.txt
echo "flight commit $(cat /home/chao/w4-flight-commit.txt)"
