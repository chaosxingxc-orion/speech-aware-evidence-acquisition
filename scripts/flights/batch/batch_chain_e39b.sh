#!/bin/bash
# Item E39b (the one recovery) four-row dry run on the E21 serving geometry through the batch driver (one step, no smoke; receipts-only read).
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-e39b.out
COMMIT=$(cat /home/chao/e39b-arm-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-e21-native-window-flightruntime-np4-max1024-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps=[{"order":1,"short":"e39bs4","kind":"cell","experiment":"e21-native-window-four-row-e39b-dry-run-v1","cell":"e21-native-window-system-four-row-e39b-v1","smoke_experiment":None,"smoke_cell":None,
        "campaign_plan":"configs/campaign/e21-native-window-system-four-row-e39b-v1.json","run_id":"SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1","fit_run_id":"SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E39B-V1-FIT-V1",
        "gen_attempt_id":"attempt-e21-native-window-system-four-row-e39b-v1","smoke_run_id":None,"smoke_attempt_id":None,
        "expected_rows":1,"contacts_per_row":16,"ceiling_per_row":44,"notool":True,"owner":"root-e21-native-window-system-four-row-e39b-v1"}]
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [e39bs4] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
