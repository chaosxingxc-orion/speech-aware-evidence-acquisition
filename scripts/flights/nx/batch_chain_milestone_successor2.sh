#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 151 / 187 / 250 / 251: fly the SLURP test-sample SUCCESSOR-2 composed milestone (the NX R5 composed arm on
# SLURP-TEST-SAMPLE-3010-V1) on the SLURP np4 geometry (slurp-np4, session serving-slurp-native-candidate-five-train-a-np4-v1)
# through the batch driver. ONE step, ONE cell, NO SMOKE: the queue step sets smoke_experiment and smoke_cell to None (batch_driver.sh
# skips fly_smoke when smoke_experiment is empty or None, exactly as batch_chain_comp1b_testsample.sh, batch_chain_b6.sh and
# batch_chain_cell3.sh do), because the allowance lists a test-sample smoke as not authorised and a smoke under the read id would
# consume its one attempt. ONE ATTEMPT, EVER: never re-launch after a failure (the gate refuses a second attempt of a read run id; a
# failed attempt consumes the milestone). ceiling_per_row 2 and contacts_per_row 2 are exact (policy phase-native-module-v1-c2:
# Perception 1 + Solver 1; Reviewer and Planner never visited). No in-chain replicate (decision 250 A): the read is cross-flight
# against the SEALED successor-1 columns.
# Preconditions: milestone_successor2_flip.sh wrote /home/chao/ms2-flight-commit.txt; the three rows are countersigned (READ may stay
# a draft until the seal); the receipt is minted; the resident session is the np4 one above; no other batch is running (the R6-P1
# flight has sealed). The driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not
# countersigned or whose receipt does not list both run ids eligible.
#   bash scripts/flights/nx/batch_chain_milestone_successor2.sh
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
SHORT=ms2
CELL=slurp-milestone-successor2-composed-v1
RUN=SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1
FIT_RUN=SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1
LOG=/home/chao/batch-chain-$SHORT.out
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION cell $CELL" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
for R in $RUN $FIT_RUN; do
  if [ -d "$DATA/attempts/$R" ] && [ -n "$(ls -A "$DATA/attempts/$R" 2>/dev/null)" ]; then
    echo "$R already has an attempt: ONE attempt, ever; refusing to launch" >> $LOG; exit 8
  fi
done
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The flight commit must carry the signed pin, the one-cell plan, the decision-250 exception and no smoke -- read from the checkout that will fly.
/home/chao/.venvs/speechrl/bin/python -B "$REPO/scripts/flights/nx/milestone_successor2_preflip_check.py" --repo-root "$REPO" --data-root "$DATA" >> $LOG 2>&1 \
  || { echo "successor-2 preconditions refused at the flight commit; abort" >> $LOG; exit 6; }
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" <<'PY' >> $LOG 2>&1 || { echo "successor-2 plan refused; abort" >> $LOG; exit 6; }
import json, sys
repo = sys.argv[1]
cell = "slurp-milestone-successor2-composed-v1"
plan = [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/{cell}.json"))["cells"]]
assert plan == [cell], plan
fragment = json.load(open(f"{repo}/configs/experiment/{cell}.json"))
assert fragment["cells"][0]["readiness"]["state"] == "ready", fragment["cells"][0]["readiness"]["state"]
assert fragment["owner_allowance"]["sha256"] != "0" * 64
policy = fragment["failure_policy"]
assert policy.startswith("ONE ATTEMPT, EVER") and "NO recovery re-registration" in policy and "NO resume-recovery" in policy, policy[:80]
block = json.load(open(f"{repo}/docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/registered-facts-v1.json"))["stage3_measurement"]["SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1"]
assert block["measurement_design"] == "cross-flight-no-replicate" and block["owner_ruling_decision_250"]["option"] == "A"
declared = block["expected_effect_pp"]
assert isinstance(declared, (int, float)) and not isinstance(declared, bool), f"expected_effect_pp is {declared!r}"
print("successor-2 preconditions hold at", repo, "declared", declared)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [{
    "order": 1, "short": "ms2", "kind": "cell",
    "experiment": "slurp-milestone-successor2-composed-v1",
    "cell": "slurp-milestone-successor2-composed-v1",
    "smoke_experiment": None,
    "smoke_cell": None,
    "campaign_plan": "configs/campaign/slurp-milestone-successor2-composed-v1.json",
    "run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1",
    "fit_run_id": "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1",
    "gen_attempt_id": "attempt-slurp-milestone-successor2-composed-generation-v1",
    "smoke_run_id": None,
    "smoke_attempt_id": None,
    "expected_rows": 3010, "contacts_per_row": 2, "ceiling_per_row": 2, "notool": True,
    "owner": "root-slurp-milestone-successor2-composed-v1",
}]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [ms2: the one-cell campaign, no smoke] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
