#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 187 / 196: fly the Audio2Tool consumption-module ALL-OFF arm (carrier admission gate, design 2b.3) ONLY
# after the owner reopens Audio2Tool (decision 187 keeps the GPU on SLURP until the SLURP lock), on the AUDIO2TOOL serving
# geometry through the batch driver. ONE step: the four-row form smoke first (driver-enforced), then the 400-row arm.
# The direct-only program makes exactly one contact per row (contacts_per_row = ceiling_per_row = 1); notool.
# The arm is request-identical to A2T-AA pass A / B, so it need not fly at all if the byte proof (--at a2t0) suffices:
# its module null is h_A2T by construction. Preconditions: the DRAFT rows countersigned, the receipt minted, both cells
# flipped (module_alloff_a2t0_flip.sh wrote /home/chao/module-alloff-a2t0-flight-commit.txt), the A2T session resident
# and the SLURP session stopped, no other batch running.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-module-alloff-a2t0.out
COMMIT=$(cat /home/chao/module-alloff-a2t0-flight-commit.txt) || exit 1
export BATCH_SESSION=serving-a2t-native-role-base-np3-max2048-v3
echo "chain start $(date -u +%FT%TZ) commit $COMMIT session $BATCH_SESSION" >> $LOG
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort" >> $LOG; exit 7; fi
S=$SAEA_DATA_ROOT/serving/$BATCH_SESSION
if [ ! -f "$S/session.json" ] || [ -f "$S/session-stop.json" ]; then echo "the A2T session is not resident ($S); abort" >> $LOG; exit 8; fi
SL=$SAEA_DATA_ROOT/serving/serving-slurp-native-candidate-five-train-a-np4-v1
if [ -f "$SL/session.json" ] && [ ! -f "$SL/session-stop.json" ]; then echo "the SLURP session is still resident; abort" >> $LOG; exit 8; fi
cd $MAIN || exit 1
git -C "$REPO" checkout -q --detach "$COMMIT" || { echo "checkout failed" >> $LOG; exit 2; }
echo "$COMMIT" > /home/chao/batch-flight-commit.txt
for f in /home/chao/batch-status.jsonl /home/chao/batch-done /home/chao/batch-STOP; do [ -e "$f" ] && mv "$f" "$f.$(date -u +%Y%m%dT%H%M%SZ).bak"; done
/home/chao/.venvs/speechrl/bin/python - <<'PY'
import json
steps = [
    {"order": 1, "short": "module-alloff-a2t0", "kind": "cell",
     "experiment": "a2t-native-stage3-module-alloff-v1", "cell": "a2t-native-stage3-module-alloff-v1",
     "smoke_experiment": "a2t-native-stage3-module-alloff-smoke-4-v1", "smoke_cell": "a2t-native-stage3-module-alloff-smoke-4-v1",
     "campaign_plan": "configs/campaign/a2t-native-stage3-module-alloff-v1.json",
     "run_id": "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-V1", "fit_run_id": "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-FIT-V1",
     "gen_attempt_id": "attempt-a2t-native-stage3-module-alloff-v1-generation-v1",
     "smoke_run_id": "SAEA-A2T-NATIVE-STAGE3-MODULE-ALLOFF-SMOKE-4-V1",
     "smoke_attempt_id": "attempt-a2t-native-stage3-module-alloff-smoke-4-v1-generation-v1",
     "expected_rows": 400, "contacts_per_row": 1, "ceiling_per_row": 1, "notool": True,
     "owner": "root-a2t-native-stage3-module-alloff-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [module-alloff-a2t0: smoke, then arm] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
