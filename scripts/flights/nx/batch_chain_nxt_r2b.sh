#!/bin/bash
# Decisions 77 / NX-T R2b: fly the Solver reasoning-budget raise column (TRAIN Fold B) through the batch driver, one SEGMENT per resident session.
# A driver run attaches to ONE session (BATCH_SESSION), so the read is one raised-cap Thinking segment (swap target think-budget7168-np4: the np4 x 24,576
# server geometry of NX-T R2 with the fragment's geometry cap 7,168; the smoke and the column flight run on the SAME session):
#
#   smoke   the four-row column smoke (an `engineering` driver step: it runs the registered smoke through the worker and the structural inspector and never
#           starts a campaign or a scoring job).
#   arm     the column flight (one `cell` step, ONE session). Waits for the smoke's sign-off with chain_lib.sh `wait_or_machine_signoff` (see below).
#   all     smoke, then the sign-off, then the column flight: the registered arc in ONE invocation (the default). REFUSES (exit 9) when the smoke attempt
#           already exists on the data root: a (run_id, attempt_id) pair is a one-time key and the sealed smoke is never re-flown.
#   arm-only  the RECOVERY entry (rec1, nxt_r2b_family.RECOVERIES): the column flight alone under the rec1 attempt ids. REQUIRES the smoke to be sealed (its run manifest
#           reads COMPLETED, exit 9 otherwise) and the sign-off marker to exist already (exit 5 otherwise; it never waits).
#
# SERVING. Unlike R2's `all`, every segment SWAPS to the raised-cap session first when it is not resident (`serving_swap.sh think-budget7168-np4`): R2b is launched by
# the queue hook right after R2, whose think-budget-np4 session is still resident. Hold the idle watchdog (/home/chao/saea-queue/watchdog.hold) first. Like R2's chain, it
# does not swap back; the coordinator's next step names the session it needs.
#
# SIGN-OFF (owner ruling 314 A, M6). `wait_or_machine_signoff "<reader>" <conditions> <marker> 20`: a coordinator marker that already exists is the sign-off; otherwise the reader
# (`bash scripts/flights/nx/nxt_r2b_read.sh smoke`) writes the smoke decode-cost table and smoke_signoff.py decides PASS / FAIL against the conditions file THE DERIVE EMITTED
# INSIDE THE PACKAGE (nxt_r2b_family.SIGNOFF_CONDITIONS; it follows the arm table). PASS: the machine writes /home/chao/nxt2b-decode-signoff.marker and a 20-minute VETO window
# opens (delete the marker, or create /home/chao/batch-STOP). FAIL: <marker>.refused and the chain waits for a coordinator marker (NXT2B_SIGNOFF_WAIT_SECONDS, default 43200).
# R2's chain waited for a HAND marker and idled the GPU for 1 h 43 min; this one never does.
#
# After a sealed segment the exposure-ledger rows of the flown run ids are closed with chain_lib.sh `close_rows_after_seal` (idempotent; a failure is logged, not fatal).
#
# Registered order: swap -> smoke -> machine sign-off (+ veto window) -> the column flight -> close the ledger rows. Both segments fly from ONE flight commit
# (/home/chao/nxt2b-flight-commit.txt, written by the flip).
#
# PRECONDITIONS (the coordinator's; this script refuses on the first four): no flight, lease or driver process alive and the flight lock clear (serial GPU,
# ruling 303 A: NX-T R2 has sealed); the Instruct session is not recorded resident; the cells are flipped (nxt_r2b_flip.sh).
#   bash scripts/flights/nx/batch_chain_nxt_r2b.sh [smoke|arm|all|arm-only]
SEGMENT=${1:-all}
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SHORT=nxt2b
LOG=/home/chao/batch-chain-$SHORT.out
SIGNOFF_MARKER=/home/chao/nxt2b-decode-signoff.marker
export SIGNOFF_WAIT_SECONDS=${NXT2B_SIGNOFF_WAIT_SECONDS:-43200}
export SIGNOFF_PY=/home/chao/.venvs/speechrl/bin/python
INSTRUCT_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
# The Thinking serving geometry, the sign-off conditions and the run ids to close come from the family; never a literal here.
eval "$(PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src /home/chao/.venvs/speechrl/bin/python -B -c \
  "import sys; sys.path.insert(0, '$MAIN/scripts/flights/nx'); import nxt_r2b_family as f; print('THINK_SESSION=%s SWAP_TARGET=%s SIGNOFF_CONDITIONS=%s SMOKE_CLOSE_IDS=\"%s\" ALL_CLOSE_IDS=\"%s\"' % (f.THINK_SESSION, f.THINK_SWAP_TARGET, f.SIGNOFF_CONDITIONS, ' '.join([f.CELLS['smoke']['run'], f.CELLS['smoke']['fit_run']]), ' '.join([f.CELLS['smoke']['run'], f.CELLS['smoke']['fit_run'], f.CELLS['arm']['run'], f.CELLS['arm']['fit_run']])))")" \
  || { echo "cannot read the serving geometry from the family"; exit 66; }
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
OTHER=$INSTRUCT_SESSION
. "$SP/chain_lib.sh"
case "$SEGMENT" in
  smoke|arm|arm-only|all) export BATCH_SESSION=$THINK_SESSION ;;
  *) echo "usage: batch_chain_nxt_r2b.sh [smoke|arm|all|arm-only]"; exit 64 ;;
esac

smoke_state() {  # prints sealed | opened | none for the registered smoke, read from the data root with the family's own ids
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src NXT2B_MAIN=$MAIN NXT2B_DATA=$DATA /home/chao/.venvs/speechrl/bin/python -B - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["NXT2B_MAIN"] + "/scripts/flights/nx")
import nxt_r2b_family as fam  # noqa: E402

s, data = fam.CELLS["smoke"], os.environ["NXT2B_DATA"]
manifest = os.path.join(data, "runs", s["run"], s["attempt"], s["run"] + ".run-manifest.json")
attempt = os.path.join(data, "attempts", s["run"], s["attempt"] + ".json")
try:
    sealed = json.load(open(manifest, encoding="utf-8")).get("status") == "COMPLETED"
except (OSError, ValueError):
    sealed = False
print("sealed" if sealed else ("opened" if os.path.exists(attempt) else "none"))
PY
}
SMOKE_STATE=$(smoke_state)
case "$SEGMENT" in
  all) [ "$SMOKE_STATE" = none ] || { echo "segment all refused: the smoke attempt already exists on the data root (state $SMOKE_STATE); the sealed smoke is never re-flown; use arm-only" >> $LOG; echo "refusing: smoke state $SMOKE_STATE; use arm-only"; exit 9; } ;;
  arm-only)
    [ "$SMOKE_STATE" = sealed ] || { echo "segment arm-only refused: the smoke is not sealed (state $SMOKE_STATE)" >> $LOG; echo "refusing: smoke state $SMOKE_STATE"; exit 9; }
    [ -s "$SIGNOFF_MARKER" ] || { echo "segment arm-only refused: no sign-off marker $SIGNOFF_MARKER" >> $LOG; echo "refusing: no sign-off marker"; exit 5; } ;;
esac
echo "chain start $(date -u +%FT%TZ) segment $SEGMENT commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then
  # every segment swaps to the raised-cap session itself (serving_swap.sh <target> stops the other geometries and starts this one, strict readiness)
  echo "session $BATCH_SESSION is not resident; swapping to $SWAP_TARGET $(date -u +%FT%TZ)" >> $LOG
  bash $SP/serving_swap.sh "$SWAP_TARGET" >> $LOG 2>&1 || { echo "serving_swap.sh $SWAP_TARGET failed; abort" >> $LOG; exit 6; }
fi
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "session $BATCH_SESSION is not resident after the swap (segment $SEGMENT); abort" >> $LOG; exit 6; fi
O=$DATA/serving/$OTHER
if [ -f "$O/session.json" ] && [ ! -f "$O/session-stop.json" ]; then echo "the other geometry's session $OTHER is still recorded resident; stop it first; abort" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt

run_driver() {  # run_driver <segment> : write the queue for that segment and run the batch driver
  for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
  NXT2B_SEGMENT=$1 NXT2B_MAIN=$MAIN /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
import sys

sys.path.insert(0, os.environ["NXT2B_MAIN"] + "/scripts/flights/nx")
import nxt_r2b_family as fam  # noqa: E402

segment = os.environ["NXT2B_SEGMENT"]
C = fam.CONTACTS_PER_ROW


def arm_step(order):
    spec = fam.CELLS["arm"]
    stem = spec["cell"][: -len("-v1")]
    return {"order": order, "short": "nxt2b-arm", "kind": "cell", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
            "campaign_plan": spec["campaign"], "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "expected_rows": spec["rows"], "contacts_per_row": C, "ceiling_per_row": C, "notool": True,
            "owner": f"root-{stem}-v1"}


def smoke_step(order):
    spec = fam.CELLS["smoke"]
    return {"order": order, "short": "nxt2b-smoke", "kind": "engineering", "experiment": spec["cell"], "cell": spec["cell"],
            "smoke_experiment": spec["cell"], "smoke_cell": spec["cell"], "campaign_plan": None, "run_id": spec["run"], "fit_run_id": spec["fit_run"],
            "gen_attempt_id": spec["attempt"], "smoke_run_id": spec["run"], "smoke_attempt_id": spec["attempt"],
            "expected_rows": fam.SMOKE_ROWS, "contacts_per_row": C, "ceiling_per_row": C, "notool": True, "owner": f"root-{spec['cell']}"}


steps = {"smoke": [smoke_step(1)], "arm": [arm_step(1)]}[segment]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
  echo "queue [segment $1] written; starting driver $(date -u +%FT%TZ)" >> $LOG
  bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
  RC=$?
  echo "driver exit $RC segment $1 $(date -u +%FT%TZ)" >> $LOG
  return $RC
}

signoff() {  # the machine sign-off (or a coordinator marker) between the smoke and the column flight; 0 = the column flight may start
  wait_or_machine_signoff "bash scripts/flights/nx/nxt_r2b_read.sh smoke" "$MAIN/$SIGNOFF_CONDITIONS" "$SIGNOFF_MARKER" 20
}

close_rows() {  # close_rows <run ids...> : the ledger rows of a sealed segment; a failure is logged, never fatal
  CLOSE_ROWS_REPO=$MAIN CLOSE_ROWS_PY=/home/chao/.venvs/speechrl/bin/python close_rows_after_seal "$@" || chain_log "close_rows_after_seal failed (rc=$?); close the rows by hand: ledger_mark_consumed.py --apply"
}

case "$SEGMENT" in
  smoke) run_driver smoke; RC=$?; [ $RC -eq 0 ] && close_rows $SMOKE_CLOSE_IDS; exit $RC ;;
  arm) signoff || exit $?; run_driver arm; RC=$?; [ $RC -eq 0 ] && close_rows $ALL_CLOSE_IDS; exit $RC ;;
  arm-only) run_driver arm; RC=$?; [ $RC -eq 0 ] && close_rows $ALL_CLOSE_IDS; exit $RC ;;
  all) run_driver smoke || exit $?; signoff || exit $?; run_driver arm; RC=$?; [ $RC -eq 0 ] && close_rows $ALL_CLOSE_IDS; exit $RC ;;
esac
