#!/bin/bash
# Flip cell RANKVIS (the 119-row rank-visible rendering conversion probe) to ready on master: model-free,
# one cell, no smoke. Root runs this AFTER:
#   1. countersigning the three DRAFT exposure rows (SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1, its -FIT-V1,
#      and the model-free roster row SAEA-SLURP-MF-RANKVIS-ROSTER-DERIVATION-V1; the READ row
#      SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1-READ-V1 stays a draft until the seal);
#   2. minting coordination/slurp-stage3-rankvis-fold-a-119-v1/root-admission-v1.json (decision id
#      slurp-stage3-rankvis-fold-a-119-admission-v1) with scripts/flights/rankvis/rankvis_mint_receipt.py.
# No smoke, as the CONV (70) and KPROBE (55) precedents: 119 rows is itself a form proof (claims_benefit
# false) and no smoke row was registered; the read's rendering gate refuses a number unless the flown
# requests carry the rank labels on every row.
# LOOP FORM: repin_loop_generic.sh re-runs the cycle until the package converges at one HEAD. Run this
# script again (bound 3 passes) until it reports "satisfied at <the same HEAD>" with no "committed" line;
# that HEAD is the flight commit, written to /home/chao/rankvis-flight-commit.txt (read by
# batch_chain_rankvis.sh). Untracked files count as dirt for core.flight.cli check.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
RD=docs/readiness/2026-09-27-slurp-stage3-rankvis-probe-fold-a-v1
cat > /home/chao/rankvis-arm-commit.txt <<M
research: flip cell RANKVIS (the 119-row rank-visible rendering conversion probe) to ready (owner decision 171: the registered AGREE arm with one native_episode key added -- knowledge_value_rendering, retrieval-rank order with the rank shown on the intent-boundaries and train-exemplars blocks -- on the 119 TRAIN Fold A rows AGREE delivered and got wrong, read as m of 119 against the no-op expectation 15.9; form-proof, claims_benefit false, no pooled claim ever; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-rankvis-fold-a-119-admission-v1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
M
R=$(dirname "$0")
bash $SP/repin_loop_generic.sh $R/rankvis_repin_arm.sh $RD slurp-native-stage3-rankvis-fold-a-119-v1 generation /home/chao/rankvis-arm-commit.txt || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/rankvis-flight-commit.txt
echo "flight commit $(cat /home/chao/rankvis-flight-commit.txt)"
