#!/bin/bash
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
#   bash scripts/flights/nx/nx_r1_flip.sh
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
SP=$MAIN/scripts/flights/batch
NX=$MAIN/scripts/flights/nx
RD=docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-nx-r1-solver-fold-b-v1/root-admission-v1.json" ]; then
  echo "refusing: the NX R1 decision receipt is not minted (scripts/flights/nx/nx_r1_mint_receipt.py)"; exit 6
fi
for KIND in smoke arm; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip NX-R1 ($KIND) to ready (NX programme owner decisions 228-234: same-flight Solver template column on TRAIN Fold B, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-nx-r1-solver-fold-b-admission-v1)" \
    > "/home/chao/nxr1-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  NX_KIND=smoke bash "$SP/repin_loop_generic.sh" "$NX/nx_r1_repin_cell.sh" "$RD" slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-v1 smoke-generation "/home/chao/nxr1-smoke-commit.txt" || exit $?
  NX_KIND=arm bash "$SP/repin_loop_generic.sh" "$NX/nx_r1_repin_cell.sh" "$RD" slurp-native-stage3-nx-r1-solver-fold-b-v1 generation "/home/chao/nxr1-arm-commit.txt" || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/nxr1-flight-commit.txt
echo "flight commit $CONVERGED (NX R1 smoke and arm ready at it)"
