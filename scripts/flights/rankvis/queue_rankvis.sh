#!/usr/bin/env bash
# Queue RANKVIS (owner decision 171; coordinator ruling 2026-09-28): fly the 119-row RANKVIS conversion probe in
# the first gap the coordinator opens. It ONLY waits on a marker; it never creates one.
#   1. wait for /home/chao/saea-queue/rankvis.go (created by the coordinator when the gap is real);
#   2. hold the filler: ql_hold_take queue_rankvis (queue_lib.sh; owned hold since the 2026-09-30 hold race), so
#      the filler queue pauses at its next tick. If a hold is already present it is ANOTHER owner's and is left
#      exactly as found -- this queue then neither removes it nor restarts the filler;
#   3. wait until no generation flight is alive (serving_lib.sh's precise test, as queue_lib does), no serving swap
#      is pending and no filler_queue.sh is alive; halt on a batch-STOP (never chain onto a STOP) and on a stale
#      /home/chao/batch-flight-repo.txt override;
#   4. require the resident geometry slurp-np4 READY (slurp_wait_ready.sh: /health ok, /props slots and context
#      equal to the fragment, a fresh monitor sample);
#   5. run scripts/flights/rankvis/batch_chain_rankvis.sh (flight commit /home/chao/rankvis-flight-commit.txt),
#      retrying a coarse-pgrep refusal (exit 7) only while no generation flight is alive;
#   6. require batch-done at that flight commit (a STOP halts here and the filler stays held);
#   7. release the hold THIS queue owns (ql_hold_release queue_rankvis: a successor that took it over is left
#      alone) and restart the filler only when the release removed it. The filler has no scheduled task of its own --
#      every queue calls it inline after copying it to ext4 -- so this queue does the same.
# Run it as SAEA-Queue-RANKVIS from its ext4 copy /home/chao/saea-queue/queue_rankvis.sh (bash reads a script
# incrementally and the main checkout moves under merges).
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
B=$M/scripts/flights/batch
source "$B/queue_lib.sh"
ql_init /home/chao/queue-rankvis.out
GO=/home/chao/saea-queue/rankvis.go
HOLD=/home/chao/saea-queue/filler.hold
CHAIN=$M/scripts/flights/rankvis/batch_chain_rankvis.sh
CF=/home/chao/rankvis-flight-commit.txt
QL_HOLD=$HOLD
ME=queue_rankvis
OWN_HOLD=0
release_own_hold () { local rc=1; [ "$OWN_HOLD" = 1 ] && { rc=0; ql_hold_release "$ME" || rc=$?; }; OWN_HOLD=0; return "$rc"; }
halt_before_launch () { release_own_hold; ql_halt "$@"; }

RV=$(ql_commit "$CF") || ql_halt 1 "no RANKVIS flight commit in $CF (not flipped)"
ql_say "RANKVIS flight commit ${RV:0:8}; waiting for the go marker $GO (never created by this queue)"
until [ -e "$GO" ]; do sleep 60; done
ql_say "go marker seen: $(head -1 "$GO" 2>/dev/null | cut -c1-200)"

# 2. hold the filler
if ql_hold_take "$ME"; then
  OWN_HOLD=1
else
  ql_say "filler hold owned by $(ql_hold_owner): left in place, not removed and the filler not restarted by this queue"
fi

# 3. wait for the gap
ql_say "waiting until no generation flight, swap or filler process is alive"
IDLE=0
for i in $(seq 1 2880); do   # up to 48 h
  [ -e "$QL_STOP" ] && halt_before_launch 4 "batch-STOP present: $(head -1 "$QL_STOP") -- never chaining onto a STOP"
  if saea_flight_alive >/dev/null 2>&1 || saea_swap_pending >/dev/null 2>&1 || pgrep -f "[f]iller_queue.sh" >/dev/null; then
    IDLE=0
  else
    IDLE=$((IDLE + 1))
    [ "$IDLE" -ge 3 ] && break   # three consecutive idle polls (about 2 min) so a queue between steps is not raced
  fi
  sleep 60
done
[ "$IDLE" -ge 3 ] || halt_before_launch 7 "no gap within 48 h: $(saea_flight_alive | tr '\n' ' ' | cut -c1-300)"
[ -e /home/chao/batch-flight-repo.txt ] && halt_before_launch 6 "stale /home/chao/batch-flight-repo.txt override present ($(cat /home/chao/batch-flight-repo.txt)) -- coordinator to inspect"
ql_say "gap: no generation flight, swap or filler alive for 3 polls"

# 4. the resident geometry must be slurp-np4 and ready
rc=0; bash "$B/slurp_wait_ready.sh" --timeout 600 >> "$QL_LOG" 2>&1 || rc=$?
[ "$rc" = 0 ] || halt_before_launch 8 "resident geometry is not a ready slurp-np4 session (slurp_wait_ready rc $rc) -- coordinator to inspect"
ql_say "slurp-np4 ready"

# 5. the chain
rc=0
for i in $(seq 1 40); do
  rc=0; ql_say "chain $(basename "$CHAIN") start at ${RV:0:8}"; bash "$CHAIN" >> "$QL_LOG" 2>&1 || rc=$?
  [ "$rc" = 7 ] || break
  if saea_flight_alive >/dev/null 2>&1; then break; fi
  ql_say "chain refused on the coarse pgrep (exit 7) with no generation flight alive; retry $i in 30 s"; sleep 30
done
ql_say "chain $(basename "$CHAIN") exit $rc; done=$(head -1 "$QL_DONE" 2>/dev/null) stop=$(head -1 "$QL_STOP" 2>/dev/null)"
[ "$rc" = 0 ] || ql_halt "$rc" "RANKVIS chain refused (exit $rc) -- filler stays held; coordinator to inspect"

# 6. batch-done at this flight commit (the chain ends with an echo, so require the markers)
ql_halt_on_stop
[ -s "$QL_DONE" ] || ql_halt 5 "RANKVIS: no batch-done marker after the chain -- coordinator to inspect"
FC=$(head -1 /home/chao/batch-flight-commit.txt 2>/dev/null)
[ "$FC" = "$RV" ] || ql_halt 5 "RANKVIS: batch-flight-commit is ${FC:0:8}, expected ${RV:0:8} -- coordinator to inspect"
grep -q '"short": "rankvis"' /home/chao/batch-queue.json 2>/dev/null || ql_halt 5 "RANKVIS: batch-queue.json is not RANKVIS's -- coordinator to inspect"
ql_say "RANKVIS DONE $(head -1 "$QL_DONE") at ${RV:0:8}"

# 7. release the hold and restart the filler (only when this queue owned the hold)
if [ "$OWN_HOLD" = 1 ] && release_own_hold; then
  cp "$M/scripts/flights/filler/filler_queue.sh" /home/chao/saea-queue/filler_queue.sh || ql_halt 1 "filler copy failed"
  ql_say "restarting the filler queue inline (copied to ext4 first)"
  rc=0; bash /home/chao/saea-queue/filler_queue.sh >> "$QL_LOG" 2>&1 || rc=$?
  ql_say "filler queue exited $rc; queue complete"
else
  ql_say "the filler hold belongs to another owner ($(ql_hold_owner || echo none)): left in place, filler not restarted; queue complete"
fi
