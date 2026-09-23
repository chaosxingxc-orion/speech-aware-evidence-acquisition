#!/bin/bash
# Decisions 77 / 80-83: fly cell ROLL-1 (four-row smoke, then the 625-row grouped-Solver rollout on the clean subset R01C (decision 102)) on the SLURP geometry through the batch driver.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-roll1.out
COMMIT=$(cat /home/chao/roll1-arm-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps=[{"order":1,"short":"roll1","kind":"cell",
        "experiment":"slurp-native-stage3-rollout-r01-v1","cell":"slurp-native-stage3-rollout-r01-v1",
        "smoke_experiment":"slurp-native-stage3-rollout-r01-smoke-4-v1","smoke_cell":"slurp-native-stage3-rollout-r01-smoke-4-v1",
        "campaign_plan":"configs/campaign/slurp-native-stage3-rollout-r01-v1.json",
        "run_id":"SAEA-SLURP-STAGE3-ROLLOUT-R01-V1","fit_run_id":"SAEA-SLURP-STAGE3-ROLLOUT-R01-FIT-V1",
        "gen_attempt_id":"attempt-slurp-native-stage3-rollout-r01-generation-v1",
        "smoke_run_id":"SAEA-SLURP-STAGE3-ROLLOUT-R01-SMOKE-4-V1","smoke_attempt_id":"attempt-slurp-native-stage3-rollout-r01-smoke-4-generation-recovery-v1",
        "expected_rows":625,"contacts_per_row":8,"ceiling_per_row":19,"notool":True,"owner":"root-slurp-native-stage3-rollout-r01-v1"}]
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [roll1] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
