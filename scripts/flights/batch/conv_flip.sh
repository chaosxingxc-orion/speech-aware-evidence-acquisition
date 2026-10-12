#!/bin/bash
# Flip cell CONV (the 70-row conversion probe) to ready on master: model-free, one cell, no smoke.
# Root runs this AFTER minting coordination/slurp-stage3-conv-fold-a-70-v1/root-admission-v1.json
# (decision id slurp-stage3-conv-fold-a-70-admission-v1) with the two eligible run ids
# SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1 and -FIT-V1 and this cell's caps (770 / 3080 / 1899 s / 1.0 GPU-h).
# No smoke: 70 rows is itself a form proof (claims_benefit false) and the treatment form flew its own
# four-row smoke registration under the AGREE package.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1
cat > /home/chao/conv-arm-commit.txt <<M
research: flip cell CONV (the 70-row conversion probe) to ready (owner decisions 133 and 134: the treatment w_agree 1.0 / k 60 / fuse 8-1-8 flies on exactly the 70 TRAIN Fold A rows whose gold intent boundary entry is newly delivered, against the already-sealed PLAN answers, reading P(correct given newly delivered) on intent correctness per row; form-proof, claims_benefit false, no pooled claim ever; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-conv-fold-a-70-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
bash $SP/repin_loop_generic.sh $SP/conv_repin_arm.sh $RD slurp-native-stage3-conv-fold-a-70-v1 generation /home/chao/conv-arm-commit.txt || exit $?
cp /home/chao/conv-arm-arm-flight-commit.txt /home/chao/conv-flight-commit.txt 2>/dev/null || git rev-parse HEAD > /home/chao/conv-flight-commit.txt
echo "flight commit $(cat /home/chao/conv-flight-commit.txt)"
