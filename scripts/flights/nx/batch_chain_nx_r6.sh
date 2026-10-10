#!/bin/bash
# Decisions 77 / 187: fly NX round R6-P1 on the SLURP np4 geometry (slurp-np4, session serving-slurp-native-candidate-five-train-a-np4-v1)
# through the batch driver. ONE step: the four-row form smoke first (driver-enforced), then the one-cell campaign plan. A/A-FREE:
# the twin arm aa flies inside every row, so the read is within its own flight. ceiling_per_row 10 = 2 + 2 (5 - 1) on the review-off
# module graph (Perception 1, Solver 1 + 4 Perception template-arm contacts + 4 level-2 Solver contacts); contacts_per_row 10 is exact
# (no Reviewer or Planner visit).
# Preconditions: the cell flipped in one converged loop (scripts/flights/nx/nx_r6_flip.sh wrote /home/chao/nxr6-flight-commit.txt),
# the resident session is the np4 one above, no other batch is running (the R5 flight has sealed), and root has launched it. The
# driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not countersigned or whose
# receipt does not list every run id eligible.
#   bash scripts/flights/nx/batch_chain_nx_r6.sh
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
SLUG=nx-r6-perception-fold-b
SMOKE_REC=-rec1   # the smoke's single recovery attempt suffix (nx_r6_family.SMOKE_REC); the arm keeps its first-attempt ids
SHORT=nxr6
LOG=/home/chao/batch-chain-$SHORT.out
COMMIT=$(cat /home/chao/$SHORT-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION cell $SLUG" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
NX_SLUG=$SLUG NX_SMOKE_REC=$SMOKE_REC NX_SHORT=$SHORT /home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
import os

slug = os.environ["NX_SLUG"]
rec = os.environ["NX_SMOKE_REC"]
short = os.environ["NX_SHORT"]
upper = slug.upper()
steps = [{
    "order": 1, "short": short, "kind": "cell",
    "experiment": f"slurp-native-stage3-{slug}-v1",
    "cell": f"slurp-native-stage3-{slug}-v1",
    "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1",
    "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
    "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
    "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1",
    "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
    "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
    "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
    "smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation{rec}-v1",
    "expected_rows": 1080, "contacts_per_row": 10, "ceiling_per_row": 10, "notool": True,
    "owner": f"root-slurp-native-stage3-{slug}-v1",
}]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [$SHORT: smoke, then the one-arm campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
