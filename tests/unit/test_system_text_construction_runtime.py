"""Run synthetic knowledge construction through the shared flight and executor."""

import hashlib
import json
import struct
from types import SimpleNamespace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle import (
    build_manifest,
    finalize_bundle,
    verify_bundle,
)
from speech_aware_evidence_acquisition.rails import (
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.phase_runner import run_program
from speech_aware_evidence_acquisition.rails.system_text_construction import (
    materialize_slot_construction,
)
from test_flight_runtime import (
    _FakeAdapter,
    _make_repo,
    _make_runtime,
    _write_promotion_receipt,
    _git,
    _fake_session_starter,
    _fake_session_stopper,
    _fake_runtime_receipt_loader,
)
from test_rails_frozen_core_client import _World, _CapturingTransport
from test_rails_runner import _knowledge_snapshot
from test_semantic_knowledge_preparation import _write, _roster
from test_semantic_knowledge_edits import rows, contract, proposal
from test_system_text_construction import INSTRUCTION
from test_system_text_construction_integration import _pin, _release
from test_bundle import _HUMAN_LEDGER_CELLS
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def _flight(tmp_path, response):
    world = _World(tmp_path, data_root=tmp_path / "data")
    source = world.samples[0]
    sample = SimpleNamespace(
        sample_id="slurp:train:new",
        audio_ref=source.audio_ref,
        audio_seconds=source.audio_seconds,
        media_relpath=source.audio_ref.path,
    )
    world.samples = [sample]
    from speech_aware_evidence_acquisition.core.model import (
        SpeechFeatureChunkData,
        materialize_speech_feature_packet,
    )
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        packet_id_for_sample,
    )

    feature_root = tmp_path / "features"
    packet = materialize_speech_feature_packet(
        feature_root=feature_root,
        packet_id=packet_id_for_sample(sample.sample_id),
        audio_sha256=sample.audio_ref.sha256,
        encoder_receipt_sha256="e" * 64,
        decoder_gguf_sha256="d" * 64,
        mmproj_sha256="f" * 64,
        position_mode="mrope_1d",
        causal_attention=True,
        chunks=(
            SpeechFeatureChunkData(
                n_tokens=2,
                n_pos=2,
                n_embd=4,
                feature_bytes=struct.pack("<8f", *range(8)),
                position_bytes=struct.pack("<8i", 0, 1, 0, 1, 0, 1, 0, 1),
            ),
        ),
    )

    class ConstructionAdapter(_FakeAdapter):
        def __init__(self, lock, root):
            super().__init__(lock, root)
            self.samples = world.samples

        def gold(self, sample):
            raise AssertionError("Construction must never load task gold")

        def score_response(self, gold, response):
            raise AssertionError("Construction must never score task answers")

        def extract_consumption(self, sample, supply, response):
            raise AssertionError("Construction must never derive answer quality")

    run_id = "SAEA-TEST-SYSTEM-TEXT-CONSTRUCTION-RUNTIME"
    roster = _roster((sample.sample_id,), roster_id="synthetic-runtime-construction")
    repo = _make_repo(
        tmp_path,
        run_id,
        arm="speech-feature-query",
        policy="phase-direct-only-v1",
        carrier_lock_key="slurp",
        baseline_extra={
            "scorers": [],
            "result_kind": "artifact",
            "artifact_result": {
                "schema": "saea-artifact-result-binding-v1",
                "role": "training-feedback-proposal",
                "construction_roster": {
                    "repo_relpath": "construction.json",
                    "sha256": "0" * 64,
                },
            },
        },
    )
    roster_pin = _write(repo / "construction.json", roster)
    promotion_path = _write_promotion_receipt(
        tmp_path, feature_root=str(feature_root), packet_ids=(packet.packet_id,)
    )
    promotion = json.loads(promotion_path.read_text())
    promotion["packets"][0]["packet_sha256"] = packet.packet_sha256
    promotion["packets"][0]["mmproj_sha256"] = "f" * 64
    _write(promotion_path, promotion)
    template = repo / "configs/probes/artifact_direct.txt"
    template.parent.mkdir(parents=True, exist_ok=True)
    template.write_text(INSTRUCTION)
    baseline_path = repo / "configs/baseline/b.json"
    baseline = json.loads(baseline_path.read_text())
    baseline["artifact_result"]["construction_roster"]["sha256"] = roster_pin["sha256"]
    baseline.update(
        speech_packet_promotion_receipt=str(promotion_path),
        speech_feature_key_representation_id="key-fixture",
        speech_feature_matcher_policy_id="matcher-fixture",
        phase_material={
            "direct": {
                "instruction_template": "probes/artifact_direct.txt",
                "predecessor_binding": "none",
            }
        },
    )
    snapshot = _knowledge_snapshot()
    _write(world.data_root / "knowledge.json", snapshot.frozen_json())
    baseline.update(
        knowledge_snapshot_relpath="knowledge.json",
        knowledge_snapshot_sha256=snapshot.content_hash(),
    )
    _write(baseline_path, baseline)
    model_path = repo / "configs/model/m.json"
    model = json.loads(model_path.read_text())
    model["speech_feature_root"] = str(feature_root)
    _write(model_path, model)
    _git(repo, "add", "construction.json", "configs")
    _git(repo, "commit", "-qm", "Freeze synthetic runtime construction")
    transport = _CapturingTransport(responder=lambda _: response)

    def no_score(*args, **kwargs):
        raise AssertionError("An artifact flight must schedule zero task score jobs")

    runtime = _make_runtime(
        tmp_path,
        run_id=run_id,
        repo_root=repo,
        adapter_cls=ConstructionAdapter,
        session_starter=_fake_session_starter,
        session_stopper=_fake_session_stopper,
        runtime_receipt_loader=_fake_runtime_receipt_loader,
        client_factory=FrozenCoreClient,
        payload_binding_factory=build_payload_binding,
        carrier_root_resolver=lambda *_: world.carrier_root,
        transport_factory=lambda *a, **k: transport,
        packet_promoter=lambda **kwargs: (
            [packet],
            {"feature_root": str(feature_root)},
        ),
        phase_runner=run_program,
        manifest_builder=build_manifest,
        bundle_verifier=verify_bundle,
        bundle_finalizer=finalize_bundle,
        score_batch=no_score,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    generated = runtime.run_phases()
    sealed = runtime.seal(
        ledger_cells={**_HUMAN_LEDGER_CELLS, "speech task/carrier": "slurp discovery"}
    )
    scored = runtime.score()
    assert generated["result_kind"] == "artifact"
    assert (
        generated["dispatch"]["material_source"]
        == "baseline fragment phase_material (rails.phase_material)"
    )
    assert runtime._phase_summaries[0].agent_executor_id == "openjiuwen-workflow-v1"
    assert scored["status"] == "not-applicable" and scored["job_count"] == 0
    manifest = Path(sealed["manifest_path"])
    bundle = verify_bundle(manifest)
    assert (
        bundle.attempt_state == "FINALIZED"
        and bundle.manifest["cost"]["calls_used"] == len(transport.calls) == 1
    )
    (output,) = bundle.outputs_rows
    assert output["artifact_role"] == "training-feedback-proposal"
    assert output["text"] == response
    assert transport.calls[0]["history"][-1]["content"] == INSTRUCTION
    kwargs = dict(
        base_rows=rows(),
        contract=contract(rows()),
        generation_pin=_pin(manifest, world.data_root),
        instruction=INSTRUCTION,
        data_root=world.data_root,
    )
    return repo, world.data_root, manifest, kwargs


def test_shared_flight_artifact_executes_seals_and_releases_without_task_scoring(
    tmp_path,
):
    repo, data, manifest, kwargs = _flight(tmp_path, json.dumps(proposal(rows())))
    materialized = materialize_slot_construction(**kwargs)
    assert (
        materialized["rows"][0]["extraction_cues"]
        == proposal(rows())["edits"][0]["replacement"]
    )
    prior = hashlib.sha256(manifest.read_bytes()).hexdigest()
    _release(repo, data, kwargs)
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == prior


def test_shared_flight_no_change_retains_optimizer_exposure(tmp_path):
    response = proposal(rows())
    response["edits"] = []
    repo, data, manifest, kwargs = _flight(tmp_path, json.dumps(response))
    original = manifest.read_bytes()
    result, _ = _release(repo, data, kwargs)
    assert result["rows"] == rows()
    assert result["changed_fields"] == []
    assert result["optimizer_construction_sample_ids"] == [
        "slurp:train:new",
        "slurp:train:tie",
    ]
    assert manifest.read_bytes() == original


@pytest.mark.parametrize("invalid", ["wrong-base", "routing-edit", "not-json"])
def test_shared_flight_invalid_artifact_is_preserved_without_release(tmp_path, invalid):
    response = proposal(rows())
    if invalid == "wrong-base":
        response["base_rows_sha256"] = "0" * 64
    elif invalid == "routing-edit":
        response["edits"][0]["field"] = "intent_bindings"
    text = (
        "This is not a structured proposal."
        if invalid == "not-json"
        else json.dumps(response)
    )
    repo, data, manifest, kwargs = _flight(tmp_path, text)
    original = {p: p.read_bytes() for p in manifest.parent.iterdir() if p.is_file()}
    error, message = {
        "wrong-base": (PolicyError, "frozen slot-edit contract"),
        "routing-edit": (ValueError, "non-value edit"),
        "not-json": (json.JSONDecodeError, "Expecting value"),
    }[invalid]
    with pytest.raises(error, match=message):
        _release(repo, data, kwargs)
    assert not (data / "knowledge/semantic/synthetic-slot-contracts-v1").exists()
    assert not (data / "authored.json").exists()
    assert all(p.read_bytes() == content for p, content in original.items())
    assert verify_bundle(manifest).attempt_state == "FINALIZED"
