#!/bin/bash
# Queue hook (L338, unattended hand-over): launch L338 (the lever column, owner rulings 338 and 341 A) the moment a NAMED predecessor chain has
# finished cleanly. The predecessor is an ARGUMENT (the NX-T R4 chain at the time of writing: `/home/chao/nxt4-chain.out CHAIN_NXT4_EXIT`), so the hook is not tied to one chain:
#
#   bash queue_l338_after_chain.sh <chain-out> <exit-token> <start-stamp>      (the argument order of queue_carriers_after.sh)
#       e.g. bash queue_l338_after_chain.sh /home/chao/nxt4-chain.out CHAIN_NXT4_EXIT 2026-10-19T14:00:00Z
#
#   <chain-out>    the log file the predecessor chain writes its exit line to
#   <exit-token>   the first field of the predecessor chain's exit line; the line is `<exit-token> rc=<N> <UTC timestamp>` (the form every chain wrapper writes:
#                  CHAIN_NXT2_EXIT, CHAIN_CARRIERTHINK_EXIT, ...)
#   <start-stamp>  UTC ISO stamp (the same form the wrapper writes); only an exit line LATER than it counts, so the lines of earlier attempts are ignored
#
# NOT installed by the package: the coordinator copies this file to /home/chao/saea-queue/ and starts it. The register steps of the package (derive .. commit, with
# --root-countersign) are the coordinator's and are NOT part of this hook. It polls (60 s, at most 30 h) the chain log for the first matching line:
#   rc=0      -> run, from the master checkout,
#                bash scripts/flights/batch/package_launch.sh scripts/flights/nx/l338_launch_spec.json --from flip --until chain
#                and log to /home/chao/l338-queue.out; the hook then scans the launcher's output for a flip refusal (see below) and exits with the launcher's exit code;
#   rc!=0     -> log it and exit 9 WITHOUT launching (a predecessor failure is the coordinator's to diagnose; L338 never follows a failed chain);
#   no line within 30 h -> log it and exit 8 without launching.
#
# FLIP-LOG REFUSAL GREP. repin_cell_generic.sh prints the INFORMATIONAL line `repin exit N (1 = its internal check refused the dirty tree, expected)` on every pass; a plain
# grep for "refus" matched it and blocked the R2 rec2 hook on 2026-10-18. The scan below drops exactly that line (and nothing else) before it looks for FAIL / REFUSED /
# refus, so a real refusal still stops the hook (exit 10) and the informational line never does.
#
# Exit codes: 0 launched and the launcher succeeded; 8 timed out; 9 the predecessor exited non-zero; 10 the launcher's output shows a real refusal; 64 usage; other = the
# launcher's own code.
#
# Test hooks (environment): L338_HOOK_OUT, L338_HOOK_MAIN, L338_HOOK_POLL_SECONDS, L338_HOOK_MAX_WAIT_SECONDS, L338_HOOK_LAUNCH_CMD.
CHAIN_OUT=${1:-}
TOKEN=${2:-}
STAMP=${3:-}
if [ -z "$TOKEN" ] || [ -z "$CHAIN_OUT" ] || [ -z "$STAMP" ]; then
  echo "usage: queue_l338_after_chain.sh <predecessor-chain-out> <predecessor-exit-token> <start-stamp, UTC ISO e.g. 2026-10-19T14:00:00Z>" >&2
  exit 64
fi
OUT=${L338_HOOK_OUT:-/home/chao/l338-queue.out}
MAIN=${L338_HOOK_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
POLL=${L338_HOOK_POLL_SECONDS:-60}
MAX_WAIT=${L338_HOOK_MAX_WAIT_SECONDS:-108000}
LAUNCH=${L338_HOOK_LAUNCH_CMD:-"bash scripts/flights/batch/package_launch.sh scripts/flights/nx/l338_launch_spec.json --from flip --until chain"}
INFO_RE='repin exit [0-9]+ \(1 = its internal check refused the dirty tree, expected\)'

say() { echo "$(date -u +%FT%TZ) queue_l338: $*" >> "$OUT"; }

# the first predecessor exit line stamped after the start stamp: prints "rc=<N>" (nothing when there is none yet)
predecessor_exit_after_stamp() {
  awk -v s="$STAMP" -v t="$TOKEN" '$1 == t && $3 > s { print $2; exit }' "$CHAIN_OUT" 2>/dev/null
}

# real refusal lines of a log: the informational repin line is dropped first, then FAIL / REFUSED / refus are looked for (prints the offending lines)
real_refusals() {
  grep -v -E "$INFO_RE" "$1" 2>/dev/null | grep -E "check: FAIL|GATE FAILED|REFUSED|DID NOT CONVERGE|FLIGHT COMMIT MISMATCH|NOT A FIXED POINT|refus"
}

say "armed: waiting for $TOKEN after $STAMP in $CHAIN_OUT (poll ${POLL}s, at most ${MAX_WAIT}s)"
waited=0
while :; do
  verdict=$(predecessor_exit_after_stamp)
  if [ -n "$verdict" ]; then break; fi
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    say "TIMEOUT: no $TOKEN line after $STAMP within ${MAX_WAIT}s; L338 is NOT launched"
    exit 8
  fi
  sleep "$POLL"
  waited=$(( waited + ${POLL%.*} ))
  [ "${POLL%.*}" -gt 0 ] 2>/dev/null || waited=$(( waited + 1 ))
done

if [ "$verdict" != "rc=0" ]; then
  say "the predecessor chain exited with $verdict ($TOKEN) after $STAMP; L338 is NOT launched (coordinator to diagnose)"
  exit 9
fi

say "the predecessor chain exited with rc=0 ($TOKEN); launching L338 from $MAIN: $LAUNCH"
cd "$MAIN" || { say "cannot cd to $MAIN"; exit 1; }
LAUNCH_LOG=$(mktemp "${TMPDIR:-/tmp}/l338-launch.XXXXXX")
bash -c "$LAUNCH" > "$LAUNCH_LOG" 2>&1
rc=$?
cat "$LAUNCH_LOG" >> "$OUT"
bad=$(real_refusals "$LAUNCH_LOG")
rm -f "$LAUNCH_LOG"
say "launcher exit rc=$rc"
if [ -n "$bad" ]; then
  say "the launcher's output shows a real refusal (the informational repin line is ignored): $(echo "$bad" | head -3 | tr '\n' '|')"
  [ "$rc" -eq 0 ] && rc=10
fi
exit $rc
