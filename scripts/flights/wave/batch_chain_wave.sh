#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Owner decisions 77 / 160 / 164: fly the knowledge wave on the SLURP np4 geometry through the batch driver as
# ONE chain with ONE shared in-chain A/A (SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1, the retained AGREE arm's own
# bytes), in the order the A/A -> W1 -> W3a -> W4, each arm read against that A/A.
#
# The driver flies ONE smoke per step and then that step's campaign plan, so the order is realised as THREE
# steps of ONE queue, the A/A in the first, on the same resident session with nothing else between them:
#   step 1 (w1): the W1 four-row form smoke, then the wave campaign plan
#                configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json = [the shared A/A, the W1 arm];
#   step 2 (w3): the W3 four-row form smoke, then W3's plan [the W3 arm] -- W3a ONLY (W3b, the per-intent
#                exemplar cap, is dropped; wave_preconditions.py refuses a W3 arm that still carries it);
#   step 3 (w4): the W4 four-row form smoke, then W4's plan [the W4 arm].
# Why this order, as decision 160 set it for COMP-1 + G5: the first arm's form is smoked before anything is
# spent; the A/A is spent only beside the arm it is first read against; a later smoke failure leaves a complete,
# readable (A/A, W1) pair instead of an orphaned A/A. The driver inspects each step's LAST cell (the W1, W3 and
# W4 arms); a passing step-1 inspect implies the A/A sealed first. ceiling_per_row 11 = 1 + 2 x (1 + 3 + 1) at
# max_revisions 1; contacts_per_row 5 is informational (the sealed AGREE arm realised 4.060).
# WAVE_SKIP_W3=1 at flip time drops step 2; the chain reads the step list the flip converged on
# (/home/chao/wave-flight-steps.txt) and never decides it itself.
#
# Preconditions: scripts/flights/wave/wave_flip.sh converged every cell at one HEAD and wrote
# /home/chao/wave-flight-commit.txt and /home/chao/wave-flight-steps.txt; the resident session is
# serving-slurp-native-candidate-five-train-a-np4-v1; no other batch is running. The driver's own registration
# gate (scripts/checks/flight_registration_check.py) then refuses any step whose rows are not countersigned or
# whose receipt does not list every run id eligible.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=$SAEA_DATA_ROOT
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-wave.out
QUEUE=/home/chao/batch-queue.json
PY=/home/chao/.venvs/speechrl/bin/python
COMMIT=$(cat /home/chao/wave-flight-commit.txt) || exit 1
STEPS=$(cat /home/chao/wave-flight-steps.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT steps [$STEPS] session $BATCH_SESSION" >> $LOG
case "$STEPS" in "w1 w3 w4"|"w1 w4") ;; *) echo "unexpected step list [$STEPS]; abort" >> $LOG; exit 3;; esac
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
# The flight commit must carry the shared mode (decision 164) -- read from the checkout that will fly.
SKIP=()
case " $STEPS " in *" w3 "*) ;; *) SKIP=(--skip-w3);; esac
PYTHONDONTWRITEBYTECODE=1 $PY -B "$REPO/scripts/flights/wave/wave_preconditions.py" --repo-root "$REPO" --data-root "$DATA" \
  --mode chain "${SKIP[@]}" >> $LOG 2>&1 || { echo "shared-A/A precondition refused; abort" >> $LOG; exit 6; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
QUEUE="$QUEUE" STEPS="$STEPS" $PY - <<'PY'
import json
import os
common = {"expected_rows": 1080, "contacts_per_row": 5, "ceiling_per_row": 11, "notool": True}
catalogue = {
    "w1": {"short": "w1", "kind": "cell",
           "experiment": "slurp-native-stage3-w1-cardsel-fold-a-v1",
           "cell": "slurp-native-stage3-w1-cardsel-fold-a-v1",
           "smoke_experiment": "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1",
           "smoke_cell": "slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1",
           "campaign_plan": "configs/campaign/slurp-native-stage3-wave1-fold-a-v1.json",
           "run_id": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-V1",
           "fit_run_id": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-FIT-V1",
           "gen_attempt_id": "attempt-slurp-native-stage3-w1-cardsel-fold-a-generation-v1",
           "smoke_run_id": "SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-SMOKE-4-V1",
           "smoke_attempt_id": "attempt-slurp-native-stage3-w1-cardsel-fold-a-smoke-4-generation-v1",
           "owner": "root-slurp-native-stage3-w1-cardsel-fold-a-v1"},
    "w3": {"short": "w3", "kind": "cell",
           "experiment": "slurp-native-stage3-w3-fold-a-v1",
           "cell": "slurp-native-stage3-w3-fold-a-v1",
           "smoke_experiment": "slurp-native-stage3-w3-fold-a-smoke-4-v1",
           "smoke_cell": "slurp-native-stage3-w3-fold-a-smoke-4-v1",
           "campaign_plan": "configs/campaign/slurp-native-stage3-w3-fold-a-v1.json",
           "run_id": "SAEA-SLURP-STAGE3-W3-FOLD-A-V1",
           "fit_run_id": "SAEA-SLURP-STAGE3-W3-FOLD-A-FIT-V1",
           "gen_attempt_id": "attempt-slurp-native-stage3-w3-fold-a-generation-v1",
           "smoke_run_id": "SAEA-SLURP-STAGE3-W3-FOLD-A-SMOKE-4-V1",
           "smoke_attempt_id": "attempt-slurp-native-stage3-w3-fold-a-smoke-4-generation-v1",
           "owner": "root-slurp-native-stage3-w3-fold-a-v1"},
    "w4": {"short": "w4", "kind": "cell",
           "experiment": "slurp-native-stage3-w4-fold-a-v1",
           "cell": "slurp-native-stage3-w4-fold-a-v1",
           "smoke_experiment": "slurp-native-stage3-w4-fold-a-smoke-4-v1",
           "smoke_cell": "slurp-native-stage3-w4-fold-a-smoke-4-v1",
           "campaign_plan": "configs/campaign/slurp-native-stage3-w4-fold-a-v1.json",
           "run_id": "SAEA-SLURP-STAGE3-W4-FOLD-A-V1",
           "fit_run_id": "SAEA-SLURP-STAGE3-W4-FOLD-A-FIT-V1",
           "gen_attempt_id": "attempt-slurp-native-stage3-w4-fold-a-generation-v1",
           "smoke_run_id": "SAEA-SLURP-STAGE3-W4-FOLD-A-SMOKE-4-V1",
           "smoke_attempt_id": "attempt-slurp-native-stage3-w4-fold-a-smoke-4-generation-v1",
           "owner": "root-slurp-native-stage3-w4-fold-a-v1"},
}
steps = [dict(catalogue[name], order=index, **common) for index, name in enumerate(os.environ["STEPS"].split(), start=1)]
json.dump(steps, open(os.environ["QUEUE"], "w"), indent=1)
PY
echo "queue [w1: smoke, then the shared A/A + the W1 arm; then$(echo " $STEPS" | sed 's/ w1//; s/ w3/ w3: smoke, then the W3a arm;/; s/ w4/ w4: smoke, then the W4 arm/')] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
