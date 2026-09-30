#!/bin/bash
# Decisions 77 / 195 / 204: fly the consumption module's first end-to-end cell (COMP-1b as a module block on lock v2.1,
# DEV-2000-ADDED; migration step 6) ONLY IF the coordinator decided it flies (it need not if the byte proof holds), on the SLURP np4 geometry through the batch driver. ONE
# step: the four-row form smoke first (driver-enforced), then the registered two-cell campaign plan, which flies the
# in-chain A/A (the module's OFF arm on lock v2.1) and then
# the module arm in the SAME chain -- instrument note rule 3. The driver inspects the ARM's run id at step end (it is the
# last cell flown, so a passing inspect implies the A/A sealed first). ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at
# max_revisions 1; contacts_per_row 5 is informational (the sealed DEV plan arm realised 4.07 on this roster; COMP-1b
# realised 4.04 on Fold A). The smoke's expected row count (4) is hardcoded inside batch_driver.sh.
# Preconditions: the seven DRAFT rows are countersigned, the receipt is minted, all
# three cells were flipped in one converged cycle (module_comp1bdev_flip.sh wrote /home/chao/module-comp1bdev-flight-commit.txt), the
# resident session is serving-slurp-native-candidate-five-train-a-np4-v1, and no other batch is running. An aborted
# campaign leaves locks/flight.lock behind and the next launch refuses on it.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-module-comp1bdev.out
COMMIT=$(cat /home/chao/module-comp1bdev-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The flight commit must carry the declared expectation and the two-cell plan -- read from the checkout that will fly.
/home/chao/.venvs/speechrl/bin/python -B - "$REPO" <<'PY' >> $LOG 2>&1 || { echo "module-cell precondition refused; abort" >> $LOG; exit 6; }
import json, sys
repo = sys.argv[1]
rd = f"{repo}/docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1"
plan = [c["cell"] for c in json.load(open(f"{repo}/configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json"))["cells"]]
assert plan == ["slurp-native-stage3-module-comp1b-aa-dev2000-added-v1", "slurp-native-stage3-module-comp1b-dev2000-added-v1"], plan
declared = json.load(open(f"{rd}/registered-facts-v1.json"))["stage3_measurement"]["SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1"]["expected_effect_pp"]
assert isinstance(declared, (int, float)) and not isinstance(declared, bool), f"expected_effect_pp is {declared!r}, not a declared number"
print("module-cell preconditions hold at", repo, "declared", declared)
PY
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "module-comp1bdev", "kind": "cell",
     "experiment": "slurp-native-stage3-module-comp1b-dev2000-added-v1",
     "cell": "slurp-native-stage3-module-comp1b-dev2000-added-v1",
     "smoke_experiment": "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-module-comp1b-dev2000-added-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-module-comp1b-dev2000-added-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-generation-v1",
     "expected_rows": 1000, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-module-comp1b-dev2000-added-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [module-comp1bdev: smoke, then A/A + arm in one campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
