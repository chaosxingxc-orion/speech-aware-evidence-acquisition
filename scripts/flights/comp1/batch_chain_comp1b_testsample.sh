#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 151 / 202: fly the COMP-1b TEST-SAMPLE milestone on the SLURP np4 geometry through the batch driver.
# ONE step, NO SMOKE (the allowance names no smoke run id; a smoke under a read id would consume its one attempt): the
# registered two-cell campaign plan flies MILESTONE-00-PLAN (the locked v2.0 plan, the comparator) and then MILESTONE-01
# (COMP-1b) in the SAME chain -- instrument rule 3. ONE ATTEMPT EACH, EVER: never re-launch after a failure (the gate
# refuses a second attempt of a read run id; a failed attempt consumes the milestone number).
# ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1.
# Preconditions: comp1b_testsample_flip.sh wrote /home/chao/comp1bts-flight-commit.txt; the five rows are countersigned;
# the receipt is minted; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1; no other batch runs.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1bts.out
DATA=$SAEA_DATA_ROOT
COMMIT=$(cat /home/chao/comp1bts-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
for RUN in SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-00-PLAN-V1 SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1; do
  if [ -d "$DATA/attempts/$RUN" ] && [ -n "$(ls -A "$DATA/attempts/$RUN" 2>/dev/null)" ]; then
    echo "$RUN already has an attempt: ONE attempt, ever; refusing to launch" >> $LOG; exit 8
  fi
done
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
/home/chao/.venvs/speechrl/bin/python -B "$REPO/scripts/flights/comp1/comp1b_testsample_preflip_check.py" --repo-root "$REPO" --data-root "$DATA" >> $LOG 2>&1 \
  || { echo "milestone preconditions refused at the flight commit; abort" >> $LOG; exit 6; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" <<'PY' >> $LOG 2>&1 || { echo "milestone plan refused; abort" >> $LOG; exit 6; }
import json, sys
repo = sys.argv[1]
plan = [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/slurp-native-stage3-comp1b-testsample-v1.json"))["cells"]]
assert plan == ["slurp-native-stage3-plan-testsample-milestone00-v1", "slurp-native-stage3-comp1b-testsample-v1"], plan
print("milestone plan holds at", repo)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "comp1bts", "kind": "cell",
     "experiment": "slurp-native-stage3-comp1b-testsample-v1",
     "cell": "slurp-native-stage3-comp1b-testsample-v1",
     "smoke_experiment": None, "smoke_cell": None,
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1b-testsample-v1.json",
     "run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-V1",
     "fit_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-FIT-V1",
     "gen_attempt_id": "attempt-slurp-test-sample-3010-milestone-01-generation-v1",
     "smoke_run_id": None, "smoke_attempt_id": None,
     "expected_rows": 3010, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1b-testsample-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [comp1bts: MILESTONE-00-PLAN + MILESTONE-01 in one campaign, no smoke] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
