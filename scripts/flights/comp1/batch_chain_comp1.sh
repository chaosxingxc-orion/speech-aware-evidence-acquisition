#!/bin/bash
# Decisions 77 / 138 / 152: fly the COMP-1 family on the SLURP np4 geometry through the batch driver.
# ONE step: the four-row form smoke first (driver-enforced), then the registered two-cell campaign plan,
# which flies the request-identical A/A (the locked plan's own bytes at k 60) and then the composed arm in
# the SAME chain -- instrument note rule 3. The driver inspects the ARM's run id at step end (it is the last
# cell flown, so a passing inspect implies the A/A sealed first). ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at
# max_revisions 1; contacts_per_row 5 is informational (the sealed PLAN arm realised 5.023). The citation
# contract adds tokens per Solver contact, never contacts.
# Preconditions: the expectation is declared, the receipt is minted, all three cells were flipped in one
# converged cycle (comp1_flip.sh), the resident session is serving-slurp-native-candidate-five-train-a-np4-v1,
# and no other batch is running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-comp1.out
COMMIT=$(cat /home/chao/comp1-flight-commit.txt) || exit 1
# Owner decision 160 (2026-09-27): COMP-1's A/A is ALSO cell G5's in-chain replicate. While the G5 campaign
# plan carries the G5 arm alone (the shared mode), COMP-1 flies ONLY in the combined chain
# scripts/flights/comp1/batch_chain_comp1_g5.sh, or G5 loses its in-chain null; COMP1_ALONE=1 overrides,
# and only when the owner has withdrawn G5 from the chain.
if [ "${COMP1_ALONE:-0}" != "1" ] && ! grep -q "slurp-native-stage3-g5-aa-fold-a-v1" /mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/configs/campaign/slurp-native-stage3-g5-fold-a-v1.json; then
  echo "refusing (owner decision 160): the shared A/A must fly beside BOTH arms -- use scripts/flights/comp1/batch_chain_comp1_g5.sh"; exit 6
fi
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
    {"order": 1, "short": "comp1", "kind": "cell",
     "experiment": "slurp-native-stage3-comp1-fold-a-v1",
     "cell": "slurp-native-stage3-comp1-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-comp1-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-comp1-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-comp1-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-comp1-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
     "owner": "root-slurp-native-stage3-comp1-fold-a-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [comp1: smoke, then A/A + arm in one campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
