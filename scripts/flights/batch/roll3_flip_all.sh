#!/bin/bash
# Flip cell ROLL-3 and its four-row smoke to ready on master: model-free, two cells in two cycles
# (generation smoke, then the arm). Root runs this AFTER minting
# coordination/slurp-stage3-roll-3-dev2000-added-v1/root-admission-v1.json (decision id slurp-stage3-roll-3-dev2000-added-admission-v1) with THIS family's FOUR eligible run ids --
# SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-V1, -FIT-V1, -SMOKE-4-V1, -SMOKE-4-FIT-V1 -- and this family's
# budget caps (generation 19,000 / fit endpoint 76,000 / repeated speech 56,688 s / 11.2 GPU-h on
# the arm; 76 / 304 / 155 s / 1.0 on the smoke). Without that,
# core.flight.campaign.declared_readiness refuses the smoke ("run ... is not eligible in decision
# receipt").
#
# The two FIT cells (SAEA-SLURP-STAGE3-ROLL-3-DEV2000-ADDED-FIT-V1 and -SMOKE-4-FIT-V1) are NOT flipped:
# they are spend identities, never flown as generation cells.
#
# dry-run-v1.md quotes the PRE-FLIP composed hash of the smoke exactly once: after the smoke flip, re-run
# scripts/flights/batch/roll3_dry_run.py at the flipped bytes and rewrite that one line before the arm flip,
# or the residue check refuses it (cell ROLL-2's lesson).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1
for K in smoke arm; do
cat > /home/chao/roll3-$K-commit.txt <<M
research: flip cell ROLL-3 ($K) to ready (the Stage-3 sealed-sample-pool asset on the evaluation roster DEV-2000-ADDED: cell ROLL-2's grouped-Solver form at samples 5 / temperature 0.7 / min_support 3, re-pointed onto DEV-2000-ADDED's 1,000 rows so the program gains the sealed five-sample pool it has on R01C and TRAIN Fold A and lacks where every admitted policy must later be replicated, making selection, commit, verification, projection and re-ranking policies readable offline at about 0.53 pp at zero GPU cost; DESCRIPTIVE, no comparator and no admission claim; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-roll-3-dev2000-added-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/roll3_repin_smoke.sh $RD slurp-native-stage3-roll-3-dev2000-added-smoke-4-v1 smoke-generation /home/chao/roll3-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/roll3_repin_arm.sh $RD slurp-native-stage3-roll-3-dev2000-added-v1 generation /home/chao/roll3-arm-commit.txt || exit $?
cp /home/chao/roll3-arm-flight-commit.txt /home/chao/roll3-flight-commit.txt
echo "flight commit $(cat /home/chao/roll3-flight-commit.txt)"
