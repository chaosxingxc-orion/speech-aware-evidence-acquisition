#!/bin/bash
# Flip cell ROLL-2 and its four-row smoke to ready on master: model-free, two cells in two cycles
# (generation smoke, then the arm). Root runs this AFTER minting
# coordination/slurp-stage3-roll-2-fold-a-v1/root-admission-v1.json (decision id
# slurp-stage3-roll-2-fold-a-admission-v1) with THIS family's FOUR eligible run ids --
# SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-V1, -FIT-V1, -SMOKE-4-V1, -SMOKE-4-FIT-V1 -- and this family's
# budget caps (generation 20,520 / fit endpoint 82,080 / repeated speech 58,607 s / 12.0 GPU-h on
# the arm; 76 / 304 / 202 s / 1.0 on the smoke). Without that,
# core.flight.campaign.declared_readiness refuses the smoke ("run ... is not eligible in decision
# receipt").
#
# The two FIT cells (SAEA-SLURP-STAGE3-ROLL-2-FOLD-A-FIT-V1 and -SMOKE-4-FIT-V1) are NOT flipped:
# they are spend identities, never flown as generation cells.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-roll-2-fold-a-v1
for K in smoke arm; do
cat > /home/chao/roll2-$K-commit.txt <<M
research: flip cell ROLL-2 ($K) to ready (the Stage-3 sealed-sample-pool asset on the v2.0 lock roster: cell ROLL-1's grouped-Solver form at samples 5 / temperature 0.7 / min_support 3, re-pointed onto TRAIN Fold A's 1,080 rows so the program gains the sealed five-sample pool it has on R01C and lacks where the lock lives, making selection, commit, verification, projection and re-ranking policies readable offline at about 0.51 pp at zero GPU cost; DESCRIPTIVE, no comparator and no admission claim; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-roll-2-fold-a-admission-v1)

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/roll2_repin_smoke.sh $RD slurp-native-stage3-roll-2-fold-a-smoke-4-v1 smoke-generation /home/chao/roll2-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/roll2_repin_arm.sh $RD slurp-native-stage3-roll-2-fold-a-v1 generation /home/chao/roll2-arm-commit.txt || exit $?
cp /home/chao/roll2-arm-flight-commit.txt /home/chao/roll2-flight-commit.txt
echo "flight commit $(cat /home/chao/roll2-flight-commit.txt)"
