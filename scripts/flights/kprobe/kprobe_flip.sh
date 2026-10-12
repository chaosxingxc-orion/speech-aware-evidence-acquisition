#!/bin/bash
# Flip cell KPROBE (the 55-row centroid-key conversion probe) to ready on master: model-free, one
# cell, no smoke. Root runs this AFTER:
#   1. countersigning the three DRAFT exposure rows (SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-V1, its -FIT-V1,
#      and the model-free key-file row SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1);
#   2. minting coordination/slurp-stage3-kprobe-fold-a-55-v1/root-admission-v1.json (decision id
#      slurp-stage3-kprobe-fold-a-55-admission-v1) with the TWO eligible run ids and this cell's caps:
#      scripts/flights/kprobe/kprobe_mint_receipt.py copies the package's draft, sets status decided,
#      stamps the time and re-hashes every antecedent path. Without both ids
#      core.flight.campaign.declared_readiness refuses ("run ... is not eligible in decision receipt").
# No smoke: 55 rows is itself a form proof (claims_benefit false) and the treatment form is the locked
# plan's, which flew its own smoke; only one retrieval-key file differs.
# Sibling flips on master move this package's hashes: repin_loop_generic.sh re-runs the cycle until the
# package converges at one HEAD. Untracked files count as dirt for core.flight.cli check.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1
cat > /home/chao/kprobe-arm-commit.txt <<M
research: flip cell KPROBE (the 55-row centroid-key conversion probe) to ready (owner decision 145: the locked PLAN plan with one pin moved -- the intent-boundary Perception facet_source to the centroid key file, k 8 / fuse 8-1-8 unchanged -- flies on exactly the TRAIN Fold A rows whose gold intent boundary entry that key newly delivers, against the already-sealed PLAN answers, reading P(correct given newly delivered) on intent correctness per row behind a delivery gate; form-proof, claims_benefit false, no pooled claim ever; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-kprobe-fold-a-55-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
KP=$(dirname "$0")
bash $SP/repin_loop_generic.sh $KP/kprobe_repin_arm.sh $RD slurp-native-stage3-kprobe-fold-a-55-v1 generation /home/chao/kprobe-arm-commit.txt || exit $?
cp /home/chao/kprobe-arm-flight-commit.txt /home/chao/kprobe-flight-commit.txt 2>/dev/null || git rev-parse HEAD > /home/chao/kprobe-flight-commit.txt
echo "flight commit $(cat /home/chao/kprobe-flight-commit.txt)"
