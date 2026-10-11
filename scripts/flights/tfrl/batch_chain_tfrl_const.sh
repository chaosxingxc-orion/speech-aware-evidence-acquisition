#!/bin/bash
# Decisions 77 / 187: fly the construction-source lock column on the SLURP np4 geometry (session serving-slurp-native-candidate-five-train-a-np4-v1)
# through the batch driver. DRAFT / HELD: NOT executed by the loop driver; the coordinator or owner starts SAEA-Batch-Driver from PowerShell.
#   bash scripts/flights/tfrl/batch_chain_tfrl_const.sh      # the four-row smoke, then the 625-row plain-lock column
# The column's ceiling_per_row is the program ceiling (2 for phase-native-module-v1-c2), read from the cell's registered facts, never hard-coded.
# Preconditions: the cells flipped in one converged loop (tfrl_const_flip.sh wrote /home/chao/tfrl-const-column-flight-commit.txt), the resident
# session is the np4 one above, no other batch is running (one experiment in flight), and the driver's registration gate
# (scripts/checks/flight_registration_check.py) refuses a step whose rows are not countersigned.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
SHORT=tfrl-const
LOG=/home/chao/batch-chain-$SHORT.out
COMMIT=$(cat /home/chao/$SHORT-column-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
TFRL_SHORT=$SHORT /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os

short = os.environ["TFRL_SHORT"]
slug = "tfrl-construction-lock-r01c"
facts = json.load(open("docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1/registered-facts-v1.json", encoding="utf-8"))
contacts = int(facts["accounting"]["contacts_per_row"])
upper = slug.upper()
steps = [{
    "order": 1, "short": short, "kind": "cell",
    "experiment": f"slurp-native-stage3-{slug}-v1", "cell": f"slurp-native-stage3-{slug}-v1",
    "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1", "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
    "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
    "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1", "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
    "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
    "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
    "smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation-v1",
    "expected_rows": int(facts["accounting"]["rows"]), "contacts_per_row": contacts, "ceiling_per_row": contacts, "notool": True,
    "owner": f"root-slurp-native-stage3-{slug}-v1",
}]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [$SHORT] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
