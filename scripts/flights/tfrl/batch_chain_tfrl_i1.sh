#!/bin/bash
# Decisions 77 / 187: fly the loop iteration cells on the SLURP np4 geometry (session serving-slurp-native-candidate-five-train-a-np4-v1)
# through the batch driver. DRAFT / HELD: NOT executed by the loop driver; the coordinator or owner starts SAEA-Batch-Driver from PowerShell.
#   TFRL_ITER=1 bash scripts/flights/tfrl/batch_chain_tfrl_i1.sh column      # the four-row smoke, then the 1,080-row supply column
#   TFRL_ITER=1 bash scripts/flights/tfrl/batch_chain_tfrl_i1.sh proposers   # the typed proposer cell, then the ACE reflector cell (text-only)
# The column's ceiling_per_row is the iteration's program ceiling (c4 with the typed arm empty, c5 with typ or par, c6 with both): read
# from the cell's registered facts, never hard-coded. Preconditions: the cells flipped in one converged loop (tfrl_i1_flip.sh wrote
# /home/chao/tfrl-i<n>-<which>-flight-commit.txt), the resident session is the np4 one above, no other batch is running (one experiment in
# flight), and the driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not countersigned.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
ITER=${TFRL_ITER:-1}
WHICH=${1:-column}
SHORT=tfrl-i$ITER
LOG=/home/chao/batch-chain-$SHORT-$WHICH.out
COMMIT=$(cat /home/chao/$SHORT-$WHICH-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION which $WHICH" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
TFRL_ITER=$ITER TFRL_WHICH=$WHICH TFRL_SHORT=$SHORT /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os

t = int(os.environ["TFRL_ITER"])
which = os.environ["TFRL_WHICH"]
short = os.environ["TFRL_SHORT"]
root = "docs/readiness/2026-10-11-slurp-tfrl-loop-i%d-%s-v1"
steps = []
if which == "column":
    slug = f"tfrl-loop-i{t}-fold-b"
    facts = json.load(open(root % (t, "fold-b") + "/registered-facts-v1.json", encoding="utf-8"))
    contacts = int(facts["accounting"]["contacts_per_row"])
    upper = slug.upper()
    steps.append({
        "order": 1, "short": short, "kind": "cell",
        "experiment": f"slurp-native-stage3-{slug}-v1", "cell": f"slurp-native-stage3-{slug}-v1",
        "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1", "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
        "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
        "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1", "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
        "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
        "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
        "smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation-v1",
        "expected_rows": 1080, "contacts_per_row": contacts, "ceiling_per_row": contacts, "notool": True,
        "owner": f"root-slurp-native-stage3-{slug}-v1",
    })
else:
    for order, (tag, kind) in enumerate((("proposer", "typed"), ("ace-reflector", "ace")), start=1):
        slug = f"tfrl-{tag}-i{t}"
        facts = json.load(open(root % (t, "proposers") + "/registered-facts-v1.json", encoding="utf-8"))
        rows = int(facts["rows"][kind])
        steps.append({
            "order": order, "short": f"{short}-{kind}", "kind": "cell",
            "experiment": f"slurp-native-stage3-{slug}-v1", "cell": f"slurp-native-stage3-{slug}-v1",
            "smoke_experiment": None, "smoke_cell": None, "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
            "run_id": f"SAEA-SLURP-STAGE3-{slug.upper()}-V1", "fit_run_id": None,
            "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
            "smoke_run_id": None, "smoke_attempt_id": None,
            "expected_rows": rows, "contacts_per_row": 1, "ceiling_per_row": 1, "notool": True,
            "owner": f"root-slurp-native-stage3-{slug}-v1",
        })
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [$SHORT $WHICH] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
