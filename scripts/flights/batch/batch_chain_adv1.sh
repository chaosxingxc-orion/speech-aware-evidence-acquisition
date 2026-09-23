#!/bin/bash
# Decisions 77 / 82 / 101 / 106: fly cell ADV-1 (four-row form smoke, then the 225-row SYSTEM-level
# semantic-advantage contact over the disagreeing ROLL-1 rows) on the SLURP geometry through the
# batch driver. The smoke's own expected row count is hardcoded at 4 inside batch_driver.sh;
# expected_rows below is the ARM's. ceiling_per_row 1 is the advantage program's OWN per-row
# ceiling (configs/policy/phase-stage3-advantage-v2.json: one phase, max_contacts 1), so
# contacts_per_row is 1 as well and cap = target.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-adv1.out
COMMIT=$(cat /home/chao/adv1-arm-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps=[{"order":1,"short":"adv1","kind":"cell",
        "experiment":"slurp-native-stage3-advantage-r01-v1","cell":"slurp-native-stage3-advantage-r01-v1",
        "smoke_experiment":"slurp-native-stage3-advantage-r01-smoke-4-v1","smoke_cell":"slurp-native-stage3-advantage-r01-smoke-4-v1",
        "campaign_plan":"configs/campaign/slurp-native-stage3-advantage-r01-v1.json",
        "run_id":"SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1","fit_run_id":"SAEA-SLURP-STAGE3-ADVANTAGE-R01-FIT-V1",
        "gen_attempt_id":"attempt-slurp-native-stage3-advantage-r01-v1-generation",
        "smoke_run_id":"SAEA-SLURP-STAGE3-ADVANTAGE-R01-SMOKE-4-V1","smoke_attempt_id":"attempt-slurp-native-stage3-advantage-r01-smoke-4-v1-generation-recovery",
        "expected_rows":225,"contacts_per_row":1,"ceiling_per_row":1,"notool":True,"owner":"root-slurp-native-stage3-advantage-r01-v1"}]
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [adv1] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
