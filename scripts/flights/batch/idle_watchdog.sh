#!/bin/bash
# The IDLE WATCHDOG (owner decision 182, docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md
# row 182): "Authorise an IDLE WATCHDOG as an engineering-base item: a scheduled task that, every few
# minutes, when no flight/driver/swap is alive, no STOP is live, the serving geometry is healthy or
# swappable, and a registered ready-chain list names a next chain, launches that chain through the batch
# driver (row 77 unchanged: flights only through the driver), logging every decision?" Ruling: authorised.
# "The watchdog never launches onto a STOP, never edits records, never starts a CPU sidecar, respects the
# hold files, and its ready-chain list is a committed file the coordinator edits."
#
# Register it as a Windows Scheduled Task (owner decision 77), like every other long-lived WSL process:
#   powershell -File scripts/flights/batch/saea_task.ps1 -Name SAEA-Watchdog \
#     -Script /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch/idle_watchdog.sh \
#     -RepeatMinutes 5
# Pause it with /home/chao/saea-queue/watchdog.hold (present -> log and exit 0; nothing else is touched).
#
# On every tick, in order:
#   1. exit quietly (0) if a flight/driver/swap/filler/queue process is already alive: the same precise
#      checks serving_swap.sh and the coordinator queues use (saea_flight_alive: core.flight.cli
#      campaign|worker, batch_driver.sh, core.flight.lease_cli, locks/flight.lock; saea_swap_pending;
#      filler_queue.sh; a saea-queue/queue_*.sh coordinator queue script);
#   2. /home/chao/batch-STOP: NEVER launched onto except one recovery case (coordinator diagnosis,
#      2026-09-28 night: the resident llama-server died on a CUDA abort after 14.6 h, and the next resume
#      attempt then STOPped on a urllib3 RemoteDisconnected / "Remote end closed connection" -- the SERVER
#      was gone, not the experiment). A STOP is a SERVER-DEATH STOP only when its own text, or the log
#      file its own "...; see <path>" message names, contains "RemoteDisconnected" or "Remote end closed
#      connection" verbatim (idle_watchdog_recovery.py classify_stop; no other text ever qualifies) AND
#      the resident server's /health check fails right now. Only then: the STOP is archived to a dated
#      .bak, logged once as "server-death STOP archived", and the tick proceeds to normal selection with
#      a forced geometry restart (see step 5b) instead of a plain swap. Every other STOP exits quietly,
#      logged once per STOP file content (an md5 of its bytes) so a long-lived STOP does not flood the log;
#   3. exit quietly if /home/chao/saea-queue/watchdog.hold exists (the coordinator's pause switch);
#   4. exit quietly if the study MASTER tree ($SAEA_MAIN, never a worktree) is dirty
#      (`git status --porcelain`);
#   5. otherwise ask idle_watchdog_select.py -- a pure, unit-tested function -- for the first entry of
#      ready_chains.json that is enabled, whose carrier is in allowed_carriers, whose hold_file (if any)
#      is absent, and whose flight_commit_file either does not gate it at all (null: the filler entry) or
#      exists, is non-empty, and has no batch-done marker already recorded against that exact commit;
#   5b. UPTIME RESTART (coordinator, 2026-09-28 night): when the selected entry's geometry is already the
#      resident one and no flight is alive, and the resident server process has been up longer than 12 h
#      (SAEA_WATCHDOG_MAX_UPTIME_SECONDS; the server that died was up 14.6 h), the geometry is force-
#      restarted (serving_swap.sh ... --restart, which turns the usual "already resident" no-op into a
#      real stop+start of the SAME geometry) before launching, logged as "uptime restart". The same forced
#      restart also fires after a server-death STOP recovery (step 2), whatever the uptime;
#   6. --dry-run stops here: it only logs and prints the decision, and changes nothing (no swap, no
#      restart, no STOP archival, no launch);
#   7. otherwise: ensure the entry's serving geometry with `serving_swap.sh <geometry> [--restart]` (a
#      no-op when already resident and no restart was called for; a failure refuses the launch and changes
#      nothing else), copy the chain script to its `ext4_copy_target` first when the entry declares one
#      (the filler entry: bash reads a script incrementally and the main checkout moves under merges --
#      see filler_queue.sh's own header), then launch it as a Windows Scheduled Task through
#      saea_task.ps1 -Start -- the SAME mechanism serving_swap.sh uses to start a serving task -- so the
#      chain's own batch driver, registration gate and flight-worktree checkout apply exactly as they do
#      when a coordinator queue launches it by hand. The watchdog exits immediately once the launch call
#      returns; the chain then runs for its own (possibly hours-long) duration under its own scheduled
#      task, independent of this tick.
#
# It never edits a record (the STOP archival in step 2 is the one exception, and only for a STOP this
# script itself proves is a dead server, never a real failure), never starts a CPU sidecar, and never
# touches a hold file (present or absent) -- it only reads them. Single-instance and idempotent: a PID
# lock file with a dead-pid check (SAEA_WATCHDOG_LOCK) makes an overlapping tick exit quietly instead of
# queuing or racing a second one.
#
# Flags: --dry-run (decide and log/print; swap, restart, archive and launch nothing).
# Environment overrides (all optional; for the test harness and for running by hand): SAEA_READY_CHAINS,
# SAEA_WATCHDOG_LOG, SAEA_WATCHDOG_LOCK, SAEA_WATCHDOG_HOLD, SAEA_WATCHDOG_STOP_SEEN,
# SAEA_WATCHDOG_TASK_NAME, SAEA_WATCHDOG_MAX_UPTIME_SECONDS, SAEA_PYTHON, plus every serving_lib.sh /
# queue_lib.sh override (SAEA_MAIN, SAEA_RUNTIME_ROOT, SAEA_SERVING_SWAP, SAEA_SERVING_SESSION,
# SAEA_DATA, ...).
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=queue_lib.sh
source "$HERE/queue_lib.sh"

PY=${SAEA_PYTHON:-/home/chao/.venvs/speechrl/bin/python}
CONFIG=${SAEA_READY_CHAINS:-$HERE/ready_chains.json}
LOG=${SAEA_WATCHDOG_LOG:-$SAEA_RUNTIME_ROOT/watchdog.out}
LOCK=${SAEA_WATCHDOG_LOCK:-$SAEA_RUNTIME_ROOT/watchdog.lock}
HOLD=${SAEA_WATCHDOG_HOLD:-/home/chao/saea-queue/watchdog.hold}
STOP_SEEN=${SAEA_WATCHDOG_STOP_SEEN:-$SAEA_RUNTIME_ROOT/watchdog-stop-seen}
TASK_NAME=${SAEA_WATCHDOG_TASK_NAME:-SAEA-Watchdog-Chain}
MAX_UPTIME_SECONDS=${SAEA_WATCHDOG_MAX_UPTIME_SECONDS:-43200}
SS=${SAEA_SERVING_SESSION:-$SAEA_MAIN/scripts/serving_session.sh}

DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    -h|--help) sed -n '2,68p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "idle_watchdog: unknown argument $1" >&2; exit 64 ;;
  esac
  shift
done

ql_init "$LOG"
field() { "$PY" -c "import json,sys; d=json.loads(sys.argv[1]); v=d.get(sys.argv[2]); print('' if v is None else v)" "$1" "$2"; }

# ---- single-instance: a PID lock file with a dead-pid check ----
if [ -f "$LOCK" ]; then
  OLD=$(cat "$LOCK" 2>/dev/null)
  if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
    ql_say "another idle_watchdog tick is alive (pid $OLD); exiting quietly"
    exit 0
  fi
  ql_say "stale lock ($LOCK: pid ${OLD:-<empty>} not alive); taking over"
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

# ---- 1. a flight/driver/swap/filler/queue process already alive ----
wd_busy() {
  local reasons="" out
  if out=$(saea_flight_alive); then reasons="flight: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-200)"; fi
  if out=$(saea_swap_pending); then reasons="${reasons:+$reasons; }swap pending: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-200)"; fi
  if pgrep -f '[f]iller_queue\.sh' >/dev/null 2>&1; then reasons="${reasons:+$reasons; }filler_queue.sh alive"; fi
  if pgrep -f '[s]aea-queue/queue_[^ ]*\.sh' >/dev/null 2>&1; then reasons="${reasons:+$reasons; }a coordinator queue script is alive"; fi
  [ -n "$reasons" ] || return 1
  printf '%s' "$reasons"
}
if REASONS=$(wd_busy); then
  ql_say "busy, exiting quietly: $REASONS"
  exit 0
fi

# a resident server's /health, straight on the port -- the ONLY thing that tells a crashed process
# (session.json still says "resident") from a healthy one.
wd_health_ok() {
  command -v curl >/dev/null 2>&1 || return 1
  local code
  code=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://$SAEA_SERVING_HOST:$SAEA_SERVING_PORT/health" 2>/dev/null)
  [ "$code" = "200" ]
}

# ---- 2. batch-STOP: never launched onto, except a proven SERVER-DEATH STOP (see header) ----
FORCE_RESTART=0
if [ -e "$QL_STOP" ]; then
  CLASSIFY=$("$PY" -B "$HERE/idle_watchdog_recovery.py" classify-stop --stop-file "$QL_STOP")
  SERVER_DEATH=$(printf '%s\n' "$CLASSIFY" | sed -n '1p')
  LOG_NAMED=$(printf '%s\n' "$CLASSIFY" | sed -n '2p')
  if [ "$SERVER_DEATH" = "true" ] && ! wd_health_ok; then
    BAK="$QL_STOP.$(date -u +%Y%m%dT%H%M%SZ).bak"
    mv "$QL_STOP" "$BAK"
    ql_say "server-death STOP archived to $BAK (RemoteDisconnected/Remote end closed connection${LOG_NAMED:+ in $LOG_NAMED}, /health failing): $(head -1 "$BAK")"
    FORCE_RESTART=1
    # fall through to the normal gates and selection below -- this is the one case that does NOT exit here
  else
    HASH=$(md5sum "$QL_STOP" 2>/dev/null | cut -d' ' -f1)
    PREV=$(cat "$STOP_SEEN" 2>/dev/null || true)
    if [ "$HASH" != "$PREV" ]; then
      ql_say "batch-STOP present, refusing to launch anything: $(head -1 "$QL_STOP")"
      printf '%s' "$HASH" > "$STOP_SEEN"
    fi
    exit 0
  fi
fi

# ---- 3. the coordinator's pause switch ----
if [ -e "$HOLD" ]; then
  ql_say "watchdog held ($HOLD present); exiting quietly"
  exit 0
fi

# ---- 4. the study MASTER tree must be clean (never a worktree) ----
DIRTY=$(git -C "$SAEA_MAIN" status --porcelain 2>&1)
if [ -n "$DIRTY" ]; then
  ql_say "master tree ($SAEA_MAIN) is dirty, exiting quietly: $(printf '%s' "$DIRTY" | head -3 | tr '\n' ';')"
  exit 0
fi

# ---- 5. select the next entry (pure, unit-tested logic in idle_watchdog_select.py) ----
[ -f "$CONFIG" ] || { ql_say "ready-chain list missing: $CONFIG"; exit 1; }
CUR_COMMIT=""
[ -f "$SAEA_RUNTIME_ROOT/batch-flight-commit.txt" ] && CUR_COMMIT=$(head -1 "$SAEA_RUNTIME_ROOT/batch-flight-commit.txt" 2>/dev/null)
SEL_ARGS=(--config "$CONFIG")
[ -n "$CUR_COMMIT" ] && SEL_ARGS+=(--batch-flight-commit "$CUR_COMMIT")
[ -s "$QL_DONE" ] && SEL_ARGS+=(--batch-done-present)
if ! SEL=$("$PY" -B "$HERE/idle_watchdog_select.py" "${SEL_ARGS[@]}"); then
  ql_say "selection helper failed: $SEL"
  exit 1
fi
ql_say "selection: $(printf '%s' "$SEL" | tr -d '\n')"
DECISION=$(field "$SEL" decision)
if [ "$DECISION" != "launch" ]; then
  ql_say "no eligible ready-chain entry this tick"
  exit 0
fi
ENTRY=$(field "$SEL" entry)
GEOMETRY=$(field "$SEL" geometry)
CHAIN_REL=$(field "$SEL" chain_script)
EXT4=$(field "$SEL" ext4_copy_target)
COMMIT=$(field "$SEL" commit)

# ---- 5b. same-geometry uptime restart (coordinator, 2026-09-28 night) ----
wd_current_geometry() {  # the resident geometry's name, or empty when none/unrecognised (never fails the tick)
  local res rc sid
  res=$(bash "$SS" resident 2>/dev/null); rc=$?
  [ $rc -eq 0 ] || return 0
  sid=$(printf '%s' "$res" | "$PY" -c "import json,sys
try:
    print(json.load(sys.stdin).get('session_id') or '')
except Exception:
    print('')" 2>/dev/null)
  [ -n "$sid" ] || return 0
  saea_target_for_session "$sid" 2>/dev/null
  return 0
}
if [ "$FORCE_RESTART" != 1 ]; then
  CUR_GEOM=$(wd_current_geometry)
  if [ -n "$CUR_GEOM" ] && [ "$CUR_GEOM" = "$GEOMETRY" ]; then
    PORT_PID=$(saea_port_server_pids | awk '{print $1; exit}')
    ELAPSED=""
    [ -n "$PORT_PID" ] && ELAPSED=$(ps -o etimes= -p "$PORT_PID" 2>/dev/null | tr -d ' ')
    if [ -n "$ELAPSED" ]; then
      UPTIME_DECISION=$("$PY" -B "$HERE/idle_watchdog_recovery.py" uptime --elapsed-seconds "$ELAPSED" --max-uptime-seconds "$MAX_UPTIME_SECONDS")
      if [ "$UPTIME_DECISION" = "true" ]; then
        FORCE_RESTART=1
        ql_say "uptime restart: $GEOMETRY resident ${ELAPSED}s (> ${MAX_UPTIME_SECONDS}s bound); $([ "$DRY" = 1 ] && echo "would restart" || echo "restarting") before launching '$ENTRY'"
      fi
    fi
  fi
fi

# ---- 6. --dry-run stops here ----
if [ "$DRY" = 1 ]; then
  MSG="DRY-RUN would launch '$ENTRY' on $GEOMETRY (commit ${COMMIT:-none}, restart=$FORCE_RESTART) via $CHAIN_REL"
  ql_say "$MSG"
  echo "$MSG"
  exit 0
fi

# ---- 7. ensure geometry (forcing a restart when step 2 or 5b called for one), then launch through the
#         SAME mechanism the queues use ----
SWAP_ARGS=("$GEOMETRY")
[ "$FORCE_RESTART" = 1 ] && SWAP_ARGS+=(--restart)
ql_say "launching '$ENTRY': ensuring serving geometry ${SWAP_ARGS[*]}"
if ! ql_swap "${SWAP_ARGS[@]}"; then
  ql_say "swap to $GEOMETRY failed; refusing to launch '$ENTRY'"
  exit 1
fi
SCRIPT_ABS="$SAEA_MAIN/$CHAIN_REL"
if [ -n "$EXT4" ]; then
  cp "$SCRIPT_ABS" "$EXT4" || { ql_say "copy of $SCRIPT_ABS to $EXT4 failed; refusing to launch '$ENTRY'"; exit 1; }
  SCRIPT_ABS="$EXT4"
fi
[ -f "$SCRIPT_ABS" ] || { ql_say "chain script $SCRIPT_ABS missing; refusing to launch '$ENTRY'"; exit 1; }
PS=$(saea_powershell)
OUT=$("$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$TASK_NAME" -Script "$SCRIPT_ABS" -Start 2>&1 | tr -d '\r'; exit "${PIPESTATUS[0]}")
RC=$?
ql_say "task launch ($TASK_NAME -> $SCRIPT_ABS) exit $RC: $(printf '%s' "$OUT" | tail -1)"
[ "$RC" = 0 ] || exit 1
ql_say "launched '$ENTRY' at ${COMMIT:-<no flight-commit gate>}"
exit 0
