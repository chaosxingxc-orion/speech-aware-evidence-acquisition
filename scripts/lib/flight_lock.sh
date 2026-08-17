#!/usr/bin/env bash
# Flight lock: advisory single-flight guard for scripts/run_arm_sequence.sh.
#
# Why: a paired experiment's arms all drive the SAME GPU/llama-server
# singleton (run_arm_sequence.sh's own gpu_is_clean() already refuses to
# start an arm beside a live server for exactly this reason). Nothing
# previously stopped a SECOND `run_arm_sequence.sh` invocation -- a second
# terminal, a forgotten background job -- from launching mid-flight and
# colliding with the first. This lockfile makes "one flight at a time" an
# enforced precondition, not an operator discipline.
#
# Sourced by run_arm_sequence.sh (or any other launcher); never executed
# directly. Public functions:
#
#   flight_lock_path                    -> echoes the lock file path
#   flight_lock_is_stale FILE           -> 0 (stale: pid dead/unparsable) /
#                                           1 (live: pid alive)
#   flight_lock_acquire RUN_IDS_JSON    -> creates the lock; refuses (1) if a
#                                           LIVE lock exists; loudly warns and
#                                           replaces a STALE one; registers an
#                                           EXIT trap that releases the lock
#                                           it just wrote
#   flight_lock_release                 -> removes the lock (idempotent)
#
# Lock content is one JSON object: {"run_ids": [...], "pid": N,
# "started_at": "...Z", "study_head": "<40-hex>"}. `study_head` is read back
# by core.bundle.git_commit's narrowed COMPLETED-manifest bind (Python side,
# core/flight_lock.py) to refuse binding a commit the flight never actually
# ran under, even when ordinary non-load-bearing dirt is tolerated there.

flight_lock_path() {
  : "${SPEECHRL_DATA_DIR:?SPEECHRL_DATA_DIR must be set}"
  echo "${SPEECHRL_DATA_DIR%/}/locks/flight.lock"
}

# Internal: best-effort pid extraction from a lock file's JSON body without
# depending on a JSON tool being installed -- the field is always written by
# flight_lock_acquire in the fixed shape `"pid": N`, so a plain pattern match
# is sufficient and never needs to round-trip through a real parser.
_flight_lock_pid_of() {
  sed -n 's/.*"pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$1" 2>/dev/null | head -n1
}

flight_lock_is_stale() {
  local lock_file="$1" pid
  pid="$(_flight_lock_pid_of "$lock_file")"
  if [ -z "$pid" ]; then
    return 0 # unparsable pid -> treat as stale, never as a permanent jam
  fi
  if kill -0 "$pid" 2>/dev/null; then
    return 1 # a process with this pid is alive -> the lock is live
  fi
  return 0 # no such process -> stale
}

flight_lock_release() {
  local lock_file
  lock_file="$(flight_lock_path)" || return 0
  rm -f "$lock_file"
}

flight_lock_acquire() {
  local run_ids_json="$1"
  local lock_file lock_dir
  lock_file="$(flight_lock_path)" || return 2
  lock_dir="$(dirname "$lock_file")"
  mkdir -p "$lock_dir"

  if [ -f "$lock_file" ]; then
    if flight_lock_is_stale "$lock_file"; then
      echo "WARNING: stale flight lock at $lock_file (owning pid is no longer running) -- clearing it and proceeding" >&2
      echo "  stale lock contents were:" >&2
      sed 's/^/    /' "$lock_file" >&2
    else
      echo "REFUSED: a live flight lock already exists at $lock_file -- another sequence is in flight" >&2
      echo "  lock contents:" >&2
      sed 's/^/    /' "$lock_file" >&2
      return 1
    fi
  fi

  local pid started_at study_head
  pid=$$
  started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  study_head="$(git rev-parse HEAD 2>/dev/null || echo unknown)"
  printf '{"run_ids": %s, "pid": %s, "started_at": "%s", "study_head": "%s"}\n' \
    "$run_ids_json" "$pid" "$started_at" "$study_head" > "$lock_file"

  # shellcheck disable=SC2064 -- lock_file is intentionally expanded NOW
  # (the path this specific invocation acquired), not re-evaluated at trap
  # time against whatever SPEECHRL_DATA_DIR/flight_lock_path might resolve
  # to later.
  trap "rm -f \"$lock_file\"" EXIT
  return 0
}
