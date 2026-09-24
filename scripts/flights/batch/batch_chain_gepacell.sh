#!/bin/bash
# Decisions 77 / 83 / 99 / 101 / 106: fly cell CELL-1-GEPA (four-row form smoke, then the 1,080-row
# TRAIN Fold A arm) and then its derangement twin (its own four-row smoke, then its own 1,080-row
# arm) on the SLURP serving geometry through the batch driver. Two steps: the twin never flies
# beside the arm, and each arm opens only after its own smoke seals (the driver enforces both --
# one step at a time, smoke before arm inside a step).
#
# CELL-1-GEPA is CELL-1 with the stage3-deltas store at the GEPA release (448 values: 248
# GEPA-authored rows appended to the 200 iteration-1 rows the owner-decision-83 retention
# kept). Every identity here is new. ceiling_per_row 11 is the locked plan's
# OWN per-row ceiling (configs/policy/phase-native-candidates-review-revise-v1.json max_contacts 11,
# resolved from the unchanged role graph perception 1 / solver 1 / reviewer 3 / planner 1 with
# max_revisions 1 as 1 + 2 x (3 + 1 + 1)); contacts_per_row 4 is the REALISED figure CELL-1
# measured (4.216) and is informational. The smoke's own expected row count is hardcoded at 4
# inside batch_driver.sh.
#
# Before this runs: the flight lock must be clear. An aborted campaign leaves locks/flight.lock
# behind and the next launch refuses on it.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-gepacell.out
COMMIT=$(cat /home/chao/gepacell-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "gepacell", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-gepa-r01-v1",
     "cell": "slurp-native-stage3-delta-cell-gepa-r01-v1",
     "smoke_experiment": "slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-gepa-r01-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-gepa-r01-v1-generation",
     "smoke_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1-generation",
     "expected_rows": 1080, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-gepa-r01-v1"},
    {"order": 2, "short": "gepacelltwin", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-gepa-r01-v1",
     "cell": "slurp-native-stage3-delta-cell-gepa-r01-twin-v1",
     "smoke_experiment": "slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-delta-cell-gepa-r01-smoke-4-twin-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-gepa-r01-twin-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-gepa-r01-v1-twin",
     "smoke_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-SMOKE-4-TWIN-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-delta-cell-gepa-r01-smoke-4-v1-twin",
     "expected_rows": 1080, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-gepa-r01-twin-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [gepacell, gepacelltwin] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
