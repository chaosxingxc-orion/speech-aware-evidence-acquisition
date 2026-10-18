#!/bin/bash
# Flip the two NX-T R3 cells (smoke, the Solver template column flight) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole
# pass commits nothing, and only then is HEAD recorded as the flight commit. Run it through the ext4 package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/nxt_r3_flip.sh" \
#     --package docs/readiness/2026-10-18-slurp-nxt-r3-solver-template-fold-b-v1 \
#     --cells slurp-native-stage3-nxt-r3-solver-template-fold-b-smoke-4-v1,slurp-native-stage3-nxt-r3-solver-template-fold-b-v1 \
#     --pins-commit-msg /home/chao/nxt3-pins-commit.txt
# Root runs this ONLY after: 1. countersigning the five DRAFT rows with countersign-row-texts-v1.json; 2. minting the receipt with
# scripts/flights/nx/nxt_r3_mint_receipt.py; 3. no other experiment in flight (NX-T R2 rec2 has sealed: ruling 303 A, serial GPU; the queue hook waits for CHAIN_NXT2_EXIT rc=0 and
# reads nxt_r3_arms.json); 4. the serving target (serving_lib.sh think-budget-np4, the resident np4 Thinking session) being on master (the swap is the chain's and a no-op when resident). --allow-output-change must
# never be passed.
# NXT3_KINDS selects the cells to flip. The default is "smoke arm". RECOVERY rec1 (nxt_r3_family.RECOVERIES, once a recovery input is committed): the sealed smoke
# is flipped no more (its rows are consumed), so export NXT3_KINDS=arm for the rec1 flip (the NX-T R1 lesson, 2026-10-14). Flipping is not flying.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/nx
SLUG=nxt-r3-solver-template-fold-b
PKGN=slurp-nxt-r3-solver-template-fold-b-v1
SHORT=nxt3
LABEL=NXT-R3
RD=docs/readiness/2026-10-18-$PKGN
KINDS=${NXT3_KINDS:-"smoke arm"}
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/$PKGN/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/nx/nxt_r3_mint_receipt.py)"; exit 6
fi
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
declare -A CELL=([smoke]=slurp-native-stage3-$SLUG-smoke-4-v1 [arm]=slurp-native-stage3-$SLUG-v1)
declare -A PLAN=([smoke]=smoke-generation [arm]=generation)
# RECOVERY (rec1, nxt_r3_family.RECOVERIES): the recovered cell's plans are <prefix>-plan-registered-rec1-v1.json; repin_loop_generic.sh reads the marker from
# PLAN_REC. The marker comes from the family (empty for a cell on its first attempt), never from a literal here.
declare -A REC_OF
for KIND in smoke arm; do
  REC_OF[$KIND]=$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MAIN/src" /home/chao/.venvs/speechrl/bin/python -B -c \
    "import sys; sys.path.insert(0, '$DIRD'); import nxt_r3_family as f; print(f.rec_suffix('$KIND'))") || { echo "cannot read the recovery marker of $KIND from the family"; exit 66; }
done
for KIND in $KINDS; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner ruling 326 A: the Solver instruction-template column on the Thinking core, TRAIN Fold B, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-nxt-r3-solver-template-fold-b-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for KIND in $KINDS; do
    PLAN_REC="${REC_OF[$KIND]}" NXT3_KIND=$KIND bash "$SP/repin_loop_generic.sh" "$DIRD/nxt_r3_repin_cell.sh" "$RD" "${CELL[$KIND]}" "${PLAN[$KIND]}" "/home/chao/$SHORT-$KIND-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke and the column flight ready at it)"
