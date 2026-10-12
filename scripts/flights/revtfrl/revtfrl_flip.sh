#!/bin/bash
# Flip the REV-TFRL-1 family (smoke, in-chain A/A, arm) to ready on master: model-free, three cells in
# three LOOP cycles converging at ONE HEAD, which becomes the flight commit. Root runs this ONLY after:
#   1. countersigning the eight DRAFT exposure rows (the three generation rows, their three FIT rows,
#      the model-free credit read SAEA-SLURP-STAGE3-REVIEWER-CREDIT-TABLE-V1 and the READ row
#      SAEA-SLURP-STAGE3-REVTFRL-FOLD-A-READ-V1 -- the READ row may stay a draft until the seal);
#   2. minting coordination/slurp-stage3-revtfrl-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-revtfrl-fold-a-admission-v1) with scripts/flights/revtfrl/revtfrl_mint_receipt.py.
# --allow-output-change must never be passed: no cell carries a committed pin; the flip mints each cell's
# own supply (item E16) beside the kept agreement-table requirement, and the arm's and the A/A's minted
# supplies must carry the sealed AGREE output digest
# eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae (the Reviewer instruction is not an
# input to the first-phase supply). Sibling flips on master move this package's hashes:
# repin_loop_generic.sh re-runs each cycle until the package converges; then re-run every cycle once more
# and require "satisfied at <the same HEAD>" with zero "committed" lines. Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-reviewer-tfrl-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
for K in smoke aa arm; do
cat > /home/chao/revtfrl-$K-commit.txt <<M
research: flip REV-TFRL-1 ($K) to ready (the first training-free RL optimisation of the Reviewer node, owner decision 165: the AGREE arm with the Reviewer instruction moved from G5's text to the contrastive review form selected offline over sealed TRAIN R01C trajectories, read on no harm at its in-chain A/A (AGREE with G5's Reviewer text) with the node's within-trajectory credit beside it; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-revtfrl-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
R=$(dirname "$0")
bash $SP/repin_loop_generic.sh $R/revtfrl_repin_smoke.sh $RD slurp-native-stage3-revtfrl-fold-a-smoke-4-v1 smoke-generation /home/chao/revtfrl-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $R/revtfrl_repin_aa.sh    $RD slurp-native-stage3-revtfrl-aa-fold-a-v1      aa-generation    /home/chao/revtfrl-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $R/revtfrl_repin_arm.sh   $RD slurp-native-stage3-revtfrl-fold-a-v1         generation       /home/chao/revtfrl-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/revtfrl-flight-commit.txt
echo "flight commit $(cat /home/chao/revtfrl-flight-commit.txt)"
