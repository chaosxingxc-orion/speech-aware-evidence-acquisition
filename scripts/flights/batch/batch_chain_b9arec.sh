#!/bin/bash
# Decision 77: re-pin the batch flight worktree at the B9a-rec flight commit, clear the old STOP/done markers (archived), write the
# one-step queue and run the driver. Assumes no batch is running (checked here).
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-b9arec.out
COMMIT=$(cat /home/chao/b9arec-flight-commit.txt) || exit 1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
name, tag = "plan-acquisition-b9a-recovery", "PLAN-ACQUISITION-B9A-RECOVERY"
steps=[{"order":1,"short":"b9arec","kind":"cell",
        "experiment":f"slurp-native-{name}-v1","cell":f"slurp-native-{name}-v1",
        "smoke_experiment":f"slurp-native-{name}-smoke-4-v1","smoke_cell":f"slurp-native-{name}-smoke-4-v1",
        "campaign_plan":f"configs/campaign/slurp-native-{name}-v1.json",
        "run_id":f"SAEA-SLURP-NATIVE-{tag}-V1","fit_run_id":f"SAEA-SLURP-NATIVE-{tag}-FIT-V1",
        "gen_attempt_id":f"attempt-slurp-native-{name}-train-fold-a-generation-v1",
        "smoke_run_id":f"SAEA-SLURP-NATIVE-{tag}-SMOKE-4-V1","smoke_attempt_id":f"attempt-slurp-native-{name}-smoke-4-generation-v1",
        "expected_rows":1080,"contacts_per_row":4,"ceiling_per_row":11,"notool":True,"owner":f"root-slurp-native-{name}-v1"}]
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [b9arec] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
