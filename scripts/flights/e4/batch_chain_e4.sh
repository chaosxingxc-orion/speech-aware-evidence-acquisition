#!/bin/bash
# Decisions 77 / 185: fly cell E4-1 on the SLURP np4 geometry (slurp-np4, session
# serving-slurp-native-candidate-five-train-a-np4-v1) through the batch driver. ONE step: the four-row
# charged dry run first (driver-enforced), then the one-cell campaign plan
# configs/campaign/slurp-native-stage3-relisten-fold-a-v1.json. No A/A cell: the two shadow columns are read
# against the same flight's delivered column. ceiling_per_row 17 = 1 + 2 x (1 + 3 + 1) + 2 x 3 (the relisten
# stage: up to 3 blind + 3 forced-choice contacts after ACCEPT); contacts_per_row 6 is informational (the
# sealed AGREE arm realised 4.06 per row; the relisten stage adds 0.94 blind contacts per row on the sealed
# AGREE answers plus at most as many forced-choice contacts).
# Preconditions: both cells flipped in one converged loop (scripts/flights/e4/e4_flip.sh wrote
# /home/chao/e4-flight-commit.txt), the resident session is the np4 one above, and no other batch is
# running. The driver's own registration gate (scripts/checks/flight_registration_check.py) refuses a step
# whose rows are not countersigned or whose receipt does not list every run id eligible.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-e4.out
COMMIT=$(cat /home/chao/e4-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "e4", "kind": "cell",
     "experiment": "slurp-native-stage3-relisten-fold-a-v1",
     "cell": "slurp-native-stage3-relisten-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-relisten-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-relisten-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-relisten-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-relisten-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-relisten-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 6, "ceiling_per_row": 17, "notool": True,
     "owner": "root-slurp-native-stage3-relisten-fold-a-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [e4: dry run, then the one-arm campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
