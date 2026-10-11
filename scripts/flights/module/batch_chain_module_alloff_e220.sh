#!/bin/bash
# Decisions 77 / 91 / 187 / 196: fly the Earnings-22 consumption-module ALL-OFF arm (carrier admission gate, design 2b.3)
# ONLY after the owner reopens Earnings (decision 187 keeps the GPU on SLURP until the SLURP lock), on the E22 serving
# geometry through the batch driver, in the E35 form: TWO cell steps -- the four-row smoke (1 call, 4 windows), then the
# whole-dev arm (10 calls, 451 windows). expected_rows counts CALLS; contacts_per_row is windows per call (informational);
# ceiling_per_row 400 as E35. The direct baselines declare no fit identity. This arm's in-chain A/A (a second pass) is
# what gives Earnings its module null on the native-window form; it is not registered here.
# Preconditions: the DRAFT rows countersigned, the receipt minted, both cells flipped (module_alloff_e220_flip.sh wrote
# /home/chao/module-alloff-e220-flight-commit.txt), the E22 session resident, no other batch running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-module-alloff-e220.out
COMMIT=$(cat /home/chao/module-alloff-e220-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-e22-native-window-flightruntime-np4-max1024-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
def step(order, short, cell, run, rows, cpr):
    return {"order": order, "short": short, "kind": "cell", "experiment": cell, "cell": cell,
            "smoke_experiment": None, "smoke_cell": None, "campaign_plan": f"configs/campaign/{cell}.json",
            "run_id": run, "fit_run_id": None, "gen_attempt_id": f"attempt-{cell}-generation-v1",
            "smoke_run_id": None, "smoke_attempt_id": None, "expected_rows": rows, "contacts_per_row": cpr,
            "ceiling_per_row": 400, "notool": True, "owner": "root-earnings22-native-stage3-module-alloff-v1"}
steps = [step(1, "module-alloff-e220-s4", "earnings22-native-stage3-module-alloff-smoke-4-v1",
              "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1", 1, 4),
         step(2, "module-alloff-e220", "earnings22-native-stage3-module-alloff-v1",
              "SAEA-EARNINGS22-NATIVE-STAGE3-MODULE-ALLOFF-V1", 10, 45)]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [module-alloff-e220-s4, module-alloff-e220] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
