#!/bin/bash
# Decisions 77 / 101 and board route F2: fly cell ROLL-AA (four-row form smoke, then the 200-row
# arm) on the SLURP serving geometry through the batch driver. ONE step: the arm opens only after
# its own smoke seals (the driver enforces smoke before arm inside a step).
#
# ROLL-AA is cell ROLL-1 with the Solver group at the E2b greedy-repeat twin form, N = 2: the
# locked v2.0 plan's Solver answering the IDENTICAL prompt twice per row, greedy. ceiling_per_row
# 13 is the grouped-Solver graph's OWN ceiling at samples 2
# (configs/policy/phase-native-candidates-review-revise-samples2-v1.json max_contacts 13, resolved
# from perception 1 / solver 1 x 2 samples / reviewer 3 / planner 1 with max_revisions 1 as
# 1 + 2 x (2 + 3 + 1)); contacts_per_row 5 is the EXPECTED figure (CELL-1 measured 4.216 at
# samples 1 and a two-sample group adds one contact per Solver visit) and is informational. The
# smoke's own expected row count is hardcoded at 4 inside batch_driver.sh.
#
# Before this runs: the flight lock must be clear. An aborted campaign leaves locks/flight.lock
# behind and the next launch refuses on it.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-rollaa.out
COMMIT=$(cat /home/chao/rollaa-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "rollaa", "kind": "cell",
     "experiment": "slurp-native-stage3-roll-aa-v1",
     "cell": "slurp-native-stage3-roll-aa-v1",
     "smoke_experiment": "slurp-native-stage3-roll-aa-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-roll-aa-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-roll-aa-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-ROLL-AA-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-ROLL-AA-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-roll-aa-v1-generation",
     "smoke_run_id": "SAEA-SLURP-STAGE3-ROLL-AA-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-roll-aa-smoke-4-v1-generation",
     "expected_rows": 200, "contacts_per_row": 5, "ceiling_per_row": 13, "notool": True,
     "owner": "root-slurp-native-stage3-roll-aa-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [rollaa] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
