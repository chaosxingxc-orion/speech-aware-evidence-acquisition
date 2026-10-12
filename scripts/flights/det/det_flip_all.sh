#!/bin/bash
# Flip cell DET (pass A, then pass B) to ready on master: model-free, two cells in two re-pin
# cycles. Root runs this AFTER:
#   1. minting coordination/slurp-stage3-det-np1-fold-a-50-v1/root-admission-v1.json (decision id
#      slurp-stage3-det-np1-fold-a-50-admission-v1) with the FOUR eligible run ids
#      SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1, -A-FIT-V1, -B-V1, -B-FIT-V1 and this cell's caps
#      (scripts/flights/det/det_mint_receipt.py copies the package's draft, sets status decided,
#      stamps the time and re-hashes every antecedent path); without the four ids
#      core.flight.campaign.declared_readiness refuses ("run ... is not eligible in decision receipt");
#   2. countersigning the five DRAFT exposure rows (A, A-FIT, B, B-FIT, READ).
# The two FIT cells are NOT flipped: they are spend identities, never flown as generation cells.
#
# ORDER MATTERS. Pass A flips before pass B because B is A's request-identical second pass: its
# prepared first-phase supply MUST reproduce A's byte for byte, and the check is only meaningful
# once A's is minted. A different value means the pair is not a pair -- stop and report, never
# pass --allow-output-change. Sibling flips invalidate each other's pinned hashes:
# repin_loop_generic.sh re-runs each cycle until the package converges at one HEAD. Untracked
# files count as dirt for core.flight.cli check; the tree must be clean of them before this runs.
#
# The flip does not need the DET serving session: core.flight.cli check attaches to nothing.
# The resident np4 session is swapped at LAUNCH time (batch_chain_det.sh's preconditions).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-det-np1-fold-a-50-v1
for K in a b; do
cat > /home/chao/det-$K-commit.txt <<M
research: flip cell DET pass $K to ready (owner decision 140: the single-slot, prompt-cache-off determinism probe -- the locked v2.0 plan, byte-identical, flown twice in one chain on the first 50 TRAIN Fold A rows at np1 x 24,576 with --no-cache-prompt, reading per-row byte identity of the delivered answer between the passes and contacts per minute / prompt tokens per second beside ROLL-2's np4 numbers; form-proof, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-det-np1-fold-a-50-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
DET=$(dirname "$0")
bash $SP/repin_loop_generic.sh $DET/det_repin_a.sh $RD slurp-native-stage3-det-np1-fold-a-50-a-v1 a-generation /home/chao/det-a-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $DET/det_repin_b.sh $RD slurp-native-stage3-det-np1-fold-a-50-b-v1 b-generation /home/chao/det-b-commit.txt || exit $?
cp /home/chao/det-b-flight-commit.txt /home/chao/det-flight-commit.txt
echo "flight commit $(cat /home/chao/det-flight-commit.txt)"
