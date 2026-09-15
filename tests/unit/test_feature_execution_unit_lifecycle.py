"""Configured lifecycle proof for source-bound feature execution units."""
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.core.bundle.outputs import (
    _minimum_model_calls_from_trace,
    _verify_outputs_trace_binding,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.model.transport import LlamaServerTransport
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity, WindowRequestBatch, prepare_window_feature_inventory,
)
from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnitRoster
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter
from test_feature_execution_unit_client import _feature_unit_world
from test_flight_runtime import _FakeGate, _git_init_commit, _write_configs, _write_exposure_ledger
from test_flight_runtime import (
    _fake_bundle_finalizer,
    _fake_bundle_verifier,
    _fake_ledger_validator,
    _fake_score_batch,
    _fake_session_stopper,
)
from test_llama_server_transport import (
    _base_url,
    _fake_inference_session,
    _fake_runtime_receipt,
    _live,
    _MODEL_FILES,
    _spawn_live_matching_process,  # noqa: F401
)
from test_native_episode_runner import _wire_response
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
    ("policy", "planned_calls", "actual_contacts"),
    (("phase-direct-only-v1", 2, 2), ("phase-native-review-revise-v1", 22, 8)),
)
def test_configured_feature_units_complete_shared_lifecycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
    planned_calls: int,
    actual_contacts: int,
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
                "max_revisions": 1,
                "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
                "roles": {
                    role: {
                        "phase_id": role,
                        "max_iterations": 3 if role == "reviewer" else 1,
                    }
                    for role in phases
                },
            },
            native_contact_fit={
                "run_id": f"{run_id}-FIT",
                "attempt_id": "attempt-fit",
                "contact_cap": 22,
            },
        )
    _write_configs(
        repo, arm="speech-feature-query", policy=policy, carrier_lock_key="fake-carrier",
        model_extra={
            "transport": "llama-server", "base_url": _base_url(),
            "runtime_receipt": "receipts/inference.json", "prompt_order": "speech-query-prefix-v2",
            "preserve_wire_responses": policy == "phase-native-review-revise-v1",
            "speech_feature_root": str(feature_root),
            "decoding_params": {"temperature": 0, "max_tokens": 64},
            "server_args": [], "server_env": {
                "LLAMA_SPEECH_FEATURE_ROOT": str(feature_root),
                "LLAMA_SPEECH_DECODER_SHA256": "d" * 64,
            },
        },
        baseline_extra=baseline,
        execution_plan_overrides={
            "planned_model_calls": planned_calls,
            "planned_speech_audio_seconds": math.ceil(
                sum(unit.slice_record.audio_seconds for unit in attached.units)
                * (actual_contacts // len(attached.units))
            ),
        },
    )
    for phase in phases:
        prompt = repo / "configs/probes" / f"{phase}.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text(f"Complete the {phase} role for this speech window.\n", encoding="utf-8")
    _write_exposure_ledger(repo, run_id)
    _git_init_commit(repo)

    rendered = []

    def post(_url, body):
        request = json.loads(body)
        rendered.append(request)
        wire_text = json.dumps(request, sort_keys=True)
        current_instruction = json.dumps(request["messages"][-1], sort_keys=True)
        window = "one" if "window/0" in wire_text else "two"
        if "Complete the planner role" in current_instruction:
            text = "ACCEPT"
        elif "Complete the solver role" in current_instruction:
            text = f"solver window {window}"
        elif "Complete the reviewer role" in current_instruction:
            text = f"reviewer window {window}"
        elif "Complete the perception role" in current_instruction:
            text = f"perception window {window}"
        else:
            text = f"direct window {window}"
        return _wire_response(text)

    def transport_factory(values, data_root, *, session, runtime_receipt, runtime_root):
        return LlamaServerTransport(
            values["base_url"], data_root, session, runtime_receipt, runtime_root,
            post=post, prompt_order=values["prompt_order"],
            feature_root=Path(values["speech_feature_root"]),
            preserve_wire_responses=values["preserve_wire_responses"],
        )

    decoder = replace(_MODEL_FILES[0], sha256="d" * 64)

    def session_starter(**kwargs):
        return replace(
            _fake_inference_session(host=kwargs["host"], port=kwargs["port"]),
            model_files=(decoder,),
        )

    def runtime_receipt():
        receipt = _fake_runtime_receipt()
        receipt["gguf_files"][0] = {"path": decoder.path, "sha256": decoder.sha256}
        return receipt

    manifest_checks = []

    def manifest_builder(**kwargs):
        result = kwargs["result"]
        rows = tuple(json.loads(line) for line in result.outputs_path.read_text().splitlines())
        trace_path = result.outputs_path.with_name(f"{run_id}.trace.jsonl")
        traces = {
            row["record_id"]: row["payload"]
            for row in (json.loads(line) for line in trace_path.read_text().splitlines())
        }
        _verify_outputs_trace_binding(rows, traces)
        assert _minimum_model_calls_from_trace(traces) == actual_contacts
        assert len(rows) == 1 and rows[0]["sample_id"] == parent.sample_id
        assert rows[0]["text"] == (
            "direct window one direct window two"
            if policy == "phase-direct-only-v1"
            else "solver window one solver window two"
        )
        assert [
            source["execution_unit_id"]
            for source in rows[0]["execution_unit_delivery"]["sources"]
        ] == [unit.request_key for unit in attached.units]
        path = Path(kwargs["run_dir"]) / f"{run_id}.run-manifest.json"
        path.write_text(json.dumps({
            "schema": "synthetic-complete-trace-bound-manifest-v1",
            "run_id": run_id,
            "outputs_sha256": hashlib.sha256(result.outputs_path.read_bytes()).hexdigest(),
            "trace_manifest_hash": result.trace_manifest_hash,
            "model_contacts": actual_contacts,
        }, sort_keys=True), encoding="utf-8")
        manifest_checks.append(path)
        return path

    score_jobs = []

    def scoring_handoff(jobs, **kwargs):
        assert manifest_checks and len(jobs) == 1
        assert jobs[0].manifest == manifest_checks[0].resolve()
        score_jobs.extend(jobs)
        return _fake_score_batch(jobs, **kwargs)

    if policy == "phase-native-review-revise-v1":
        from speech_aware_evidence_acquisition.core import preparation_fit

        def fit_factory(runtime, program, plan):
            def gate(request):
                runtime._transport.render_request(request.payload_bytes)
                gate.receipts.append({
                    "prepared_request_sha256": hashlib.sha256(request.payload_bytes).hexdigest(),
                    "capacity_verified": True,
                })
            gate.receipts = []
            return gate

        monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", fit_factory)

    runtime = FlightRuntime(
        repo, world.data_root, model="m", dataset="d", baseline="b", experiment="e",
        run_id=run_id, attempt_id="attempt-lifecycle", runtime_root=_live["runtime_root"],
        adapter_factory=lambda _lock, _root: _WindowAdapter(samples),
        gate_factory=lambda *_args, **_kwargs: _FakeGate(), lock={},
        carrier_root_resolver=lambda _lock, _key, _root: world.carrier_root,
        session_starter=session_starter,
        session_stopper=_fake_session_stopper,
        serving_session_finder=lambda _root: None,
        runtime_receipt_loader=lambda _path: runtime_receipt(),
        transport_factory=transport_factory,
        manifest_builder=manifest_builder,
        bundle_verifier=_fake_bundle_verifier,
        bundle_finalizer=_fake_bundle_finalizer,
        ledger_validator=_fake_ledger_validator,
        score_batch=scoring_handoff,
        host="127.0.0.1", port=_live["port"],
    )

    runtime.preflight()
    runtime.preprocess(workers=1)
    assert runtime.execution_unit_roster() == attached
    runtime.serve()
    phase_receipt = runtime.run_phases(workers=1)
    assert phase_receipt["contact_count"] == actual_contacts
    runtime.seal()
    runtime.score()
    assert len(rendered) == actual_contacts
    assert len(score_jobs) == 1
    assert runtime.receipts.completed_stages() == (
        "preflight", "preprocess", "serve", "run_phases", "seal", "score",
    )
