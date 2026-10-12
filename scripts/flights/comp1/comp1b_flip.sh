#!/bin/bash
# Flip the COMP-1b family (smoke, arm -- no A/A) to ready on master: model-free, two cells in two cycles
# converging at ONE HEAD, which becomes the flight commit. Root runs this ONLY after:
#   1. the DRAFT exposure rows (arm, arm-fit, smoke, smoke-fit, the READ row) are countersigned;
#   2. coordination/slurp-stage3-comp1b-fold-a-v1/root-admission-v1.json is minted with the four eligible
#      run ids (a comp1b_mint_receipt.py in the pattern of scripts/flights/comp1/comp1_mint_receipt.py);
#   3. scripts/checks/stage3_effect_floor_check.py passes on the arm (expected_effect_pp 4.26 is already
#      declared, not a placeholder -- unlike cell COMP-1, this family carries no TBD gate).
# --allow-output-change must never be passed: no cell carries a committed pin; the flip re-mints each
# cell's own supply (item E16) and keeps the agreement-table requirement beside it. The arm's re-minted
# supply is expected to reproduce cell COMP-1's own arm supply digest ce68bebc... exactly, since the
# citation contract never touches the first-phase supply.
# NO A/A REPIN: the comparator is the EXISTING SEALED in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1
# cell COMP-1 already flew (owner decision 160's shared-A/A pattern, as cell G5 reused it) -- it is read,
# never re-flown or re-pinned by this family.
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs each cycle until the
# package converges at one HEAD. Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
for K in smoke arm; do
cat > /home/chao/comp1b-$K-commit.txt <<M
research: flip COMP-1b ($K) to ready (COMP-1 minus the citation contract, 2026-09-29 SLU-harm attribution branch fable/comp1slu commit e30aa1b61: cell COMP-1's own agreement term (w_agree 1.0, k 60, fuse 8-1-8) and centroid boundary key, byte for byte, with the citation contract saea-solver-cited-answer-v1 reverted to the locked plan's non-cited program; comparator the EXISTING SEALED in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1, reused cross-flight, never re-flown (decision 160); intent primary declared 4.26 pp, official SLU-F1 the guard h_SLU 1.2485 (decision 133); re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1b-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/comp1b_repin_smoke.sh $RD slurp-native-stage3-comp1b-fold-a-smoke-4-v1 smoke-generation /home/chao/comp1b-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1b_repin_arm.sh   $RD slurp-native-stage3-comp1b-fold-a-v1         generation       /home/chao/comp1b-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/comp1b-flight-commit.txt
echo "flight commit $(cat /home/chao/comp1b-flight-commit.txt)"
