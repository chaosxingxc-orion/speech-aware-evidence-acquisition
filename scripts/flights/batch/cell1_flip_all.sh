#!/bin/bash
# Flip cell CELL-1 and its derangement twin to ready on master: model-free, four cells in four
# cycles (generation smoke, twin smoke, arm, twin). Root runs this AFTER minting
# coordination/slurp-stage3-delta-cell-r01-v1/root-admission-v1.json (decision id
# slurp-stage3-delta-cell-r01-admission-v1) AND after step 1b of section 10 of
# docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md, which rewrites the
# minted receipt's eligible_run_ids to this family's eight run ids and its budget caps to this
# family's -- without that step core.flight.campaign.declared_readiness refuses the twin and both
# smokes ("run ... is not eligible in decision receipt").
#
# The two FIT cells of the arm fragment (slurp-native-stage3-delta-cell-r01-fit-v1 and
# ...-r01-twin-fit-v1) are NOT flipped: they are spend identities, never flown as generation cells.
#
# 2026-09-23, THIRD FAILURE: the generation smoke is now the REPLACEMENT cell
# slurp-native-stage3-delta-cell-smoke-4-v3 (experiment fragment of the same name, plan prefix
# smoke-v3-generation); run ids SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1 (two failures) and
# ...-SMOKE-4-V2 (12 contacts, reviewer_0_input) are both retired and take no further attempt. The
# twin smoke keeps its v1 cell id and its v1 plan prefix. Root must ALSO extend the minted receipt's
# eligible_run_ids to SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3 and
# SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3-FIT-V1, or declared_readiness refuses the new smoke.
# Every CELL-1 cell must be re-pinned in this one cycle: rails/knowledge_stores.py carries the fix
# and is hashed into every prepared first-phase artifact identity.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1
for K in smoke twin-smoke arm twin; do
cat > /home/chao/cell1-$K-commit.txt <<M
research: flip cell CELL-1 ($K) to ready (Stage-3 S3-6 / S3-4s: the locked v2.0 plan plus the per-node stage3-deltas store on TRAIN Fold A, with its derangement twin as the form control; owner decisions 83, 99, 101, 106; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-delta-cell-r01-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/cell1_repin_smoke.sh $RD slurp-native-stage3-delta-cell-smoke-4-v3 smoke-v3-generation /home/chao/cell1-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell1_repin_twin_smoke.sh $RD slurp-native-stage3-delta-cell-smoke-4-twin-v1 twin-smoke-generation /home/chao/cell1-twin-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell1_repin_arm.sh $RD slurp-native-stage3-delta-cell-r01-v1 generation /home/chao/cell1-arm-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/cell1_repin_twin.sh $RD slurp-native-stage3-delta-cell-r01-twin-v1 twin-generation /home/chao/cell1-twin-commit.txt || exit $?
cp /home/chao/cell1-twin-flight-commit.txt /home/chao/cell1-flight-commit.txt
echo "flight commit $(cat /home/chao/cell1-flight-commit.txt)"
