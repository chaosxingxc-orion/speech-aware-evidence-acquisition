#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The IDLE-FILLER QUEUE (owner decision 162). Loops forever; on every tick it asks
# filler_queue_decide.py for ONE decision and records it in /home/chao/filler-queue.out:
#   HALT      batch-STOP present -> log and exit 3 (never skip a failed chunk; root diagnoses, then restarts)
#   WAIT      main-line chain ready (/home/chao/mainline-ready), a flight/driver process alive,
#             locks/flight.lock, a stale batch-flight-repo.txt override, a batch-done younger than the
#             grace period, or the np4 session not resident / healthy / idle / freshly sampled
#   LAUNCH k  the lowest unflown, minted, flipped chunk -> record it in /home/chao/filler-queue-state.jsonl
#             BEFORE launching (so a crash can never re-fly it), then run batch_chain_filler.sh k in the
#             foreground; the next tick re-checks everything, so a main-line chain waits at most ONE chunk.
# It never touches serving tasks, the serving geometry, locks/ or any scheduled task.
#
# Run it as a Windows scheduled task (decision 77), like /home/chao/saea-queue/queue_after_*.sh: COPY it
# to ext4 first (bash reads a script incrementally, and the main checkout moves under merges):
#   cp scripts/flights/filler/filler_queue.sh /home/chao/saea-queue/filler_queue.sh
# The decision function and the chain script are read from the main checkout on every tick.
#
# Flags: --dry-run (decide and log, never launch; LAUNCH is logged as "DRY-RUN would launch")
#        --once (one tick, then exit)   --interval S (default 60)
#        --status-json FILE (dry runs only: read the serving status from FILE instead of serving_session.sh)
# Environment: FILLER_HOME (default /home/chao), FILLER_QUEUE_LOG, FILLER_STATE, SAEA_MAIN, SPEECHRL_DATA_DIR,
#              FILLER_HOLD (default /home/chao/saea-queue/filler.hold: while it exists, log "filler held" and exit 0).
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
FD=$MAIN/scripts/flights/filler
PY=${FILLER_PY:-/home/chao/.venvs/speechrl/bin/python}
H=${FILLER_HOME:-/home/chao}
LOG=${FILLER_QUEUE_LOG:-$H/filler-queue.out}
STATE=${FILLER_STATE:-$H/filler-queue-state.jsonl}
DATA=$SAEA_DATA_ROOT
CHAIN=${FILLER_CHAIN:-$FD/batch_chain_filler.sh}
HOLD=${FILLER_HOLD:-/home/chao/saea-queue/filler.hold}
DRY=0; ONCE=0; INTERVAL=60; STATUS_JSON=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --once) ONCE=1 ;;
    --interval) INTERVAL=$2; shift ;;
    --status-json) STATUS_JSON=$2; shift ;;
    *) echo "unknown flag $1" >&2; exit 2 ;;
  esac
  shift
done
[ -n "$STATUS_JSON" ] && [ "$DRY" != 1 ] && { echo "--status-json is for dry runs only" >&2; exit 2; }
export PYTHONDONTWRITEBYTECODE=1
say () { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }
field () { "$PY" -c "import json,sys; d=json.loads(sys.argv[1]); v=d.get(sys.argv[2]); print('' if v is None else v)" "$1" "$2"; }
say "queue start pid $$ dry_run=$DRY once=$ONCE interval=${INTERVAL}s main=$MAIN"
while true; do
  # HOLD switch (coordinator, 2026-09-28): while the hold file exists the filler launches nothing -- it logs
  # "filler held" and exits 0, so a queue that ends in this script hands the card on without flying a chunk.
  # Checked on every tick, before any decision. The hold is owned (queue_lib.sh ql_hold_take / ql_hold_release, since
  # the 2026-09-30 hold race): its first word is the owner token, and the held line names it ("legacy" = an empty,
  # pre-ownership file). Only the owner releases it.
  if [ -e "$HOLD" ]; then
    HOLD_OWNER=$(awk 'NR == 1 { print $1 " since " $2; exit }' "$HOLD" 2>/dev/null)
    say "filler held ($HOLD present, owner ${HOLD_OWNER:-legacy}); exit 0 before launching anything"; echo "filler held"; exit 0
  fi
  ARGS=(--home "$H" --data-root "$DATA" --main "$MAIN" --state-file "$STATE")
  [ -n "$STATUS_JSON" ] && ARGS+=(--status-json "$STATUS_JSON")
  D=$("$PY" -B "$FD/filler_queue_decide.py" "${ARGS[@]}" 2>&1)
  DECISION=$(field "$D" decision 2>/dev/null)
  say "$D"
  case "$DECISION" in
    HALT) say "HALT: $(field "$D" reason)"; exit 3 ;;
    WAIT) ;;
    LAUNCH)
      K=$(field "$D" chunk); COMMIT=$(field "$D" commit)
      if [ "$DRY" = 1 ]; then
        say "DRY-RUN would launch chunk $K at ${COMMIT:0:8} via $CHAIN"
      else
        echo "{\"chunk\": $K, \"commit\": \"$COMMIT\", \"launched_at\": \"$(date -u +%FT%TZ)\"}" >> "$STATE"
        say "LAUNCH chunk $K at ${COMMIT:0:8}"
        bash "$CHAIN" "$K"; RC=$?
        say "chunk $K chain returned $RC; done=$( [ -e "$H/batch-done" ] && head -1 "$H/batch-done" ) stop=$( [ -e "$H/batch-STOP" ] && head -1 "$H/batch-STOP" )"
        # The chain refused BEFORE the driver started (1 no commit file, 2 checkout / queue step, 6 stale
        # override, 7 a batch appeared): nothing flew, so the chunk is released for a later tick.
        case "$RC" in 1|2|6|7) echo "{\"chunk\": $K, \"released\": true, \"chain_rc\": $RC, \"at\": \"$(date -u +%FT%TZ)\"}" >> "$STATE"; say "chunk $K released (chain refused before the driver, rc $RC)";; esac
      fi ;;
    *) say "no decision could be read; halt"; exit 4 ;;
  esac
  [ "$ONCE" = 1 ] && exit 0
  sleep "$INTERVAL"
done
