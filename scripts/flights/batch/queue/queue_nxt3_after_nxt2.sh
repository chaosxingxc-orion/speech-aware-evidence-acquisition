#!/bin/bash
# Queue hook (NX-T R3, unattended R2 rec2 -> R3 hand-over): launch NX-T R3 the moment NX-T R2 (rec2) has finished cleanly.
#
#   bash queue_nxt3_after_nxt2.sh <start-stamp>        e.g. 2026-10-18T12:40:00Z   (UTC, the same ISO form the R2 chain wrapper writes)
#
# NOT installed by the package: the coordinator copies this file to /home/chao/saea-queue/ and starts it with the R2 rec2 launch stamp as its first argument. The register
# steps of the package (derive .. commit, with --root-countersign) are the coordinator's and are NOT part of this hook. It polls (60 s, at most 30 h) the R2 chain log
# /home/chao/nxt2-chain.out for the first line
#     CHAIN_NXT2_EXIT rc=<N> <UTC timestamp>
# whose timestamp is LATER than the start stamp (the lines of earlier R2 attempts are ignored):
#   rc=0      -> run, from the master checkout,
#                bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r3_launch_spec.json --from flip --until chain
#                and log to /home/chao/nxt3-queue.out; the hook then scans the launcher's output for a flip refusal (see below) and exits with the launcher's exit code;
#   rc!=0     -> log it and exit 9 WITHOUT launching (an R2 failure is the coordinator's to diagnose; R3 never follows a failed R2);
#   no line within 30 h -> log it and exit 8 without launching.
#
# FLIP-LOG REFUSAL GREP. repin_cell_generic.sh prints the INFORMATIONAL line `repin exit N (1 = its internal check refused the dirty tree, expected)` on every pass; a plain
# grep for "refus" matched it and blocked the R2 rec2 hook on 2026-10-18. The scan below drops exactly that line (and nothing else) before it looks for FAIL / REFUSED /
# refus, so a real refusal still stops the hook (exit 10) and the informational line never does.
#
# Exit codes: 0 launched and the launcher succeeded; 8 timed out; 9 R2 exited non-zero; 10 the launcher's output shows a real refusal; 64 usage; other = the launcher's own code.
#
# Test hooks (environment): NXT3_HOOK_CHAIN_OUT, NXT3_HOOK_OUT, NXT3_HOOK_MAIN, NXT3_HOOK_POLL_SECONDS, NXT3_HOOK_MAX_WAIT_SECONDS, NXT3_HOOK_LAUNCH_CMD.
STAMP=${1:-}
[ -n "$STAMP" ] || { echo "usage: queue_nxt3_after_nxt2.sh <R2-start-stamp, UTC ISO e.g. 2026-10-18T12:40:00Z>" >&2; exit 64; }
CHAIN_OUT=${NXT3_HOOK_CHAIN_OUT:-/home/chao/nxt2-chain.out}
OUT=${NXT3_HOOK_OUT:-/home/chao/nxt3-queue.out}
MAIN=${NXT3_HOOK_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
POLL=${NXT3_HOOK_POLL_SECONDS:-60}
MAX_WAIT=${NXT3_HOOK_MAX_WAIT_SECONDS:-108000}
LAUNCH=${NXT3_HOOK_LAUNCH_CMD:-"bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r3_launch_spec.json --from flip --until chain"}
INFO_RE='repin exit [0-9]+ \(1 = its internal check refused the dirty tree, expected\)'

say() { echo "$(date -u +%FT%TZ) queue_nxt3: $*" >> "$OUT"; }

# the first R2 exit line stamped after the start stamp: prints "rc=<N>" (nothing when there is none yet)
r2_exit_after_stamp() {
  awk -v s="$STAMP" '$1 == "CHAIN_NXT2_EXIT" && $3 > s { print $2; exit }' "$CHAIN_OUT" 2>/dev/null
}

# real refusal lines of a log: the informational repin line is dropped first, then FAIL / REFUSED / refus are looked for (prints the offending lines)
real_refusals() {
  grep -v -E "$INFO_RE" "$1" 2>/dev/null | grep -E "check: FAIL|GATE FAILED|REFUSED|DID NOT CONVERGE|FLIGHT COMMIT MISMATCH|NOT A FIXED POINT|refus"
}

say "armed: waiting for CHAIN_NXT2_EXIT after $STAMP in $CHAIN_OUT (poll ${POLL}s, at most ${MAX_WAIT}s)"
waited=0
while :; do
  verdict=$(r2_exit_after_stamp)
  if [ -n "$verdict" ]; then break; fi
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    say "TIMEOUT: no CHAIN_NXT2_EXIT line after $STAMP within ${MAX_WAIT}s; NX-T R3 is NOT launched"
    exit 8
  fi
  sleep "$POLL"
  waited=$(( waited + ${POLL%.*} ))
  [ "${POLL%.*}" -gt 0 ] 2>/dev/null || waited=$(( waited + 1 ))
done

if [ "$verdict" != "rc=0" ]; then
  say "NX-T R2 exited with $verdict after $STAMP; NX-T R3 is NOT launched (coordinator to diagnose)"
  exit 9
fi

say "NX-T R2 exited with rc=0; launching NX-T R3 from $MAIN: $LAUNCH"
cd "$MAIN" || { say "cannot cd to $MAIN"; exit 1; }
LAUNCH_LOG=$(mktemp "${TMPDIR:-/tmp}/nxt3-launch.XXXXXX")
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
