#!/usr/bin/env bash
# Syntax + import + dry-construction check for the launcher. ZERO model
# contact: nothing here spawns a server, loads a weight file or issues a
# request. It only proves the instrument itself parses, imports, and can
# compose its own identity/plan objects.
source "$(dirname "$0")/env.sh"
cd "$SCRATCH"

echo "=== bash -n ==="
for f in env.sh run_chain.sh takeoff_state.sh run_pytest.sh syntax_check.sh archive.sh bank_binding_check.sh probe_dims.sh; do
  [ -e "$f" ] && bash -n "$f" && echo "  ok $f"
done

echo
echo "=== python -m py_compile ==="
python -m py_compile launch_pemb4r_flight.py flight_identity.py glap_loader.py && echo "  ok (no .pyc written: PYTHONDONTWRITEBYTECODE=1)"

echo
echo "=== import + dry composition (no server, no weights, no contact) ==="
python - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, ".")

import flight_identity as fid
import glap_loader  # noqa: F401 -- import must cost nothing and load no weights
import launch_pemb4r_flight as L

from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path
from speech_aware_evidence_acquisition.rails.probes import pemb4r_flight as F

lock = load_lock(umbrella_lock_path())
root = data_root()
print("stages          :", L.STAGES)
print("arms            :", F.ARM_IDS)
print("models          :", F.MODELS)
print("ports           :", fid.SERVER_PORT_BY_MODEL, "generation", fid.GENERATION_PORT)
print("feat caches     :", fid.FEAT_CACHE_BY_MODEL, "core", fid.CORE_FEAT_CACHE_DIR)
print("gate contacts   :", fid.PLANNED_GATE_CONTACTS, fid.GATE_CONTACT_PLAN)
print("planned budgets :", fid.PLANNED_BUDGETS)

declared = {m: fid.gguf_declared_embedding_length(root / fid.gguf_relpaths(m)[0]) for m in ("lco3", "lco7", "qw")}
declared["glap"] = 1024
print("declared dims   :", declared)

fake_sha = {rel: "0" * 64 for rel in fid.all_hashed_relpaths()}
values = fid.build_values(L.REPO, lock, fake_sha, declared)
print("config hash (dry, placeholder hashes):", fid.config_hash_of(values))
print("transport       :", values["transport"], "| core server_args:", values["server_args"])
print("generation -np  :", values["generation_session"]["parallelism_np"])
print("decoding params :", values["decoding_params"])
print("core feat cache :", values["server_env"]["LLAMA_MTMD_FEAT_CACHE_DIR"])

plan = F.build_execution_plan(lock=lock, attempt_id="attempt-dry-0000")
print("machinery plan  :", plan.execution_profile, plan.planned_model_calls, plan.planned_speech_audio_seconds, plan.planned_gpu_hours)
print("protocol hash   :", plan.protocol_hash)

acc = F.GpuHoursAccounting(wall_hours=9.9, gpu_active_hours=0.4, measured_equivalent_hours=0.2)
F.assert_gpu_hours_within_ceiling(acc)
print("gpu accounting  : wall never gates -- 9.9 h wall accepted at 0.4 h active / 0.2 h measured-equivalent")
print("SYNTAX CHECK DONE")
PY
