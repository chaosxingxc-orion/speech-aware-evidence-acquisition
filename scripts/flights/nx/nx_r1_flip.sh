#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the NX R1 cell (smoke, then arm) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one
# whole pass commits nothing (a later flip rewrites shared files such as the exposure ledger after an earlier cycle reported
# "satisfied"; the shared protocol hash propagates once), and only then is HEAD recorded as the NX R1 flight commit. Root runs
# this ONLY after:
#   1. countersigning the four DRAFT flight rows (arm, arm FIT, smoke, smoke FIT); the READ row
#      SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1 stays a draft until the seal;
#   2. minting coordination/slurp-nx-r1-solver-fold-b-v1/root-admission-v1.json with scripts/flights/nx/nx_r1_mint_receipt.py;
#   3. the instrument branch (fable/nx-harness, merge c474b79af or later) is on master and the cell passes core.flight.cli
#      check there; no concurrent merge (a flip loop commits a half-resolved merge).
# --allow-output-change must never be passed.
#   bash scripts/flights/nx/nx_r1_flip.sh [1|2]
# The optional argument is the R1 iteration (default 1); iteration 2 flips its own two cells, writes
# /home/chao/nxr1i2-flight-commit.txt and needs its own minted receipt (coordination/slurp-nx-r1-i2-solver-fold-b-v1/).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
NX=$MAIN/scripts/flights/nx
ITER=${1:-1}
case "$ITER" in
  1) SLUG=nx-r1-solver-fold-b; SHORT=nxr1; LABEL=NX-R1 ;;
  2) SLUG=nx-r1-i2-solver-fold-b; SHORT=nxr1i2; LABEL=NX-R1-I2 ;;
  *) echo "usage: nx_r1_flip.sh [1|2]" >&2; exit 2 ;;
esac
export NX_ITER=$ITER
RD=docs/readiness/2026-10-09-slurp-$SLUG-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/nx/nx_r1_mint_receipt.py --iteration $ITER)"; exit 6
fi
for KIND in smoke arm; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (NX programme owner decisions 228-234: same-flight Solver template column on TRAIN Fold B, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  NX_KIND=smoke bash "$SP/repin_loop_generic.sh" "$NX/nx_r1_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-smoke-4-v1 smoke-generation "/home/chao/$SHORT-smoke-commit.txt" || exit $?
  NX_KIND=arm bash "$SP/repin_loop_generic.sh" "$NX/nx_r1_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-v1 generation "/home/chao/$SHORT-arm-commit.txt" || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke and arm ready at it)"
