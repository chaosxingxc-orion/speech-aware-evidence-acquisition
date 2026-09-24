#!/bin/bash
# Decisions 77 / 83 / 99 / 101 / 106 (and 110, pending): fly the CELL-3 family on the SLURP serving
# geometry through the batch driver, in THREE steps:
#
#   1. PLANr-DEV2000  -- the roster's own null, 1,000 rows, NO SMOKE (cell B6's own why_no_smoke
#      rule: a request-identical replicate of a form already sealed and flown on this exact roster
#      raises no structural question a four-row flight would answer). A step without a smoke sets
#      smoke_experiment and smoke_cell to None, exactly as batch_chain_b6.sh does.
#   2. CELL-3 arm     -- its own four-row smoke, then the 1,000-row arm.
#   3. CELL-3 twin    -- its own four-row smoke, then the 1,000-row twin arm.
#
# The driver enforces both orderings: one step at a time, smoke before arm inside a step. The twin
# never flies beside the arm. PLANr flies FIRST because CELL-3 has no margin until the own-null read
# has sealed -- see docs/readiness/2026-09-24-slurp-stage3-delta-cell-r03-gate-v1-preregistration.md
# section 4a.
#
# CELL-3 is cell B6's plan arm plus the released stage3-deltas-v2 store applied under a coverage
# gate (three candidate-bound routes gated over seven scenarios; CELL-2's Perception unconditional
# route removed). Every identity here is new. ceiling_per_row 11 is the locked plan's OWN per-row
# ceiling (configs/policy/phase-native-candidates-review-revise-v1.json max_contacts 11, resolved
# from the unchanged role graph perception 1 / solver 1 / reviewer 3 / planner 1 with max_revisions
# 1 as 1 + 2 x (3 + 1 + 1)); contacts_per_row 4 is the REALISED figure cell B6 measured on this
# roster (4.071) and is informational. The smoke's own expected row count is hardcoded at 4 inside
# batch_driver.sh.
#
# Before this runs: the flight lock must be clear. An aborted campaign leaves locks/flight.lock
# behind and the next launch refuses on it.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-cell3.out
COMMIT=$(cat /home/chao/cell3-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "cell3planr", "kind": "cell",
     "experiment": "slurp-native-default-plan-dev2000-added-replicate-v1",
     "cell": "slurp-native-default-plan-dev2000-added-replicate-v1",
     "smoke_experiment": None,
     "smoke_cell": None,
     "campaign_plan": "configs/campaign/slurp-native-default-plan-dev2000-added-replicate-v1.json",
     "run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-V1",
     "fit_run_id": "SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-REPLICATE-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-default-plan-dev2000-added-replicate-generation-v1",
     "smoke_run_id": None,
     "smoke_attempt_id": None,
     "expected_rows": 1000, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-default-plan-dev2000-added-replicate-v1"},
    {"order": 2, "short": "cell3", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-r03-gate-v1",
     "cell": "slurp-native-stage3-delta-cell-r03-gate-v1",
     "smoke_experiment": "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-r03-gate-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-r03-gate-v1-generation",
     "smoke_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1-generation",
     "expected_rows": 1000, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-r03-gate-v1"},
    {"order": 3, "short": "cell3twin", "kind": "cell",
     "experiment": "slurp-native-stage3-delta-cell-r03-gate-v1",
     "cell": "slurp-native-stage3-delta-cell-r03-gate-twin-v1",
     "smoke_experiment": "slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-delta-cell-r03-gate-smoke-4-twin-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-delta-cell-r03-gate-twin-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-TWIN-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-delta-cell-r03-gate-v1-twin",
     "smoke_run_id": "SAEA-SLURP-STAGE3-DELTA-CELL-R03-GATE-SMOKE-4-TWIN-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-delta-cell-r03-gate-smoke-4-v1-twin",
     "expected_rows": 1000, "contacts_per_row": 4, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-delta-cell-r03-gate-twin-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [cell3planr, cell3, cell3twin] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
