#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# SUPERSEDED (2026-10-11): the CPU sidecar encodes at 16-19 s per row (about 4.7 h for Fold B) and the owner ruled that rate unacceptable;
# the pass was stopped after 50 rows. The live chain is scripts/flights/direct/direct_fb_packets_gpu.sh (GPU encoder inside a serving-swap
# window, exposure row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-GPU-V1). This script is kept for the record and REFUSES (exit 13) unless
# --allow-cpu is given; with it, every driver call runs `--geometry cpu --allow-cpu` against the CPU run id and the CPU roots.
#
# The Thinking-core speech-packet preparation chain of the 266-E read (owner decision 266-E, 2026-10-11): a CPU-only llama-server
# sidecar (-ngl 0 --no-mmproj-offload, the Thinking decoder AND its own bf16 mmproj) on port 8081, BESIDE the resident GPU session, in
# two attempts of ONE run id (the plan budget is run-cumulative):
#
#   smoke    thinking-smoke-4   the first 4 Fold B rows encoded into the legacy cache only (no packet, no promotion receipt)
#   fold-b   thinking-fold-b    the remaining cold rows (1,076) encoded, then all 1,080 promoted into the empty Thinking packet root
#                               and the promotion receipt EVO-FOLD-B-V2-promotion.json written (create-only)
#
# This is the Thinking sibling of scripts/flights/batch/prep_generic_task_entry.sh: it reuses serving_lib.sh for every
# collision predicate, so the pass cannot collide with the resident serving session (decisions 162 and 163 and the "CPU sidecar
# blocks serving restart" and "serving entry reaper kills sidecars" lessons of scripts/flights/batch/README.md):
#   - refuse while ANY generation flight, lease, batch driver or flight.lock is alive (one experiment in flight);
#   - refuse while another CPU llama-server or a packet preprocess driver is up (one resident CPU sidecar at a time);
#   - refuse unless a GPU serving session is resident and running and no serving swap is pending (saea_sidecar_admission);
#   - refuse while the Thinking GPU session itself is resident (the packets precede the swap);
#   - refuse when host-available memory is below the start floor (the Thinking GGUF plus mmproj is about 21 GB on the CPU) or the
#     data disk is short; a watchdog stops the driver if available memory falls below the runtime floor;
#   - at the end WAIT until no CPU sidecar remains, so a following serving swap (which refuses on a 12 GB host-free reading) finds
#     the host clear. Never start a serving swap while this chain runs.
# It also refuses unless the exposure row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1 is root-countersigned, the tree is
# clean, and the driver's own dry-run of both rosters passes (pins vs lock, roots empty, ledger row present).
#
# It authorises nothing: the row's countersignature is the authorisation, and the run makes exactly the contacts that row declares.
#
#   bash scripts/flights/direct/direct_fb_packets.sh --allow-cpu --check     # every guard + both dry-runs; no side effects
#   bash scripts/flights/direct/direct_fb_packets.sh --run [--stage all|smoke|fold-b]   # foreground (a WSL shell; dies with it)
#   bash scripts/flights/direct/direct_fb_packets.sh --task                  # start the Windows task SAEA-Packets-THINK (survives
#                                                                            # the session) running direct_fb_packets_task_entry.sh
# Exit codes: 0 ok; 2 dirty tree; 3 a dry-run refused; 4 another CPU sidecar; 6 Thinking GPU session resident; 7 a flight is alive;
# 8 host memory or disk short; 10 sidecar admission refused; 11 the exposure row is not countersigned; 12 task start failed;
# 13 the CPU chain is superseded and --allow-cpu was not given; 20 smoke failed; 21 Fold B failed; 22 a sidecar did not go away; 64 usage.
set -u
MODE=
STAGE=all
ALLOW_CPU=0
while [ $# -gt 0 ]; do
  case "$1" in
    --allow-cpu) ALLOW_CPU=1 ;;
    --check) MODE=check ;;
    --run) MODE=run ;;
    --task) MODE=task ;;
    --stage) STAGE=${2:-}; shift ;;
    *) echo "unknown argument $1"; exit 64 ;;
  esac
  shift
done
case "$MODE:$STAGE" in
  check:all|run:all|run:smoke|run:fold-b|task:all) ;;
  *) echo "usage: direct_fb_packets.sh --allow-cpu --check | --run [--stage all|smoke|fold-b] | --task   (SUPERSEDED: use direct_fb_packets_gpu.sh)"; exit 64 ;;
esac
if [ "$ALLOW_CPU" != 1 ]; then
  echo "REFUSED (13): the CPU sidecar chain is SUPERSEDED (16-19 s per row; the owner stopped it after 50 rows). The live chain is bash scripts/flights/direct/direct_fb_packets_gpu.sh. Pass --allow-cpu to run this one for the record."
  exit 13
fi

REPO=${PACKETS_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
PY=${PACKETS_PY:-/home/chao/.venvs/speechrl/bin/python}
DRIVER=$REPO/scripts/slurp_fold_preprocess_thinking.py
THINK_SESSION=serving-slurp-thinking-direct-fold-b-np4-v1
DATA_DISK=${PACKETS_DATA_DISK:-/home/chao}
START_FLOOR_GB=${PACKETS_START_FLOOR_GB:-26}
WATCHDOG_FLOOR_GB=${PACKETS_WATCHDOG_FLOOR_GB:-6}
MIN_FREE_DISK_GB=${PACKETS_MIN_FREE_DISK_GB:-5}
GONE_WAIT_SECONDS=${PACKETS_GONE_WAIT_SECONDS:-180}
OUT=${PACKETS_OUT:-$DATA/prepared/slurp-direct-fb-thinking-packets-v1}
TASK_NAME=SAEA-Packets-THINK
TASK_ENTRY=$REPO/scripts/flights/direct/direct_fb_packets_task_entry.sh
export SAEA_MAIN=$REPO SAEA_DATA=$DATA
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
# shellcheck source=../batch/serving_lib.sh
source "$REPO/scripts/flights/batch/serving_lib.sh"

# Recovery labelling. After a FAILED attempt (contacts counted, no encoder receipt) the driver refuses every default attempt id and demands
# --recovery-of; the Windows task cannot take arguments, so the labels come from an optional shell-syntax file the coordinator writes:
#   SMOKE_ATTEMPT=attempt-packets-thinking-smoke-4-v2   FOLD_ATTEMPT=attempt-packets-thinking-fold-b-v2   RECOVERY_OF=<failed attempt id>
RECOVERY_FILE=${PACKETS_RECOVERY_FILE:-/home/chao/direct-fb-packets.recovery}
SMOKE_ATTEMPT=; FOLD_ATTEMPT=; RECOVERY_OF=
# shellcheck disable=SC1090
[ -f "$RECOVERY_FILE" ] && . "$RECOVERY_FILE"
ROSTER_ARGS=()
roster_args() {  # roster_args <roster>: sets ROSTER_ARGS from the recovery labels
  ROSTER_ARGS=()
  local attempt=
  case "$1" in thinking-smoke-4) attempt=$SMOKE_ATTEMPT ;; thinking-fold-b) attempt=$FOLD_ATTEMPT ;; esac
  [ -z "$attempt" ] || ROSTER_ARGS+=(--attempt-id "$attempt")
  [ -z "$RECOVERY_OF" ] || ROSTER_ARGS+=(--recovery-of "$RECOVERY_OF")
}

RC=0
fail() { echo "REFUSED ($1): $2"; [ "$RC" = 0 ] && RC=$1; return 0; }

available_gb() {
  if [ -n "${PACKETS_AVAILABLE_GB:-}" ]; then echo "$PACKETS_AVAILABLE_GB"; return; fi
  free -g | awk '/^Mem:/{print $7}'
}

free_disk_gb() {
  if [ -n "${PACKETS_FREE_DISK_GB:-}" ]; then echo "$PACKETS_FREE_DISK_GB"; return; fi
  df -BG --output=avail "$DATA_DISK" | tail -1 | tr -dc '0-9'
}

driver() { "$PY" -B "$DRIVER" "$@" --geometry cpu --allow-cpu; }

# The process-level and host guards: cheap, repeated between the two attempts.
runtime_guards() {
  local out
  if out=$(saea_flight_alive); then fail 7 "a generation flight, lease, batch driver or flight.lock is alive (one experiment in flight): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"; fi
  out=$(saea_cpu_sidecars)
  [ -z "$out" ] || fail 4 "a CPU llama-server or a packet preprocess driver is already up (one resident CPU sidecar at a time): $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-240)"
  if [ -f "$DATA/serving/$THINK_SESSION/session.json" ] && [ ! -f "$DATA/serving/$THINK_SESSION/session-stop.json" ]; then
    fail 6 "the Thinking GPU session $THINK_SESSION is recorded resident; the packets are prepared BEFORE the serving swap"
  fi
  if ! out=$(saea_sidecar_admission "${SAEA_SERVING_SESSION:-$REPO/scripts/serving_session.sh}"); then
    fail 10 "$out"
  fi
  local avail disk
  avail=$(available_gb)
  if [ -z "$avail" ] || [ "$avail" -lt "$START_FLOOR_GB" ]; then
    fail 8 "host-available memory ${avail:-unknown} GB is below the ${START_FLOOR_GB} GB start floor (the Thinking decoder plus mmproj load on the CPU)"
  fi
  disk=$(free_disk_gb)
  if [ -z "$disk" ] || [ "$disk" -lt "$MIN_FREE_DISK_GB" ]; then
    fail 8 "free space on $DATA_DISK is ${disk:-unknown} GB, below ${MIN_FREE_DISK_GB} GB (the legacy cache and the packets each hold about 0.4 GB of features)"
  fi
}

registry_guards() {
  local dirt
  git -C "$REPO" rev-parse HEAD > /dev/null 2>&1 || { fail 2 "$REPO is not a git checkout"; return 0; }
  dirt=$(git -C "$REPO" status --short | grep -vc '^??')
  [ "$dirt" = "0" ] || fail 2 "dirty tree ($dirt tracked changes); the launch binds a clean, countersigned HEAD"
  driver --check-ledger > /dev/null || fail 11 "the exposure row SAEA-SLURP-DIRECT-ONLY-FOLD-B-THINKING-PACKETS-V1 (CPU, superseded) is absent, inconsistent or not root-countersigned (driver --check-ledger)"
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

wait_sidecars_gone() {
  local waited=0 left
  while true; do
    left=$(saea_cpu_sidecars)
    [ -z "$left" ] && return 0
    [ "$waited" -ge "$GONE_WAIT_SECONDS" ] && { echo "a CPU sidecar is still up after ${GONE_WAIT_SECONDS}s: $(printf '%s' "$left" | tr '\n' ' ' | cut -c1-240)"; return 1; }
    sleep 5; waited=$((waited + 5))
  done
}

run_attempt() {  # run_attempt <roster> <rc-on-failure>
  local roster=$1 failcode=$2 wd rc
  mkdir -p "$OUT" || return "$failcode"
  (
    while true; do
      local av
      av=$(available_gb)
      echo "watchdog $(date -u +%T) available_gb=$av" >> "$OUT/watchdog-$roster.log"
      if [ -n "$av" ] && [ "$av" -lt "$WATCHDOG_FLOOR_GB" ]; then
        echo "WATCHDOG: available memory ${av} GB < ${WATCHDOG_FLOOR_GB} GB; stopping the packet driver $(date -u +%FT%TZ)" | tee -a "$OUT/watchdog-$roster.log"
        pkill -f "slurp_fold_preprocess_thinking.py --roster $roster --run"
        exit 0
      fi
      sleep 10
    done
  ) &
  wd=$!
  echo "== attempt $roster $(date -u +%FT%TZ)"
  roster_args "$roster"
  driver --roster "$roster" --run --workers 4 --promote-workers 8 "${ROSTER_ARGS[@]}" --output "$OUT/encoder-report-$roster.json"
  rc=$?
  kill "$wd" 2>/dev/null
  echo "== attempt $roster exit $rc $(date -u +%FT%TZ)"
  [ "$rc" = 0 ] || return "$failcode"
  return 0
}

echo "direct_fb_packets $MODE stage $STAGE $(date -u +%FT%TZ) HEAD $(git -C "$REPO" rev-parse --short HEAD 2>/dev/null)"

case "$MODE" in
  check)
    registry_guards; runtime_guards; dry_runs thinking-smoke-4 thinking-fold-b
    [ "$RC" = 0 ] && echo "CHECK PASS: every guard and both dry-runs; nothing was started" || echo "CHECK REFUSED (first code $RC)"
    exit "$RC"
    ;;
  task)
    registry_guards; runtime_guards; dry_runs thinking-smoke-4 thinking-fold-b
    [ "$RC" = 0 ] || { echo "TASK REFUSED (first code $RC); nothing was started"; exit "$RC"; }
    PS=$(saea_powershell)
    out=$("$PS" -NoProfile -File "$SAEA_TASK_PS1_WIN" -Name "$TASK_NAME" -Script "$TASK_ENTRY" -Start 2>&1 | tr -d '\r'; exit "${PIPESTATUS[0]}")
    trc=$?
    printf '%s\n' "$out" | sed 's/^/    ps: /'
    [ "$trc" = 0 ] || { echo "the task did not start (exit $trc)"; exit 12; }
    echo "TASK STARTED: $TASK_NAME; follow /home/chao/direct-fb-packets-*.log (newest)"
    exit 0
    ;;
  run)
    registry_guards
    runtime_guards
    case "$STAGE" in
      smoke) dry_runs thinking-smoke-4 ;;
      fold-b) dry_runs thinking-fold-b ;;
      all) dry_runs thinking-smoke-4 thinking-fold-b ;;
    esac
    [ "$RC" = 0 ] || { echo "RUN REFUSED (first code $RC); nothing was started"; exit "$RC"; }
    if [ "$STAGE" = all ] || [ "$STAGE" = smoke ]; then
      run_attempt thinking-smoke-4 20 || exit $?
      wait_sidecars_gone || exit 22
    fi
    if [ "$STAGE" = all ] || [ "$STAGE" = fold-b ]; then
      if [ "$STAGE" = all ]; then
        RC=0; runtime_guards; dry_runs thinking-fold-b
        [ "$RC" = 0 ] || { echo "FOLD-B REFUSED after the smoke (first code $RC); the smoke stands"; exit "$RC"; }
      fi
      run_attempt thinking-fold-b 21 || exit $?
      wait_sidecars_gone || exit 22
      echo "PACKETS DONE: next python -B scripts/slurp_fold_preprocess_thinking.py --pin-receipt   (prints; add --write to substitute the zero sentinel in the two baselines)"
    else
      echo "SMOKE DONE: read $OUT/encoder-report-thinking-smoke-4.json; then --run --stage fold-b"
    fi
    exit 0
    ;;
esac
