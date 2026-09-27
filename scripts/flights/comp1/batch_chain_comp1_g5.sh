#!/bin/bash
# Owner decisions 77 / 138 / 152 / 153 / 160: fly COMP-1 and G5 on the SLURP np4 geometry through the
# batch driver as ONE chain with ONE shared in-chain A/A (COMP-1's SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1).
#
# The driver flies ONE smoke per step and then that step's campaign plan, so decision 160's single
# campaign [COMP-1 smoke, G5 smoke, shared A/A, COMP-1 arm, G5 arm] is realised as TWO steps of ONE queue,
# the A/A in the first, on the same resident session with nothing else between them:
#   step 1 (comp1): the COMP-1 four-row form smoke, then COMP-1's registered campaign plan
#                   [the shared A/A, the COMP-1 arm];
#   step 2 (g5):    the G5 four-row form smoke, then G5's campaign plan [the G5 arm] (its own A/A dropped
#                   and superseded unflown).
# Why this order and not [A/A] then [both arms]: the riskiest form (COMP-1's three composed factors) is
# smoked before anything is spent; the A/A is spent only beside the arm it is first read against; and a
# G5 smoke failure leaves a complete, readable COMP-1 pair instead of an orphaned A/A. Both arms are read
# at the same null in the same serving state, which is what decision 160 asks.
# The driver inspects each step's LAST cell (the COMP-1 arm, then the G5 arm); a passing step-1 inspect
# implies the A/A sealed first. ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1;
# contacts_per_row 5 is informational (the sealed PLAN arm realised 4.096).
#
# Preconditions: comp1_g5_flip.sh converged all five cells at one HEAD and wrote
# /home/chao/comp1g5-flight-commit.txt; the resident session is
# serving-slurp-native-candidate-five-train-a-np4-v1; no other batch is running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1g5.out
QUEUE=/home/chao/batch-queue.json
COMMIT=$(cat /home/chao/comp1g5-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The flight commit must carry the shared mode (decision 160) -- read from the checkout that will fly.
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" <<'PY' >> $LOG 2>&1 || { echo "shared-A/A precondition refused; abort" >> $LOG; exit 6; }
import json, sys
repo = sys.argv[1]
def cells(name):
    return [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/{name}.json"))["cells"]]
assert json.load(open(f"{repo}/docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/shared-aa-proof-v1.json"))["verdict"] == "IDENTICAL"
assert cells("slurp-native-stage3-comp1-fold-a-v1") == ["slurp-native-stage3-comp1-aa-fold-a-v1", "slurp-native-stage3-comp1-fold-a-v1"]
assert cells("slurp-native-stage3-g5-fold-a-v1") == ["slurp-native-stage3-g5-fold-a-v1"]
facts = json.load(open(f"{repo}/docs/readiness/2026-09-27-slurp-stage3-g5-fold-a-v1/registered-facts-v1.json"))
assert facts["stage3_measurement"]["SAEA-SLURP-STAGE3-G5-FOLD-A-V1"]["replicate_run_id"] == "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1"
print("shared-A/A preconditions hold at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os
steps = [
    {"order": 1, "short": "comp1", "kind": "cell",
     "experiment": "slurp-native-stage3-comp1-fold-a-v1",
     "cell": "slurp-native-stage3-comp1-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-comp1-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-comp1-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1-fold-a-v1"},
    {"order": 2, "short": "g5", "kind": "cell",
     "experiment": "slurp-native-stage3-g5-fold-a-v1",
     "cell": "slurp-native-stage3-g5-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-g5-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-g5-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-g5-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-g5-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-G5-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-g5-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-g5-fold-a-v1"},
]
json.dump(steps, open(os.environ["QUEUE"], "w"), indent=1)
PY
echo "queue [comp1: smoke, then the shared A/A + the COMP-1 arm; g5: smoke, then the G5 arm] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
