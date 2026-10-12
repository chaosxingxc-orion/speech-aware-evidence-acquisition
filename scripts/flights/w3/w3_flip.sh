#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the W3 family (four-row smoke, then the arm) to ready on master: model-free, one cell per cycle,
# the two cycles converging at ONE HEAD, which becomes the flight commit. The shared wave-1 A/A
# SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 is the coordinator's and is flipped by the coordinator's own
# script, never here. Root runs this ONLY after:
#   1. countersigning the DRAFT exposure rows of this family (SAEA-SLURP-STAGE3-W3-FOLD-A-V1 and its
#      -FIT-V1, SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1 and its -FIT-V1, the READ row
#      SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1, and the two model-free rows
#      SAEA-SLURP-W3-INTENT-CONTRAST-CARDS-BUILD-V1 and SAEA-SLURP-W3-CONTRAST-CAP-OFFLINE-V1);
#   2. minting coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-w3-contrast-fold-a-admission-v1) with scripts/flights/w3/w3_mint_receipt.py, which
#      copies the package's draft with its FOUR eligible run ids and this family's caps, sets status
#      decided, stamps the time and re-hashes every antecedent path.
# --allow-output-change must never be passed: no cell carries a committed pin; the flip mints each
# cell's own supply (item E16), and every minted supply must reproduce the AGREE family's own output
# digest (arm eab5c61e92a47c1723c478f2b7914abade6152b195f676d7d32251f3d18884ae). Sibling flips on master
# move this package's hashes: repin_loop_generic.sh re-runs each cycle until the package converges at
# one HEAD; then re-run every cycle once more and require "satisfied at <the same HEAD>" with zero
# "committed" lines. Untracked files count as dirt for core.flight.cli check.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1
if [ ! -f $SAEA_DATA_ROOT/coordination/slurp-stage3-w3-contrast-fold-a-v1/root-admission-v1.json ]; then
  echo "refusing: the W3 decision receipt is not minted (scripts/flights/w3/w3_mint_receipt.py)"; exit 6
fi
W3=$(dirname "$0")
for K in smoke arm; do
cat > /home/chao/w3-$K-commit.txt <<M
research: flip W3a ($K) to ready (knowledge-wave item W3 as W3a alone, owner decision 164 and the coordinator ruling of 2026-09-27: the retained AGREE arm with the intent-boundaries store moved to the contrast-card release intent-boundaries-contrast-v1, the Solver exemplar supply the AGREE arm's own; read on no harm at the shared wave-1 in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w3-contrast-fold-a-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
done
bash $SP/repin_loop_generic.sh $W3/w3_repin_smoke.sh $RD slurp-native-stage3-w3-fold-a-smoke-4-v1 smoke-generation /home/chao/w3-smoke-commit.txt || exit $?
bash $SP/repin_loop_generic.sh $W3/w3_repin_arm.sh   $RD slurp-native-stage3-w3-fold-a-v1         generation       /home/chao/w3-arm-commit.txt   || exit $?
cd ${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition} && git rev-parse HEAD > /home/chao/w3-flight-commit.txt
echo "flight commit $(cat /home/chao/w3-flight-commit.txt)"
