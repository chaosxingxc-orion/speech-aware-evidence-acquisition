#!/bin/bash
# Flip the consumption module's first end-to-end cell (COMP-1b as a module block on lock v2.1, DEV-2000-ADDED; migration
# step 6, owner decisions 195/196/204) -- smoke, in-chain A/A, arm -- to ready on master: model-free, three cells in
# three cycles converging at ONE HEAD, which becomes the flight commit. HELD: the cell need not fly if the module byte
# proof holds (scripts/analysis/module_equivalence_proof.py --at m0 m6); root runs this ONLY after the coordinator decides
# it flies and:
#   1. the seven DRAFT exposure rows are countersigned (arm, arm FIT, A/A, A/A FIT, smoke, smoke FIT, READ);
#   2. coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json is minted with the six eligible run ids
#      (scripts/flights/module/module_comp1bdev_mint_receipt.py);
#   3. scripts/checks/stage3_effect_floor_check.py passes on the arm (expected_effect_pp 4.6 from the A2 read).
# --allow-output-change must never be passed: no cell carries a committed pin; the flip re-mints each cell's own
# supply (item E16). Expected output digests: A/A d57ee9d6..., arm ecca16a2..., smoke d5ec9b15... (cell A2's own;
# the lock-v2.1 Reviewer pin never touches the first-phase supply).
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs each cycle until the package
# converges at one HEAD (loop form). Untracked files count as dirt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
for K in smoke aa arm; do
cat > /home/chao/module-comp1bdev-$K-commit.txt <<M
research: flip the module cell ($K) to ready (migration step 6: COMP-1b as a consumption-module block on lock v2.1 -- agree-vote-seed w_agree 1.0 / k 60 with this roster's table SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1 + centroid-boundary-key -- with its in-chain A/A = the module's OFF arm on lock v2.1 (output digest d57ee9d6) and its four-row smoke; intent primary declared 4.6 pp from the A2 read, official SLU-F1 the guard at h_SLU 1.2525; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-module-comp1b-dev2000-added-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
CP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $CP/module_comp1bdev_repin_smoke.sh $RD slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1 smoke-generation /home/chao/module-comp1bdev-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $CP/module_comp1bdev_repin_aa.sh    $RD slurp-native-stage3-module-comp1b-aa-dev2000-added-v1 aa-generation    /home/chao/module-comp1bdev-aa-commit.txt    || exit $?
bash $SP/repin_loop_generic.sh $CP/module_comp1bdev_repin_arm.sh   $RD slurp-native-stage3-module-comp1b-dev2000-added-v1 generation       /home/chao/module-comp1bdev-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/module-comp1bdev-flight-commit.txt
echo "flight commit $(cat /home/chao/module-comp1bdev-flight-commit.txt)"
