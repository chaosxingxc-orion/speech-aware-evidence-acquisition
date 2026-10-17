#!/bin/bash
# Queue hook (owner ruling 327 A, unattended R2 -> R2b hand-over): launch NX-T R2b the moment NX-T R2 has finished cleanly.
#
#   bash queue_nxt2b_after_nxt2.sh <R2-start-stamp>        e.g. 2026-10-17T12:40:00Z   (UTC, the same ISO form the R2 chain wrapper writes)
#
# Install by copying this file to /home/chao/saea-queue/ (the register steps of the package -- derive .. commit, with --root-countersign -- are the coordinator's and
# are NOT part of this hook). It polls (60 s, at most 30 h) the R2 chain log /home/chao/nxt2-chain.out for the first line
#     CHAIN_NXT2_EXIT rc=<N> <UTC timestamp>
# whose timestamp is LATER than the start stamp (the lines of earlier R2 attempts are ignored):
#   rc=0      -> run, from the master checkout,
#                bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r2b_launch_spec.json --from flip --until chain
#                and log to /home/chao/nxt2b-queue.out; the hook exits with the launcher's exit code;
#   rc!=0     -> log it and exit 9 WITHOUT launching (an R2 failure is the coordinator's to diagnose; R2b never follows a failed R2);
#   no line within 30 h -> log it and exit 8 without launching.
# Exit codes: 0 launched and the launcher succeeded; 8 timed out; 9 R2 exited non-zero; 64 usage; other = the launcher's own code.
#
# Test hooks (environment): NXT2B_HOOK_CHAIN_OUT, NXT2B_HOOK_OUT, NXT2B_HOOK_MAIN, NXT2B_HOOK_POLL_SECONDS, NXT2B_HOOK_MAX_WAIT_SECONDS, NXT2B_HOOK_LAUNCH_CMD.
STAMP=${1:-}
[ -n "$STAMP" ] || { echo "usage: queue_nxt2b_after_nxt2.sh <R2-start-stamp, UTC ISO e.g. 2026-10-17T12:40:00Z>" >&2; exit 64; }
CHAIN_OUT=${NXT2B_HOOK_CHAIN_OUT:-/home/chao/nxt2-chain.out}
OUT=${NXT2B_HOOK_OUT:-/home/chao/nxt2b-queue.out}
MAIN=${NXT2B_HOOK_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
POLL=${NXT2B_HOOK_POLL_SECONDS:-60}
MAX_WAIT=${NXT2B_HOOK_MAX_WAIT_SECONDS:-108000}
LAUNCH=${NXT2B_HOOK_LAUNCH_CMD:-"bash scripts/flights/batch/package_launch.sh scripts/flights/nx/nxt_r2b_launch_spec.json --from flip --until chain"}

say() { echo "$(date -u +%FT%TZ) queue_nxt2b: $*" >> "$OUT"; }

# the first R2 exit line stamped after the start stamp: prints "rc=<N>" (nothing when there is none yet)
r2_exit_after_stamp() {
  awk -v s="$STAMP" '$1 == "CHAIN_NXT2_EXIT" && $3 > s { print $2; exit }' "$CHAIN_OUT" 2>/dev/null
}

say "armed: waiting for CHAIN_NXT2_EXIT after $STAMP in $CHAIN_OUT (poll ${POLL}s, at most ${MAX_WAIT}s)"
waited=0
while :; do
  verdict=$(r2_exit_after_stamp)
  if [ -n "$verdict" ]; then break; fi
  if [ "$waited" -ge "$MAX_WAIT" ]; then
    say "TIMEOUT: no CHAIN_NXT2_EXIT line after $STAMP within ${MAX_WAIT}s; NX-T R2b is NOT launched"
    exit 8
  fi
  sleep "$POLL"
  waited=$(( waited + ${POLL%.*} ))
  [ "${POLL%.*}" -gt 0 ] 2>/dev/null || waited=$(( waited + 1 ))
done

if [ "$verdict" != "rc=0" ]; then
  say "NX-T R2 exited with $verdict after $STAMP; NX-T R2b is NOT launched (coordinator to diagnose)"
  exit 9
fi

say "NX-T R2 exited with rc=0; launching NX-T R2b from $MAIN: $LAUNCH"
cd "$MAIN" || { say "cannot cd to $MAIN"; exit 1; }
bash -c "$LAUNCH" >> "$OUT" 2>&1
rc=$?
say "launcher exit rc=$rc"
exit $rc
