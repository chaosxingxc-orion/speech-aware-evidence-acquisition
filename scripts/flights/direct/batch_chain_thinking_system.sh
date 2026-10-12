#!/bin/bash
# Decisions 77 / 268-B: fly the locked SLURP system on the Thinking core (TRAIN Fold B) through the batch driver, one SEGMENT per resident session.
# A driver run attaches to ONE session (BATCH_SESSION), so the read is one Thinking segment:
#
#   smoke   the four-row Thinking-system smoke (an `engineering` driver step: it runs the registered smoke through the worker and the structural
#           inspector and never starts a campaign or a scoring job). Session: the THINK-BUDGET session.
#   arms    the Thinking system arm `lock`, then its request-identical twin `aa` (two `cell` steps, ONE chain, ONE session). REFUSES to start until
#           the coordinator's sign-off marker exists (SIGNOFF_MARKER: a one-line file after the coordinator read the smoke's per-node table with
#           `bash scripts/flights/direct/thinking_system_read.sh smoke`); it WAITS for the marker (TSYS_SIGNOFF_WAIT_SECONDS, default 43200) and aborts
#           on a batch-STOP.
#   all     smoke, then the wait for the marker, then the arms: the registered arc in ONE invocation (the default).
#
# Registered order: swap to think-budget-np4 -> smoke -> sign-off -> lock -> aa -> swap back to slurp-np4. All segments fly from ONE flight commit
# (/home/chao/tsys-flight-commit.txt, written by the flip).
#
# PRECONDITIONS (the coordinator's; this script refuses on the first four): no flight, lease or driver process alive and the flight lock clear; the
# THINK-BUDGET session is the RESIDENT one (a mismatch exits 6 and starts nothing); the other geometry's session is not recorded resident; the cells
# are flipped (thinking_system_flip.sh). WHILE the Thinking session is resident the idle watchdog MUST be held (/home/chao/saea-queue/watchdog.hold).
#   bash scripts/flights/direct/batch_chain_thinking_system.sh [smoke|arms|all]
SEGMENT=${1:-all}
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SHORT=tsys
LOG=/home/chao/batch-chain-$SHORT.out
SIGNOFF_MARKER=/home/chao/tsys-decode-signoff.marker
THINK_SESSION=serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1
INSTRUCT_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
case "$SEGMENT" in
  smoke|arms|all) export BATCH_SESSION=$THINK_SESSION; OTHER=$INSTRUCT_SESSION ;;
  *) echo "usage: batch_chain_thinking_system.sh [smoke|arms|all]"; exit 64 ;;
esac
echo "chain start $(date -u +%FT%TZ) segment $SEGMENT commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident (segment $SEGMENT); swap first (serving_swap.sh think-budget-np4); abort" >> $LOG; exit 6; fi
O=$DATA/serving/$OTHER
if [ -f "$O/session.json" ] && [ ! -f "$O/session-stop.json" ]; then echo "the other geometry's session $OTHER is still recorded resident; stop it first; abort" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt

run_driver() {  # run_driver <segment> : write the queue for that segment and run the batch driver
  for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
  TSYS_SEGMENT=$1 TSYS_MAIN=$MAIN /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["TSYS_MAIN"] + "/scripts/flights/direct")
import thinking_system_family as fam  # noqa: E402

segment = os.environ["TSYS_SEGMENT"]
C = fam.CONTACTS_PER_ROW


def arm_step(order, key):
    spec = fam.CELLS[key]
    stem = spec["cell"][: -len("-v1")]
    return {"order": order, "short": f"tsys-{key}", "kind": "cell", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
            "campaign_plan": spec["campaign"], "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "expected_rows": spec["rows"], "contacts_per_row": C, "ceiling_per_row": C, "notool": True,
            "owner": f"root-{stem}-v1"}


def smoke_step(order):
    spec = fam.CELLS["smoke"]
    return {"order": order, "short": "tsys-smoke", "kind": "engineering", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": spec["cell"], "smoke_cell": spec["cell"], "campaign_plan": None, "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "smoke_run_id": spec["run"], "smoke_attempt_id": spec["attempt"],
            "expected_rows": fam.SMOKE_ROWS, "contacts_per_row": C, "ceiling_per_row": C, "notool": True, "owner": f"root-{spec['cell']}"}


steps = {"smoke": [smoke_step(1)], "arms": [arm_step(1, "lock"), arm_step(2, "aa")]}[segment]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
  echo "queue [segment $1] written; starting driver $(date -u +%FT%TZ)" >> $LOG
  bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
  RC=$?
  echo "driver exit $RC segment $1 $(date -u +%FT%TZ)" >> $LOG
  return $RC
}

wait_signoff() {
  local waited=0 limit=${TSYS_SIGNOFF_WAIT_SECONDS:-43200}
  while [ ! -s "$SIGNOFF_MARKER" ]; do
    [ -e /home/chao/batch-STOP ] && { echo "batch-STOP present while waiting for the sign-off; abort" >> $LOG; return 8; }
    [ $waited -ge $limit ] && { echo "no sign-off marker $SIGNOFF_MARKER after ${limit}s; abort (the arms are not opened)" >> $LOG; return 5; }
    [ $((waited % 600)) -eq 0 ] && echo "waiting for the sign-off marker $SIGNOFF_MARKER ($waited s) $(date -u +%FT%TZ)" >> $LOG
    sleep 60; waited=$((waited + 60))
  done
  echo "sign-off marker present: $(head -c 200 "$SIGNOFF_MARKER" | tr '\n' ' ')" >> $LOG
  return 0
}

case "$SEGMENT" in
  smoke) run_driver smoke; exit $? ;;
  arms) wait_signoff || exit $?; run_driver arms; exit $? ;;
  all) run_driver smoke || exit $?; wait_signoff || exit $?; run_driver arms; exit $? ;;
esac
