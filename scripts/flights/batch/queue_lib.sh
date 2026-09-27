# shellcheck shell=bash
# The unattended-queue pattern of /home/chao/saea-queue/queue_after_*.sh as a library (owner decision 163), so a
# queue is ten lines and every step keeps its real exit code. Source it, then:
#
#   source /mnt/d/.../scripts/flights/batch/queue_lib.sh
#   ql_init /home/chao/queue-agree-a2t.out
#   AG=$(ql_commit /home/chao/agree-flight-commit.txt) || ql_halt 1 "no AGREE flight commit"
#   ql_wait_driver_start "$AG" 60000       || ql_halt 3 "AGREE driver never started"
#   ql_wait_terminal                       || ql_halt $? "AGREE did not finish (4 STOP, 5 processes gone)"
#   ql_swap a2t-np3                        || ql_halt $? "swap to A2T failed"
#   ql_chain "$QL_BATCH/batch_chain_a2taa.sh"; RC=$?
#   ql_swap slurp-np4                      || ql_halt $? "swap back to np4 failed -- coordinator to inspect"
#   ql_halt_on_stop; [ "$RC" = 0 ] || ql_halt "$RC" "A2T-AA chain returned $RC"
#   ql_say "queue complete"
#
# Rules it carries: a STOP halts (never skipped over); no step reports success by default -- every function
# returns the exit status of what it ran, captured with `rc=0; cmd || rc=$?` (the 2026-09-27 "np4 back: rc 0" line
# logged a wait script that exited 0 on SESSION STOPPED EARLY); the swap is serving_swap.sh, never a separate WSL
# switch plus Windows task switch; the generation-flight test is serving_lib.sh's precise one.
QL_BATCH=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=serving_lib.sh
source "$QL_BATCH/serving_lib.sh"
QL_SWAP=${SAEA_SERVING_SWAP:-$QL_BATCH/serving_swap.sh}
QL_DRIVER_OUT=${QL_DRIVER_OUT:-$SAEA_RUNTIME_ROOT/batch-driver.out}
QL_DONE=${QL_DONE:-$SAEA_RUNTIME_ROOT/batch-done}
QL_STOP=${QL_STOP:-$SAEA_RUNTIME_ROOT/batch-STOP}
QL_POLL=${QL_POLL:-60}
QL_LOG=${QL_LOG:-/dev/stdout}

ql_init() { QL_LOG=$1; : >> "$QL_LOG"; ql_say "queue start ($(basename "${0:-queue}"))"; }
ql_say() { echo "$(date -u +%FT%TZ) $*" >> "$QL_LOG"; }
ql_halt() { local code=${1:-1}; shift; ql_say "HALT (exit $code): $*"; exit "$code"; }

# ql_commit <file>: the first line of a flight-commit file (1 when missing or empty).
ql_commit() { local c; c=$(head -1 "$1" 2>/dev/null); [ -n "$c" ] || return 1; echo "$c"; }

# ql_wait_driver_start <commit> [max_seconds=57600]: 0 once batch-driver.out shows driver-start for that commit.
ql_wait_driver_start() {
  local commit=$1 max=${2:-57600} waited=0
  until grep -q "driver-start.*$commit" "$QL_DRIVER_OUT" 2>/dev/null; do
    [ "$waited" -ge "$max" ] && return 1
    sleep 30; waited=$((waited + 30))
  done
  ql_say "driver-start seen for $commit"
}

# ql_wait_terminal: blocks until the running chain ends. 0 batch-done (non-empty), 4 batch-STOP, 5 every
# generation-flight process gone without a marker.
ql_wait_terminal() {
  while true; do
    if [ -s "$QL_DONE" ]; then ql_say "DONE $(head -1 "$QL_DONE")"; return 0; fi
    if [ -e "$QL_STOP" ]; then ql_say "STOPPED $(head -1 "$QL_STOP")"; return 4; fi
    if [ -z "$(saea_generation_flight_pids)" ]; then
      sleep 5   # the marker is written just before the driver exits
      [ -s "$QL_DONE" ] && continue
      [ -e "$QL_STOP" ] && continue
      ql_say "flight processes gone without a done or STOP marker"; return 5
    fi
    sleep "$QL_POLL"
  done
}

# ql_halt_on_stop: halts the queue (exit 4) when batch-STOP exists.
ql_halt_on_stop() { [ -e "$QL_STOP" ] && ql_halt 4 "batch-STOP present: $(head -1 "$QL_STOP")"; return 0; }

# ql_swap <target> [serving_swap.sh options]: the whole geometry swap; returns serving_swap.sh's exit status.
ql_swap() {
  local rc=0
  ql_say "swap to $1"
  bash "$QL_SWAP" "$@" >> "$QL_LOG" 2>&1 || rc=$?
  ql_say "swap to $1 exit $rc"
  return "$rc"
}

# ql_chain <chain script> [args]: runs one batch chain; returns its exit status.
ql_chain() {
  local rc=0
  ql_say "chain $(basename "$1") start"
  bash "$@" >> "$QL_LOG" 2>&1 || rc=$?
  ql_say "chain $(basename "$1") exit $rc; done=$(head -1 "$QL_DONE" 2>/dev/null) stop=$(head -1 "$QL_STOP" 2>/dev/null)"
  return "$rc"
}

# ql_wait_sidecars_gone [max_seconds=43200]: 0 once no CPU sidecar (non-8080 llama-server, packet preprocess) runs.
ql_wait_sidecars_gone() {
  local max=${1:-43200} waited=0
  while [ -n "$(saea_cpu_sidecars)" ]; do
    [ "$waited" = 0 ] && ql_say "waiting for the CPU sidecar to finish: $(saea_cpu_sidecars | head -2 | tr '\n' ';')"
    [ "$waited" -ge "$max" ] && return 1
    sleep 60; waited=$((waited + 60))
  done
  return 0
}
