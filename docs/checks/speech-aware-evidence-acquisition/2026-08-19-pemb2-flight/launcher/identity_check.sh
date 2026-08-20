#!/usr/bin/env bash
# Identity-only dry check: build both runs' config values, hashes, plans and
# server argv WITHOUT touching the data root's media, spawning a server, or
# contacting a model. Catches a launcher wiring defect before the slow
# split-load pre-flight pays 13 minutes for it.
SDIR=/mnt/c/Users/35686/AppData/Local/Temp/claude/D--chao-workspace-exploring-l4-intelligence-studies-speech-aware-evidence-acquisition/6d9f1834-68e9-41a7-bbcc-724898cf15a9/scratchpad/tri2/pemb
source "$SDIR/env.sh"
cd "$REPO"
LOG="$SCRATCH/identity-check.log"
{
for RUN in A B; do
  case "$RUN" in
    A) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/slurp-q4km ;;
    B) export SAEA_FEAT_CACHE_DIR=/home/chao/feat-cache/audio2tool-q4km ;;
  esac
  echo "=== Run $RUN (SAEA_FEAT_CACHE_DIR=$SAEA_FEAT_CACHE_DIR) ==="
  SAEA_RUN="$RUN" python - <<'PY'
import json
import os
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, os.environ["SCRATCH"])

from flight_identity import (
    EXECUTION_PROFILE,
    RUNS,
    SPLIT_ROLE,
    build_values,
    config_hash_of,
    run_id_for,
    server_args,
    server_env,
    split_identity_hash_for,
)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.config import protocol_hash as ph

run_key = os.environ["SAEA_RUN"]
block = RUNS[run_key]
values = build_values(REPO, run_key)
cfg = config_hash_of(values)
split = split_identity_hash_for(run_key)
print("  run_id:", run_id_for(run_key))
print("  split_identity_hash:", split)
print("  config_hash:", cfg)
print("  protocol_hash:", ph(cfg, str(values["arm"]), split))
print("  base_url:", values["base_url"])
print("  server_args:", " ".join(server_args(values)))
print("  server_env:", json.dumps(server_env(values), sort_keys=True))
print("  planned:", json.dumps(block["planned_budgets"], sort_keys=True))
print("  registered:", json.dumps(block["registered_ceilings"], sort_keys=True))
plan = ExecutionPlan(
    run_id=run_id_for(run_key),
    execution_profile=EXECUTION_PROFILE,
    carrier_lock_key=str(block["carrier_lock_key"]),
    split_role=SPLIT_ROLE,
    split_identity_hash=split,
    planned_model_calls=int(block["planned_budgets"]["model_calls"]),
    planned_gpu_hours=float(block["planned_budgets"]["gpu_hours"]),
    planned_speech_audio_seconds=int(block["planned_budgets"]["speech_audio_seconds"]),
    protocol_hash=ph(cfg, str(values["arm"]), split),
    attempt_id="attempt-identitycheck-000000",
).validate()
print("  ExecutionPlan: OK", plan.execution_profile, plan.split_role, plan.carrier_lock_key)
PY
  echo
done
echo "IDENTITY CHECK DONE"
} 2>&1 | tee "$LOG"
