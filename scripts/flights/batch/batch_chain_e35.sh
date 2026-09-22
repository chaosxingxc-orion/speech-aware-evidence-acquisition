#!/bin/bash
# Decision 91: fly the four E35 cells on the E21 serving geometry through the batch driver (four-row pair first, then sub10 pair).
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-e35.out
COMMIT=$(cat /home/chao/e35-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-e21-native-window-flightruntime-np4-max1024-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
def step(order, short, exp, cell, run, fit, att, rows, cpr, ceil):
    return {"order":order,"short":short,"kind":"cell","experiment":exp,"cell":cell,"smoke_experiment":None,"smoke_cell":None,
            "campaign_plan":f"configs/campaign/{cell}.json","run_id":run,"fit_run_id":fit,"gen_attempt_id":att,"smoke_run_id":None,"smoke_attempt_id":None,
            "expected_rows":rows,"contacts_per_row":cpr,"ceiling_per_row":ceil,"notool":True,"owner":f"root-{cell}"}
steps=[step(1,"e35s4","e21-native-window-four-row-direct-vs-system-v1","e21-native-window-system-four-row-v1","SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1","SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-V1-FIT-RECOVERY-V3","attempt-e21-native-window-system-four-row-recovery-v4",1,16,44),
       step(2,"e35d10","e21-native-window-sub10-direct-vs-system-v1","e21-native-window-direct-sub10-v1","SAEA-E21-NATIVE-WINDOW-DIRECT-SUB10-V1",None,"attempt-e21-native-window-direct-sub10-v1",10,34,400),
       step(3,"e35s10","e21-native-window-sub10-direct-vs-system-v1","e21-native-window-system-sub10-v1","SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1","SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-V1-FIT","attempt-e21-native-window-system-sub10-v1",10,136,400)]
# rows = CALLS; the direct four-row arm sealed on the first launch and is not re-queued; the system four-row arm flies as recovery-v4 with fit run FIT-RECOVERY-V3.
json.dump(steps, open("/home/chao/batch-queue.json","w"), indent=1)
PY
echo "queue [e35s4 e35d10 e35s10] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
