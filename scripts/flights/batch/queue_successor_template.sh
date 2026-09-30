#!/usr/bin/env bash
# TEMPLATE: a successor queue that runs ONE chain after a predecessor queue, with an OWNED filler hold (queue_lib.sh
# ql_hold_take / ql_hold_release / ql_hold_owner; coordinator fix after the 2026-09-30 hold race). Copy it to
# /home/chao/saea-queue/queue_<name>.sh, fill the CHANGE-ME block, `bash -n` it, and run it from that ext4 copy as a
# scheduled task (decision 77). It refuses to run while ME is still CHANGE-ME.
#
# The 2026-09-30 race it prevents: queue_a2.sh (successor) waited for "NEXT DONE" and "filler hold removed" with a
# bare grep, which also matched queue_next.sh's own preamble line ("requiring '...' and 'filler hold removed' in
# ..."). It therefore touched filler.hold on "NEXT DONE" alone (01:59:48Z); queue_next.sh's release step then removed
# that hold with `rm -f` (02:00:16Z) and started the filler inline, and queue_a2.sh waited ~30 min for a filler that
# nothing held. The GPU idled until the coordinator re-created the hold by hand (02:31:55Z).
#
# Protocol:
#   1. wait for the predecessor's DONE line with ql_seg_line (the message must START with the phrase, in the
#      predecessor's last run; a phrase quoted inside another line never matches). Halt on a HALT line there, a
#      batch-STOP, or the predecessor gone without DONE;
#   2. ql_hold_take "$ME" "$PRED_TOKEN" AT ONCE -- before the predecessor's release step (the predecessors sleep 60 s
#      between DONE and release). Held by the predecessor -> handed over to ME; no hold -> taken; held by any other
#      owner (the coordinator, a third queue) -> left untouched, and this queue neither releases it nor restarts the
#      filler. The predecessor's ql_hold_release then logs "hold owned by $ME; not released" and does not start the
#      filler. A PRE-OWNERSHIP predecessor (`touch` + `rm -f`) cannot honour this: set PRED_TOKEN=legacy and
#      PRED_LEGACY=1, which waits for its real "filler hold removed" line first and takes the hold after it (the
#      filler that predecessor starts inline sees the hold at its next tick and exits);
#   3. wait for the filler to exit at its chunk boundary; re-take the hold if it vanished while this queue owns it;
#   4. with no flight / swap alive for three polls, a ready slurp-np4 session and the flight commit re-verified, run
#      the chain; require batch-done at its own flight commit (a STOP halts and leaves the hold in place);
#   5. print "<LABEL> DONE", sleep 60 (the window a successor uses to take the hold over), then ql_hold_release "$ME";
#      restart the filler inline ONLY when that release removed the hold.
#
# Swapping a corrected script in for a RUNNING queue (bash reads a script incrementally, so a running script is never
# edited in place):
#   a. write the corrected script beside the live one as queue_<name>.sh.next; `bash -n` it; diff it against the live
#      script;
#   b. only while the live queue is still in its step-1 wait (its log's last line is the "requiring ..." preamble and
#      the predecessor has NOT yet logged DONE), stop it: its scheduled task (saea_task.ps1 -Name <task> -Stop), or
#      `kill <pid>` of the `bash /home/chao/saea-queue/queue_<name>.sh` process -- never the predecessor, never a
#      flight process, never batch-STOP;
#   c. `mv queue_<name>.sh queue_<name>.sh.pre-<change>-<UTC>.bak && mv queue_<name>.sh.next queue_<name>.sh`
#      (rename, never rewrite in place), then start the task again (saea_task.ps1 -Name <task> -Start); the fresh
#      run appends a new "queue start" segment to the same log;
#   d. if the predecessor already logged DONE, do NOT swap: let the live script run and handle the hold by hand.
M=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
B=$M/scripts/flights/batch
source "$B/queue_lib.sh"
# ---- CHANGE-ME block ----------------------------------------------------------------------------------------------
ME=CHANGE-ME                                  # this queue's hold token, e.g. queue_e6 ([A-Za-z0-9._-]+)
LOG=/home/chao/queue-CHANGE-ME.out
PRED_LOG=/home/chao/queue-CHANGE-ME.out       # the predecessor's log
PRED_SCRIPT=queue_CHANGE-ME.sh                # the predecessor's basename (its "queue start (<basename>)" line)
PRED_TOKEN=queue_CHANGE-ME                    # the predecessor's hold token; "legacy" for a touch/rm -f predecessor
PRED_LEGACY=0                                 # 1 when the predecessor is pre-ownership (see protocol step 2)
PRED_DONE="CHANGE-ME DONE"                    # the predecessor's DONE phrase
LABEL=CHANGE-ME                               # this queue's chain label; logs "<LABEL> DONE"
CF=/home/chao/CHANGE-ME-flight-commit.txt     # this chain's flight-commit file
REC=CHANGE-ME                                 # the recorded flip commit (full hash)
CHAIN=$M/scripts/flights/CHANGE-ME/batch_chain_CHANGE-ME.sh
# --------------------------------------------------------------------------------------------------------------------
[ "$ME" != CHANGE-ME ] || { echo "queue_successor_template.sh is a template: fill the CHANGE-ME block" >&2; exit 2; }
ql_init "$LOG"
QL_HOLD=/home/chao/saea-queue/filler.hold
declare -F ql_hold_take >/dev/null || ql_halt 1 "queue_lib.sh on master has no ql_hold_take"
verify() {
  local c
  c=$(ql_commit "$CF") || ql_halt 1 "no $CF"
  [ "$c" = "$REC" ] || ql_halt 1 "$CF is ${c:0:9}, expected ${REC:0:9}"
}
verify
ql_say "flight commit ${REC:0:8}; waiting for $PRED_SCRIPT's '$PRED_DONE' line in $PRED_LOG (hold token $ME, predecessor $PRED_TOKEN)"

# 1. the predecessor's DONE (and, for a legacy predecessor, its real release line)
pred_ready() {
  ql_seg_line "$PRED_LOG" "$PRED_SCRIPT" "$PRED_DONE" || return 1
  [ "$PRED_LEGACY" = 1 ] || return 0
  ql_seg_line "$PRED_LOG" "$PRED_SCRIPT" "filler hold removed"
}
poll=60
while true; do
  ql_halt_on_stop
  ql_seg_line "$PRED_LOG" "$PRED_SCRIPT" "HALT" && ql_halt 5 "$PRED_SCRIPT halted -- coordinator to inspect"
  pred_ready && break
  ql_seg_line "$PRED_LOG" "$PRED_SCRIPT" "$PRED_DONE" && poll=3
  if ! pgrep -f "[/]$PRED_SCRIPT" >/dev/null; then
    sleep 3
    pred_ready && break
    ql_halt 5 "$PRED_SCRIPT is gone without '$PRED_DONE' -- coordinator to inspect"
  fi
  sleep $poll
done
ql_say "$PRED_SCRIPT reported '$PRED_DONE'"

# 2. take the hold at once (handed over from the predecessor)
OWN_HOLD=0
if ql_hold_take "$ME" "$PRED_TOKEN"; then OWN_HOLD=1
else ql_say "filler hold owned by $(ql_hold_owner || echo none): this queue flies without owning it and will neither release it nor restart the filler"; fi

# 3. the filler exits at its chunk boundary
sleep 30   # a legacy predecessor starts its filler inline just after its release
for i in $(seq 1 600); do   # up to 10 h: one filler chunk
  ql_halt_on_stop
  if [ "$OWN_HOLD" = 1 ] && [ "$(ql_hold_owner)" != "$ME" ]; then
    ql_say "our filler hold vanished or changed owner ($(ql_hold_owner || echo none)); re-taking"
    ql_hold_take "$ME" || OWN_HOLD=0
  fi
  pgrep -f "[f]iller_queue.sh" >/dev/null || break
  sleep 60
done
pgrep -f "[f]iller_queue.sh" >/dev/null && ql_halt 7 "the filler did not exit within 10 h of the hold (owner $(ql_hold_owner || echo none))"

# 4. the chain
idle=0
for i in $(seq 1 40); do
  ql_halt_on_stop
  if saea_flight_alive >/dev/null 2>&1 || saea_swap_pending >/dev/null 2>&1; then idle=0; else idle=$((idle + 1)); fi
  [ "$idle" -ge 3 ] && break
  sleep 30
done
[ "$idle" -ge 3 ] || ql_halt 7 "$LABEL: a generation flight or swap is still alive: $(saea_flight_alive | tr '\n' ' ' | cut -c1-300)"
[ -e /home/chao/batch-flight-repo.txt ] && ql_halt 6 "$LABEL: stale /home/chao/batch-flight-repo.txt override present -- coordinator to inspect"
rc=0; bash "$B/slurp_wait_ready.sh" --timeout 600 >> "$QL_LOG" 2>&1 || rc=$?
[ "$rc" = 0 ] || ql_halt 8 "$LABEL: resident geometry is not a ready slurp-np4 session (slurp_wait_ready rc $rc)"
verify
ql_say "slurp-np4 ready; launching $LABEL at ${REC:0:8}"
for i in $(seq 1 40); do
  rc=0; bash "$CHAIN" >> "$QL_LOG" 2>&1 || rc=$?
  [ "$rc" = 7 ] || break
  saea_flight_alive >/dev/null 2>&1 && break
  ql_say "$LABEL chain refused on the coarse pgrep (exit 7) with no generation flight alive; retry $i in 30 s"; sleep 30
done
ql_say "$LABEL chain exit $rc; done=$(head -1 "$QL_DONE" 2>/dev/null) stop=$(head -1 "$QL_STOP" 2>/dev/null)"
ql_halt_on_stop
[ "$rc" = 0 ] || ql_halt "$rc" "$LABEL chain refused or failed (exit $rc)"
[ -s "$QL_DONE" ] || ql_halt 5 "no batch-done marker after the $LABEL chain -- coordinator to inspect"
fc=$(head -1 /home/chao/batch-flight-commit.txt 2>/dev/null)
[ "$fc" = "$REC" ] || ql_halt 5 "$LABEL: batch-flight-commit is ${fc:0:8}, expected ${REC:0:8}"

# 5. DONE, the successor window, then release our own hold only
ql_say "$LABEL DONE $(head -1 "$QL_DONE")"
sleep 60
if [ "$OWN_HOLD" = 1 ] && ql_hold_release "$ME"; then
  cp "$M/scripts/flights/filler/filler_queue.sh" /home/chao/saea-queue/filler_queue.sh || ql_halt 1 "filler copy failed"
  rc=0; bash /home/chao/saea-queue/filler_queue.sh >> "$QL_LOG" 2>&1 || rc=$?
  ql_say "filler queue exited $rc; queue complete"
else
  ql_say "filler hold not ours to release (owner $(ql_hold_owner || echo none)); filler not restarted; queue complete"
fi
