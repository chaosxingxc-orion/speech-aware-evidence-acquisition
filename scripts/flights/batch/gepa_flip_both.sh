#!/bin/bash
# Flip the GEPA cells (the four-row form smoke, then the 68-group arm) to ready on master:
# model-free. Root runs this AFTER minting
# coordination/slurp-stage3-delta-cell-gepa-r01-v1/root-admission-v1.json (decision id
# slurp-stage3-gepa-r01-admission-v1); see section 13 of
# docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1-preregistration.md for the mint command.
#
# BEFORE this runs: the merge that carries the GEPA arm moves core/flight/runtime.py, which is
# hashed into every prepared phase-supply artifact's identity. Re-pin the CELL-1 family in the same
# cycle (scripts/flights/batch/cell1_flip_all.sh) and NEVER pass --allow-output-change: their
# output is expected to reproduce byte for byte because no selection path moved.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1
for K in smoke arm; do
cat > /home/chao/gepa-$K-commit.txt <<M
research: flip cell GEPA-R01 ($K) to ready (Stage-3 layer A, the GEPA reflective per-(scenario, node) proposal over the sealed ROLL-1 rollouts; owner decisions 82, 83, 101; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-gepa-r01-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $SP/gepa_repin_smoke.sh $RD slurp-native-stage3-gepa-r01-smoke-4-v1 smoke-generation /home/chao/gepa-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $SP/gepa_repin_arm.sh $RD slurp-native-stage3-gepa-r01-v1 generation /home/chao/gepa-arm-commit.txt
