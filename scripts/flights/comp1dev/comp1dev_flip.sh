#!/bin/bash
# Flip the COMP-1 DEV-2000-ADDED family (smoke, in-chain A/A, arm) to ready on master: model-free, three cells in three
# cycles converging at ONE HEAD, which becomes the flight commit. Root runs this ONLY after:
#   1. the coordinator has replaced the arm's expected_effect_pp placeholder with the number declared from the COMP-1
#      Fold A read in BOTH places (registered-facts-v1.json and the preregistration fence; owner decision 139) and
#      scripts/checks/stage3_effect_floor_check.py passes;
#   2. the eight DRAFT exposure rows are countersigned (the six flight/FIT rows, the agreement-table row, the READ row);
#   3. coordination/slurp-stage3-comp1-dev2000-added-v1/root-admission-v1.json is minted with the six eligible run ids
#      (scripts/flights/comp1dev/comp1dev_mint_receipt.py refuses while the placeholder stands).
# --allow-output-change must never be passed: no cell carries a committed pin; the flip re-mints each cell's own supply
# (item E16) and keeps this roster's agreement-table requirement beside it. The A/A's re-minted supply must again carry
# output digest d57ee9d6... (the sealed DEV plan arm's).
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs each cycle until the package
# converges at one HEAD (loop form). Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
if grep -q "TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ" "$MAIN/$RD/registered-facts-v1.json" "$MAIN/$RD-preregistration.md"; then
  echo "refusing to flip: the arm's expected_effect_pp is still the placeholder (owner decision 139)"; exit 6
fi
for K in smoke aa arm; do
cat > /home/chao/comp1dev-$K-commit.txt <<M
research: flip COMP-1 DEV-2000-ADDED ($K) to ready (the fresh-roster replication of the first composed Stage-3 arm, owner decision 161: the sealed DEV plan arm + the agreement term as AGREE carries it (w_agree 1.0, k 60, fuse 8-1-8; this roster's table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + the centroid boundary key as KPROBE pins it + the citation contract saea-solver-cited-answer-v1 with the unwrapping normaliser, with its in-chain A/A (the DEV plan arm's own bytes, prepared output digest d57ee9d6) and its four-row smoke; intent primary, official SLU-F1 (slurp-slu-official) the guard; expected_effect_pp declared by the coordinator from the COMP-1 Fold A read (decision 139); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-dev2000-added-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/comp1dev_repin_smoke.sh $RD slurp-native-stage3-comp1-dev2000-added-smoke-4-v1 smoke-generation /home/chao/comp1dev-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1dev_repin_aa.sh    $RD slurp-native-stage3-comp1-aa-dev2000-added-v1      aa-generation    /home/chao/comp1dev-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1dev_repin_arm.sh   $RD slurp-native-stage3-comp1-dev2000-added-v1         generation       /home/chao/comp1dev-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/comp1dev-flight-commit.txt
echo "flight commit $(cat /home/chao/comp1dev-flight-commit.txt)"
