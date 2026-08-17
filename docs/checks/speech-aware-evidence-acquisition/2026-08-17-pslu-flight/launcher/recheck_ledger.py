"""Fast re-check of the exposure-ledger row ONLY (no split reload, no model
contact): runs the gate's own ``_require_exposure_preregistration`` against the
plan this flight will carry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path("/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from flight_identity import RUN_ID, build_values, config_hash_of  # noqa: E402

from speech_aware_evidence_acquisition.contracts import ExecutionPlan, FrozenCoreGate  # noqa: E402
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    model_lock_key,
    protocol_hash as compute_protocol_hash,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.data.lock import data_root, load_lock, umbrella_lock_path  # noqa: E402
from speech_aware_evidence_acquisition.rails.probes.pslu_flight import (  # noqa: E402
    load_pslu_sample_manifest,
)

FLIGHT = json.loads((REPO / "configs/probes/g0-binding/pslu-flight.json").read_text(encoding="utf-8"))

lock = load_lock(umbrella_lock_path())
root = data_root()
values = build_values(REPO)
manifest = load_pslu_sample_manifest(REPO / FLIGHT["sample_manifest"])
phash = compute_protocol_hash(config_hash_of(values), str(values["arm"]), manifest.split_identity_hash)

plan = ExecutionPlan(
    run_id=RUN_ID,
    execution_profile=FLIGHT["execution_plan"]["execution_profile"],
    carrier_lock_key=FLIGHT["execution_plan"]["carrier_lock_key"],
    split_role=FLIGHT["execution_plan"]["split_role"],
    split_identity_hash=manifest.split_identity_hash,
    planned_model_calls=int(FLIGHT["execution_plan"]["planned_model_calls"]),
    planned_gpu_hours=float(FLIGHT["execution_plan"]["planned_gpu_hours"]),
    planned_speech_audio_seconds=int(FLIGHT["execution_plan"]["planned_speech_audio_seconds"]),
    protocol_hash=phash,
    attempt_id="attempt-recheck-000000",
).validate()

gate = FrozenCoreGate.for_study_repo(
    REPO,
    root,
    Path("/home/chao"),
    runtime_receipt_relpath=runtime_receipt_relpath(values),
    expected_model_lock_key=model_lock_key(values),
)
gate._require_exposure_preregistration(plan, lock)
print("exposure pre-registration check: PASS")
gate._resolve_carrier_dataset_entry(plan.carrier_lock_key, lock)
print("carrier scope check: PASS")
gate._validate_e0()
print("E0 receipt check: PASS")
print(f"runtime receipt: {runtime_receipt_relpath(values)}  model_lock_key: {model_lock_key(values)}")
