#!/bin/bash
# Decisions 77 / 133 / 134: fly cell CONV (the 70-row conversion probe, arm only, no smoke) on the SLURP
# serving geometry through the batch driver. ONE step. Comparator answers are already sealed (PLAN on
# Fold A), so this is the treatment alone. ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1;
# contacts_per_row 6 is informational (the sealed PLAN arm realised 5.023 per row).
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-conv.out
COMMIT=$(cat /home/chao/conv-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "conv", "kind": "cell",
     "experiment": "slurp-native-stage3-conv-fold-a-70-v1",
     "cell": "slurp-native-stage3-conv-fold-a-70-v1",
     "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
     "campaign_plan": "configs/campaign/slurp-native-stage3-conv-fold-a-70-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-conv-fold-a-70-generation-v1",
     "expected_rows": 70, "contacts_per_row": 6, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-conv-fold-a-70-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [conv] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
