#!/bin/bash
# Owner decisions 77 / 172: fly cell W4-SV on the SLURP np4 geometry through the batch driver. ONE step: the
# four-row form smoke first (driver-enforced), then the one-cell campaign plan
# configs/campaign/slurp-native-stage3-w4sv-fold-a-v1.json. There is no separate A/A: the in-flight twin arm
# t-twin is the null, so nothing else flies in this chain. ceiling_per_row 13 = 1 + 2 x (1 + 3 + 1) + (3 - 1) at
# max_revisions 1 with three first-visit Solver arms; contacts_per_row 6 is informational (the AGREE bytes realised
# 4.07 per row on this roster, plus exactly 2 arm contacts).
# Preconditions: scripts/flights/w4sv/w4sv_flip.sh converged both cells at one HEAD and wrote
# /home/chao/w4sv-flight-commit.txt; the resident session is serving-slurp-native-candidate-five-train-a-np4-v1;
# no other batch is running. The driver's own registration gate (scripts/checks/flight_registration_check.py)
# refuses a step whose rows are not countersigned or whose receipt does not list every run id eligible.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-w4sv.out
COMMIT=$(cat /home/chao/w4sv-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-slurp-native-candidate-five-train-a-np4-v1
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
PROOF=$REPO/docs/readiness/2026-09-28-slurp-stage3-w4-sv-fold-a-v1/arm-a-byte-identity-proof-v1.json
ARMB=$(/home/chao/.venvs/speechrl/bin/python -c "import json;print(json.load(open('$PROOF')).get('arm_b_verdict'))") || exit 3
[ "$ARMB" = "ARM-B-VARIES" ] || { echo "the flight commit's arm-A proof reads $ARMB; abort" >> $LOG; exit 6; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "w4sv", "kind": "cell",
     "experiment": "slurp-native-stage3-w4sv-fold-a-v1",
     "cell": "slurp-native-stage3-w4sv-fold-a-v1",
     "smoke_experiment": "slurp-native-stage3-w4sv-fold-a-smoke-4-v1",
     "smoke_cell": "slurp-native-stage3-w4sv-fold-a-smoke-4-v1",
     "campaign_plan": "configs/campaign/slurp-native-stage3-w4sv-fold-a-v1.json",
     "run_id": "SAEA-SLURP-STAGE3-W4SV-FOLD-A-V1",
     "fit_run_id": "SAEA-SLURP-STAGE3-W4SV-FOLD-A-FIT-V1",
     "gen_attempt_id": "attempt-slurp-native-stage3-w4sv-fold-a-generation-v1",
     "smoke_run_id": "SAEA-SLURP-STAGE3-W4SV-FOLD-A-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-slurp-native-stage3-w4sv-fold-a-smoke-4-generation-v1",
     "expected_rows": 1080, "contacts_per_row": 6, "ceiling_per_row": 13, "notool": True,
     "owner": "root-slurp-native-stage3-w4sv-fold-a-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [w4sv: smoke, then the arm in one campaign] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
