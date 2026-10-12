#!/bin/bash
# Flip cell ROLL-AA and its four-row smoke to ready on master: model-free, two cells in two cycles
# (generation smoke, then the arm). Root runs this AFTER minting
# coordination/slurp-stage3-roll-aa-v1/root-admission-v1.json (decision id
# slurp-stage3-roll-aa-admission-v1) with THIS family's FOUR eligible run ids --
# SAEA-SLURP-STAGE3-ROLL-AA-V1, -FIT-V1, -SMOKE-4-V1, -SMOKE-4-FIT-V1 -- and this family's budget
# caps. Without that, core.flight.campaign.declared_readiness refuses the smoke
# ("run ... is not eligible in decision receipt").
#
# The two FIT cells (SAEA-SLURP-STAGE3-ROLL-AA-FIT-V1 and -SMOKE-4-FIT-V1) are NOT flipped: they
# are spend identities, never flown as generation cells.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-24-slurp-stage3-roll-aa-v1
for K in smoke arm; do
cat > /home/chao/rollaa-$K-commit.txt <<M
research: flip cell ROLL-AA ($K) to ready (board route F2, the Stage-3 within-flight A/A null: the locked v2.0 plan's Solver answering the identical prompt twice per row, greedy, on 200 R01C construction rows, so the program learns the within-flight paired noise floor h_within that the ROLL-2 variant rollouts are read against; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-roll-aa-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/rollaa_repin_smoke.sh $RD slurp-native-stage3-roll-aa-smoke-4-v1 smoke-generation /home/chao/rollaa-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/rollaa_repin_arm.sh $RD slurp-native-stage3-roll-aa-v1 generation /home/chao/rollaa-arm-commit.txt || exit $?
cp /home/chao/rollaa-arm-flight-commit.txt /home/chao/rollaa-flight-commit.txt
echo "flight commit $(cat /home/chao/rollaa-flight-commit.txt)"
