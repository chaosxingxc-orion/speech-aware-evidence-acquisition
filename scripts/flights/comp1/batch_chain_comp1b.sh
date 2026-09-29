#!/bin/bash
# Decisions 77 / 160: fly the COMP-1b family on the SLURP np4 geometry through the batch driver. ONE step:
# the four-row form smoke first (driver-enforced), then the registered ONE-cell campaign plan, which flies
# the COMP-1b arm ALONE -- the comparator is the EXISTING SEALED in-chain A/A
# SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 cell COMP-1 already flew, reused cross-flight and never re-flown
# (owner decision 160's shared-A/A pattern, as cell G5's own campaign plan carried its arm alone after the
# same decision). ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1; contacts_per_row 5 is
# informational (the sealed PLAN arm realised 5.023; removing the citation contract removes tokens, never
# contacts).
# Preconditions: the DRAFT exposure rows are countersigned, the receipt is minted, both cells were flipped
# in one converged cycle (comp1b_flip.sh), the resident session is
# serving-slurp-native-candidate-five-train-a-np4-v1, and no other batch is running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1b.out
COMMIT=$(cat /home/chao/comp1b-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "comp1b", "kind": "cell",
     "experiment": "slurp-native-stage3-comp1b-fold-a-v1",
     "cell": "slurp-native-stage3-comp1b-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-comp1b-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-comp1b-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1b-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1b-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-comp1b-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1b-fold-a-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [comp1b: smoke, then arm alone -- the shared A/A is reused, never re-flown] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
