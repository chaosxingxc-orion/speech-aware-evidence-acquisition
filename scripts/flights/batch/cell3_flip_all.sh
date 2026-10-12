#!/bin/bash
# Flip cell CELL-3, its derangement twin and the roster's own-null replicate to ready on master:
# model-free, five cells in five cycles (PLANr-DEV2000, generation smoke, twin smoke, arm, twin).
#
# Root runs this AFTER minting
# coordination/slurp-stage3-delta-cell-r03-gate-v1/root-admission-v1.json (decision id
# slurp-stage3-delta-cell-r03-gate-admission-v1) AND after the receipt edit of section 10 of
# docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1-preregistration.md, which rewrites
# the minted receipt's eligible_run_ids to this family's TEN run ids and its budget caps to this
# family's -- without that step core.flight.campaign.declared_readiness refuses every cell but the
# first ("run ... is not eligible in decision receipt").
#
# The FIVE FIT cells (slurp-native-default-plan-dev2000-added-replicate-fit-v1,
# slurp-native-stage3-delta-cell-r03-gate-fit-v1, ...-twin-fit-v1, ...-smoke-4-fit-v1 and
# ...-smoke-4-twin-fit-v1) are NOT flipped: they are spend identities, never flown as generation
# cells.
#
# PLANr-DEV2000 is flipped FIRST because it flies first: CELL-3 has no margin until the own-null
# read has sealed. Its prepared artifact MUST reproduce cell B6's
# 36463545fa791723c2adee82db9fb8c78420c72d0ebc07d4ec179cc0ddb2e179 exactly -- a different value
# means the replicate is not a replicate. Stop and report; never pass --allow-output-change.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1
cat > /home/chao/cell3-planr-commit.txt <<M
research: flip cell PLANr-DEV2000 to ready (the DEV-2000-ADDED roster's own null for Stage-3 iteration 3: the request-identical second pass of cell B6's plan arm, flown first so CELL-3 is not read under an imported margin; owner decisions 83, 99, 101, 106; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-delta-cell-r03-gate-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
for K in smoke twin-smoke arm twin; do
cat > /home/chao/cell3-$K-commit.txt <<M
research: flip cell CELL-3 ($K) to ready (Stage-3 S3-6 iteration 3: the locked v2.0 plan plus the coverage-gated stage3-deltas-v2 store on the fresh DEV-2000-ADDED roster, with its derangement twin as the form control; owner decisions 83, 99, 101, 106; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-delta-cell-r03-gate-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/cell3_repin_planr.sh $RD slurp-native-default-plan-dev2000-added-replicate-v1 planr-generation /home/chao/cell3-planr-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell3_repin_smoke.sh $RD slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1 smoke-generation /home/chao/cell3-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell3_repin_twin_smoke.sh $RD slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-v1 twin-smoke-generation /home/chao/cell3-twin-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell3_repin_arm.sh $RD slurp-native-stage3-delta-cell-r03-gate-v1 generation /home/chao/cell3-arm-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell3_repin_twin.sh $RD slurp-native-stage3-delta-cell-r03-gate-twin-v1 twin-generation /home/chao/cell3-twin-commit.txt || exit $?
cp /home/chao/cell3-twin-flight-commit.txt /home/chao/cell3-flight-commit.txt
echo "flight commit $(cat /home/chao/cell3-flight-commit.txt)"
