#!/bin/bash
# Decisions 77 / 85 / 97: fly the two pruning cells (P1 then P0), each smoke then arm, on the SLURP geometry through the batch driver.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-prune.out
COMMIT=$(cat /home/chao/prune-review-off-arm-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
def step(order, short, name, tag, cpr, ceil, smoke_attempt=None):
    return {"order":order,"short":short,"kind":"cell",
        "experiment":f"slurp-native-{name}-v1","cell":f"slurp-native-{name}-v1",
        "smoke_experiment":f"slurp-native-{name}-smoke-4-v1","smoke_cell":f"slurp-native-{name}-smoke-4-v1",
        "campaign_plan":f"configs/campaign/slurp-native-{name}-v1.json",
        "run_id":f"SAEA-SLURP-NATIVE-{tag}-V1","fit_run_id":f"SAEA-SLURP-NATIVE-{tag}-FIT-V1",
        "gen_attempt_id":f"attempt-slurp-native-{name}-train-fold-a-generation-v1",
        "smoke_run_id":f"SAEA-SLURP-NATIVE-{tag}-SMOKE-4-V1","smoke_attempt_id":smoke_attempt or f"attempt-slurp-native-{name}-smoke-4-generation-v1",
        "expected_rows":1080,"contacts_per_row":cpr,"ceiling_per_row":ceil,"notool":True,"owner":f"root-slurp-native-{name}-v1"}
steps=[step(1,"p1","prune-reviewer1","PRUNE-REVIEWER1",4,7,"attempt-slurp-native-prune-reviewer1-smoke-4-generation-recovery-v1"), step(2,"p0","prune-review-off","PRUNE-REVIEW-OFF",2,2)]
import os
only = os.environ.get("PRUNE_ONLY")
if only: steps = [s for s in steps if s["short"] == only]  # e.g. PRUNE_ONLY=p0 after P1 sealed (the driver's smoke-wait bug ended the first two-step run)
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [p1 p0] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
