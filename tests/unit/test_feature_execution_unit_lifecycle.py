"""Configured lifecycle proof for source-bound feature execution units."""
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity, WindowRequestBatch, prepare_window_feature_inventory,
)
from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnitRoster
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter
from test_feature_execution_unit_client import _feature_unit_world
from test_flight_runtime import _FakeGate, _git_init_commit, _write_configs, _write_exposure_ledger
from test_rails_runner import _knowledge_snapshot


@dataclass(frozen=True)
class _Sample:
    sample_id: str
    media_relpath: str
    audio_ref: object
    audio_seconds: float


class _WindowAdapter(TaskAdapter):
    SERVING_SLOTS = 2
    SERVING_SLOT_TOKENS = 8192
    SERVING_MAX_TOKENS = 64

    def __init__(self, samples):
        self.samples = tuple(samples)

    def load_split(self, split_id):
        assert split_id == "fake-split"
        return self.samples

    def build_task_contract(self, sample, obs):
        return "Return the transcript for this registered speech window."

    def instruction(self, sample):
        return "Transcribe the registered speech window."

    def gold(self, sample):
        raise AssertionError("generation must not read gold")

    def score_response(self, gold, response):
        raise AssertionError("generation must not score")


@pytest.mark.parametrize(
    ("policy", "planned_calls"),
    (("phase-direct-only-v1", 2), ("phase-native-review-revise-v1", 8)),
)
def test_configured_feature_units_complete_shared_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, policy: str, planned_calls: int
):
    """The real configured path must not require a fake whole-parent packet."""
    from speech_aware_evidence_acquisition.core import preparation_window_packets as packets_module
    from speech_aware_evidence_acquisition.core.preparation_window_packets import (
        PreparedWindowFeaturePackets, WindowPacketBinding,
    )

    world, parent, _, _, feature_root, attached, packets = _feature_unit_world(tmp_path)
    samples = (_Sample(parent.sample_id, parent.audio_ref.path, parent.audio_ref, parent.audio_seconds),)
    raw = ExecutionUnitRoster(tuple(replace(
        unit, speech_packet_id=None, speech_packet_sha256=None,
    ) for unit in attached.units))
    split_hash = split_identity_hash(prefixed("fake-carrier", (parent.sample_id,)))
    batch = WindowRequestBatch(
        tuple({
            "sample_id": unit.parent_sample_id,
            "media_relpath": unit.slice_record.media_relpath,
            "audio_seconds": unit.slice_record.audio_seconds,
            "sample_rate_hz": unit.slice_record.sample_rate_hz,
        } for unit in raw.units),
        tuple(unit.request_key for unit in raw.units),
        tuple(unit.slice_record.trace_view() for unit in raw.units),
    )
    inventory = world.data_root / "prepared/units.json"
    prepare_window_feature_inventory(
        inventory, batches={"proof": batch}, data_root=world.data_root,
        encoder_identity=WindowFeatureEncoderIdentity("a" * 64, "b" * 40, "d" * 64, "f" * 64),
    )
    packet_path = world.data_root / "prepared/packets.json"
    packet_path.write_text("{}", encoding="utf-8")
    bindings = tuple(WindowPacketBinding(
        request_key=unit.request_key,
        source_key=f"{unit.request_key}@{unit.slice_record.sha256}",
        packet_id=packet.packet_id,
        packet_sha256=packet.packet_sha256,
        audio_sha256=unit.slice_record.sha256,
        cache_key=f"cache-{index}",
        sources=({"source_provenance": unit.slice_record.trace_view()},),
        chunks=(),
    ) for index, (unit, packet) in enumerate(zip(raw.units, packets, strict=True)))
    prepared = PreparedWindowFeaturePackets(
        inventory_file_sha256="1" * 64, cache_audit_file_sha256="2" * 64,
        provenance_file_sha256="3" * 64, inventory_sha256="4" * 64,
        encoder_identity={"decoder_gguf_sha256": "d" * 64}, legacy_cache_dir="unused",
        feature_root=str(feature_root), request_count=2, unique_packet_count=2,
        bindings=bindings, by_request_key={item.request_key: item for item in bindings},
    )
    monkeypatch.setattr(
        packets_module, "load_prepared_window_feature_packets",
        lambda path, expected_sha256, data_root: prepared,
    )

    snapshot = _knowledge_snapshot()
    snapshot_path = world.data_root / "knowledge/snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot.frozen_json(), sort_keys=True), encoding="utf-8")
    run_id = f"SAEA-WINDOW-LIFECYCLE-{planned_calls}"
    repo = tmp_path / "repo"
    phases = ("direct",) if policy == "phase-direct-only-v1" else (
        "perception", "solver", "reviewer", "planner",
    )
    baseline = {
        "knowledge_snapshot_relpath": "knowledge/snapshot.json",
        "knowledge_snapshot_sha256": snapshot.content_hash(),
        "prepared_execution_units": {
            "relpath": "prepared/units.json", "sha256": hashlib.sha256(inventory.read_bytes()).hexdigest(),
            "batch": "proof", "registry_run_id": "feature-unit-source", "unit_count": 2,
            "split_identity_hash": split_hash,
        },
        "prepared_window_feature_packets": {
            "path": str(packet_path), "sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        },
        "phase_material": {phase: {
            "instruction_fill": None, "instruction_template": f"probes/{phase}.txt",
            "predecessor_binding": "none",
        } for phase in phases},
        "speech_feature_key_representation_id": "window-query-v1",
        "speech_feature_matcher_policy_id": "window-direct-v1",
    }
    if policy == "phase-native-review-revise-v1":
        baseline.update(
            native_episode={
                "schema": "saea-native-episode-config-v1", "episode_id": "configured-window-proof",
                "max_revisions": 0,
                "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
                "roles": {role: {"phase_id": role, "max_iterations": 1} for role in phases},
            },
            native_contact_fit={"run_id": f"{run_id}-FIT", "attempt_id": "attempt-fit", "contact_cap": 8},
        )
    _write_configs(
        repo, arm="speech-feature-query", policy=policy, carrier_lock_key="fake-carrier",
        model_extra={
            "runtime_receipt": "receipts/inference.json", "prompt_order": "speech-query-prefix-v2",
            "speech_feature_root": str(feature_root),
            "decoding_params": {"temperature": 0, "max_tokens": 64},
            "server_args": [], "server_env": {
                "LLAMA_SPEECH_FEATURE_ROOT": str(feature_root),
                "LLAMA_SPEECH_DECODER_SHA256": "d" * 64,
            },
        },
        baseline_extra=baseline,
        execution_plan_overrides={
            "planned_model_calls": planned_calls, "planned_speech_audio_seconds": 3,
        },
    )
    for phase in phases:
        prompt = repo / "configs/probes" / f"{phase}.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(f"Complete the {phase} role for this speech window.\n", encoding="utf-8")
    _write_exposure_ledger(repo, run_id)
    _git_init_commit(repo)

    runtime = FlightRuntime(
        repo, world.data_root, model="m", dataset="d", baseline="b", experiment="e",
        run_id=run_id, attempt_id="attempt-lifecycle", runtime_root=tmp_path / "runtime",
        adapter_factory=lambda _lock, _root: _WindowAdapter(samples),
        gate_factory=lambda *_args, **_kwargs: _FakeGate(), lock={},
    )

    runtime.preflight()
    runtime.preprocess(workers=1)
    assert runtime.execution_unit_roster() == attached
