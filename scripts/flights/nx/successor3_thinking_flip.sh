#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the SUCCESSOR-3 cell (slurp-milestone-successor3-thinking-system-v1; owner ruling 301 A) to ready on master: model-free, in LOOP FORM -- one convergence loop,
# re-run until one whole pass commits nothing, and only then is HEAD recorded as the flight commit (/home/chao/ms3-flight-commit.txt). NO SMOKE cell and NO twin exist
# and none is flipped: the allowance lists a test-sample smoke as not authorised, and a smoke under the read id would consume its one attempt. Run it through the ext4
# package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/nx/successor3_thinking_flip.sh" \
#     --package docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1 --cells slurp-milestone-successor3-thinking-system-v1 \
#     --pins-commit-msg /home/chao/ms3-pins-commit.txt
# Root runs this ONLY after: 1. the v2 allowance is signed and pinned and the packets window wrote the Thinking sample promotion receipt, the cell was re-derived with
# --require-receipt and the package re-written; 2. countersigning the DRAFT rows (packets, run, FIT; READ may stay a draft until the seal) -- the countersignature of the
# first consumed row names the conversational report of the P3.1 read to the owner; 3. minting the receipt with successor3_thinking_mint_receipt.py; 4. no other
# experiment in flight and no concurrent merge (a flip loop commits a half-resolved merge).
# The flip refuses on any refusal of successor3_thinking_preflip_check.py (allowance pin / status / ids, a registered smoke or twin, a pending pin, a missing packets receipt,
# an existing attempt). After the flip, refresh the registered plan pins (the writer copies the minted supply pin into the plans) and flip again. --allow-output-change must never be passed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
NX=$MAIN/scripts/flights/nx
PY=/home/chao/.venvs/speechrl/bin/python
SLUG=milestone-successor3-thinking-system
LABEL=SUCCESSOR3-THINKING-SYSTEM
RD=docs/readiness/2026-10-14-slurp-$SLUG-v1
CELL=slurp-$SLUG-v1
case "$(realpath -m "$MAIN")" in /mnt/*) [ "${SAEA_ALLOW_9P_FLIP:-0}" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/nx/successor3_thinking_mint_receipt.py)"; exit 6
fi
$PY -B "$NX/successor3_thinking_preflip_check.py" --repo-root "$MAIN" --data-root "$DATA" || { echo "$LABEL flip REFUSED by the preflip gate"; exit 6; }
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
  "research: flip $LABEL to ready (test-sample successor 3, owner ruling 301 A: the Thinking system on SLURP-TEST-SAMPLE-3010-V1, one attempt, no smoke; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
  > /home/chao/ms3-arm-commit.txt
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  bash "$SP/repin_loop_generic.sh" "$NX/successor3_thinking_repin_cell.sh" "$RD" "$CELL" generation /home/chao/ms3-arm-commit.txt || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/ms3-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL ready at it)"
