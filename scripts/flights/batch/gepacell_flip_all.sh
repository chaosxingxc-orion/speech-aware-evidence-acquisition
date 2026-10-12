#!/bin/bash
# Flip cell CELL-1-GEPA and its derangement twin to ready on master: model-free, four cells in four
# cycles (generation smoke, twin smoke, arm, twin). Root runs this AFTER minting
# coordination/slurp-stage3-delta-cell-gepa-r01-v1/cell-admission-v1.json (decision id
# slurp-stage3-delta-cell-gepa-r01-admission-v1) AND after the receipt edit of section 10 of
# docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1-preregistration.md, which rewrites the
# minted receipt's eligible_run_ids to this family's EIGHT run ids and its budget caps to this
# family's -- without that step core.flight.campaign.declared_readiness refuses the twin and both
# smokes ("run ... is not eligible in decision receipt").
#
# The four FIT cells (slurp-native-stage3-delta-cell-gepa-r01-fit-v1,
# ...-gepa-r01-twin-fit-v1, ...-gepa-r01-smoke-4-fit-v1 and ...-gepa-r01-smoke-4-twin-fit-v1)
# are NOT flipped: they are spend
# identities, never flown as generation cells.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-24-slurp-stage3-delta-cell-gepa-r01-v1
for K in smoke twin-smoke arm twin; do
cat > /home/chao/gepacell-$K-commit.txt <<M
research: flip cell CELL-1-GEPA ($K) to ready (Stage-3 S3-6, the GEPA family: the locked v2.0 plan plus the released 448-value stage3-deltas-gepa-v1 store on TRAIN Fold A, with its derangement twin as the form control; owner decisions 83, 99, 101, 106; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-delta-cell-gepa-r01-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/gepacell_repin_smoke.sh $RD slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1 smoke-generation /home/chao/gepacell-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/gepacell_repin_twin_smoke.sh $RD slurp-native-stage3-delta-cell-gepa-r01-smoke-4-twin-v1 twin-smoke-generation /home/chao/gepacell-twin-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/gepacell_repin_arm.sh $RD slurp-native-stage3-delta-cell-gepa-r01-v1 generation /home/chao/gepacell-arm-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/gepacell_repin_twin.sh $RD slurp-native-stage3-delta-cell-gepa-r01-twin-v1 twin-generation /home/chao/gepacell-twin-commit.txt || exit $?
cp /home/chao/gepacell-twin-flight-commit.txt /home/chao/gepacell-flight-commit.txt
echo "flight commit $(cat /home/chao/gepacell-flight-commit.txt)"
