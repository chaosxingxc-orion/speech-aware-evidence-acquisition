#!/bin/bash
# Flip cell ADV-1 (the four-row form smoke, then the 225-row arm) to ready on master: model-free.
# Root runs this AFTER minting coordination/slurp-stage3-advantage-r01-v1/root-admission-v1.json
# (decision id slurp-stage3-advantage-r01-admission-v1); see section 13 of
# docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1-preregistration.md for the mint command.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1
for K in smoke arm; do
cat > /home/chao/adv1-$K-commit.txt <<M
research: flip cell ADV-1 ($K) to ready (Stage-3 S3-4 / S3-4s SYSTEM-level semantic advantage on the 225 disagreeing ROLL-1 rows; owner decisions 82, 101, 106; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-advantage-r01-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/adv1_repin_smoke.sh $RD slurp-native-stage3-advantage-r01-smoke-4-v1 smoke-generation /home/chao/adv1-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/adv1_repin_arm.sh $RD slurp-native-stage3-advantage-r01-v1 generation /home/chao/adv1-arm-commit.txt
