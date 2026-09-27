#!/bin/bash
# Decisions 77 / 127 / 159: fly the SLOTFILL family on the SLURP np4 geometry through the batch
# driver. ONE step, the AGREE / G5 chain shape: the four-row form smoke first (driver-enforced),
# then the registered two-cell campaign plan, which flies the A/A (the locked form WITHOUT the
# dispatch key) and then the SLOTFILL arm (the key armed) in the SAME chain on the SAME resident
# session -- instrument note rule 3, and the same-session twin the throughput read needs. The
# driver inspects the ARM's run id at step end (it is the last cell flown, so a passing inspect
# implies the A/A sealed first); the read inspects the A/A explicitly before any number is read.
# ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1; contacts_per_row 5 is
# informational (the sealed PLAN arm realised 4.096 per row: 4,424 contacts). The key moves no
# contact: the arm should spend the A/A's contacts in less wall.
#
# Preconditions: all three cells were flipped in one converged cycle (slotfill_flip.sh), the
# resident session is serving-slurp-native-candidate-five-train-a-np4-v1, and no other batch is
# running. If the round shares one A/A across its base items, the campaign plan carries the arm
# alone and the shared A/A flies in the same chain under its own step.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-slotfill.out
COMMIT=$(cat /home/chao/slotfill-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "slotfill", "kind": "cell",
     "experiment": "slurp-native-stage3-slotfill-fold-a-v1",
     "cell": "slurp-native-stage3-slotfill-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-slotfill-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-slotfill-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-slotfill-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-slotfill-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-SLOTFILL-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-slotfill-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-slotfill-fold-a-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [slotfill: smoke, then A/A + arm in one campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
