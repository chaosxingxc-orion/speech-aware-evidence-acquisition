#!/bin/bash
# Flip the AGREE family (smoke, in-chain A/A, treatment arm) to ready on master: model-free, three cells in
# three cycles converging at ONE HEAD, which becomes the flight commit. Root runs this ONLY after (1) the
# owner's disposition on the CONV probe's m (decision 139: no pre-committed if-then), (2) the arm's
# expected_effect_pp is re-declared from that m in registered-facts-v1.json and the preregistration fence,
# and (3) the re-pin tool's preparation-requirement fix is on master (it is, since f7eed5ad). The receipt
# coordination/slurp-stage3-agree-w1-fold-a-v1/root-admission-v1.json is already minted with six eligible
# run ids. --allow-output-change must never be passed: no cell carries a committed pin; the flip mints each
# cell's own supply (item E16) and now keeps the agreement-table requirement beside it.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1
for K in smoke aa arm; do
cat > /home/chao/agree-$K-commit.txt <<M
research: flip AGREE ($K) to ready (the intent-boundary agreement term -- w_agree 1.0 over the self-excluded exemplar-intent vote, k 60 recall, fuse_coverage 8-1-8 -- with its in-chain A/A at w_agree 0.0 and its four-row smoke; owner decisions 133 (intent primary), 134 (probe first), 137 (absolute target), 139 (disposition taken on the measured m); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-agree-w1-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/agree_repin_smoke.sh $RD slurp-native-stage3-agree-w1-fold-a-smoke-4-v1 smoke-generation /home/chao/agree-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/agree_repin_aa.sh    $RD slurp-native-stage3-agree-aa-fold-a-v1       aa-generation    /home/chao/agree-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $SP/agree_repin_arm.sh   $RD slurp-native-stage3-agree-w1-fold-a-v1       generation       /home/chao/agree-arm-commit.txt   || exit $?
cd ${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition} && git rev-parse HEAD > /home/chao/agree-flight-commit.txt
echo "flight commit $(cat /home/chao/agree-flight-commit.txt)"
