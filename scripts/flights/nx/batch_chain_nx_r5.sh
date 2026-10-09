#!/bin/bash
# Decisions 77 / 187: fly NX round R5 (the composed read on DEV-2000-ADDED) on the SLURP np4 geometry through the batch driver.
# ONE step: the four-row form smoke of the composed cell first (driver-enforced), then the registered TWO-cell campaign plan, which flies the
# module OFF-arm replicate (full graph, lock v2.1 + v3) and then the composed arm (review-off, lock v2.2 with v4g) in the SAME chain --
# instrument note rule 3. The driver inspects the last cell flown (the composed arm), so a passing inspect implies the replicate sealed first.
# With --campaign-plan the inspector reads each member's REGISTERED contact ceiling (replicate 11, composed arm 2); ceiling_per_row 11 below is
# the largest of them. contacts_per_row 3 is informational (replicate about 4.07, composed arm exactly 2). The smoke's expected row count (4) is
# hardcoded inside batch_driver.sh.
# Preconditions: decision 238 ruled and the R1 iteration-2 verdict on file; the DRAFT rows of BOTH packages countersigned and BOTH receipts
# minted; the three cells flipped in one converged loop (scripts/flights/nx/nx_r5_flip.sh wrote /home/chao/nxr5-flight-commit.txt); the resident
# session is serving-slurp-native-candidate-five-train-a-np4-v1; no other batch is running. An aborted campaign leaves locks/flight.lock behind and
# the next launch refuses on it. The driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not
# countersigned or whose receipts do not list every run id eligible.
#   bash scripts/flights/nx/batch_chain_nx_r5.sh
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
SLUG=nx-r5-composed-dev2000-added; SHORT=nxr5
LOG=/home/chao/batch-chain-$SHORT.out
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION cell $SLUG" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The flight commit must carry the declared expectation and the two-cell plan -- read from the checkout that will fly.
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" <<'PY' >> $LOG 2>&1 || { echo "R5 precondition refused; abort" >> $LOG; exit 6; }
import json, sys
repo = sys.argv[1]
rd = f"{repo}/docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1"
plan = [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/slurp-native-stage3-nx-r5-composed-dev2000-added-v1.json"))["cells"]]
assert plan == ["slurp-native-stage3-module-comp1b-aa-dev2000-added-v1", "slurp-native-stage3-nx-r5-composed-dev2000-added-v1"], plan
block = json.load(open(f"{rd}/registered-facts-v1.json"))["stage3_measurement"]["SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1"]
declared = block["expected_effect_pp"]
assert isinstance(declared, (int, float)) and not isinstance(declared, bool), f"expected_effect_pp is {declared!r}, not a declared number"
assert block["measurement_design"] == "cross-flight-with-in-chain-replicate" and block["replicate_run_id"] == "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1"
print("R5 preconditions hold at", repo, "declared", declared)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
NX_SLUG=$SLUG NX_SHORT=$SHORT /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os

slug = os.environ["NX_SLUG"]
short = os.environ["NX_SHORT"]
upper = slug.upper()
steps = [{
    "order": 1, "short": short, "kind": "cell",
    "experiment": f"slurp-native-stage3-{slug}-v1",
    "cell": f"slurp-native-stage3-{slug}-v1",
    "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1",
    "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
    "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
    "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1",
    "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
    "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
    "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
    "smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation-v1",
    "expected_rows": 1000, "contacts_per_row": 3, "ceiling_per_row": 11, "notool": True,
    "owner": f"root-slurp-native-stage3-{slug}-v1",
}]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [$SHORT: smoke, then the replicate + composed-arm campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
