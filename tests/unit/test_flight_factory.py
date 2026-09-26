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
    doc.update(carrier_lock_key="slurp", split_id="DEV-1000")
    (repo / "configs/dataset/d.json").write_text(json.dumps(doc))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind synthetic view")
    runtime = build_flight_runtime(
        repo, data, model="m", dataset="d", baseline="b", experiment="e",
        run_id="SLURP-FACTORY", attempt_id="a", runtime_root=tmp_path / "runtime",
        lock={}, gate_factory=lambda *a, **kw: _FakeGate(), **_HAPPY_PATH_KWARGS,
    )
    runtime.preflight()
    assert len(runtime.adapter.load_split("DEV-1000")) == 1
    sample = runtime.adapter.load_split("DEV-1000")[0]
    assert not sample.scenario and not sample.entities
    assert runtime.adapter.instruction(sample) == "Listen and return the spoken command."
    with pytest.raises(RuntimeViewError, match="gold"):
        runtime.adapter.gold(sample)
    assert runtime.adapter.serving_geometry()["slots"] == 2


def _factory_runtime_for_slurp_rows(
    tmp_path, *, split_id, sample_ids, registered_ids, split_role="discovery",
):
    repo = _make_repo(
        tmp_path, "SLURP-TRAIN-FACTORY", carrier_lock_key="slurp",
        model_extra={"server_args": ["-np", "2", "-c", "8192"]},
        baseline_extra={"task_instruction": "Return the spoken command.",
                        "serving_slots": 2, "serving_slot_tokens": 4096},
        execution_plan_overrides={"split_role": split_role},
        experiment_extra=(
            {"populations": [{"dataset_fragment": "d", "ids": registered_ids}]}
            if registered_ids is not None else {}
        ),
    )
    data = tmp_path / "data"
    document = view(data)
    first = document["items"][0]
    document["items"] = []
    for number, sample_id in enumerate(sample_ids):
        path = data / "media" / f"row-{number}.wav"
        path.write_bytes(f"synthetic media {number}".encode())
        document["items"].append({
            **first,
            "sample_id": sample_id,
            "media_relpath": f"media/row-{number}.wav",
            "audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "packet_id": f"packet-{number}",
        })
    document.update(
        count=len(document["items"]), carrier_lock_key="slurp",
        split_id=split_id, split_name=split_id,
    )
    (repo / "configs/dataset/d.json").write_text(json.dumps(document))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind synthetic TRAIN view")
    return build_flight_runtime(
        repo, data, model="m", dataset="d", baseline="b", experiment="e",
        run_id="SLURP-TRAIN-FACTORY", attempt_id="a", runtime_root=tmp_path / "runtime",
        lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(),
        **_HAPPY_PATH_KWARGS,
    )


def test_factory_allows_only_explicit_registered_train_population_on_discovery(tmp_path):
    selected = "slurp:train:one:audio"
    runtime = _factory_runtime_for_slurp_rows(
        tmp_path, split_id="discovery",
        sample_ids=[selected, "slurp:train:two:audio"], registered_ids=[selected],
    )
    runtime.preflight()
    samples = runtime.adapter.load_split("discovery")
    assert [sample.sample_id for sample in samples] == [selected]
    assert not samples[0].scenario and not samples[0].entities
    with pytest.raises(RuntimeViewError, match="gold"):
        runtime.adapter.gold(samples[0])


def test_factory_allows_named_registered_train_roster_with_discovery_role(tmp_path):
    runtime = _factory_runtime_for_slurp_rows(
        tmp_path, split_id="TRAIN-A-1080",
        sample_ids=["slurp:train:one:audio"],
        registered_ids=["slurp:train:one:audio"],
    )
    runtime.preflight()
    assert len(runtime.adapter.load_split("TRAIN-A-1080")) == 1


@pytest.mark.parametrize(
    "split_id,sample_ids,registered_ids,split_role,match",
    [
        ("discovery", ["slurp:train:one:audio"], None,
         "discovery", "explicit registered population"),
        ("discovery", ["slurp:train:one:audio", "slurp:devel:two:audio"],
         ["slurp:train:one:audio", "slurp:devel:two:audio"], "discovery", "mix"),
        ("discovery", ["slurp:test:one:audio"], ["slurp:test:one:audio"],
         "discovery", "non-discovery"),
        ("DEV-1000", ["slurp:train:one:audio"], ["slurp:train:one:audio"],
         "discovery", "non-devel"),
        ("devel", ["slurp:train:one:audio"], ["slurp:train:one:audio"],
         "discovery", "non-devel"),
        ("TRAIN-A-1080", ["slurp:train:one:audio"], ["slurp:train:one:audio"],
         "dev", "discovery split role"),
    ],
)
def test_factory_refuses_unbound_or_wrong_namespace_train_populations(
    tmp_path, split_id, sample_ids, registered_ids, split_role, match,
):
    with pytest.raises(RuntimeViewError, match=match):
        _factory_runtime_for_slurp_rows(
            tmp_path, split_id=split_id, sample_ids=sample_ids,
            registered_ids=registered_ids, split_role=split_role,
        )


def test_factory_keeps_legacy_devel_rows_valid_under_discovery(tmp_path):
    runtime = _factory_runtime_for_slurp_rows(
        tmp_path, split_id="discovery",
        sample_ids=["slurp:devel:one:audio"], registered_ids=None,
    )
    runtime.preflight()
    assert len(runtime.adapter.load_split("discovery")) == 1


def test_runtime_slurp_adapter_validates_and_retains_generator_samples(tmp_path):
    from speech_aware_evidence_acquisition.rails.adapters.slurp import SlurpSample
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import RuntimeSlurpAdapter
    from speech_aware_evidence_acquisition.rails.obs import AudioRef

    def samples():
        yield SlurpSample(
            sample_id="slurp:train:one:audio",
            audio_ref=AudioRef(path="one.wav", sha256="0" * 64),
            audio_seconds=1.0, utterance_id="one", media_relpath="one.wav",
            scenario="leaked", action="", intent="", entities=(),
        )

    with pytest.raises(RuntimeViewError, match="gold labels"):
        RuntimeSlurpAdapter(
            {}, tmp_path, repo_root=tmp_path, split_id="discovery",
            samples=samples(), instruction_text="Return the command.",
            split_role="discovery", registered_population_bound=True,
        )


def test_named_dev_roster_returns_only_on_exact_registered_alias(tmp_path):
    repo = _make_repo(
        tmp_path, "SLURP-NAMED-DEV", carrier_lock_key="slurp",
        model_extra={"server_args": ["-np", "2", "-c", "8192"]},
        baseline_extra={"task_instruction": "Return the spoken command.",
                        "serving_slots": 2, "serving_slot_tokens": 4096},
    )
    data = tmp_path / "data"
    doc = view(data)
    doc.update(carrier_lock_key="slurp", split_id="DEV-1000-REPLICATE")
    (repo / "configs/dataset/d.json").write_text(json.dumps(doc))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind named dev view")
    runtime = build_flight_runtime(
        repo, data, model="m", dataset="d", baseline="b", experiment="e",
        run_id="SLURP-NAMED-DEV", attempt_id="a", runtime_root=tmp_path / "runtime",
        lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(), **_HAPPY_PATH_KWARGS,
    )
    runtime.preflight()
    assert len(runtime.adapter.load_split("DEV-1000-REPLICATE")) == 1
    with pytest.raises(RuntimeViewError, match="registered split"):
        runtime.adapter.load_split("DEV-1000")
    with pytest.raises(RuntimeViewError, match="registered split"):
        runtime.adapter.load_split("devel")


def test_named_dev_roster_rejects_foreign_split_and_non_devel_source_ids(tmp_path):
    repo = _make_repo(
        tmp_path, "SLURP-NAMED-DEV-REJECT", carrier_lock_key="slurp",
        model_extra={"server_args": ["-np", "2", "-c", "8192"]},
        baseline_extra={"task_instruction": "Return the spoken command.",
                        "serving_slots": 2, "serving_slot_tokens": 4096},
    )
    data = tmp_path / "data"
    doc = view(data)
    doc.update(carrier_lock_key="slurp", split_id="TEST-1000")
    (repo / "configs/dataset/d.json").write_text(json.dumps(doc))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind invalid named split")
    with pytest.raises(RuntimeViewError, match="discovery/devel"):
        build_flight_runtime(
            repo, data, model="m", dataset="d", baseline="b", experiment="e",
            run_id="SLURP-NAMED-DEV-REJECT", attempt_id="a", runtime_root=tmp_path / "runtime",
            lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(), **_HAPPY_PATH_KWARGS,
        )

    doc["split_id"] = "DEV-1000"
    doc["items"][0]["sample_id"] = "slurp:test:one:audio"
    (repo / "configs/dataset/d.json").write_text(json.dumps(doc))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "bind non-devel source id")
    with pytest.raises(RuntimeViewError, match="non-devel sample"):
        build_flight_runtime(
            repo, data, model="m", dataset="d", baseline="b", experiment="e",
            run_id="SLURP-NAMED-DEV-REJECT-2", attempt_id="a", runtime_root=tmp_path / "runtime-2",
            lock={}, lock_path=None, gate_factory=lambda *a, **kw: _FakeGate(), **_HAPPY_PATH_KWARGS,
        )


def test_runtime_view_population_is_exact_and_hashes_selected_media(tmp_path):
    doc = view(tmp_path)
    samples = load_runtime_view(doc, tmp_path, sample_ids=["slurp:devel:one:audio"])
    assert len(samples) == 1
    with pytest.raises(RuntimeViewError, match="missing"):
        load_runtime_view(doc, tmp_path, sample_ids=["absent"])


def test_roster_samples_preserves_legacy_devel_default_without_split_id(tmp_path):
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import roster_samples

    samples = roster_samples(view(tmp_path), tmp_path)
    assert [sample.sample_id for sample in samples] == ["slurp:devel:one:audio"]


def test_roster_samples_refuses_malformed_id_before_indexing_utterance(tmp_path):
    from speech_aware_evidence_acquisition.rails.adapters.slurp_runtime import roster_samples

    document = view(tmp_path)
    document["items"][0]["sample_id"] = "slurp"
    with pytest.raises(RuntimeViewError, match="non-SLURP sample"):
        roster_samples(document, tmp_path)


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
    values["request_decoding_overrides"] = {"max_tokens": 256}
    geometry = configured_geometry(values, defaults=(8, 8192, 64))
    assert geometry == {"slots": 2, "slot_tokens": 4096, "max_tokens": 256}
    assert values["server_args"] == ["-np", "2", "-c", "8192"]
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



def test_builtin_task_adapters_registers_earnings21_and_slurp():
    from speech_aware_evidence_acquisition.core.base import TASK_ADAPTERS
    from speech_aware_evidence_acquisition.core.flight.factory import (
        register_builtin_task_adapters,
    )

    register_builtin_task_adapters()
    assert "slurp" in TASK_ADAPTERS.names()
    assert "earnings21-original" in TASK_ADAPTERS.names()


def test_window_fit_inputs_bind_window_sources_and_payload_boundary(tmp_path):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime

    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={"arm": "bare-core"})
    runtime.preparation_context = lambda: {
        "values": {"arm": "bare-core"},
        "split_identity_hash": "0" * 64,
        "runtime_receipt": {"sha256": "receipt"},
        "required_identity": {"sha256": "identity"},
    }
    batch = SimpleNamespace(
        source_bindings=(
            {"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/fit-run/windows/c1.wav", "sha256": "a"},
        ),
    )
    first = runtime.request_fit_inputs(
        [{"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/fit-run/windows/c1.wav"}],
        window_batch=batch,
    )
    batch.source_bindings = (
        {"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/fit-run/windows/c1.wav", "sha256": "changed"},
    )
    second = runtime.request_fit_inputs(
        [{"sample_id": "e21:c1", "media_relpath": "windows/c1.wav"}],
        window_batch=batch,
    )
    assert first["sources"]["window_sources"][0]["sha256"] == "a"
    assert first["sources"]["window_sources"][0]["media_relpath"] == (
        "derived/obs-slices/<run-id>/windows/c1.wav"
    )
    assert first != second
    other_run = runtime.request_fit_inputs(
        [{"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/generation-run/windows/c1.wav"}],
        window_batch=SimpleNamespace(
            source_bindings=(
                {"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/generation-run/windows/c1.wav", "sha256": "a"},
            ),
        ),
    )
    assert first == other_run
    arbitrary_path = runtime.request_fit_inputs(
        [{"sample_id": "e21:c1", "media_relpath": "windows/c1.wav"}],
        window_batch=SimpleNamespace(
            source_bindings=(
                {"sample_id": "e21:c1", "media_relpath": "windows/c1.wav", "sha256": "a"},
            ),
        ),
    )
    assert first != arbitrary_path
    changed_window = runtime.request_fit_inputs(
        [{"sample_id": "e21:c1", "media_relpath": "windows/changed.wav"}],
        window_batch=batch,
    )
    assert first["sources"]["boundary_sha256"] != changed_window["sources"]["boundary_sha256"]


def test_window_fit_refuses_non_raw_or_adaptive_adapter(tmp_path):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.preparation import PreparationError

    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._prepare = lambda: (
        {"policy": "obs-agent-loop-ojw"},
        "earnings21-original",
        "discovery",
        "identity",
    )
    runtime._adapter = SimpleNamespace(
        preprocess_plan=lambda: {"kind": "adaptive-windows"},
    )
    with pytest.raises(PreparationError, match="raw-speech-windows"):
        runtime.materialize_window_batch()



def test_prepared_window_fit_accepts_matching_receipt_and_rejects_changed_source(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    import hashlib

    receipt = tmp_path / "fit.json"
    receipt.write_text("fit", encoding="utf-8")
    digest = hashlib.sha256(receipt.read_bytes()).hexdigest()
    batch = SimpleNamespace(
        payloads=(
            {"sample_id": "e21:c1", "media_relpath": "windows/c1.wav"},
            {"sample_id": "e21:c1", "media_relpath": "windows/c2.wav"},
        ),
        request_keys=("e21:c1#w0001", "e21:c1#w0002"),
        source_bindings=(
            {"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/fit-run/windows/c1.wav", "sha256": "a"},
            {"sample_id": "e21:c1", "media_relpath": "windows/c2.wav", "sha256": "b"},
        ),
    )
    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._adapter = SimpleNamespace(
        preprocess_plan=lambda: {"kind": "raw-speech-windows"},
    )
    runtime._prepare = lambda: ({}, "earnings21-original", "discovery", "identity")
    runtime.materialize_window_batch = lambda: batch
    runtime.request_fit_inputs = lambda payloads, *, window_batch: {
        "window_sources": list(window_batch.source_bindings)
    }
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation.load_artifact",
        lambda path, expected_sha256, kind, inputs: {
            "every_request_fits": True,
            "rows": [
                {"request_key": key, "fits": True}
                for key in batch.request_keys
            ],
            "sample_count": 2,
        },
    )

    accepted = runtime._verify_prepared_request_fit(
        {"relpath": "fit.json", "sha256": digest}
    )
    assert accepted["every_request_fits"] is True
    assert accepted["sample_count"] == 2

    batch.source_bindings = (
        {"sample_id": "e21:c1", "media_relpath": "derived/obs-slices/fit-run/windows/c1.wav", "sha256": "changed"},
        batch.source_bindings[1],
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation.load_artifact",
        lambda path, expected_sha256, kind, inputs: (_ for _ in ()).throw(
            PreparationError("window source binding changed")
        ),
    )
    with pytest.raises(PreparationError, match="source binding changed"):
        runtime._verify_prepared_request_fit(
            {"relpath": "fit.json", "sha256": digest}
        )
