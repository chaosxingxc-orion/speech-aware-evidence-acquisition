#!/bin/bash
# Flip the SLOTFILL family (smoke, in-chain A/A, treatment arm) to ready on master: model-free,
# three cells in three cycles converging at ONE HEAD, which becomes the flight commit. Root runs
# this ONLY after:
#   1. countersigning the seven DRAFT exposure rows (SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1 and its
#      -FIT-V1, SAEA-SLURP-STAGE3-SLOTFILL-AA-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1 and its -FIT-V1, and the model-free proof row
#      SAEA-SLURP-SLOTFILL-MODEL-FREE-PROOF-V1);
#   2. minting coordination/slurp-stage3-slotfill-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-slotfill-fold-a-admission-v1) with
#      scripts/flights/slotfill/slotfill_mint_receipt.py, which copies the package draft with its
#      SIX eligible run ids and this family's caps, sets status decided, stamps the time and
#      re-hashes every antecedent path;
#   3. deciding whether the round shares ONE A/A across its base items: if so, drop the SLOTFILL
#      A/A from configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json, re-point the arm's
#      replicate_run_id in the package and the preregistration fence, and skip the aa cycle below.
#      The throughput read needs a same-session twin, so a shared A/A serves it only when it flies
#      in the same chain on the same session.
# --allow-output-change must never be passed: no cell carries a committed pin; the flip mints each
# cell's own supply (item E16), and every minted supply must reproduce the sealed PLAN output digest
# ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f. Sibling flips on master move this
# package's hashes: repin_loop_generic.sh re-runs each cycle until the package converges at one
# HEAD; then re-run every cycle once more and require "satisfied at <the same HEAD>" with zero
# "committed" lines. Untracked files count as dirt for core.flight.cli check.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-slotfill-fold-a-v1
SF=$(dirname "$0")
for K in smoke aa arm; do
cat > /home/chao/slotfill-$K-commit.txt <<M
research: flip SLOTFILL ($K) to ready (the dispatcher slot-fill key -- recall prefetch, role input off the shared event loop, frozen static heap; scheduling only, proven byte-identical -- with its in-chain A/A without the key and its four-row smoke; owner decisions 127 (no-harm admission), 140 (throughput first-class) and 159 (priority engineering-base item); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-slotfill-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SF/slotfill_repin_smoke.sh $RD slurp-native-stage3-slotfill-fold-a-smoke-4-v1 smoke-generation /home/chao/slotfill-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SF/slotfill_repin_aa.sh    $RD slurp-native-stage3-slotfill-aa-fold-a-v1       aa-generation    /home/chao/slotfill-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SF/slotfill_repin_arm.sh   $RD slurp-native-stage3-slotfill-fold-a-v1          generation       /home/chao/slotfill-arm-commit.txt   || exit $?
cd ${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition} && git rev-parse HEAD > /home/chao/slotfill-flight-commit.txt
echo "flight commit $(cat /home/chao/slotfill-flight-commit.txt)"
