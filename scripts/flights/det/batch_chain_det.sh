#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 140: fly cell DET -- pass A, then pass B -- on the DET serving geometry through the
# batch driver. TWO steps in ONE chain (the VAR1 PLAN / PLANR shape), no smoke: the form is the locked
# plan itself, which has flown its own smoke and 1,080-row arm; the only new thing is the geometry,
# and a 50-row pass IS the form proof. ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at max_revisions 1;
# contacts_per_row 5 is informational (the sealed PLAN arm realised 5.023 per row).
#
# PRECONDITIONS (the coordinator's, in this order; this script refuses on the first two):
#   1. no flight, lease or driver process alive, and the flight lock clear;
#   2. the resident session is the DET session serving-slurp-native-det-np1-nocache-v1, started
#      from q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1
#      (scripts/flights/det/serving_task_entry_det.sh) AFTER the np4 session
#      serving-slurp-native-candidate-five-train-a-np4-v1 was stopped cleanly (one resident server
#      per geometry; core.session.serving.find_resident_session refuses two). The driver's own
#      prelaunch checks the session by id and requires it idle and healthy.
#   3. both cells flipped to ready (det_flip_all.sh) and the flight commit recorded in
#      /home/chao/det-flight-commit.txt.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
DATA=$SAEA_DATA_ROOT
LOG=/home/chao/batch-chain-det.out
COMMIT=$(cat /home/chao/det-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-det-np1-nocache-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh|lease_cli' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
[ -e "$DATA/locks/flight.lock" ] && { echo "flight.lock present; abort" >> $LOG; exit 7; }
S=$DATA/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "DET session $BATCH_SESSION is not resident; start it first (serving_task_entry_det.sh); abort" >> $LOG; exit 6; fi
NP4=$DATA/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$NP4/session.json" ] && [ ! -f "$NP4/session-stop.json" ]; then echo "the np4 session is still recorded resident; stop it first; abort" >> $LOG; exit 6; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
def step(order, p):
    P = p.upper()
    return {"order": order, "short": f"det-{p}", "kind": "cell",
            "experiment": f"slurp-native-stage3-det-np1-fold-a-50-{p}-v1",
            "cell": f"slurp-native-stage3-det-np1-fold-a-50-{p}-v1",
            "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
            "campaign_plan": f"configs/campaign/slurp-native-stage3-det-np1-fold-a-50-{p}-v1.json",
            "run_id": f"SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-{P}-V1",
            "fit_run_id": f"SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-{P}-FIT-V1",
            "gen_attempt_id": f"attempt-slurp-native-stage3-det-np1-fold-a-50-{p}-generation-v1",
            "expected_rows": 50, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True,
            "owner": f"root-slurp-native-stage3-det-np1-fold-a-50-{p}-v1"}
json.dump([step(1, "a"), step(2, "b")], open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [det-a, det-b] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
