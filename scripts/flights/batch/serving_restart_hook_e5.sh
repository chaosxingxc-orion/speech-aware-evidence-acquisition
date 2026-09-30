#!/bin/bash
# The E5-0 restart-gap hook (owner decision 201; coordinator ruling Q4: E5-0 runs as a queue chain step at the 12-h
# serving restart, scripted and receipted, never by hand). It runs the pinned Whisper transcript pass
# (scripts/flights/e5/e5_tool_pass.sh both) in the gap between "old session stopped" and "new session launched",
# ONLY when the request file exists, and is a logged no-op otherwise.
#
# Contract:
#   * trigger: the request file ${SAEA_E5_REQUEST:-/home/chao/e5-tool-pass.request} exists (the root creates it after
#     countersigning SAEA-SLURP-ASR-TOOL-PASS-V1 and -FOLD-B-V1). A line "mode=cpu" in it selects the CPU fallback;
#     anything else is GPU.
#   * idempotent: an flock on ${SAEA_E5_LOCKFILE:-/home/chao/e5-tool-pass.lock} admits one hook at a time (a second
#     concurrent call logs "E5-0 BUSY" and exits 0); a sealed roster is the tool pass's own warm path (no contact);
#     no request file -> "E5-0 SKIP" and exit 0.
#   * log: one line each of "E5-0 START", "E5-0 DONE" or "E5-0 FAILED rc=N" appended to
#     ${SAEA_E5_LOG:-/home/chao/e5-tool-pass.log} (the tool pass's own lines go there too) and echoed to stdout.
#   * request file: removed on DONE; on FAILED renamed to <request>.failed-<UTC stamp> so the next restart does NOT
#     retry (one-shot attempt semantics; a recovery needs its own registration).
#   * exit status: the tool pass's (0 done or skipped, 3 refused, 1 failed); the caller records it and ALWAYS
#     proceeds to launch the new session -- the hook never keeps the card empty.
#
# How the queues invoke it (queue_a2.sh / queue_next.sh are live under /home/chao/saea-queue/ and are NOT edited
# here): in maybe_restart(), replace
#       rc=0; ql_swap slurp-np4 --restart || rc=$?
# with
#       rc=0; ql_swap slurp-np4 --restart --gap-hook "$B/serving_restart_hook_e5.sh" || rc=$?
# serving_swap.sh --gap-hook runs this script after its clean stop (port 8080 verified free) and before its start,
# under the swap lock and the pending marker (no CPU sidecar can start meanwhile), records step "gap-hook" with the
# exit status in its JSON summary, and never lets the hook's status stop the start. maybe_restart() already runs
# only at an idle moment (no flight, no swap); the tool pass re-checks both itself. Expected gap: about 10 min per
# roster on the GPU (model load plus about 5 min of decode), about 20 min for both.
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
REQUEST=${SAEA_E5_REQUEST:-/home/chao/e5-tool-pass.request}
LOG=${SAEA_E5_LOG:-/home/chao/e5-tool-pass.log}
LOCKFILE=${SAEA_E5_LOCKFILE:-/home/chao/e5-tool-pass.lock}
TOOL=${SAEA_E5_TOOL_PASS:-$REPO/scripts/flights/e5/e5_tool_pass.sh}

say() { local line; line="$(date -u +%FT%TZ) $*"; echo "$line"; echo "$line" >> "$LOG"; }

if [ ! -e "$REQUEST" ]; then
  say "E5-0 SKIP (no request file $REQUEST)"
  exit 0
fi
exec 8>"$LOCKFILE" || { say "E5-0 FAILED rc=1 (lock file $LOCKFILE unwritable)"; exit 1; }
if ! flock -n 8; then
  say "E5-0 BUSY (another hook holds $LOCKFILE)"
  exit 0
fi
[ -e "$REQUEST" ] || { say "E5-0 SKIP (request consumed by a concurrent hook)"; exit 0; }
MODE=gpu
grep -qx 'mode=cpu' "$REQUEST" 2>/dev/null && MODE=cpu
say "E5-0 START rosters=fold-a,fold-b mode=$MODE tool=$TOOL"
rc=0
if [ "$MODE" = cpu ]; then
  bash "$TOOL" both --cpu >> "$LOG" 2>&1 || rc=$?
else
  bash "$TOOL" both >> "$LOG" 2>&1 || rc=$?
fi
if [ "$rc" = 0 ]; then
  rm -f "$REQUEST"
  say "E5-0 DONE rc=0 (request file removed)"
else
  mv -f "$REQUEST" "$REQUEST.failed-$(date -u +%Y%m%dT%H%M%SZ)"
  say "E5-0 FAILED rc=$rc (request file renamed; no automatic retry)"
fi
exit "$rc"
