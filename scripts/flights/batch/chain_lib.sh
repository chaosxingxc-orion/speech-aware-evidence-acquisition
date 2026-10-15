#!/bin/bash
# Shared helpers for batch chains (efficiency measures M6 and M7, owner ruling 314 A). Source it; it defines functions only.
#
#   . "$(dirname "${BASH_SOURCE[0]}")/../batch/chain_lib.sh"
#
# chain_log <text...>        append a UTC-stamped line to $LOG (stderr when LOG is unset)
# wait_or_machine_signoff <reader-cmd> <conditions-json> <marker> <veto-minutes>
#     1. a marker that already exists is the coordinator's sign-off: return 0 at once (a marker whose first line starts with
#        "machine sign-off" is re-subject to the veto window);
#     2. otherwise run <reader-cmd> (it writes the smoke decode-cost table), then smoke_signoff.py decides PASS / FAIL;
#     3. PASS: the machine wrote the marker; wait the VETO window (minutes; 0 = none). Deleting the marker vetoes (return 10);
#        creating $CHAIN_STOP_FILE (default /home/chao/batch-STOP) aborts (return 8). Both are logged;
#     4. FAIL (or the reader failed): <marker>.refused is written and the chain falls back to waiting for a coordinator marker
#        (return 5 after SIGNOFF_WAIT_SECONDS, 8 on STOP). A coordinator marker that appears needs no veto window.
#   Env: SIGNOFF_VETO_MINUTES (default for the 4th argument, 20), SIGNOFF_POLL_SECONDS (60), SIGNOFF_VETO_UNIT_SECONDS (60, tests set 1),
#        SIGNOFF_WAIT_SECONDS (else NXT1_SIGNOFF_WAIT_SECONDS, else 43200), SIGNOFF_PY (else PY, else python3), SAEA_DATA_ROOT / DATA (data root).
# close_rows_after_seal <run-id>...
#     closes the exposure-ledger rows of the flown run ids with ledger_mark_consumed.py --apply (idempotent: only rows still at
#     consumed = no with sealed evidence change) and commits docs/exposure-ledger.md alone (CLOSE_ROWS_COMMIT=0 to skip the commit).
#   Env: CLOSE_ROWS_REPO (else MAIN), CLOSE_ROWS_PY (else PY, else python3), CLOSE_ROWS_TODAY, SAEA_DATA_ROOT / DATA.

CHAIN_LIB_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

chain_log() { echo "$(date -u +%FT%TZ) $*" >> "${LOG:-/dev/stderr}"; }

_signoff_is_machine() { head -c 20 "$1" 2>/dev/null | grep -q '^machine sign-off'; }

_signoff_veto_wait() {  # _signoff_veto_wait <marker> <minutes>
  local marker=$1 minutes=$2 stop=${CHAIN_STOP_FILE:-/home/chao/batch-STOP}
  local poll=${SIGNOFF_POLL_SECONDS:-60} unit=${SIGNOFF_VETO_UNIT_SECONDS:-60} start window
  if [ "$minutes" -le 0 ] 2>/dev/null; then chain_log "veto window 0: the column starts now"; return 0; fi
  window=$(( minutes * unit )); start=$(date +%s)
  chain_log "VETO WINDOW ${minutes} min: machine sign-off written; the column starts unless $marker is deleted or $stop is created"
  while [ $(( $(date +%s) - start )) -lt "$window" ]; do
    [ -e "$stop" ] && { chain_log "VETO: $stop created during the veto window; abort"; return 8; }
    [ -s "$marker" ] || { chain_log "VETO: sign-off marker $marker deleted during the veto window; abort"; return 10; }
    sleep "$poll"
  done
  [ -e "$stop" ] && { chain_log "VETO: $stop created at the end of the veto window; abort"; return 8; }
  [ -s "$marker" ] || { chain_log "VETO: sign-off marker $marker deleted at the end of the veto window; abort"; return 10; }
  chain_log "veto window elapsed without a veto; the column may start"
  return 0
}

wait_or_machine_signoff() {
  [ $# -ge 3 ] || { chain_log "wait_or_machine_signoff: usage <reader-cmd> <conditions-json> <marker> [veto-minutes]"; return 64; }
  local reader_cmd=$1 conditions=$2 marker=$3 veto=${4:-${SIGNOFF_VETO_MINUTES:-20}}
  local stop=${CHAIN_STOP_FILE:-/home/chao/batch-STOP} poll=${SIGNOFF_POLL_SECONDS:-60}
  local limit=${SIGNOFF_WAIT_SECONDS:-${NXT1_SIGNOFF_WAIT_SECONDS:-43200}} py=${SIGNOFF_PY:-${PY:-python3}} waited=0 rc
  if [ -s "$marker" ]; then
    if _signoff_is_machine "$marker"; then chain_log "machine sign-off marker already present: $(head -c 200 "$marker" | head -1)"; _signoff_veto_wait "$marker" "$veto"; return $?; fi
    chain_log "coordinator sign-off marker present: $(head -c 200 "$marker" | tr '\n' ' ')"; return 0
  fi
  if eval "$reader_cmd" >> "${LOG:-/dev/stderr}" 2>&1; then
    "$py" -B "$CHAIN_LIB_DIR/smoke_signoff.py" --conditions "$conditions" --data-root "${DATA:-${SAEA_DATA_ROOT:-}}" --marker "$marker" --veto-minutes "$veto" >> "${LOG:-/dev/stderr}" 2>&1
    rc=$?
    if [ $rc -eq 0 ] && [ -s "$marker" ]; then
      chain_log "machine sign-off PASS: $(head -c 200 "$marker" | head -1)"
      _signoff_veto_wait "$marker" "$veto"; return $?
    fi
    chain_log "machine sign-off REFUSED (rc=$rc, see $marker.refused): $(head -1 "$marker.refused" 2>/dev/null); waiting for a coordinator marker"
  else
    chain_log "sign-off reader failed; waiting for a coordinator marker"
  fi
  local t0; t0=$(date +%s)
  while [ ! -s "$marker" ]; do
    [ -e "$stop" ] && { chain_log "batch-STOP present while waiting for the sign-off; abort"; return 8; }
    [ "$waited" -ge "$limit" ] && { chain_log "no sign-off marker $marker after ${limit}s; abort (the column flight is not opened)"; return 5; }
    sleep "$poll"; waited=$(( $(date +%s) - t0 ))
  done
  chain_log "coordinator sign-off marker present: $(head -c 200 "$marker" | tr '\n' ' ')"
  return 0
}

close_rows_after_seal() {
  [ $# -ge 1 ] || { chain_log "close_rows_after_seal: usage <run-id>..."; return 64; }
  local repo=${CLOSE_ROWS_REPO:-${MAIN:-}} py=${CLOSE_ROWS_PY:-${PY:-python3}} today=${CLOSE_ROWS_TODAY:-$(date -u +%F)} args=() r out rc msg
  [ -n "$repo" ] || { chain_log "close_rows_after_seal: no repo (CLOSE_ROWS_REPO / MAIN)"; return 64; }
  for r in "$@"; do args+=(--run-id "$r"); done
  out=$("$py" -B "$repo/scripts/flights/batch/ledger_mark_consumed.py" --repo-root "$repo" --data-root "${DATA:-${SAEA_DATA_ROOT:-}}" --today "$today" "${args[@]}" --apply 2>&1); rc=$?
  chain_log "close_rows_after_seal rc=$rc: $(printf '%s' "$out" | head -3 | tr '\n' ' ' | cut -c1-300)"
  [ $rc -eq 0 ] || return $rc
  [ "${CLOSE_ROWS_COMMIT:-1}" = 1 ] || return 0
  git -C "$repo" diff --quiet -- docs/exposure-ledger.md && { chain_log "close_rows_after_seal: ledger unchanged (already closed)"; return 0; }
  local gd; gd=$(git -C "$repo" rev-parse --git-dir)
  case "$gd" in /*) ;; *) gd=$repo/$gd ;; esac
  if [ -e "$gd/MERGE_HEAD" ] || [ -d "$gd/rebase-merge" ] || [ -d "$gd/rebase-apply" ]; then chain_log "close_rows_after_seal: merge in progress; ledger left dirty"; return 3; fi
  msg=$(mktemp /tmp/close_rows_msg.XXXXXX)
  printf 'ledger: close the exposure rows of the sealed run(s) %s (ledger_mark_consumed.py --apply)\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' "$*" > "$msg"
  git -C "$repo" commit -q -F "$msg" -- docs/exposure-ledger.md; rc=$?
  rm -f "$msg"
  chain_log "close_rows_after_seal: ledger commit rc=$rc"
  return $rc
}
