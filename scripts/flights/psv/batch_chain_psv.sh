#!/bin/bash
# Decisions 77 / 184 / 187: fly P-SV-1 then P-SV-2 on the SLURP np4 geometry (slurp-np4, session
# serving-slurp-native-candidate-five-train-a-np4-v1) through the batch driver. TWO steps, each the four-row form
# smoke first (driver-enforced), then the one-cell campaign plan. A/A-FREE: the twin branch t-twin flies inside
# every row (ruling O6), so each read is within its own flight. ceiling_per_row 15 = 11 + 2 (K - 1), K = 3, level 2;
# contacts_per_row 8 is informational (the sealed AGREE arm realised 4.06 per row on Fold A, plus exactly 4 branch
# contacts per row: B and T each one Perception and one first-visit Solver contact).
# Preconditions: both cells flipped in one converged loop (scripts/flights/psv/psv_flip.sh wrote
# /home/chao/psv-flight-commit.txt), the resident session is the np4 one above, and no other batch is running.
# The driver's registration gate (scripts/checks/flight_registration_check.py) refuses a step whose rows are not
# countersigned or whose receipt does not list every run id eligible.
#   bash scripts/flights/psv/batch_chain_psv.sh [psv1 psv2 psv3 psv4]   (default psv1 psv2 unchanged; name psv3/psv4 to fly them)
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-psv.out
CELLS="${*:-psv1 psv2}"
COMMIT=$(cat /home/chao/psv-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION cells $CELLS" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
# shellcheck disable=SC2086
/home/chao/.venvs/speechrl/bin/python - $CELLS <<'PY'
import json
import sys

steps = []
for order, key in enumerate(sys.argv[1:], start=1):
    slug = f"{key}-fold-b"
    upper = slug.upper()
    steps.append({
        "order": order, "short": key, "kind": "cell",
        "experiment": f"slurp-native-stage3-{slug}-v1",
        "cell": f"slurp-native-stage3-{slug}-v1",
        "smoke_experiment": f"slurp-native-stage3-{slug}-smoke-4-v1",
        "smoke_cell": f"slurp-native-stage3-{slug}-smoke-4-v1",
        "campaign_plan": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
        "run_id": f"SAEA-SLURP-STAGE3-{upper}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}-FIT-V1",
        "gen_attempt_id": f"attempt-slurp-native-stage3-{slug}-generation-v1",
        "smoke_run_id": f"SAEA-SLURP-STAGE3-{upper}-SMOKE-4-V1",
        "smoke_attempt_id": f"attempt-slurp-native-stage3-{slug}-smoke-4-generation-v1",
        "expected_rows": 1080, "contacts_per_row": 8, "ceiling_per_row": 15, "notool": True,
        "owner": f"root-slurp-native-stage3-{slug}-v1",
    })
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [$CELLS: smoke, then the one-arm campaign, each] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
