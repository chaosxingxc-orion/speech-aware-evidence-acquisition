#!/bin/bash
# ONE tool for a serving-geometry swap, run from WSL (owner decision 163, track ENGINEERING). It replaces the
# hand-run pair "WSL switch script + Windows scheduled-task switch" whose halves were run separately on 2026-09-27
# (one ran while the other refused) and it never leaves the card without a server on a refusal it could foresee.
#
#   serving_swap.sh <slurp-np4|a2t-np3|e21-np4|det-np1|think-np4|think-budget-np4|think-budget7168-np4> [--dry-run] [--restart] [--min-host-free-gb 4.0]
#                   [--margin-gb 0.5] [--wait-timeout 600] [--monitor-delay 20] [--no-restore]
#                   [--gap-hook <script>]
#   serving_swap.sh --stop-only [--dry-run]            stop the resident session and leave the card EMPTY (no target)
#   serving_swap.sh <target> --start-only [--dry-run]  start <target> only when NOTHING else is resident (a different
#                                                      resident geometry refuses with exit 10; the target already resident
#                                                      is the usual readiness-checked no-op)
#   The pair brackets a GPU window in which the card must hold no server (the Thinking packet encoder pass of the 266-E
#   read: scripts/flights/direct/direct_fb_packets_gpu.sh). --stop-only needs no target, skips the host-memory and target
#   precondition steps (nothing starts), and exits 0 "stopped" (or "no-op" when nothing was resident). It never restores:
#   the caller owns the restore (a full `serving_swap.sh <previous>` or `--start-only`).
#
# In order:
#   1. one swap at a time (flock on $SAEA_SWAP_LOCK) and the pending marker $SAEA_SWAP_PENDING, which refuses every
#      CPU sidecar launch for the duration (decision 162; serving_lib.sh saea_sidecar_admission);
#   2. precise flight check: a generation flight (core.flight.cli campaign|worker, batch_driver.sh,
#      core.flight.lease_cli) or $DATA/locks/flight.lock refuses; a model-free core.flight.cli prepare-supply/check
#      in a worktree does not;
#   3. the resident session (serving_session.sh resident) mapped onto the geometry table; an unrecorded server on
#      port 8080 or an unknown session refuses; the target already resident is a no-op after a readiness check --
#      UNLESS --restart was given (owner decision 182, the idle watchdog's uptime/server-death recovery: a
#      session record can say "resident" for a process that already died, e.g. a CUDA abort, or one the
#      coordinator wants recycled past its uptime bound), in which case it falls through to the normal stop+start
#      of that same geometry below instead of the fast no-op path;
#   4. host-memory pre-check BEFORE anything is stopped: serving_session.sh host-memory with the start guard
#      (--min-host-free-gb, default 4.0) plus --margin-gb headroom; a proven shortfall refuses and names the CPU
#      sidecars holding memory (2026-09-27: 11.7 GB and 10.1 GB under a resident 8081 sidecar failed two restarts
#      AFTER the running geometry had been stopped);
#   5. clean stop of the current session (serving_session.sh stop), its leftover wrapper, port 8080 verified free,
#      then its Windows tasks stopped;
#   5b. with --restart --gap-hook <script> only: `bash <script>` runs in the gap, after the stop (port verified
#      free) and before the start, still under the swap lock and the pending marker (so no CPU sidecar starts);
#      its exit status is recorded (step gap-hook) and never stops the start (E5-0, owner decision 201:
#      serving_restart_hook_e5.sh);
#   6. the target's Windows serving task started through saea_task.ps1 -Start (WSL interop PowerShell), its monitor
#      task --monitor-delay seconds later;
#   7. the strict readiness wait (serving_wait_ready.sh --since <this start>);
#   8. on any failure after the stop: the target torn down and the previous geometry restored the same way
#      (--no-restore skips it);
#   9. one final JSON summary line (schema saea-serving-swap-summary-v1), also appended to
#      $SAEA_RUNTIME_ROOT/serving-swap.jsonl.
# --dry-run prints the plan and every precondition verdict and acts on nothing (it reads /health on port 8080 only
# through serving_session.sh resident; it starts, stops and registers nothing).
#
# Exit: 0 swapped / no-op / dry-run with every precondition passing; 7 generation flight alive; 8 host memory short
# (or unreadable guard); 9 another swap holds the lock; 10 resident state unknown or an unrecorded server; 11 the
# current session could not be stopped cleanly (nothing was started); 12 the target failed and the previous geometry
# was restored; 13 the target failed and nothing could be restored; 64 usage.
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
# shellcheck source=serving_lib.sh
source "$HERE/serving_lib.sh"

TARGET=
DRY=0
RESTART=0
MIN=$SAEA_MIN_HOST_FREE_GB
MARGIN=0.5
WAIT=600
MONITOR_DELAY=20
RESTORE=1
GAP_HOOK=
STOP_ONLY=0
START_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --restart) RESTART=1 ;;
    --min-host-free-gb) MIN=${2:-}; shift ;;
    --margin-gb) MARGIN=${2:-}; shift ;;
    --wait-timeout) WAIT=${2:-}; shift ;;
    --monitor-delay) MONITOR_DELAY=${2:-}; shift ;;
    --no-restore) RESTORE=0 ;;
    --gap-hook) GAP_HOOK=${2:-}; shift ;;
    --stop-only) STOP_ONLY=1 ;;
    --start-only) START_ONLY=1 ;;
    -h|--help) sed -n '2,55p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*) echo "serving_swap: unknown option $1"; exit 64 ;;
    *) [ -z "$TARGET" ] || { echo "serving_swap: one target only"; exit 64; }; TARGET=$1 ;;
  esac
  shift
done
if [ "$STOP_ONLY" = 1 ]; then
  [ "$START_ONLY" = 0 ] || { echo "serving_swap: --stop-only and --start-only are exclusive"; exit 64; }
  [ -z "$TARGET" ] || { echo "serving_swap: --stop-only takes no target (it stops whatever is resident)"; exit 64; }
  [ "$RESTART" = 0 ] && [ -z "$GAP_HOOK" ] || { echo "serving_swap: --stop-only takes neither --restart nor --gap-hook"; exit 64; }
  TARGET=none; G_SID=none; G_FRAGMENT=none; G_SERVING_TASK=; G_MONITOR_TASK=; G_SERVING_ENTRY=; G_MONITOR_ENTRY=
else
  saea_geometry "$TARGET" || { echo "usage: serving_swap.sh <$(echo $SAEA_TARGETS | tr ' ' '|')> [--dry-run] [options] | --stop-only; see --help"; exit 64; }
  [ "$START_ONLY" = 0 ] || [ "$RESTART" = 0 ] || { echo "serving_swap: --start-only and --restart are exclusive"; exit 64; }
fi
if [ -n "$GAP_HOOK" ]; then
  [ "$RESTART" = 1 ] || { echo "serving_swap: --gap-hook needs --restart"; exit 64; }
  [ -f "$GAP_HOOK" ] || { echo "serving_swap: --gap-hook script not found: $GAP_HOOK"; exit 64; }
fi

SS=${SAEA_SERVING_SESSION:-$REPO/scripts/serving_session.sh}
PS=$(saea_powershell)
export SPEECHRL_DATA_DIR=$SAEA_DATA PYTHONDONTWRITEBYTECODE=1
STARTED=$(date -u +%FT%TZ)
STEPS=$(mktemp)
FROM=unknown
HOST_FREE=null
trap 'rm -f "$STEPS"' EXIT

say() { echo "$(date -u +%FT%TZ) swap: $*"; }
record() { printf '%s\t%s\t%s\n' "$1" "$2" "$(printf '%s' "${3:-}" | tr '\t\n' '  ' | cut -c1-600)" >> "$STEPS"; say "$1: $2${3:+ -- $3}"; }
finish() {
  local result=$1 code=$2 line
  line=$(python3 - "$STEPS" "$TARGET" "$FROM" "$result" "$code" "$DRY" "$STARTED" "$HOST_FREE" <<'PY'
import json, sys
from datetime import datetime, timezone
steps_path, target, source, result, code, dry, started, host_free = sys.argv[1:9]
steps = []
for line in open(steps_path, encoding="utf-8", errors="replace"):  # the ps1 echoes locale (GBK) bytes on a refusal; never let the summary itself crash
    name, _, rest = line.rstrip("\n").partition("\t")
    verdict, _, detail = rest.partition("\t")
    steps.append({"step": name, "verdict": verdict, "detail": detail})
print(json.dumps({
    "schema": "saea-serving-swap-summary-v1", "target": target, "from": source, "result": result,
    "exit": int(code), "dry_run": dry == "1", "host_free_gb": None if host_free == "null" else float(host_free),
    "started_at": started, "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "steps": steps,
}, sort_keys=True))
PY
)
  echo "$line"
  [ "$DRY" = 1 ] || echo "$line" >> "$SAEA_RUNTIME_ROOT/serving-swap.jsonl" 2>/dev/null
  exit "$code"
}
task() {  # task <-Stop|-Start|-Status> <name> [script]
  local verb=$1 name=$2 script=${3:-} out rc
  if [ -n "$script" ]; then
    out=$("$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$name" -Script "$script" "$verb" 2>&1 | tr -d '\r'; exit "${PIPESTATUS[0]}")
  else
    out=$("$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$name" "$verb" 2>&1 | tr -d '\r'; exit "${PIPESTATUS[0]}")
  fi
  rc=$?
  printf '%s\n' "$out" | sed 's/^/    ps: /'
  TASK_OUT=$(printf '%s' "$out" | tail -1)
  return $rc
}

# ------------------------------------------------------------------ preconditions (dry-run and real run alike)
say "target $TARGET ($G_SID, fragment $G_FRAGMENT)$([ $DRY = 1 ] && echo ' [DRY RUN]')"
REFUSE=0
refuse() { [ "$REFUSE" = 0 ] && REFUSE=$1; }

exec 9>"$SAEA_SWAP_LOCK" || { record swap-lock unwritable "$SAEA_SWAP_LOCK"; finish refused 9; }
if flock -n 9; then
  record swap-lock free "$SAEA_SWAP_LOCK"
  [ "$DRY" = 1 ] && flock -u 9
else
  record swap-lock busy "another serving_swap.sh holds $SAEA_SWAP_LOCK: $(cat "$SAEA_SWAP_PENDING" 2>/dev/null)"
  refuse 9
fi

if REASONS=$(saea_flight_alive); then
  record flight alive "$REASONS"
  refuse 7
else
  record flight none "no generation flight (core.flight.cli campaign|worker, batch_driver.sh, lease_cli) and no flight.lock"
fi

MISSING=
if [ "$STOP_ONLY" = 0 ]; then
  for f in "$G_SERVING_ENTRY" "$G_MONITOR_ENTRY"; do [ -f "$SAEA_MAIN/$f" ] || MISSING="$MISSING $SAEA_MAIN/$f"; done
  if [ -n "$MISSING" ]; then record target-entries missing "$MISSING"; refuse 10; else record target-entries present "$G_SERVING_TASK=$G_SERVING_ENTRY $G_MONITOR_TASK=$G_MONITOR_ENTRY"; fi
else
  record target-entries not-needed "--stop-only starts nothing"
fi

RES=$(bash "$SS" resident 2>&1)
RES_RC=$?
CUR=none
case $RES_RC in
  0)
    CUR_SID=$(printf '%s' "$RES" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("session_id") or "")' 2>/dev/null)
    if CUR=$(saea_target_for_session "$CUR_SID"); then
      record resident "$CUR" "$CUR_SID $(printf '%s' "$RES" | python3 -c 'import json,sys; d=json.load(sys.stdin); print("process_state", d.get("process_state"), "stale", d.get("stale"))' 2>/dev/null)"
    else
      CUR=unknown; record resident unknown "session '$CUR_SID' is not in the geometry table; stop it by hand"; refuse 10
    fi ;;
  3)
    if PORT=$(saea_port_server_pids) && [ -n "$PORT" ]; then
      CUR=unknown; record resident unrecorded-server "no session is recorded resident but a llama-server holds port $SAEA_SERVING_PORT: $PORT"; refuse 10
    else
      record resident none "no session recorded resident and port $SAEA_SERVING_PORT holds no llama-server (the card has no server)"
    fi ;;
  *) CUR=unknown; record resident cannot-tell "serving_session.sh resident exit $RES_RC: $RES"; refuse 10 ;;
esac
FROM=$CUR

SIDECARS=$(saea_cpu_sidecars)
record cpu-sidecars "$([ -n "$SIDECARS" ] && echo present || echo none)" "$SIDECARS"

if [ "$START_ONLY" = 1 ] && [ "$CUR" != none ] && [ "$CUR" != unknown ] && [ "$CUR" != "$TARGET" ]; then
  record start-only refused "--start-only needs an empty card but $CUR is resident; use a full swap or --stop-only first"
  refuse 10
fi
if [ "$STOP_ONLY" = 1 ] && [ "$CUR" = none ] && [ "$REFUSE" = 0 ]; then
  record plan no-op "--stop-only: nothing is resident, the card is already empty"
  finish "$([ "$DRY" = 1 ] && echo dry-run || echo no-op)" "$REFUSE"
fi

if [ "$CUR" = "$TARGET" ] && [ "$RESTART" != 1 ] && [ "$STOP_ONLY" = 0 ]; then
  # Nothing is stopped or started, so no precondition can make the no-op unsafe: only the read-only readiness
  # check runs (a queue may ask for the geometry it already has while another flight holds the card).
  record plan no-op "$TARGET is already the resident geometry; readiness check only"
  if [ "$DRY" = 1 ]; then finish dry-run 0; fi
  bash "$HERE/serving_wait_ready.sh" "$TARGET" --since 0 --timeout 60 --poll 5 | sed 's/^/    wait: /'
  RC=${PIPESTATUS[0]}
  record ready-check "$([ "$RC" = 0 ] && echo ready || echo "not-ready-$RC")" "resident $TARGET"
  [ "$RC" = 0 ] && finish no-op 0
  finish no-op-not-ready 10
fi
if [ "$CUR" = "$TARGET" ] && [ "$RESTART" = 1 ]; then
  record plan restart "--restart requested while $TARGET is already resident: falling through to a normal stop+start of the same geometry instead of the no-op path"
fi

if [ "$STOP_ONLY" = 1 ]; then
  HM=; HM_RC=0
  record host-memory not-needed "--stop-only starts nothing"
else
HM=$(bash "$SS" host-memory --min-host-free-gb "$MIN" --margin-gb "$MARGIN" 2>&1)
HM_RC=$?
fi
HOST_FREE=$(printf '%s' "$HM" | python3 -c 'import json,sys; v=json.load(sys.stdin).get("host_free_gb"); print("null" if v is None else round(v, 2))' 2>/dev/null || echo null)
[ -n "$HOST_FREE" ] || HOST_FREE=null
case $HM_RC in
  0)
    if [ "$STOP_ONLY" = 1 ]; then
      :
    elif [ "$HOST_FREE" = null ]; then
      record host-memory unavailable "no Windows reading; start's guard fails open, so the swap does too"
    else
      record host-memory admits "host free ${HOST_FREE} GB >= guard $MIN + margin $MARGIN GB (read with the current geometry still resident)"
    fi ;;
  4)
    record host-memory short "host free ${HOST_FREE} GB < guard $MIN + margin $MARGIN GB: the $TARGET start would refuse after the stop and leave the card empty; nothing is stopped.$([ -n "$SIDECARS" ] && echo " CPU sidecars holding host memory: $(echo "$SIDECARS" | tr '\n' ';') -- wait for them to finish (decision 162: sidecars run only inside long resident flights) or free host memory")"
    refuse 8 ;;
  *) record host-memory guard-unreadable "serving_session.sh host-memory exit $HM_RC: $HM"; refuse 8 ;;
esac

if [ "$STOP_ONLY" = 1 ]; then
  STATUS_NAMES=$( [ "$CUR" != unknown ] && { saea_geometry "$CUR"; echo "$G_SERVING_TASK $G_MONITOR_TASK"; } )
else
  STATUS_NAMES="$( [ "$CUR" != none ] && [ "$CUR" != unknown ] && { saea_geometry "$CUR"; echo "$G_SERVING_TASK $G_MONITOR_TASK"; } ) $(saea_geometry "$TARGET"; echo "$G_SERVING_TASK $G_MONITOR_TASK")"
fi
for name in $STATUS_NAMES; do
  task -Status "$name" >/dev/null 2>&1
  record task-status "$name" "$TASK_OUT"
done
[ "$STOP_ONLY" = 1 ] || saea_geometry "$TARGET"

PLAN="stop session $CUR (serving_session.sh stop, leftover wrapper killed, port $SAEA_SERVING_PORT verified free), stop its tasks"
[ "$CUR" = none ] && PLAN="nothing resident to stop"
if [ "$STOP_ONLY" = 1 ]; then
  PLAN="$PLAN; start NOTHING (--stop-only: the card stays empty for the caller; no restore)"
else
  PLAN="$PLAN; start $G_SERVING_TASK ($SAEA_MAIN/$G_SERVING_ENTRY), ${MONITOR_DELAY}s later $G_MONITOR_TASK ($SAEA_MAIN/$G_MONITOR_ENTRY); serving_wait_ready.sh $TARGET --since <start> --timeout $WAIT"
  if [ "$RESTORE" = 1 ] && [ "$CUR" != none ]; then PLAN="$PLAN; on failure restore $CUR the same way"; else PLAN="$PLAN; no restore"; fi
fi
record plan "$([ "$REFUSE" = 0 ] && echo go || echo refused)" "$PLAN"

[ "$REFUSE" != 0 ] && finish refused "$REFUSE"
[ "$DRY" = 1 ] && finish dry-run 0

# ------------------------------------------------------------------ the swap
printf '{"pid": %s, "target": "%s", "from": "%s", "started_at": "%s"}\n' "$$" "$TARGET" "$CUR" "$STARTED" > "$SAEA_SWAP_PENDING"
trap 'rm -f "$STEPS"; rm -f "$SAEA_SWAP_PENDING"' EXIT

wait_port_free() {
  local i
  for i in $(seq 1 30); do
    [ -z "$(saea_port_server_pids)" ] && return 0
    sleep 2
  done
  return 1
}

stop_geometry() {  # stop_geometry <target>: clean stop of that session (if resident), its wrapper, its tasks
  local t=$1 out rc sid
  saea_geometry "$t"
  sid=$G_SID
  if [ -f "$G_SESSION_DIR/session.json" ] && [ ! -f "$G_SESSION_DIR/session-stop.json" ]; then
    out=$(bash "$SS" stop --session-id "$sid" 2>&1); rc=$?
    record "stop-session-$t" "$([ $rc = 0 ] && echo stopped || echo "exit-$rc")" "$(printf '%s' "$out" | tail -3)"
  else
    record "stop-session-$t" not-resident "$sid has no live session record"
  fi
  sleep 5
  for p in $(pgrep -f -- "[c]ore\.session\.serving start .*--session-id $sid( |$)" 2>/dev/null); do
    kill "$p" 2>/dev/null && record "stop-wrapper-$t" killed "$p"
  done
  if wait_port_free; then
    record "port-$SAEA_SERVING_PORT" free "after stopping $t"
  else
    record "port-$SAEA_SERVING_PORT" held "$(saea_port_server_pids)"
    return 1
  fi
  saea_geometry "$t"
  task -Stop "$G_SERVING_TASK"; record "task-stop" "$G_SERVING_TASK" "$TASK_OUT"
  task -Stop "$G_MONITOR_TASK"; record "task-stop" "$G_MONITOR_TASK" "$TASK_OUT"
  return 0
}

start_geometry() {  # start_geometry <target>: tasks started, strict wait; 0 only when READY
  local t=$1 t0 rc
  saea_geometry "$t"
  t0=$(date +%s)
  if ! task -Start "$G_SERVING_TASK" "$SAEA_MAIN/$G_SERVING_ENTRY"; then
    record "task-start" "$G_SERVING_TASK-failed" "$TASK_OUT"; return 1
  fi
  record "task-start" "$G_SERVING_TASK" "$TASK_OUT"
  sleep "$MONITOR_DELAY"
  if ! task -Start "$G_MONITOR_TASK" "$SAEA_MAIN/$G_MONITOR_ENTRY"; then
    record "task-start" "$G_MONITOR_TASK-failed" "$TASK_OUT"; return 1
  fi
  record "task-start" "$G_MONITOR_TASK" "$TASK_OUT"
  bash "$HERE/serving_wait_ready.sh" "$t" --since "$t0" --timeout "$WAIT" --poll 5 | sed 's/^/    wait: /'
  rc=${PIPESTATUS[0]}
  record "ready-$t" "$([ "$rc" = 0 ] && echo ready || echo "not-ready-exit-$rc")" "strict wait since $t0"
  return "$rc"
}

if REASONS=$(saea_flight_alive); then   # a flight launched since the precondition read
  record flight alive-at-stop "$REASONS"
  finish refused 7
fi
if [ "$CUR" != none ]; then
  if ! stop_geometry "$CUR"; then
    finish failed-stop 11
  fi
fi
if [ "$STOP_ONLY" = 1 ]; then
  record stop-only stopped "the card is empty; $CUR was stopped and nothing was started (the caller restores)"
  finish stopped 0
fi
if [ -n "$GAP_HOOK" ]; then   # step 5b: the restart gap; the hook's status is recorded, never fatal to the start
  record gap-hook start "$GAP_HOOK (port $SAEA_SERVING_PORT free, swap lock and pending marker held)"
  bash "$GAP_HOOK" 2>&1 | sed 's/^/    hook: /'
  GAP_RC=${PIPESTATUS[0]}
  record gap-hook "exit-$GAP_RC" "$GAP_HOOK"
fi
if start_geometry "$TARGET"; then
  finish swapped 0
fi
say "the $TARGET start failed; tearing it down"
stop_geometry "$TARGET" || record teardown-"$TARGET" incomplete "port $SAEA_SERVING_PORT still held"
if [ "$RESTORE" != 1 ] || [ "$CUR" = none ]; then
  record restore skipped "$([ "$CUR" = none ] && echo 'nothing was resident before the swap' || echo '--no-restore')"
  finish failed-unrestored 13
fi
say "restoring $CUR"
if start_geometry "$CUR"; then
  finish failed-restored 12
fi
finish failed-unrestored 13
