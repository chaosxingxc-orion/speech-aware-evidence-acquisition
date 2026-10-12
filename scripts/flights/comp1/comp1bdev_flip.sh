#!/bin/bash
# Flip cell A2 (COMP-1b on DEV-2000-ADDED, owner decision 198) -- smoke, in-chain A/A, arm -- to ready on master:
# model-free, three cells in three cycles converging at ONE HEAD, which becomes the flight commit. Root runs this
# ONLY after:
#   1. the DRAFT exposure rows are countersigned (arm, arm FIT, smoke, smoke FIT, the READ row, and the A/A's two
#      rows, which the A2 registration re-pointed at this package);
#   2. coordination/slurp-stage3-comp1b-dev2000-added-v1/root-admission-v1.json is minted with the six eligible run
#      ids (scripts/flights/comp1/comp1bdev_mint_receipt.py);
#   3. scripts/checks/stage3_effect_floor_check.py passes on the arm (expected_effect_pp 3.8 is declared from the
#      COMP-1b Fold A read, not a placeholder).
# --allow-output-change must never be passed: no cell carries a committed pin; the flip re-mints each cell's own
# supply (item E16) and keeps this roster's agreement-table requirement beside it. Expected output digests: A/A
# d57ee9d6..., arm ecca16a2..., smoke d5ec9b15... (the superseded placeholder's own; the citation contract never
# touches the first-phase supply).
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs each cycle until the package
# converges at one HEAD (loop form). Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
for K in smoke aa arm; do
cat > /home/chao/comp1bdev-$K-commit.txt <<M
research: flip A2 ($K) to ready (COMP-1b on DEV-2000-ADDED, owner decision 198: the sealed DEV plan arm + the agreement term (w_agree 1.0, k 60, fuse 8-1-8; this roster's table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + the centroid boundary key, no citation contract, with its in-chain A/A (the DEV plan arm's own bytes at k 60, prepared output digest d57ee9d6) and its four-row smoke; intent primary declared 3.8 pp from the COMP-1b Fold A read, official SLU-F1 (slurp-slu-official) the guard at h_SLU 1.2525; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-comp1b-dev2000-added-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/comp1bdev_repin_smoke.sh $RD slurp-native-stage3-comp1b-dev2000-added-smoke-4-v1 smoke-generation /home/chao/comp1bdev-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1bdev_repin_aa.sh    $RD slurp-native-stage3-comp1-aa-dev2000-added-v1       aa-generation    /home/chao/comp1bdev-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $CP/comp1bdev_repin_arm.sh   $RD slurp-native-stage3-comp1b-dev2000-added-v1         generation       /home/chao/comp1bdev-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/comp1bdev-flight-commit.txt
echo "flight commit $(cat /home/chao/comp1bdev-flight-commit.txt)"
