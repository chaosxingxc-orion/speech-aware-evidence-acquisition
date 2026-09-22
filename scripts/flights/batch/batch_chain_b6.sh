#!/bin/bash
# Decision 77: wait for the running batch (B9a-rec) to finish, then re-pin the batch flight worktree at the B6 flight commit,
# write the two-step queue (direct arm, then plan arm; no smokes) and run the driver. Never touches a live flight.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-b6.out
COMMIT=$(cat /home/chao/b6-flight-commit.txt) || exit 1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT" >> $LOG
while true; do
  if [ -e /home/chao/batch-STOP ]; then echo "STOP marker present; chain aborts $(date -u +%FT%TZ)" >> $LOG; exit 8; fi
  if [ -e /home/chao/batch-done ] && [ -z "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then break; fi
  sleep 120
done
echo "previous batch done $(date -u +%FT%TZ); re-pinning $REPO to $COMMIT" >> $LOG
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps=[
 {"order":1,"short":"b6direct","kind":"cell","experiment":"slurp-direct-max512-dev2000-added-v1","cell":"slurp-direct-max512-dev2000-added-v1",
  "smoke_experiment":None,"smoke_cell":None,"campaign_plan":"configs/campaign/slurp-direct-max512-dev2000-added-v1.json",
  "run_id":"SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-V1","fit_run_id":"SAEA-SLURP-DIRECT-MAX512-DEV2000-ADDED-FIT-V1",
  "gen_attempt_id":"attempt-slurp-direct-max512-dev2000-added-generation-v1","smoke_run_id":None,"smoke_attempt_id":None,
  "expected_rows":1000,"contacts_per_row":1,"ceiling_per_row":1,"notool":True,"owner":"root-slurp-b6-dev2000-added-direct-v1"},
 {"order":2,"short":"b6plan","kind":"cell","experiment":"slurp-native-default-plan-dev2000-added-v1","cell":"slurp-native-default-plan-dev2000-added-v1",
  "smoke_experiment":None,"smoke_cell":None,"campaign_plan":"configs/campaign/slurp-native-default-plan-dev2000-added-v1.json",
  "run_id":"SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1","fit_run_id":"SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-FIT-V1",
  "gen_attempt_id":"attempt-slurp-native-default-plan-dev2000-added-generation-v1","smoke_run_id":None,"smoke_attempt_id":None,
  "expected_rows":1000,"contacts_per_row":4,"ceiling_per_row":11,"notool":True,"owner":"root-slurp-b6-dev2000-added-plan-v1"}]
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [b6direct, b6plan] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
