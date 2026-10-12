#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip cell W4-SV (smoke, then arm) to ready on master: model-free, two cells in two LOOP cycles converging at ONE
# HEAD, which becomes the W4-SV flight commit. Root runs this ONLY after:
#   0. the arm-B blocker is fixed (docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/README.md, "BLOCKED") and
#      scripts/flights/w4sv/w4sv_arm_a_proof.py, re-run at the fixed HEAD, rewrote the package's
#      arm-a-byte-identity-proof-v1.json with arm_b_verdict ARM-B-VARIES -- this script REFUSES otherwise;
#   1. countersigning the four DRAFT flight rows (SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1 and its -FIT-V1,
#      SAEA-SLURP-STAGE3-W4SV-FOLD-A-SMOKE-4-V1 and its -FIT-V1) and the two model-free rows
#      (SAEA-SLURP-STAGE3-W4SV-FIT-MEASURE-V1, SAEA-SLURP-STAGE3-W4SV-ARM-A-BYTE-IDENTITY-PROOF-V1); the READ row
#      SAEA-SLURP-STAGE3-W4SV-FOLD-A-COLUMN-READ-V1 stays a draft until the seal;
#   2. minting coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json (decision id
#      slurp-stage3-w4sv-fold-a-admission-v1, four eligible run ids) with scripts/flights/w4sv/w4sv_mint_receipt.py.
# --allow-output-change must never be passed: the flip mints each cell's own supply (item E16) and neither the
# alternate nor the arm group is an input to it, so the minted digests must be the AGREE arm's / smoke's
# (eab5c61e... / 308601c5...). Sibling flips move this package's hashes: repin_loop_generic.sh re-runs each cycle
# until it converges; then re-run this script once more and require "satisfied at <the same HEAD>" with zero
# "committed" lines. Untracked files count as dirt.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
SP=$MAIN/scripts/flights/batch
PY=/home/chao/.venvs/speechrl/bin/python
RD=docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1
if [ ! -f $SAEA_DATA_ROOT/coordination/slurp-stage3-w4sv-fold-a-v1/root-admission-v1.json ]; then
  echo "refusing: the W4-SV decision receipt is not minted (scripts/flights/w4sv/w4sv_mint_receipt.py)"; exit 6
fi
VERDICT=$($PY -c "import json;d=json.load(open('$MAIN/$RD/arm-a-byte-identity-proof-v1.json'));print(d.get('arm_b_verdict'),d.get('verdict'))") || exit 8
case "$VERDICT" in
  "ARM-B-VARIES IDENTICAL"|"ARM-B-VARIES IDENTICAL-MODULO-PROGRAM-FIELDS") ;;
  *) echo "refusing: the committed arm-A proof reads [$VERDICT]; arm b-w4 must vary (ARM-B-VARIES) and arm A must match the AGREE arm"; exit 7 ;;
esac
W=$(dirname "$0")
for K in smoke arm; do
  {
    echo "research: flip W4-SV ($K) to ready (the W4 slot conventions as the first cell of the same-flight supply-variant instrument, owner decision 172: the retained AGREE arm with three first-visit Solver arms -- b-w4 release swap to slot-contracts-w4-v1, t-twin replicate of a-agree, a-agree delivering -- read as first-visit columns b-w4 vs a-agree against the twin null, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w4sv-fold-a-admission-v1)"
    echo
    echo "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
  } > /home/chao/w4sv-$K-commit.txt
done
bash "$SP/repin_loop_generic.sh" "$W/w4sv_repin_smoke.sh" $RD slurp-native-stage3-w4sv-fold-a-smoke-4-v1 smoke-generation /home/chao/w4sv-smoke-commit.txt || exit $?
bash "$SP/repin_loop_generic.sh" "$W/w4sv_repin_arm.sh"   $RD slurp-native-stage3-w4sv-fold-a-v1         generation       /home/chao/w4sv-arm-commit.txt   || exit $?
cd "$MAIN" && git rev-parse HEAD > /home/chao/w4sv-flight-commit.txt
echo "flight commit $(cat /home/chao/w4sv-flight-commit.txt)"
