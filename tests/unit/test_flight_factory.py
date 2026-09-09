"""A shared factory composes registered carriers without loading gold or endpoints."""
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.rails.adapters.runtime_view import (
    RuntimeViewError, load_runtime_view,
)
from test_flight_runtime import _make_repo, _HAPPY_PATH_KWARGS, _FakeGate, _git


def view(tmp_path):
    audio = tmp_path / "media" / "one.wav"
    audio.parent.mkdir(parents=True)
    audio.write_bytes(b"synthetic media")
    return {
        "schema": "saea-speech-native-runtime-view-v1", "count": 1,
        "items": [{
            "sample_id": "slurp:devel:one:audio",
            "media_relpath": "media/one.wav",
            "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
            "audio_seconds": 1.0, "sample_rate_hz": 16000, "packet_id": "packet-one",
        }],
    }


@pytest.mark.parametrize("mutation,match", [
    (lambda doc: doc["items"][0].update(scenario="gold"), "label"),
    (lambda doc: doc["items"].append(dict(doc["items"][0])), "count"),
    (lambda doc: doc["items"][0].update(media_relpath="../escape.wav"), "confined"),
    (lambda doc: doc["items"][0].update(audio_sha256="0"*64), "hash"),
])
def test_runtime_view_refuses_leaks_duplicates_paths_and_identity(tmp_path, mutation, match):
    doc = view(tmp_path)
    mutation(doc)
    with pytest.raises(RuntimeViewError, match=match):
        load_runtime_view(doc, tmp_path)


def test_factory_uses_label_free_slurp_and_same_runtime(tmp_path):
    repo = _make_repo(
        tmp_path, "SLURP-FACTORY", carrier_lock_key="slurp",
        model_extra={"server_args": ["-np", "2", "-c", "8192"],
                     "base_url": "http://127.0.0.1:8080"},
        baseline_extra={"task_instruction": "Listen and return the spoken command.",
                        "serving_slots": 2, "serving_slot_tokens": 4096},
    )
    data = tmp_path / "data"
    doc = view(data)
    doc.update(carrier_lock_key="slurp", split_id="devel")
    (repo / "configs/dataset/d.json").write_text(json.dumps(doc))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind synthetic view")
    runtime = build_flight_runtime(
        repo, data, model="m", dataset="d", baseline="b", experiment="e",
        run_id="SLURP-FACTORY", attempt_id="a", runtime_root=tmp_path / "runtime",
        lock={}, gate_factory=lambda *a, **kw: _FakeGate(), **_HAPPY_PATH_KWARGS,
    )
    runtime.preflight()
    assert len(runtime.adapter.load_split("devel")) == 1
    sample = runtime.adapter.load_split("devel")[0]
    assert not sample.scenario and not sample.entities
    assert runtime.adapter.instruction(sample) == "Listen and return the spoken command."
    with pytest.raises(RuntimeViewError, match="gold"):
        runtime.adapter.gold(sample)
    assert runtime.adapter.serving_geometry()["slots"] == 2


def test_runtime_view_population_is_exact_and_hashes_selected_media(tmp_path):
    doc = view(tmp_path)
    samples = load_runtime_view(doc, tmp_path, sample_ids=["slurp:devel:one:audio"])
    assert len(samples) == 1
    with pytest.raises(RuntimeViewError, match="missing"):
        load_runtime_view(doc, tmp_path, sample_ids=["absent"])


def test_runtime_geometry_and_registered_population_are_checked():
    from speech_aware_evidence_acquisition.rails.adapters.runtime_view import (
        configured_geometry, registered_population_ids,
    )
    values = {
        "populations": [{"dataset_fragment": "d", "ids": ["one", "two"]}],
        "server_args": ["-np", "2", "-c", "8192"],
        "serving_slots": 2, "serving_slot_tokens": 4096,
    }
    assert registered_population_ids(values, "d") == ("one", "two")
    assert configured_geometry(values, defaults=(8, 8192, 64))["slots"] == 2
    values["populations"][0]["ids"] = ["one", "one"]
    with pytest.raises(RuntimeViewError, match="repeats"):
        registered_population_ids(values, "d")
    values["server_args"] = ["-np", "2", "-c", "4096"]
    with pytest.raises(RuntimeViewError, match="geometry"):
        configured_geometry(values, defaults=(8, 8192, 64))


def test_carrier_material_binding_reuses_frozen_provider_and_critic(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime_material import bind_runtime_material
    from speech_aware_evidence_acquisition.reproduction import slurp_official_eval
    from test_slurp_intent_candidates import _snapshot, _write_bank

    path, digest = _write_bank(tmp_path, {"s1": ("alarm_query",)}, {"s1": ("iot_set",)}, k=1)
    snapshot = _snapshot()
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot.frozen_json()))
    values = {
        "candidate_bank_relpath": path.name, "candidate_bank_sha256": digest,
        "phase_supply": {"direct": {}},
        "knowledge_snapshot_relpath": snapshot_path.name,
        "knowledge_snapshot_sha256": snapshot.content_hash(),
        "phase_review": {"direct": {"judges": ["slurp-legal-label-flag-v1"]}},
    }
    providers, reviews = {}, {}
    class Runtime:
        def bind_phase_supply_providers(self, value):
            providers.update(value)
        def bind_phase_review_material(self, value):
            reviews.update(value)
    inventory = object()
    monkeypatch.setattr(slurp_official_eval, "load_legal_intent_inventory", lambda *args: inventory)
    receipt = bind_runtime_material(Runtime(), values, {}, tmp_path)
    assert receipt["candidate_bank"]["rows"] == 1
    assert "direct" in providers
    assert reviews["direct"]["slurp-legal-label-flag-v1"]["inventory"] is inventory
    values["knowledge_snapshot_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="hash"):
        bind_runtime_material(Runtime(), values, {}, tmp_path)


def test_legacy_slurp_wrapper_reexports_shared_adapter_loader_and_binder():
    import runpy
    from pathlib import Path
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import (
        RuntimeSlurpAdapter, roster_samples,
    )
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime_material import bind_runtime_material
    repo = Path(__file__).resolve().parents[2]
    namespace = runpy.run_path(str(repo / "scripts/flights/run_slurp_closed_list_cell.py"))
    assert namespace["ClosedListSlurpAdapter"] is RuntimeSlurpAdapter
    assert namespace["roster_samples"] is roster_samples
    assert namespace["_bind_ku_s4_material"] is bind_runtime_material
