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
# The filler hold is owned (ql_hold_take / ql_hold_release / ql_hold_owner, below); the successor pattern that uses it
# is queue_successor_template.sh.
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

# ql_seg_line <log> <queue script basename> <phrase>: 0 when the LAST run of that queue in <log> (from its
# "queue start (<basename>)" line on) logged a line whose MESSAGE -- the text after the leading timestamp -- starts
# with <phrase> (a fixed string). A phrase quoted inside another line never matches: on 2026-09-30 a bare
# `grep -q "filler hold removed"` matched queue_next.sh's own preamble ("requiring '...' and 'filler hold removed'
# in ..."), so queue_a2.sh took its hold 28 s BEFORE queue_next.sh's release step removed it.
ql_seg_line() {
  awk -v q="queue start ($2)" -v p="$3" '
    index($0, q) { found = 0 }
    { msg = substr($0, index($0, " ") + 1); if (index(msg, p) == 1) found = 1 }
    END { exit (found ? 0 : 1) }' "$1" 2>/dev/null
}

# ---- Filler-hold ownership (2026-09-30 hold race) ----------------------------------------------------------------
# The filler hold used to be an empty touch-file that ANY queue removed with `rm -f`: queue_a2.sh created it at
# 01:59:48Z, the predecessor queue_next.sh's release step deleted it at 02:00:16Z and started the filler inline, and
# queue_a2.sh waited ~30 min for a filler that had no hold (the GPU idled until the coordinator re-created it).
# A hold is now OWNED: the file holds one line "<owner token> <UTC time taken>", and only its owner removes it.
#   ql_hold_take <owner> [<predecessor>]  0: taken (new), already ours, or handed over from <predecessor> (the
#                                         successor names its predecessor; "legacy" adopts an unowned, empty
#                                         pre-ownership hold file). 1: held by another owner -- logs
#                                         "hold already held by <owner>" and does NOT overwrite. 2: bad token.
#   ql_hold_release <owner>               0: removed (logs "filler hold removed (owner <owner>)") or no hold present.
#                                         3: owned by another -- logs "hold owned by <other>; not released" and
#                                         leaves it in place. 2: bad token.
#   ql_hold_owner                         prints the owner token ("legacy" for an empty file); exit 1 when no hold.
# Succession: the successor takes the hold with its own token, naming its predecessor, BEFORE the predecessor
# releases; the predecessor's release then finds the successor's token and leaves the hold alone. A queue restarts
# the filler only when its own release removed the hold (exit 0). Take and release serialise on flock(1) over
# "<hold>.lock"; the filler and the idle watchdog only test that the hold file exists. QL_HOLD overrides the path.
QL_HOLD=${QL_HOLD:-/home/chao/saea-queue/filler.hold}
_ql_hold_valid() { [[ "$1" =~ ^[A-Za-z0-9._-]+$ ]] && [ "$1" != legacy ]; }
_ql_hold_read() {
  local o
  [ -e "$QL_HOLD" ] || return 1
  o=$(awk 'NR == 1 { print $1; exit }' "$QL_HOLD" 2>/dev/null)
  echo "${o:-legacy}"
}
_ql_hold_write() { printf '%s %s\n' "$1" "$(date -u +%FT%TZ)" > "$QL_HOLD.tmp.$$" && mv -f "$QL_HOLD.tmp.$$" "$QL_HOLD"; }
_ql_hold_locked() {   # run "$@" under an exclusive flock on <hold>.lock (unserialised when flock is absent)
  if command -v flock >/dev/null 2>&1; then
    ( flock -w 30 9 || { ql_say "hold lock $QL_HOLD.lock busy for 30 s"; exit 4; }; "$@" ) 9>>"$QL_HOLD.lock"
  else
    "$@"
  fi
}
_ql_hold_take() {
  local me=$1 pred=${2:-} cur
  if cur=$(_ql_hold_read); then
    if [ "$cur" = "$me" ]; then ql_say "filler hold already ours ($me)"; return 0; fi
    if [ -n "$pred" ] && [ "$cur" = "$pred" ]; then
      _ql_hold_write "$me" || return 1
      ql_say "filler hold handed over from $cur to $me"; return 0
    fi
    ql_say "hold already held by $cur; not overwritten (taker $me)"; return 1
  fi
  _ql_hold_write "$me" || return 1
  ql_say "filler hold taken by $me"
}
_ql_hold_release() {
  local me=$1 cur
  if ! cur=$(_ql_hold_read); then ql_say "no filler hold to release ($me)"; return 0; fi
  if [ "$cur" != "$me" ]; then ql_say "hold owned by $cur; not released (releaser $me)"; return 3; fi
  rm -f "$QL_HOLD" && ql_say "filler hold removed (owner $me)"
}
ql_hold_owner() { _ql_hold_read; }
ql_hold_take() {
  _ql_hold_valid "${1:-}" || { ql_say "ql_hold_take: bad owner token '${1:-}'"; return 2; }
  [ -z "${2:-}" ] || [ "$2" = legacy ] || _ql_hold_valid "$2" || { ql_say "ql_hold_take: bad predecessor token '$2'"; return 2; }
  _ql_hold_locked _ql_hold_take "$1" "${2:-}"
}
ql_hold_release() {
  _ql_hold_valid "${1:-}" || { ql_say "ql_hold_release: bad owner token '${1:-}'"; return 2; }
  _ql_hold_locked _ql_hold_release "$1"
}
