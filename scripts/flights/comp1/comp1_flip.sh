#!/bin/bash
# Flip the COMP-1 family (smoke, in-chain A/A, arm) to ready on master: model-free, three cells in three
# cycles converging at ONE HEAD, which becomes the flight commit. Root runs this ONLY after:
#   1. the coordinator has replaced the arm's expected_effect_pp placeholder with the number composed
#      from the AGREE and KPROBE reads in BOTH places (registered-facts-v1.json and the preregistration
#      fence; owner decisions 139 and 152) and scripts/checks/stage3_effect_floor_check.py passes;
#   2. the seven DRAFT exposure rows are countersigned;
#   3. coordination/slurp-stage3-comp1-fold-a-v1/root-admission-v1.json is minted with the six eligible
#      run ids (scripts/flights/comp1/comp1_mint_receipt.py refuses while the placeholder stands).
# --allow-output-change must never be passed: no cell carries a committed pin; the flip re-mints each
# cell's own supply (item E16) and keeps the agreement-table requirement beside it. The A/A's re-minted
# supply must again carry output digest ba5e1faa...
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs each cycle until the
# package converges at one HEAD. Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
if grep -q "TO-BE-DECLARED-BY-COORDINATOR-FROM-AGREE-AND-KPROBE-READS" "$MAIN/$RD/registered-facts-v1.json" "$MAIN/$RD-preregistration.md"; then
  echo "refusing to flip: the arm's expected_effect_pp is still the placeholder (owner decisions 139 and 152)"; exit 6
fi
for K in smoke aa arm; do
cat > /home/chao/comp1-$K-commit.txt <<M
research: flip COMP-1 ($K) to ready (the first composed Stage-3 arm, owner decisions 138 and 152: the locked PLAN plan + the agreement term as AGREE carries it (w_agree 1.0, k 60, fuse 8-1-8) + the centroid boundary key as KPROBE pins it + the citation contract saea-solver-cited-answer-v1 with the unwrapping normaliser, with its in-chain A/A (the lock's own bytes, prepared output digest ba5e1faa) and its four-row smoke; intent primary, official SLU-F1 the guard (decision 133); expected_effect_pp declared by the coordinator from the AGREE and KPROBE reads (decision 139); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/comp1_repin_smoke.sh $RD slurp-native-stage3-comp1-fold-a-smoke-4-v1 smoke-generation /home/chao/comp1-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1_repin_aa.sh    $RD slurp-native-stage3-comp1-aa-fold-a-v1      aa-generation    /home/chao/comp1-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1_repin_arm.sh   $RD slurp-native-stage3-comp1-fold-a-v1         generation       /home/chao/comp1-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/comp1-flight-commit.txt
echo "flight commit $(cat /home/chao/comp1-flight-commit.txt)"
