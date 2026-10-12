#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 91 / 158: fly the E41 four-row dry run (one step, no smoke; receipts-only read)
# on the E21 serving geometry through the batch driver. Mirrors scripts/flights/batch/batch_chain_e39b.sh, with the
# serving-swap preconditions of scripts/flights/det/batch_chain_det.sh made explicit for the E21 geometry.
# rows = CALLS: one call (4 windows); ceiling_per_row 44 = 4 windows x 11; contacts_per_row 20 is informational (E39b realised 25).
#
# PRECONDITIONS (the coordinator's, in this order; this script refuses on each):
#   1. no flight, lease or driver process alive, and the flight lock clear;
#   2. the resident session is serving-e21-native-window-flightruntime-np4-max1024-v1 (Windows Scheduled Task
#      SAEA-Serving-E21 -> scripts/flights/batch/serving_task_entry_e21.sh), started AFTER the SLURP np4 session
#      serving-slurp-native-candidate-five-train-a-np4-v1 was stopped cleanly (scripts/flights/batch/
#      serving_switch_to_e21.sh; one resident server per geometry). The driver's own prelaunch checks the
#      session by id and requires it idle and healthy;
#   3. the cell flipped to ready (scripts/flights/e41/e41_flip_dryrun.sh) and its flight commit recorded in
#      /home/chao/e41-dryrun-flight-commit.txt.
# Row 158 schedules E41 on the GPU AFTER COMP-1, so the SLURP line keeps the card; return the SLURP geometry
# (scripts/flights/batch/serving_switch_a2t_to_slurp.sh or serving_switch_to_slurp.sh) after the seal.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
LOG=/home/chao/batch-chain-e41-dryrun.out
COMMIT=$(cat /home/chao/e41-dryrun-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-e21-native-window-flightruntime-np4-max1024-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "E21 session $BATCH_SESSION is not resident; start it first (serving_task_entry_e21.sh); abort" >> $LOG; exit 6; fi
NP4=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$NP4/session.json" ] && [ ! -f "$NP4/session-stop.json" ]; then echo "the SLURP np4 session is still recorded resident; stop it first (serving_switch_to_e21.sh); abort" >> $LOG; exit 6; fi
[ -e /home/chao/batch-flight-repo.txt ] && { echo "a stale /home/chao/batch-flight-repo.txt override exists; archive it first; abort" >> $LOG; exit 6; }
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "e41dry", "kind": "cell",
     "experiment": "e21-native-window-four-row-e41-dry-run-v1",
     "cell": "e21-native-window-system-four-row-e41-v1",
     "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
     "campaign_plan": "configs/campaign/e21-native-window-system-four-row-e41-v1.json",
     "run_id": "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1",
     "fit_run_id": "SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1-FIT-V1",
     "gen_attempt_id": "attempt-e21-native-window-system-four-row-e41-v1",
     "expected_rows": 1, "contacts_per_row": 20, "ceiling_per_row": 44, "notool": True,
     "owner": "root-e21-native-window-system-four-row-e41-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [e41-dryrun] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
