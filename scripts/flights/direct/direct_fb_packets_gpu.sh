#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The Thinking-core speech-packet preparation chain of the 266-E read on the GPU (owner ruling of 2026-10-11: the CPU sidecar at 16-19 s per
# row is unacceptable; this supersedes scripts/flights/direct/direct_fb_packets.sh, which now refuses unless --allow-cpu).
#
# The 24 GB card holds ONE core, so the GPU encoder pass runs inside a SERVING-SWAP WINDOW that this script owns end to end:
#
#   1  hold the idle watchdog (touch /home/chao/saea-queue/watchdog.hold, remembered if this script created it);
#   2  serving_swap.sh --stop-only          the resident Instruct session is stopped cleanly (its tasks too); the card is empty;
#   3  driver --geometry gpu --roster thinking-smoke-4 --run     4 rows into the GPU legacy cache (the proof of the fixed form);
#   4  driver --geometry gpu --smoke-rate   the measured seconds per row; a projected Fold B encode above the cap stops the window;
#   5  driver --geometry gpu --roster thinking-fold-b --run      the remaining cold rows encoded, then all 1,080 promoted into the
#                                                                empty GPU packet root and the promotion receipt written;
#   6  serving_swap.sh think-np4 --start-only   the Thinking serving session starts (the flight follows; the watchdog hold STAYS);
#   ON ANY FAILURE after step 2: stray encoder server stopped, serving_swap.sh slurp-np4 --start-only restores the Instruct geometry,
#   the hold is removed if this script created it, and the exit code names the failed step. Exit 25 means the RESTORE failed: the card
#   may be EMPTY and the coordinator must act (serving_swap.sh slurp-np4).
# Every event is stamped (UTC) and written to $OUT/window-events.tsv and $OUT/window-summary.json (schema saea-packets-gpu-window-summary-v1).
#
# The driver itself refuses to start while any serving session is resident, anything listens on port 8080, or GPU memory is in use, so a
# window that did not actually empty the card cannot encode. The exposure row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1 must be
# root-countersigned (driver --check-ledger); the script authorises nothing: the row's countersignature is the authorisation.
#
#   bash scripts/flights/direct/direct_fb_packets_gpu.sh --check            every guard, both dry-runs and the swap dry-run; no side effects
#   bash scripts/flights/direct/direct_fb_packets_gpu.sh --run [--stage all|smoke|fold-b|dev2000-added|test-sample-3010] [--max-fold-seconds N]
#   bash scripts/flights/direct/direct_fb_packets_gpu.sh --task             start the Windows task SAEA-Packets-THINK-GPU (survives the session)
# --stage smoke: stop Instruct, the 4-row proof, then restore INSTRUCT (a short window); --stage fold-b: stop Instruct, Fold B, start Thinking.
# --stage dev2000-added (P3.1): stop Instruct, encode the 1,000 DEV-2000-ADDED rows on the GPU (roster thinking-dev2000-added, its own run id, legacy cache
#   and output directory), promote ADDITIVELY into the existing Thinking root under the NEW receipt DEV-2000-ADDED-promotion.json, then start the
#   think-budget-np4 session (the replicate flights need the budget session). The exposure row SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1 must be
#   root-countersigned; --check --stage dev2000-added runs every guard and the DEV dry-run only (the Fold B dry-runs are skipped: their root is populated).
# --stage test-sample-3010 (successor 3): the dev2000-added form on the signed SLURP test SAMPLE (roster thinking-test-sample-3010: 3,010 slurp:test: rows, split role
#   final-report, its own run id SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1, legacy cache and output directory): stop Instruct, encode, promote ADDITIVELY under the
#   NEW receipt TEST-SAMPLE-3010-promotion.json, start think-budget-np4. The roster is a final-report role: the driver refuses (every mode, before any media is opened)
#   unless contracts.plan.require_owner_split_allowance accepts the pinned owner allowance, which must PERMIT this run id as a preparation id; the exposure row must be
#   root-countersigned. Exit 27 on a failure of the sample encoder/promotion.
# Exit codes: 0 ok; 2 dirty tree; 3 a dry-run refused; 4 another llama-server or a packet driver; 7 a flight is alive; 8 host memory, disk
# or the swap dry-run short; 9 the Thinking serving entry is missing; 11 the exposure row is not countersigned; 12 task start failed;
# 14 the Instruct stop failed; 20 smoke failed; 21 Fold B failed; 26 DEV-2000-ADDED failed; 27 test-sample-3010 failed; 22 an encoder server did not go away; 23 the measured rate is
# unacceptable; 24 the Thinking start failed; 25 the Instruct RESTORE failed; 64 usage.
set -u
MODE=
STAGE=all
MAX_FOLD_SECONDS=${PACKETS_MAX_FOLD_SECONDS:-3000}
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE=check ;;
    --run) MODE=run ;;
    --task) MODE=task ;;
    --stage) STAGE=${2:-}; shift ;;
    --max-fold-seconds) MAX_FOLD_SECONDS=${2:-}; shift ;;
    *) echo "unknown argument $1"; exit 64 ;;
  esac
  shift
done
case "$MODE:$STAGE" in
  check:all|run:all|run:smoke|run:fold-b|task:all) ;;
  check:dev2000-added|run:dev2000-added|task:dev2000-added) ;;
  check:test-sample-3010|run:test-sample-3010|task:test-sample-3010) ;;
  *) echo "usage: direct_fb_packets_gpu.sh --check | --run [--stage all|smoke|fold-b|dev2000-added|test-sample-3010] [--max-fold-seconds N] | --task"; exit 64 ;;
esac

REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
PY=${PACKETS_PY:-/home/chao/.venvs/speechrl/bin/python}
DRIVER=$REPO/scripts/slurp_fold_preprocess_thinking.py
SWAP=${PACKETS_SWAP:-$REPO/scripts/flights/batch/serving_swap.sh}
INSTRUCT_TARGET=slurp-np4
THINK_TARGET=think-np4
DEV_ROSTER=thinking-dev2000-added
CHECK_ARGS=()
if [ "$STAGE" = dev2000-added ]; then THINK_TARGET=think-budget-np4; CHECK_ARGS=(--roster "$DEV_ROSTER"); fi
SAMPLE_ROSTER=thinking-test-sample-3010
if [ "$STAGE" = test-sample-3010 ]; then THINK_TARGET=think-budget-np4; CHECK_ARGS=(--roster "$SAMPLE_ROSTER"); fi
HOLD=${PACKETS_WATCHDOG_HOLD:-/home/chao/saea-queue/watchdog.hold}
DATA_DISK=${PACKETS_DATA_DISK:-/home/chao}
START_FLOOR_GB=${PACKETS_START_FLOOR_GB:-8}
MIN_FREE_DISK_GB=${PACKETS_MIN_FREE_DISK_GB:-5}
GONE_WAIT_SECONDS=${PACKETS_GONE_WAIT_SECONDS:-60}
ENCODER_PORT=8081
OUT=${PACKETS_OUT:-$DATA/prepared/slurp-direct-fb-thinking-packets-gpu-v1}
[ "$STAGE" != dev2000-added ] || OUT=${PACKETS_OUT:-$DATA/prepared/slurp-dev2000-added-thinking-packets-gpu-v1}
[ "$STAGE" != test-sample-3010 ] || OUT=${PACKETS_OUT:-$DATA/prepared/slurp-test-sample-3010-thinking-packets-gpu-v1}
TASK_NAME=SAEA-Packets-THINK-GPU
TASK_ENTRY=$REPO/scripts/flights/direct/direct_fb_packets_gpu_task_entry.sh
[ "$STAGE" != dev2000-added ] || TASK_ENTRY=$REPO/scripts/flights/direct/direct_fb_packets_gpu_dev_task_entry.sh
[ "$STAGE" != test-sample-3010 ] || TASK_ENTRY=$REPO/scripts/flights/direct/direct_fb_packets_gpu_sample_task_entry.sh
export SAEA_MAIN=$REPO SAEA_DATA=$DATA
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
# shellcheck source=../batch/serving_lib.sh
source "$REPO/scripts/flights/batch/serving_lib.sh"

# Recovery labelling (the GPU run id has its OWN file: the CPU run's /home/chao/direct-fb-packets.recovery must never leak into this run).
RECOVERY_FILE=${PACKETS_RECOVERY_FILE:-/home/chao/direct-fb-packets-gpu.recovery}
[ "$STAGE" != dev2000-added ] || RECOVERY_FILE=${PACKETS_RECOVERY_FILE:-/home/chao/direct-fb-packets-gpu-dev2000-added.recovery}
[ "$STAGE" != test-sample-3010 ] || RECOVERY_FILE=${PACKETS_RECOVERY_FILE:-/home/chao/direct-fb-packets-gpu-test-sample-3010.recovery}
SMOKE_ATTEMPT=; FOLD_ATTEMPT=; DEV_ATTEMPT=; SAMPLE_ATTEMPT=; RECOVERY_OF=
# shellcheck disable=SC1090
[ -f "$RECOVERY_FILE" ] && . "$RECOVERY_FILE"
ROSTER_ARGS=()
roster_args() {
  ROSTER_ARGS=()
  local attempt=
  case "$1" in thinking-smoke-4) attempt=$SMOKE_ATTEMPT ;; thinking-fold-b) attempt=$FOLD_ATTEMPT ;; thinking-dev2000-added) attempt=$DEV_ATTEMPT ;; thinking-test-sample-3010) attempt=$SAMPLE_ATTEMPT ;; esac
  [ -z "$attempt" ] || ROSTER_ARGS+=(--attempt-id "$attempt")
  [ -z "$RECOVERY_OF" ] || ROSTER_ARGS+=(--recovery-of "$RECOVERY_OF")
}

RC=0
fail() { echo "REFUSED ($1): $2"; [ "$RC" = 0 ] && RC=$1; return 0; }
ts() { date -u +%FT%TZ; }
driver() { "$PY" -B "$DRIVER" --geometry gpu "$@"; }
available_gb() { if [ -n "${PACKETS_AVAILABLE_GB:-}" ]; then echo "$PACKETS_AVAILABLE_GB"; else free -g | awk '/^Mem:/{print $7}'; fi; }
free_disk_gb() { if [ -n "${PACKETS_FREE_DISK_GB:-}" ]; then echo "$PACKETS_FREE_DISK_GB"; else df -BG --output=avail "$DATA_DISK" | tail -1 | tr -dc '0-9'; fi; }

# ----------------------------------------------------------------------------------------------------------------- guards
runtime_guards() {
  local out avail disk
  if out=$(saea_flight_alive); then fail 7 "a generation flight, lease, batch driver or flight.lock is alive (one experiment in flight): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"; fi
  out=$( { pgrep -af -- "[l]lama-server" 2>/dev/null | grep -v -- "--port $SAEA_SERVING_PORT"; pgrep -af -- '[s]lurp_fold_preprocess_thinking\.py|[s]lurp_evo_fold_preprocess\.py' 2>/dev/null; } | cut -c1-200)
  [ -z "$out" ] || fail 4 "another llama-server (port ${ENCODER_PORT} must be free for the encoder) or a packet driver is up: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"
  avail=$(available_gb)
  if [ -z "$avail" ] || [ "$avail" -lt "$START_FLOOR_GB" ]; then fail 8 "host-available memory ${avail:-unknown} GB is below the ${START_FLOOR_GB} GB start floor"; fi
  disk=$(free_disk_gb)
  if [ -z "$disk" ] || [ "$disk" -lt "$MIN_FREE_DISK_GB" ]; then fail 8 "free space on $DATA_DISK is ${disk:-unknown} GB, below ${MIN_FREE_DISK_GB} GB"; fi
}

registry_guards() {
  local dirt
  git -C "$REPO" rev-parse HEAD > /dev/null 2>&1 || { fail 2 "$REPO is not a git checkout"; return 0; }
  dirt=$(git -C "$REPO" status --short | grep -vc '^??')
  [ "$dirt" = "0" ] || fail 2 "dirty tree ($dirt tracked changes); the launch binds a clean, countersigned HEAD"
  driver "${CHECK_ARGS[@]}" --check-ledger > /dev/null || fail 11 "the exposure row for stage $STAGE (SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1, or SAEA-SLURP-DEV2000-ADDED-THINKING-PACKETS-GPU-V1 for dev2000-added, or SAEA-SLURP-TEST-SAMPLE-3010-THINKING-PACKETS-GPU-V1 for test-sample-3010) is absent, inconsistent or not root-countersigned (driver --check-ledger)"
}

dry_runs() {
  local roster out
  for roster in "$@"; do
    roster_args "$roster"
    if ! out=$(driver --roster "$roster" --dry-run "${ROSTER_ARGS[@]}" 2>&1); then
      fail 3 "the driver's dry-run refused for roster $roster: $(printf '%s' "$out" | grep -E 'REFUSES|REFUSED|Error|error' | tail -2 | tr '
' ' ' | cut -c1-400)"
    fi
  done
}

window_dry_run() {  # the swap tool's own preconditions for the stop, and the Thinking serving entries the window ends with
  local out
  if ! out=$(bash "$SWAP" --stop-only --dry-run 2>&1); then
    fail 8 "serving_swap.sh --stop-only --dry-run refused: $(printf '%s' "$out" | tail -1 | cut -c1-300)"
  fi
  saea_geometry "$THINK_TARGET" || { fail 9 "the geometry table has no $THINK_TARGET"; return 0; }
  [ -f "$REPO/$G_SERVING_ENTRY" ] && [ -f "$REPO/$G_MONITOR_ENTRY" ] || fail 9 "the Thinking serving entries are missing ($G_SERVING_ENTRY, $G_MONITOR_ENTRY)"
}

# --------------------------------------------------------------------------------------------------------------- the window
EVENTS=; HOLD_MINE=0; WINDOW_T0=
event() {  # event <name> [detail]
  local line
  line="$(ts)	$1	${2:-}"
  echo "== window $line"
  [ -z "$EVENTS" ] || printf '%s\n' "$line" >> "$EVENTS"
}

write_summary() {  # write_summary <result> <exit>
  [ -n "$EVENTS" ] || return 0
  python3 - "$EVENTS" "$OUT/window-summary.json" "$1" "$2" "$STAGE" "$WINDOW_T0" <<'PY'
import json, sys
from datetime import datetime, timezone
events_path, out_path, result, code, stage, started = sys.argv[1:7]
events = []
for line in open(events_path, encoding="utf-8"):
    stamp, _, rest = line.rstrip("\n").partition("\t")
    name, _, detail = rest.partition("\t")
    events.append({"at": stamp, "event": name, "detail": detail})
json.dump({"schema": "saea-packets-gpu-window-summary-v1", "result": result, "exit": int(code), "stage": stage,
           "window_started_at": started, "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "events": events},
          open(out_path, "w", encoding="utf-8"), indent=2, sort_keys=True)
PY
}

swap() {  # swap <args...>: the swap tool; its summary line is kept next to the window events
  local out rc
  out=$(bash "$SWAP" "$@" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    swap: /'
  printf '%s\n' "$out" | tail -1 >> "$OUT/swap-summaries.jsonl"
  return "$rc"
}

stop_stray_encoder() {  # the driver stops its own server; this only reaps one that survived a killed driver (exactly the encoder port)
  local pids waited=0 pattern="[l]lama-server --host 127.0.0.1 --port $ENCODER_PORT( |\$)"
  pids=$(pgrep -f -- "$pattern" 2>/dev/null)
  [ -n "$pids" ] || return 0
  event encoder-stray "SIGTERM to $(echo "$pids" | tr '
' ' ')"
  kill $pids 2>/dev/null
  while [ -n "$(pgrep -f -- "$pattern" 2>/dev/null)" ]; do
    if [ "$waited" -ge "$GONE_WAIT_SECONDS" ]; then kill -9 $pids 2>/dev/null; break; fi
    sleep 2; waited=$((waited + 2))
  done
}

encoder_gone() {
  local waited=0
  while [ -n "$(pgrep -af -- "[l]lama-server --host 127.0.0.1 --port $ENCODER_PORT( |$)" 2>/dev/null)" ]; do
    [ "$waited" -ge "$GONE_WAIT_SECONDS" ] && return 1
    sleep 2; waited=$((waited + 2))
  done
  return 0
}

release_hold() { [ "$HOLD_MINE" = 1 ] && rm -f "$HOLD" && event watchdog-hold-released "created by this window"; return 0; }

finish_failed() {  # finish_failed <code> <what>: restore the Instruct geometry, report, exit
  local code=$1 what=$2 rrc
  event failed "$what (exit $code)"
  stop_stray_encoder
  event restore-start "$INSTRUCT_TARGET --start-only"
  swap "$INSTRUCT_TARGET" --start-only
  rrc=$?
  if [ "$rrc" = 0 ]; then
    event restore-done "Instruct geometry ready"
    release_hold
    write_summary "failed-restored" "$code"
    echo "WINDOW FAILED ($what): the Instruct geometry is restored; exit $code"
    exit "$code"
  fi
  event restore-failed "serving_swap exit $rrc: the card may be EMPTY; run bash scripts/flights/batch/serving_swap.sh $INSTRUCT_TARGET"
  write_summary "failed-unrestored" 25
  echo "WINDOW FAILED ($what) AND THE RESTORE FAILED (serving_swap exit $rrc): the card may be EMPTY; the watchdog hold is left in place; exit 25"
  exit 25
}

run_attempt() {  # run_attempt <roster> <failcode>
  local roster=$1 failcode=$2 rc
  roster_args "$roster"
  event "attempt-$roster-start"
  driver --roster "$roster" --run --promote-workers 8 "${ROSTER_ARGS[@]}" --output "$OUT/encoder-report-$roster.json"
  rc=$?
  event "attempt-$roster-end" "exit $rc"
  [ "$rc" = 0 ] || finish_failed "$failcode" "driver $roster exit $rc"
  encoder_gone || finish_failed 22 "an encoder server is still up on port $ENCODER_PORT after $roster"
}

rate_gate() {
  local out rc
  roster_args thinking-smoke-4
  out=$(driver --smoke-rate --max-fold-seconds "$MAX_FOLD_SECONDS" "${ROSTER_ARGS[@]}" 2>&1); rc=$?
  printf '%s\n' "$out" | sed 's/^/    rate: /'
  event smoke-rate "$(printf '%s' "$out" | tr '\n' ' ' | cut -c1-300) (exit $rc)"
  [ "$rc" = 0 ] || finish_failed 23 "the measured GPU rate projects Fold B beyond ${MAX_FOLD_SECONDS}s or could not be read"
}

echo "direct_fb_packets_gpu $MODE stage $STAGE $(ts) HEAD $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null)"

case "$MODE" in
  check)
    registry_guards; runtime_guards
    if [ "$STAGE" = dev2000-added ]; then dry_runs "$DEV_ROSTER"; elif [ "$STAGE" = test-sample-3010 ]; then dry_runs "$SAMPLE_ROSTER"; else dry_runs thinking-smoke-4 thinking-fold-b; fi
    window_dry_run
    [ "$RC" = 0 ] && echo "CHECK PASS: every guard, both dry-runs and the swap dry-run; nothing was started" || echo "CHECK REFUSED (first code $RC)"
    exit "$RC"
    ;;
  task)
    registry_guards; runtime_guards
    if [ "$STAGE" = dev2000-added ]; then dry_runs "$DEV_ROSTER"; elif [ "$STAGE" = test-sample-3010 ]; then dry_runs "$SAMPLE_ROSTER"; else dry_runs thinking-smoke-4 thinking-fold-b; fi
    window_dry_run
    [ "$RC" = 0 ] || { echo "TASK REFUSED (first code $RC); nothing was started"; exit "$RC"; }
    PS=$(saea_powershell)
    out=$("$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$TASK_NAME" -Script "$TASK_ENTRY" -Start 2>&1 | tr -d '\r'; exit "${PIPESTATUS[0]}")
    trc=$?
    printf '%s\n' "$out" | sed 's/^/    ps: /'
    [ "$trc" = 0 ] || { echo "the task did not start (exit $trc)"; exit 12; }
    echo "TASK STARTED: $TASK_NAME; follow /home/chao/direct-fb-packets-gpu-*.log (newest)"
    exit 0
    ;;
  run)
    registry_guards
    runtime_guards
    case "$STAGE" in
      smoke) dry_runs thinking-smoke-4 ;;
      fold-b) dry_runs thinking-fold-b ;;
      all) dry_runs thinking-smoke-4 thinking-fold-b ;;
      dev2000-added) dry_runs "$DEV_ROSTER" ;;
      test-sample-3010) dry_runs "$SAMPLE_ROSTER" ;;
    esac
    window_dry_run
    [ "$RC" = 0 ] || { echo "RUN REFUSED (first code $RC); nothing was started"; exit "$RC"; }
    mkdir -p "$OUT" || exit 8
    EVENTS=$OUT/window-events.tsv
    : > "$EVENTS"
    WINDOW_T0=$(ts)
    event window-start "stage $STAGE, rate cap ${MAX_FOLD_SECONDS}s for the Fold B encode"
    if [ ! -e "$HOLD" ]; then
      mkdir -p "$(dirname "$HOLD")" && : > "$HOLD" && HOLD_MINE=1
      event watchdog-hold "created $HOLD"
    else
      event watchdog-hold "already present $HOLD"
    fi
    event instruct-stop-start "serving_swap.sh --stop-only"
    swap --stop-only
    SRC=$?
    if [ "$SRC" != 0 ]; then finish_failed 14 "serving_swap.sh --stop-only exit $SRC"; fi
    event instruct-stopped "the card is empty"
    if [ "$STAGE" = all ] || [ "$STAGE" = smoke ]; then
      run_attempt thinking-smoke-4 20
      rate_gate
    fi
    if [ "$STAGE" = all ] || [ "$STAGE" = fold-b ]; then
      run_attempt thinking-fold-b 21
    fi
    if [ "$STAGE" = test-sample-3010 ]; then
      run_attempt "$SAMPLE_ROSTER" 27      # exit 27: the sample encoder/promotion failed (final-report role: the driver already passed the allowance guard)
    fi
    if [ "$STAGE" = dev2000-added ]; then
      run_attempt "$DEV_ROSTER" 26      # exit 26: the DEV encoder/promotion failed (no rate gate: the Fold B smoke proved the GPU form)
    fi
    if [ "$STAGE" = smoke ]; then
      event instruct-restore-start "stage smoke ends on the Instruct geometry"
      swap "$INSTRUCT_TARGET" --start-only
      RRC=$?
      if [ "$RRC" != 0 ]; then
        event restore-failed "serving_swap exit $RRC"; write_summary "smoke-done-unrestored" 25
        echo "SMOKE DONE but the Instruct restore failed (exit $RRC): the card may be EMPTY; hold left in place"; exit 25
      fi
      event instruct-restored "Instruct geometry ready"
      release_hold
      write_summary "smoke-done" 0
      echo "SMOKE DONE: Instruct restored; read $OUT/encoder-report-thinking-smoke-4.json; then --run --stage fold-b"
      exit 0
    fi
    event think-start "serving_swap.sh $THINK_TARGET --start-only"
    swap "$THINK_TARGET" --start-only
    TRC=$?
    if [ "$TRC" != 0 ]; then finish_failed 24 "serving_swap.sh $THINK_TARGET --start-only exit $TRC"; fi
    event think-ready "Thinking serving session ready; watchdog hold stays in place"
    event window-end "packets prepared, Thinking resident"
    write_summary "ok" 0
    echo "WINDOW OK: packets promoted, the Thinking serving session is resident and ready; the watchdog hold $HOLD STAYS (remove it after the Instruct restore, package README step 9)."
    if [ "$STAGE" = dev2000-added ]; then
      echo "NEXT: python -B scripts/slurp_fold_preprocess_thinking.py --roster $DEV_ROSTER --pin-receipt   (verification), then thinking_system_dev_derive_cells.py --require-receipt and the DEV package writer (package README, step 3)"
    elif [ "$STAGE" = test-sample-3010 ]; then
      echo "NEXT: python -B scripts/slurp_fold_preprocess_thinking.py --roster $SAMPLE_ROSTER --pin-receipt   (verification), then successor3_thinking_derive_cells.py --require-receipt and the successor-3 package writer (package README, step 4)"
    else
      echo "NEXT: python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt   (prints; add --write to substitute the zero sentinel in the two baselines)"
    fi
    exit 0
    ;;
esac
