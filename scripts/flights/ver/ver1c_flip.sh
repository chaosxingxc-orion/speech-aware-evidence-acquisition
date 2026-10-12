#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the VER-1c cell (smoke, then arm) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one
# whole pass commits nothing (a later flip rewrites shared files such as the exposure ledger after an earlier cycle reported
# "satisfied"; the shared protocol hash propagates once), and only then is HEAD recorded as the VER-1c flight commit. Root runs
# this ONLY after:
#   1. countersigning the four DRAFT flight rows (arm, arm FIT, smoke, smoke FIT); the READ row
#      SAEA-SLURP-STAGE3-VER1C-C3-COLUMN-FOLD-A-COLUMN-READ-V1 stays a draft until the seal;
#   2. minting coordination/slurp-ver1c-c3-column-fold-a-v1/root-admission-v1.json with scripts/flights/ver/ver1c_mint_receipt.py;
#   3. the VER-1c engineering branch (sonnet/ver1b-register) is on master and the cell passes core.flight.cli check there; no
#      concurrent merge (a flip loop commits a half-resolved merge); no other experiment is in flight (one experiment in flight).
# After the flip, refresh the registered plan pins (scripts/flights/refresh_registered_plan_pins.py copies the minted supply pin into the
# plans) and flip again. --allow-output-change must never be passed.
#   bash scripts/flights/ver/ver1c_flip.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
VERD=$MAIN/scripts/flights/ver
SLUG=ver1c-c3-column-fold-a
SHORT=ver1c
LABEL=VER-1c
RD=docs/readiness/2026-10-10-slurp-$SLUG-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/ver/ver1c_mint_receipt.py)"; exit 6
fi
for KIND in smoke arm; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner decision 257: the R1 c3 Solver template column on TRAIN Fold A, the verdict source of the VER-1 rule; claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  VER_KIND=smoke bash "$SP/repin_loop_generic.sh" "$VERD/ver1c_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-smoke-4-v1 smoke-generation "/home/chao/$SHORT-smoke-commit.txt" || exit $?
  VER_KIND=arm bash "$SP/repin_loop_generic.sh" "$VERD/ver1c_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-v1 generation "/home/chao/$SHORT-arm-commit.txt" || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke and arm ready at it)"
