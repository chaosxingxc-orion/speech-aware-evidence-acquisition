#!/bin/bash
# P3.2: the Thinking speech packets of ONE carrier on the GPU, inside a SERVING-SWAP WINDOW that this script owns end to end (precedent: scripts/flights/direct/direct_fb_packets_gpu.sh).
# The 24 GB card holds ONE core, so the encoder runs with every serving session stopped:
#
#   1  hold the idle watchdog (touch /home/chao/saea-queue/watchdog.hold, remembered if this script created it);
#   2  serving_swap.sh --stop-only             the resident session is stopped cleanly (its tasks too); the card is empty;
#   3  a2t:      the driver, stage smoke (4 rows into the legacy cache only), the rate gate, stage full (the rest, then all 400 promoted, receipt written);
#      e21/e22:  per pass (smoke, then -- only if the smoke passed -- full): preflight, start the Thinking GPU encoder session under the pass's session id, hold the root lease,
#                core.flight.cli prepare-window-features, release the lease, stop the session NORMALLY, then the model-free post stage (audit, provenance, formal packets) and verify;
#   4  the Thinking serving session starts again (serving_swap.sh think-budget-np4 --start-only); the watchdog hold STAYS (the chain that follows owns its release).
# ON ANY FAILURE after step 2: a stray encoder is stopped, serving_swap.sh think-budget-np4 --start-only restores the Thinking geometry, the hold is removed if this script
# created it, and the exit code names the failed step. Exit 25 means the RESTORE failed: the card may be EMPTY and the coordinator must act.
# The exposure rows must be root-countersigned (the driver / stage preflight check them); the script authorises nothing.
#
#   bash scripts/flights/carriers/carrier_think_packets_gpu.sh --check <a2t|e21|e22>     every model-free guard and dry-run; no side effects
#   bash scripts/flights/carriers/carrier_think_packets_gpu.sh --run   <a2t|e21|e22>     the window
# Exit codes: 0 ok; 2 dirty tree; 3 a dry-run / preflight refused; 4 another llama-server or a packet driver; 7 a flight is alive; 8 host memory, disk or the swap dry-run short;
# 11 the exposure row is not countersigned; 14 the stop failed; 20 the smoke failed; 21 the full pass failed; 22 an encoder server did not go away; 23 the measured rate or
# the smoke is unacceptable; 24 the Thinking start failed; 25 the RESTORE failed; 64 usage.
set -u
MODE=; CARRIER=
[ $# -eq 2 ] || { echo "usage: carrier_think_packets_gpu.sh --check|--run <a2t|e21|e22>"; exit 64; }
case "$1" in --check) MODE=check ;; --run) MODE=run ;; *) echo "usage: carrier_think_packets_gpu.sh --check|--run <a2t|e21|e22>"; exit 64 ;; esac
case "$2" in a2t|e21|e22) CARRIER=$2 ;; *) echo "carrier must be a2t, e21 or e22"; exit 64 ;; esac

REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$REPO/scripts/lib/data_root.sh" && saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
PY=${PACKETS_PY:-/home/chao/.venvs/speechrl/bin/python}
CP=$REPO/scripts/flights/carriers
SWAP=${PACKETS_SWAP:-$REPO/scripts/flights/batch/serving_swap.sh}
THINK_TARGET=think-budget-np4
HOLD=${PACKETS_WATCHDOG_HOLD:-/home/chao/saea-queue/watchdog.hold}
DATA_DISK=${PACKETS_DATA_DISK:-/home/chao}
START_FLOOR_GB=${PACKETS_START_FLOOR_GB:-8}
MIN_FREE_DISK_GB=${PACKETS_MIN_FREE_DISK_GB:-5}
GONE_WAIT_SECONDS=${PACKETS_GONE_WAIT_SECONDS:-60}
ENC_READY_SECONDS=${PACKETS_ENCODER_READY_SECONDS:-1800}
MAX_FULL_ENCODE_SECONDS=${PACKETS_MAX_FULL_SECONDS:-3600}
LOCK=${PACKETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
OUT=${PACKETS_OUT:-$DATA/prepared/carrier-think-packets-$CARRIER-gpu-v1}
export SAEA_MAIN=$REPO SAEA_DATA=$DATA SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
# shellcheck source=../batch/serving_lib.sh
source "$REPO/scripts/flights/batch/serving_lib.sh"

RC=0
fail() { echo "REFUSED ($1): $2"; [ "$RC" = 0 ] && RC=$1; return 0; }
ts() { date -u +%FT%TZ; }
available_gb() { if [ -n "${PACKETS_AVAILABLE_GB:-}" ]; then echo "$PACKETS_AVAILABLE_GB"; else free -g | awk '/^Mem:/{print $7}'; fi; }
free_disk_gb() { if [ -n "${PACKETS_FREE_DISK_GB:-}" ]; then echo "$PACKETS_FREE_DISK_GB"; else df -BG --output=avail "$DATA_DISK" | tail -1 | tr -dc '0-9'; fi; }
a2t_driver() { "$PY" -B "$CP/carrier_think_packets.py" a2t "$@"; }
stage() { "$PY" -B "$CP/carrier_think_windows_stage.py" "$@"; }

# ----------------------------------------------------------------------------------------------------------------- guards
runtime_guards() {
  local out avail disk
  if out=$(saea_flight_alive); then fail 7 "a generation flight, lease, batch driver or flight.lock is alive (one experiment in flight): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"; fi
  out=$( { pgrep -af -- "[l]lama-server" 2>/dev/null | grep -v -- "--port $SAEA_SERVING_PORT"; pgrep -af -- '[c]arrier_think_packets\.py|[s]lurp_fold_preprocess_thinking\.py|[s]lurp_evo_fold_preprocess\.py' 2>/dev/null; } | cut -c1-200)
  [ -z "$out" ] || fail 4 "another llama-server or a packet driver is up: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"
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
}

pass_dry_runs() {  # the model-free guards of every pass of this carrier (nothing is started)
  local out
  if [ "$CARRIER" = a2t ]; then
    a2t_driver --stage smoke --check-ledger > /dev/null || fail 11 "the A2T exposure row is absent, inconsistent or not root-countersigned"
    out=$(a2t_driver --stage smoke --dry-run 2>&1) || fail 3 "the A2T dry-run refused: $(printf '%s' "$out" | tail -2 | tr '\n' ' ' | cut -c1-300)"
    return 0
  fi
  out=$("$PY" -B "$CP/carrier_think_windows.py" materialize --carrier "$CARRIER" --dry-run 2>&1) || fail 3 "the inventory materialization refused: $(printf '%s' "$out" | tail -2 | tr '\n' ' ' | cut -c1-300)"
  # preflight needs the inventories ON the data root; a --check before the first materialization reports exactly that and nothing else
  out=$(stage preflight --carrier "$CARRIER" --pass smoke --tolerate-unmaterialized 2>&1) || fail 3 "the smoke preflight refused: $(printf '%s' "$out" | grep -E '"problems"' -A6 | tr '\n' ' ' | cut -c1-400)"
}

window_dry_run() {
  local out
  if ! out=$(bash "$SWAP" --stop-only --dry-run 2>&1); then fail 8 "serving_swap.sh --stop-only --dry-run refused: $(printf '%s' "$out" | tail -1 | cut -c1-300)"; fi
  saea_geometry "$THINK_TARGET" || { fail 9 "the geometry table has no $THINK_TARGET"; return 0; }
}

# --------------------------------------------------------------------------------------------------------------- the window
EVENTS=; HOLD_MINE=0; WINDOW_T0=; ENC_PID=; LEASE_PID=
event() { local line; line="$(ts)	$1	${2:-}"; echo "== window $line"; [ -z "$EVENTS" ] || printf '%s\n' "$line" >> "$EVENTS"; }
swap() { local out rc; out=$(bash "$SWAP" "$@" 2>&1); rc=$?; printf '%s\n' "$out" | sed 's/^/    swap: /'; printf '%s\n' "$out" | tail -1 >> "$OUT/swap-summaries.jsonl"; return "$rc"; }
release_hold() { [ "$HOLD_MINE" = 1 ] && rm -f "$HOLD" && event watchdog-hold-released "created by this window"; return 0; }

stop_stray_encoder() {  # only reaps a server that survived a killed driver / a failed pass: the encoder ports 8080 (window) and 8081 (A2T sidecar)
  local pids waited=0
  [ -z "$LEASE_PID" ] || { kill "$LEASE_PID" 2>/dev/null; LEASE_PID=; }
  [ -z "$ENC_PID" ] || { kill "$ENC_PID" 2>/dev/null; ENC_PID=; }
  pids=$(pgrep -f -- "[l]lama-server --host 127.0.0.1 --port 808[01]" 2>/dev/null)
  [ -n "$pids" ] || return 0
  event encoder-stray "SIGTERM to $(echo "$pids" | tr '\n' ' ')"
  kill $pids 2>/dev/null
  while [ -n "$(pgrep -f -- "[l]lama-server --host 127.0.0.1 --port 808[01]" 2>/dev/null)" ]; do
    if [ "$waited" -ge "$GONE_WAIT_SECONDS" ]; then kill -9 $pids 2>/dev/null; break; fi
    sleep 2; waited=$((waited + 2))
  done
}
encoder_gone() { local waited=0; while [ -n "$(pgrep -af -- "[l]lama-server --host 127.0.0.1 --port 808[01]" 2>/dev/null)" ]; do [ "$waited" -ge "$GONE_WAIT_SECONDS" ] && return 1; sleep 2; waited=$((waited + 2)); done; return 0; }

write_summary() {  # write_summary <result> <exit>
  [ -n "$EVENTS" ] || return 0
  "$PY" - "$EVENTS" "$OUT/window-summary.json" "$1" "$2" "$CARRIER" "$WINDOW_T0" <<'PY'
import json, sys
from datetime import datetime, timezone
events_path, out_path, result, code, carrier, started = sys.argv[1:7]
events = []
for line in open(events_path, encoding="utf-8"):
    stamp, _, rest = line.rstrip("\n").partition("\t")
    name, _, detail = rest.partition("\t")
    events.append({"at": stamp, "event": name, "detail": detail})
json.dump({"schema": "saea-carrier-packets-gpu-window-summary-v1", "result": result, "exit": int(code), "carrier": carrier, "window_started_at": started,
           "written_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "events": events}, open(out_path, "w", encoding="utf-8"), indent=2, sort_keys=True)
PY
}

finish_failed() {  # finish_failed <code> <what>: restore the Thinking geometry, report, exit
  local code=$1 what=$2 rrc
  event failed "$what (exit $code)"
  stop_stray_encoder
  event restore-start "$THINK_TARGET --start-only"
  swap "$THINK_TARGET" --start-only; rrc=$?
  if [ "$rrc" = 0 ]; then
    event restore-done "Thinking geometry ready"; release_hold; write_summary "failed-restored" "$code"
    echo "WINDOW FAILED ($what): the Thinking geometry is restored; exit $code"; exit "$code"
  fi
  event restore-failed "serving_swap exit $rrc: the card may be EMPTY; run bash scripts/flights/batch/serving_swap.sh $THINK_TARGET"
  write_summary "failed-unrestored" 25
  echo "WINDOW FAILED ($what) AND THE RESTORE FAILED (serving_swap exit $rrc): the card may be EMPTY; the watchdog hold is left in place; exit 25"; exit 25
}

jget() { "$PY" -c 'import json,sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }

window_pass() {  # window_pass <smoke|full> <failcode> : one Earnings window pass (encode under a root lease), then the model-free post stage
  local which=$1 failcode=$2 pf run attempt session exp cell model token fifo waited=0 rc enc_log="$OUT/encoder-$which.log"
  pf=$(stage preflight --carrier "$CARRIER" --pass "$which" 2> "$OUT/preflight-$which.err") || finish_failed 3 "the $which preflight refused: $(printf '%s' "$pf" | tr '\n' ' ' | cut -c1-300)"
  run=$(printf '%s' "$pf" | jget run_id); attempt=$(printf '%s' "$pf" | jget attempt_id); session=$(printf '%s' "$pf" | jget session_id)
  exp=$(printf '%s' "$pf" | jget experiment); cell=$(printf '%s' "$pf" | jget cell); model=$(printf '%s' "$pf" | jget model_fragment)
  token=$DATA/coordination/$cell.prepare-window-features-lease.json
  mkdir -p "$DATA/analysis/$run" "$(printf '%s' "$pf" | jget cache_dir)"
  event "pass-$which-start" "$run session $session"
  bash "$REPO/scripts/serving_session.sh" start "$model" --session-id "$session" --port 8080 > "$enc_log" 2>&1 &
  ENC_PID=$!
  while [ ! -f "$DATA/serving/$session/session.json" ] || ! curl -sf "http://127.0.0.1:8080/health" > /dev/null 2>&1; do
    kill -0 "$ENC_PID" 2>/dev/null || finish_failed "$failcode" "the encoder session exited before it was ready ($(tail -c 300 "$enc_log" | tr '\n' ' '))"
    [ "$waited" -ge "$ENC_READY_SECONDS" ] && finish_failed "$failcode" "the encoder session was not ready after ${ENC_READY_SECONDS}s"
    sleep 5; waited=$((waited + 5))
  done
  event "pass-$which-encoder-up" "$session"
  fifo=$OUT/lease-$which.fifo; rm -f "$fifo"; mkfifo "$fifo"
  ( exec 3<>"$fifo"; "$PY" -B -m speech_aware_evidence_acquisition.core.flight.lease_cli --stage prepare-window-features \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" --experiment "$exp" --cell "$cell" --owner "root-$cell" \
      --expected-session-id "$session" --token-output "coordination/$cell.prepare-window-features-lease.json" <&3 > "$OUT/lease-$which.out" 2>&1 ) &
  LEASE_PID=$!
  waited=0; while [ ! -f "$token" ]; do
    [ "$waited" -ge 120 ] && finish_failed "$failcode" "the lease token never appeared ($(tail -c 300 "$OUT/lease-$which.out" | tr '\n' ' '))"
    sleep 1; waited=$((waited + 1))
  done
  "$PY" -B -m speech_aware_evidence_acquisition.core.flight.cli prepare-window-features --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --cell "$cell" --expected-session-id "$session" --lease-token-file "$token" --output "$DATA/analysis/$run/window-encoding.json" \
      > "$OUT/encode-$which.log" 2>&1; rc=$?
  timeout 5 bash -c "echo release > $fifo" > /dev/null 2>&1; sleep 3; wait "$LEASE_PID" 2>/dev/null; LEASE_PID=
  event "pass-$which-encode-end" "exit $rc"
  [ "$rc" = 0 ] || finish_failed "$failcode" "prepare-window-features exit $rc ($(tail -c 300 "$OUT/encode-$which.log" | tr '\n' ' '))"
  [ ! -f "$token" ] || finish_failed "$failcode" "the lease token is still present after the release"
  bash "$REPO/scripts/serving_session.sh" stop --session-id "$session" > "$OUT/stop-$which.log" 2>&1
  wait "$ENC_PID" 2>/dev/null; ENC_PID=
  encoder_gone || finish_failed 22 "an encoder server is still up after pass $which"
  event "pass-$which-encoder-stopped" "$session"
  stage post --carrier "$CARRIER" --pass "$which" > "$OUT/post-$which.json" 2>&1 || finish_failed "$failcode" "the post stage refused: $(tail -c 400 "$OUT/post-$which.json" | tr '\n' ' ')"
  stage verify --carrier "$CARRIER" --pass "$which" > "$OUT/verify-$which.json" 2>&1 || finish_failed "$failcode" "the verify stage refused: $(tail -c 400 "$OUT/verify-$which.json" | tr '\n' ' ')"
  event "pass-$which-done" "$(tr -d '\n ' < "$OUT/verify-$which.json" | cut -c1-200)"
}

echo "carrier_think_packets_gpu $MODE $CARRIER $(ts) HEAD $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null)"
registry_guards; runtime_guards; pass_dry_runs; window_dry_run
if [ "$MODE" = check ]; then
  [ "$RC" = 0 ] && echo "CHECK PASS: every guard, the dry-runs and the swap dry-run; nothing was started" || echo "CHECK REFUSED (first code $RC)"
  exit "$RC"
fi
[ "$RC" = 0 ] || { echo "RUN REFUSED (first code $RC); nothing was started"; exit "$RC"; }
mkdir -p "$OUT" || exit 8
EVENTS=$OUT/window-events.tsv; : > "$EVENTS"; WINDOW_T0=$(ts)
event window-start "carrier $CARRIER"
if [ "$CARRIER" != a2t ]; then
  "$PY" -B "$CP/carrier_think_windows.py" materialize --carrier "$CARRIER" > "$OUT/materialize.json" 2>&1 || { event failed "inventory materialization refused"; write_summary failed-before-stop 3; echo "REFUSED: the inventory materialization failed: $(tail -c 300 "$OUT/materialize.json")"; exit 3; }
  event inventories-materialized "$(tr -d '\n ' < "$OUT/materialize.json")"
fi
if [ ! -e "$HOLD" ]; then mkdir -p "$(dirname "$HOLD")" && : > "$HOLD" && HOLD_MINE=1; event watchdog-hold "created $HOLD"; else event watchdog-hold "already present $HOLD"; fi
event serving-stop-start "serving_swap.sh --stop-only"
swap --stop-only; SRC=$?
[ "$SRC" = 0 ] || finish_failed 14 "serving_swap.sh --stop-only exit $SRC"
event serving-stopped "the card is empty"
if [ "$CARRIER" = a2t ]; then
  event attempt-smoke-start; a2t_driver --stage smoke --run --workers 1 > "$OUT/a2t-smoke.log" 2>&1; rc=$?; event attempt-smoke-end "exit $rc"
  [ "$rc" = 0 ] || finish_failed 20 "A2T smoke exit $rc ($(tail -c 300 "$OUT/a2t-smoke.log" | tr '\n' ' '))"
  encoder_gone || finish_failed 22 "an encoder server is still up after the A2T smoke"
  a2t_driver --smoke-rate > "$OUT/a2t-rate.log" 2>&1; rc=$?; event smoke-rate "$(tr '\n' ' ' < "$OUT/a2t-rate.log" | cut -c1-300) (exit $rc)"
  [ "$rc" = 0 ] || finish_failed 23 "the measured GPU rate projects the full pass beyond its cap or could not be read"
  event attempt-full-start; a2t_driver --stage full --run --workers 1 --promote-workers 8 > "$OUT/a2t-full.log" 2>&1; rc=$?; event attempt-full-end "exit $rc"
  [ "$rc" = 0 ] || finish_failed 21 "A2T full exit $rc ($(tail -c 300 "$OUT/a2t-full.log" | tr '\n' ' '))"
  encoder_gone || finish_failed 22 "an encoder server is still up after the A2T full pass"
  a2t_driver --verify-receipt > "$OUT/a2t-verify.json" 2>&1 || finish_failed 21 "the A2T receipt did not verify ($(tail -c 300 "$OUT/a2t-verify.json" | tr '\n' ' '))"
else
  window_pass smoke 20
  event smoke-gate "the smoke pass produced and verified its packets artifact; the full pass opens"
  window_pass full 21
fi
event thinking-start "serving_swap.sh $THINK_TARGET --start-only"
swap "$THINK_TARGET" --start-only; TRC=$?
if [ "$TRC" != 0 ]; then event thinking-start-failed "serving_swap exit $TRC"; write_summary "done-thinking-start-failed" 24; echo "PACKETS DONE but the Thinking start failed (exit $TRC); hold left in place"; exit 24; fi
event thinking-ready "Thinking geometry ready; the watchdog hold stays for the chain"
write_summary "done" 0
echo "PACKETS DONE ($CARRIER); next: the next carrier's window, or carrier_think_derive_cells.py --require-receipts"
exit 0
