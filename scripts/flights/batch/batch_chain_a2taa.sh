#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Decisions 77 / 67 / 68 / 71 / 139: fly cell A2T-AA -- the four-row smoke, then pass A (400 rows), then pass B
# (400 rows, request-identical) -- on the AUDIO2TOOL serving geometry through the batch driver. TWO steps, one
# chain, one resident session. The direct-only phase program makes exactly one contact per row, so
# contacts_per_row 1 and ceiling_per_row 1 are the same number; notool: the direct baseline has no tool authority.
# Assumes: the SLURP session is STOPPED and the A2T session serving-a2t-native-role-base-np3-max2048-v3 is
# resident (serving_switch_to_a2t.sh, then SAEA-Serving-A2T + SAEA-Monitor-A2T from Windows, then a2t_wait_ready.sh);
# no batch running (checked); flight commit recorded by a2taa_flip_all.sh.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
REPO=/home/chao/saea-worktrees/fable-batch-flight
LOG=/home/chao/batch-chain-a2taa.out
COMMIT=$(cat /home/chao/a2taa-flight-commit.txt) || exit 1
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
    {"order": 1, "short": "a2taa-a", "kind": "cell",
     "experiment": "a2t-stage3-aa-paired-400-a-v1", "cell": "a2t-stage3-aa-paired-400-a-v1",
     "smoke_experiment": "a2t-stage3-aa-paired-400-smoke-4-v1", "smoke_cell": "a2t-stage3-aa-paired-400-smoke-4-v1",
     "campaign_plan": "configs/campaign/a2t-stage3-aa-paired-400-a-v1.json",
     "run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-A-V1", "fit_run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-A-FIT-V1",
     "gen_attempt_id": "attempt-a2t-stage3-aa-paired-400-a-generation-v1",
     "smoke_run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1", "smoke_attempt_id": "attempt-a2t-stage3-aa-paired-400-smoke-4-generation-v1",
     "expected_rows": 400, "contacts_per_row": 1, "ceiling_per_row": 1, "notool": True,
     "owner": "root-a2t-stage3-aa-paired-400-v1"},
    {"order": 2, "short": "a2taa-b", "kind": "cell",
     "experiment": "a2t-stage3-aa-paired-400-b-v1", "cell": "a2t-stage3-aa-paired-400-b-v1",
     "smoke_experiment": None, "smoke_cell": None, "smoke_run_id": None, "smoke_attempt_id": None,
     "campaign_plan": "configs/campaign/a2t-stage3-aa-paired-400-b-v1.json",
     "run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-B-V1", "fit_run_id": "SAEA-A2T-STAGE3-AA-PAIRED-400-B-FIT-V1",
     "gen_attempt_id": "attempt-a2t-stage3-aa-paired-400-b-generation-v1",
     "expected_rows": 400, "contacts_per_row": 1, "ceiling_per_row": 1, "notool": True,
     "owner": "root-a2t-stage3-aa-paired-400-v1"},
]
json.dump(steps, open("/home/chao/batch-queue.json", "w"), indent=1)
PY
echo "queue [a2taa-a, a2taa-b] written; starting driver $(date -u +%FT%TZ)" >> $LOG
bash $SP/batch_driver.sh >> /home/chao/batch-driver.out 2>&1
echo "driver exit $? $(date -u +%FT%TZ)" >> $LOG
