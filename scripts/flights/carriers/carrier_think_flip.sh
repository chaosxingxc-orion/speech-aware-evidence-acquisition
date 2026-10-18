#!/bin/bash
# Flip the nine carrier-base cells (A2T, E21, E22: smoke, all-off, direct each) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one
# whole pass commits nothing, and only then is HEAD recorded as the flight commit. Run it through the ext4 package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/carriers/carrier_think_flip.sh" \
#     --package docs/readiness/2026-10-18-carrier-base-thinking-v1 --cells <the nine cells, comma separated> \
#     --pins-commit-msg /home/chao/carrierthink-pins-commit.txt
# Root runs this ONLY after: 1. the P3.2 Thinking packets of every carrier are promoted and pinned in the baselines (the flip refuses a zero sentinel); 2. countersigning the
# DRAFT rows with countersign-row-texts-v1.json; 3. minting the receipt with scripts/flights/carriers/carrier_think_mint_receipt.py; 4. no other experiment in flight (ruling
# 303 A, serial GPU); 5. NX-T R3 sealed. --allow-output-change must never be passed.
# CARRIERTHINK_KEYS selects the cells to flip (default: all nine, e.g. "a2t-smoke a2t-alloff"). RECOVERY rec1 (carrier_think_family.RECOVERIES, once a recovery input is
# committed): the sealed cells are flipped no more, so export CARRIERTHINK_KEYS=<the recovered key> for the rec1 flip (the NX-T R1 lesson, 2026-10-14). Flipping is not flying.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/carriers
SHORT=carrierthink
LABEL=CARRIER-BASE-THINKING
PKGN=carrier-base-thinking-v1
RD=docs/readiness/2026-10-18-$PKGN
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/$PKGN/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/carriers/carrier_think_mint_receipt.py)"; exit 6
fi
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
declare -A CELL PLAN REC_OF
# The cell ids, the plan-name prefixes and the recovery markers come from the family, never from a literal here.
eval "$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$MAIN/src" /home/chao/.venvs/speechrl/bin/python -B -c \
  "import sys; sys.path.insert(0, '$DIRD'); import carrier_think_family as f
for k in f.ALL_KEYS:
    s = f.CELLS[k]
    print('CELL[%s]=%s PLAN[%s]=%s REC_OF[%s]=\"%s\"' % (k, s['cell'], k, s['prefix'] + 'generation', k, f.rec_suffix(k)))
print('ALL_KEYS=\"%s\"' % ' '.join(f.ALL_KEYS))")" || { echo "cannot read the cells from the family"; exit 66; }
KEYS=${CARRIERTHINK_KEYS:-$ALL_KEYS}
for KEY in $KEYS; do
  [ -n "${CELL[$KEY]}" ] || { echo "unknown cell key $KEY"; exit 64; }
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KEY) to ready (owner rulings 302 A / 306 A / 333 B: the carrier all-off and direct baselines on the Thinking core, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt carrier-base-thinking-admission-v1)" \
    > "/home/chao/$SHORT-$KEY-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for KEY in $KEYS; do
    PLAN_REC="${REC_OF[$KEY]}" CARRIERTHINK_KEY=$KEY bash "$SP/repin_loop_generic.sh" "$DIRD/carrier_think_repin_cell.sh" "$RD" "${CELL[$KEY]}" "${PLAN[$KEY]}" "/home/chao/$SHORT-$KEY-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL cells ready at it)"
