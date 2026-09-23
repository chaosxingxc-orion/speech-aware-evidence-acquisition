#!/bin/bash
# Decisions 77 / 83 / 99 / 101 / 106: fly cell CELL-1 (four-row form smoke, then the 1,080-row TRAIN
# Fold A arm) and then its derangement twin (its own four-row smoke, then its own 1,080-row arm) on
# the SLURP serving geometry through the batch driver. Two steps: the twin never flies beside the
# arm, and each arm opens only after its own smoke seals (the driver enforces both -- one step at a
# time, smoke before arm inside a step).
#
# 2026-09-23, THIRD FAILURE: step 1's smoke is the REPLACEMENT cell
# slurp-native-stage3-delta-cell-smoke-4-v3 (run id SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V3, attempt
# attempt-slurp-native-stage3-delta-cell-smoke-4-v3-generation). Run id
# SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1 failed twice and ...-SMOKE-4-V2 then metered 12 contacts
# and died at reviewer_0_input; both are retired and take no further attempt, and a plan budget is
# run-cumulative per run id, which is why the identity had to move again. Step 2's twin smoke keeps
# its own v1 run id, which never opened.
#
# 2026-09-23, the ARM's ONE recovery re-registration: step 1's arm flies under attempt
# attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery. The first arm attempt metered
# 304 contacts over 75 Perception rows of 1,080 and aborted at row ~75 -- two of those 75 Perception
# answers named ONE legal intent three times, and the stage3-deltas candidate-bound route was the
# only reader of that state in the plan that read it without the bounded first-occurrence
# projection its sibling slot-contracts candidate supply declares. The run id, the split, the
# geometry, the session, the store pins and the registered budgets are UNCHANGED (a plan budget is
# run-cumulative per run id: 304 spent + 4,424 expected is far inside the registered 11,880). Under
# the program's failure rule this is the one recovery re-registration this flight gets; a second
# failure stops it. The twin cells are untouched -- their attempts never opened -- and the v3 smoke
# keeps its own id.
#
# ceiling_per_row 11 is the locked plan's OWN per-row ceiling
# (configs/policy/phase-native-candidates-review-revise-v1.json max_contacts 11, resolved from the
# unchanged role graph perception 1 / solver 1 / reviewer 3 / planner 1 with max_revisions 1 as
# 1 + 2 x (3 + 1 + 1)); contacts_per_row 4 is the REALISED figure cell PLAN measured (4.0963) and is
# informational. The smoke's own expected row count is hardcoded at 4 inside batch_driver.sh.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-cell1.out
COMMIT=$(cat /home/chao/cell1-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "cell1", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-r01-v1",
     "cell": "slurp-native-stage3-delta-cell-r01-v1",
     # 2026-09-23 (coordinator): the v3 four-row form smoke PASSED before the first arm attempt (16 contacts, structural PASS)
     # and its attempt is consumed; the arm recovery re-flies without a smoke -- the fourth fix (8843d0a5) changes only how a
     # sealed Perception state is READ and was proven offline on four answer shapes (analysis/native_episode_dry_run.py).
     "smoke_experiment": None,
     "smoke_cell": None,
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-r01-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R01-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-r01-v1-generation-recovery-relaunch-2",
     "smoke_run_id": None,
     "smoke_attempt_id": None,
     "expected_rows": 1080, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-r01-v1"},
    {"order": 2, "short": "cell1twin", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-r01-v1",
     "cell": "slurp-native-stage3-delta-cell-r01-twin-v1",
     "smoke_experiment": "slurp-native-stage3-delta-cell-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-delta-cell-smoke-4-twin-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-r01-twin-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-r01-v1-twin",
     "smoke_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-TWIN-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-delta-cell-smoke-4-v1-twin",
     "expected_rows": 1080, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-r01-twin-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [cell1, cell1twin] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
