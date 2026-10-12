#!/bin/bash
# Flip cell ROLL-1 (smoke, then the 800-row arm) to ready on master: model-free.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-22-slurp-stage3-rollout-r01-v1
for K in smoke arm; do
cat > /home/chao/roll1-$K-commit.txt <<M
research: flip cell ROLL-1 ($K) to ready (Stage-3 S3-2 grouped-Solver rollout on roster R01; owner decisions 80-83, 96, 101; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-rollout-r01-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/roll1_repin_smoke.sh $RD slurp-native-stage3-rollout-r01-smoke-4-v1 smoke-generation /home/chao/roll1-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/roll1_repin_arm.sh $RD slurp-native-stage3-rollout-r01-v1 generation /home/chao/roll1-arm-commit.txt
