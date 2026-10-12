#!/bin/bash
# Flip the G5 family (smoke, in-chain A/A, treatment arm) to ready on master: model-free, three
# cells in three cycles converging at ONE HEAD, which becomes the flight commit. Root runs this
# ONLY after:
#   1. countersigning the seven DRAFT exposure rows (SAEA-SLURP-STAGE3-G5-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-G5-AA-FOLD-A-V1 and its -FIT-V1, SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1 and
#      its -FIT-V1, and the model-free measurement row
#      SAEA-SLURP-G5-REVIEWER-INSTRUCTION-TOKEN-MEASUREMENT-V1);
#   2. minting coordination/slurp-stage3-g5-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-g5-fold-a-admission-v1) with scripts/flights/g5/g5_mint_receipt.py, which copies
#      the package's draft with its SIX eligible run ids and this family's caps, sets status decided,
#      stamps the time and re-hashes every antecedent path. Without all six ids
#      core.flight.campaign.declared_readiness refuses ("run ... is not eligible in decision receipt");
#   3. deciding whether round 3 shares ONE A/A across its consumption-form items: if so, drop the G5
#      A/A from configs/campaign/slurp-native-stage3-g5-fold-a-v1.json, re-point the arm's
#      replicate_run_id in the package and the preregistration fence, and skip the aa cycle below.
# --allow-output-change must never be passed: no cell carries a committed pin; the flip mints each
# cell's own supply (item E16), and every minted supply must reproduce the sealed PLAN output digest
# ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f (the Reviewer instruction is not
# an input to the first-phase supply). Sibling flips on master move this package's hashes:
# repin_loop_generic.sh re-runs each cycle until the package converges at one HEAD; then re-run every
# cycle once more and require "satisfied at <the same HEAD>" with zero "committed" lines. Untracked
# files count as dirt for core.flight.cli check.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1
# Owner decision 160 (2026-09-27): G5 is read at the SHARED in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1,
# its own A/A pair is superseded unflown and its campaign plan carries the arm alone. In that mode this
# script must not run: the family flips ONLY through scripts/flights/comp1/comp1_g5_flip.sh.
if ! grep -q "slurp-native-stage3-g5-aa-fold-a-v1" ${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/configs/campaign/slurp-native-stage3-g5-fold-a-v1.json; then
  echo "refusing (owner decision 160): the G5 campaign plan carries the arm alone -- use scripts/flights/comp1/comp1_g5_flip.sh"; exit 6
fi
G5=$(dirname "$0")
for K in smoke aa arm; do
cat > /home/chao/g5-$K-commit.txt <<M
research: flip G5 ($K) to ready (the Reviewer-instruction repair -- the two sentences ordering the task-contract tool retired as item E25 deleted from the Reviewer instruction, nothing added, -52 prompt tokens per Reviewer contact -- with its in-chain A/A on the OLD instruction and its four-row smoke; owner decisions 127 (no-harm admission), 135 (deferral discharged by the AGREE read), 138 (folded into the next composed round) and 153 (round 3); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-g5-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $G5/g5_repin_smoke.sh $RD slurp-native-stage3-g5-fold-a-smoke-4-v1 smoke-generation /home/chao/g5-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $G5/g5_repin_aa.sh    $RD slurp-native-stage3-g5-aa-fold-a-v1       aa-generation    /home/chao/g5-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $G5/g5_repin_arm.sh   $RD slurp-native-stage3-g5-fold-a-v1          generation       /home/chao/g5-arm-commit.txt   || exit $?
cd ${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition} && git rev-parse HEAD > /home/chao/g5-flight-commit.txt
echo "flight commit $(cat /home/chao/g5-flight-commit.txt)"
