#!/bin/bash
# Decisions 77 / owner rulings 302 A, 306 A, 333 B: fly the carrier base on the Thinking core (P3.3: A2T -> E21 -> E22; per carrier a four-unit smoke, the machine
# sign-off, the ALL-OFF arm and the DIRECT arm) through the batch driver, back to back on the ONE resident Thinking session (the SLURP lock's). A driver run attaches to
# ONE session (BATCH_SESSION), so every segment of every carrier is a separate driver run on the same session:
#
#   <carrier>:smoke      the carrier's four-unit smoke (A2T: an `engineering` driver step; E21 / E22: the E35 one-call `cell` form). Never scores for A2T.
#   <carrier>:arms       the all-off arm then the direct arm (two `cell` steps in ONE driver run). Waits for the carrier's smoke sign-off first
#                        (chain_lib.sh `wait_or_machine_signoff`).
#   <carrier>            smoke, sign-off, arms: the registered arc of one carrier. REFUSES (exit 9) when the carrier's smoke attempt already exists on the data root:
#                        a (run_id, attempt_id) pair is a one-time key and the sealed smoke is never re-flown.
#   <carrier>:arms-only  the RECOVERY entry: the arms alone. REQUIRES the carrier's smoke to be sealed (exit 9 otherwise) and its sign-off marker to exist (exit 5).
#   all                  the three carriers in the owner's order, one after the other; the first non-zero exit stops the chain (later carriers wait for the coordinator).
#
# SERVING. The cells ride the SLURP lock's resident Thinking session; the chain SWAPS to it when it is not resident (`serving_swap.sh think-budget-np4`). Hold the idle
# watchdog (/home/chao/saea-queue/watchdog.hold) first. The chain does not swap back; the coordinator's next step names the session it needs.
#
# SIGN-OFF (owner ruling 314 A). Per carrier: `wait_or_machine_signoff "<reader>" <conditions> <marker> 20`: a coordinator marker that already exists is the sign-off;
# otherwise the reader (`bash scripts/flights/carriers/carrier_think_read.sh smoke <carrier>`) writes the smoke decode-cost table and smoke_signoff.py decides PASS / FAIL
# against the conditions file THE DERIVE EMITTED INSIDE THE PACKAGE. PASS: the machine writes /home/chao/carrierthink-<carrier>-decode-signoff.marker and a 20-minute VETO
# window opens (delete the marker, or create /home/chao/batch-STOP). FAIL: <marker>.refused and the chain waits for a coordinator marker (CARRIERTHINK_SIGNOFF_WAIT_SECONDS,
# default 43200).
#
# After a sealed segment the exposure-ledger rows of the flown run ids are closed with chain_lib.sh `close_rows_after_seal` (idempotent; a failure is logged, not fatal).
# Every segment flies from ONE flight commit (/home/chao/carrierthink-flight-commit.txt, written by the flip).
#
# PRECONDITIONS (the coordinator's; this script refuses on the first three): no flight, lease or driver process alive and the flight lock clear (serial GPU, ruling 303 A);
# the cells are flipped (carrier_think_flip.sh); every other geometry's session is stopped (the swap does it).
#   bash scripts/flights/carriers/batch_chain_carrier_think.sh [all|a2t|e21|e22|<carrier>:smoke|<carrier>:arms|<carrier>:arms-only]
SEGMENT=${1:-all}
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
SP=$MAIN/scripts/flights/batch
CP=$MAIN/scripts/flights/carriers
REPO=/home/chao/saea-worktrees/fable-batch-flight
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SHORT=carrierthink
LOG=/home/chao/batch-chain-$SHORT.out
PY=/home/chao/.venvs/speechrl/bin/python
export SIGNOFF_WAIT_SECONDS=${CARRIERTHINK_SIGNOFF_WAIT_SECONDS:-43200}
export SIGNOFF_PY=$PY
export PYTHONDONTWRITEBYTECODE=1
. "$SP/serving_lib.sh"
. "$SP/chain_lib.sh"
saea_geometry think-budget-np4 || { echo "serving_lib.sh has no think-budget-np4 geometry"; exit 66; }
THINK_SESSION=$G_SID; THINK_TARGET=think-budget-np4
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
export BATCH_SESSION=$THINK_SESSION
CARRIERS=$($PY -B $CP/carrier_think_queue.py carriers) || exit 66

case "$SEGMENT" in
  all) RUN_CARRIERS=$CARRIERS; PHASE=both ;;
  a2t|e21|e22) RUN_CARRIERS=$SEGMENT; PHASE=both ;;
  a2t:smoke|e21:smoke|e22:smoke) RUN_CARRIERS=${SEGMENT%%:*}; PHASE=smoke ;;
  a2t:arms|e21:arms|e22:arms) RUN_CARRIERS=${SEGMENT%%:*}; PHASE=arms ;;
  a2t:arms-only|e21:arms-only|e22:arms-only) RUN_CARRIERS=${SEGMENT%%:*}; PHASE=arms-only ;;
  *) echo "usage: batch_chain_carrier_think.sh [all|a2t|e21|e22|<carrier>:smoke|<carrier>:arms|<carrier>:arms-only]"; exit 64 ;;
esac

state_of() {  # state_of <carrier> state|arm-state : sealed | opened | none, read from the data root with the family's own ids
  $PY -B $CP/carrier_think_queue.py "$2" --carrier "$1" --data-root "$DATA"
}
for C in $RUN_CARRIERS; do
  SS=$(state_of "$C" state)
  case "$PHASE" in
    both) [ "$SS" = none ] || { echo "segment $C refused: the smoke attempt already exists on the data root (state $SS); the sealed smoke is never re-flown; use $C:arms-only" >> $LOG; echo "refusing: $C smoke state $SS; use $C:arms-only"; exit 9; } ;;
    arms-only)
      [ "$SS" = sealed ] || { echo "segment $C:arms-only refused: the smoke is not sealed (state $SS)" >> $LOG; echo "refusing: $C smoke state $SS"; exit 9; }
      MK=/home/chao/$SHORT-$C-decode-signoff.marker
      [ -s "$MK" ] || { echo "segment $C:arms-only refused: no sign-off marker $MK" >> $LOG; echo "refusing: no sign-off marker"; exit 5; } ;;
  esac
done
echo "chain start $(date -u +%FT%TZ) segment $SEGMENT commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then
  echo "session $BATCH_SESSION is not resident; swapping to $THINK_TARGET $(date -u +%FT%TZ)" >> $LOG
  bash $SP/serving_swap.sh "$THINK_TARGET" >> $LOG 2>&1 || { echo "serving_swap.sh $THINK_TARGET failed; abort" >> $LOG; exit 6; }
fi
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident after the swap; abort" >> $LOG; exit 6; fi
for T in $SAEA_TARGETS; do
  [ "$T" = "$THINK_TARGET" ] && continue
  saea_geometry "$T" || continue
  O=$DATA/serving/$G_SID
  if [ "$G_SID" != "$THINK_SESSION" ] && [ -f "$O/session.json" ] && [ ! -f "$O/session-stop.json" ]; then
    echo "the other geometry's session $G_SID ($T) is still recorded resident; stop it first; abort" >> $LOG; exit 6
  fi
done
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt

run_driver() {  # run_driver <carrier> <smoke|arms> : write the queue for that segment and run the batch driver
  for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
  $PY -B $CP/carrier_think_queue.py steps --carrier "$1" --phase "$2" --out /home/chao/batch-queue.json || return 66
  echo "queue [$1 $2] written; starting driver $(date -u +%FT%TZ)" >> $LOG
  bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
  local rc=$?
  echo "driver exit $rc $1 $2 $(date -u +%FT%TZ)" >> $LOG
  return $rc
}

signoff() {  # signoff <carrier> : the machine sign-off (or a coordinator marker) between the smoke and the arms; 0 = the arms may start
  wait_or_machine_signoff "bash scripts/flights/carriers/carrier_think_read.sh smoke $1" "$MAIN/docs/readiness/2026-10-18-carrier-base-thinking-v1/signoff-conditions-$1-v1.json" \
    "/home/chao/$SHORT-$1-decode-signoff.marker" 20
}

close_rows() {  # close_rows <run ids...> : the ledger rows of a sealed segment; a failure is logged, never fatal
  CLOSE_ROWS_REPO=$MAIN CLOSE_ROWS_PY=$PY close_rows_after_seal "$@" || chain_log "close_rows_after_seal failed (rc=$?); close the rows by hand: ledger_mark_consumed.py --apply"
}

run_carrier() {  # run_carrier <carrier>
  local c=$1 rc
  case "$PHASE" in
    smoke)     run_driver "$c" smoke; rc=$?; [ $rc -eq 0 ] && close_rows $($PY -B $CP/carrier_think_queue.py ids --carrier "$c" --phase smoke); return $rc ;;
    arms)      signoff "$c" || return $?; run_driver "$c" arms; rc=$?; [ $rc -eq 0 ] && close_rows $($PY -B $CP/carrier_think_queue.py ids --carrier "$c" --phase all); return $rc ;;
    arms-only) run_driver "$c" arms; rc=$?; [ $rc -eq 0 ] && close_rows $($PY -B $CP/carrier_think_queue.py ids --carrier "$c" --phase all); return $rc ;;
    both)      run_driver "$c" smoke || return $?
               close_rows $($PY -B $CP/carrier_think_queue.py ids --carrier "$c" --phase smoke)
               signoff "$c" || return $?
               run_driver "$c" arms; rc=$?; [ $rc -eq 0 ] && close_rows $($PY -B $CP/carrier_think_queue.py ids --carrier "$c" --phase all); return $rc ;;
  esac
}

for C in $RUN_CARRIERS; do
  chain_log "carrier $C begins ($PHASE)"
  run_carrier "$C"; RC=$?
  chain_log "carrier $C ended rc=$RC"
  [ $RC -eq 0 ] || exit $RC
done
exit 0
