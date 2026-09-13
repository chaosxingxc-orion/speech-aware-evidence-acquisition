"""Persisted first-phase seeds remove runtime retrieval; no model contacts."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.rails import phase_supply


def setup_runtime(tmp_path):
    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._repo_root = tmp_path
    runtime._composed = SimpleNamespace(
        values={"policy": "phase-slots-given-intent-supplied-v1", "k": 5},
        config_hash="c" * 64,
    )
    import hashlib

    (tmp_path / "frozen.json").write_bytes(b"frozen source receipt")
    runtime._composed.values["preparation_source_receipts"] = [
        {
            "root": "repository",
            "relpath": "frozen.json",
            "sha256": hashlib.sha256(b"frozen source receipt").hexdigest(),
        }
    ]
    runtime._samples = [SimpleNamespace(sample_id="s1")]
    runtime._adapter = SimpleNamespace(preprocess_plan=lambda: {})
    runtime._phase_program_material = None
    snapshot = SimpleNamespace(
        content_hash=lambda: "a" * 64,
        facets=[SimpleNamespace(facet_id="f1")],
        values=[SimpleNamespace(value_id="v1")],
    )
    spec = SimpleNamespace(as_json=lambda: {"k": 5}, phase="slots")
    supply = SimpleNamespace(
        provider_factories={"slots": lambda: object()},
        query_tables={"slots": {"s1": {"content": (1.0,)}}},
    )
    binding = {
        "knowledge_snapshot": snapshot,
        "speech_packet_bindings": {"s1": {"packet_id": "p1", "sha256": "b" * 64}},
        "supply_specs": {"slots": spec},
        "supply_for_phase": supply,
    }
    runtime._prepare = lambda: (runtime._composed.values, "slurp", "DEV", "d" * 64)
    runtime._default_phase_program_binding = lambda program, client: binding
    return runtime, binding, SimpleNamespace(phase_names=lambda: ("slots",))


def test_preparation_removes_dispatch_recomputation(tmp_path, monkeypatch):
    runtime, binding, program = setup_runtime(tmp_path)
    builder = Mock(return_value=({"s1": ("f1",)}, {"s1": ("v1",)}))
    monkeypatch.setattr(phase_supply, "build_bootstrap_selection", builder)
    receipt = runtime.prepare_phase_supply(tmp_path / "seed.json")
    assert builder.call_count == 1
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "seed.json",
        "sha256": receipt["sha256"],
    }
    monkeypatch.setattr(
        phase_supply,
        "build_bootstrap_selection",
        lambda *a, **k: pytest.fail("retrieval recomputed during dispatch"),
    )
    assert runtime._phase_supply_seeds(
        program,
        binding,
        binding["supply_specs"],
        SimpleNamespace(split_identity_hash="d" * 64),
    ) == ({"slots": {"s1": ("f1",)}}, {"slots": {"s1": ("v1",)}})


@pytest.mark.parametrize("change", ["config", "split", "packet", "snapshot"])
def test_prepared_seed_refuses_identity_drift(tmp_path, monkeypatch, change):
    runtime, binding, program = setup_runtime(tmp_path)
    monkeypatch.setattr(
        phase_supply, "build_bootstrap_selection", lambda *a, **k: ({}, {"s1": ("v1",)})
    )
    receipt = runtime.prepare_phase_supply(tmp_path / "seed.json")
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "seed.json",
        "sha256": receipt["sha256"],
    }
    plan = SimpleNamespace(split_identity_hash="d" * 64)
    if change == "config":
        runtime._composed.values["k"] = 6
    elif change == "split":
        plan.split_identity_hash = "e" * 64
    elif change == "packet":
        binding["speech_packet_bindings"]["s1"]["sha256"] = "e" * 64
    else:
        binding["knowledge_snapshot"].content_hash = lambda: "e" * 64
    with pytest.raises(PreparationError):
        runtime._phase_supply_seeds(program, binding, binding["supply_specs"], plan)


def test_unknown_seed_value_and_root_escape_refused(tmp_path, monkeypatch):
    runtime, binding, program = setup_runtime(tmp_path)
    monkeypatch.setattr(
        phase_supply,
        "build_bootstrap_selection",
        lambda *a, **k: ({}, {"s1": ("unknown",)}),
    )
    receipt = runtime.prepare_phase_supply(tmp_path / "seed.json")
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "seed.json",
        "sha256": receipt["sha256"],
    }
    with pytest.raises(PreparationError, match="selection"):
        runtime._phase_supply_seeds(
            program,
            binding,
            binding["supply_specs"],
            SimpleNamespace(split_identity_hash="d" * 64),
        )
    runtime._composed.values["prepared_phase_supply"]["relpath"] = "../escape.json"
    with pytest.raises(Exception, match="(traversal|confined|escape)"):
        runtime._phase_supply_seeds(
            program,
            binding,
            binding["supply_specs"],
            SimpleNamespace(split_identity_hash="d" * 64),
        )


def test_materialize_single_phase_uses_validated_wire_payloads(tmp_path):
    runtime, _binding, _program = setup_runtime(tmp_path)

    def wire(**kwargs):
        assert kwargs["seal_and_score"] is False
        kwargs["request_payload_observer"]({"sample_id": "s1", "actual": True})

    runtime.wire_check = wire
    assert runtime.materialize_phase_requests() == (
        {"sample_id": "s1", "actual": True},
    )


@pytest.mark.parametrize("ids", [[], ["s1", "s1"], ["other"]])
def test_materialize_refuses_partial_duplicate_or_foreign_roster(tmp_path, ids):
    runtime, _binding, _program = setup_runtime(tmp_path)

    def wire(**kwargs):
        for sid in ids:
            kwargs["request_payload_observer"]({"sample_id": sid})

    runtime.wire_check = wire
    with pytest.raises(PreparationError, match="full roster"):
        runtime.materialize_phase_requests()


def test_materialize_refuses_unsealed_multiphase_predecessors(tmp_path, monkeypatch):
    runtime, _binding, _program = setup_runtime(tmp_path)
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.flight.runtime.default_phase_program",
        lambda policy: SimpleNamespace(phase_names=lambda: ("intent", "slots")),
    )
    runtime.wire_check = lambda **k: pytest.fail("must reject before dispatch")
    with pytest.raises(PreparationError, match="one phase"):
        runtime.materialize_phase_requests()


@pytest.mark.parametrize("failure", [None, "not-fit", "missing-row", "changed-input"])
def test_actual_fit_pin_verifier_binds_all_rows(tmp_path, failure):
    from speech_aware_evidence_acquisition.core.preparation import prepare_artifact

    runtime, _binding, _program = setup_runtime(tmp_path)
    payloads = [{"sample_id": "s1"}]
    runtime.materialize_phase_requests = lambda: payloads
    runtime.request_fit_inputs = lambda p, **kwargs: {"boundary": p}
    output = {
        "rows": [{"sample_id": "s1", "fits": True}],
        "sample_count": 1,
        "every_request_fits": True,
    }
    if failure == "not-fit":
        output["every_request_fits"] = False
    if failure == "missing-row":
        output["rows"] = []
    path = tmp_path / "fit.json"
    receipt = prepare_artifact(
        path,
        kind="request-fit",
        inputs={"boundary": payloads},
        producer=lambda: output,
        contact_class="tokenizer",
    )
    runtime._composed.values["prepared_request_fit"] = {
        "relpath": "fit.json",
        "sha256": receipt["sha256"],
    }
    if failure == "changed-input":
        payloads[0]["changed"] = True
    if failure:
        with pytest.raises(PreparationError):
            runtime._verify_phase_prompt_fit()
    else:
        assert runtime._verify_phase_prompt_fit()["sample_count"] == 1


def test_materialization_restores_live_client_and_outputs_even_on_failure(tmp_path):
    runtime, _binding, _program = setup_runtime(tmp_path)
    runtime._client, runtime._output_rows = "live", ["original"]

    def wire(**kwargs):
        runtime._client, runtime._output_rows = "fake", ["fake"]
        raise RuntimeError("wire refused")

    runtime.wire_check = wire
    with pytest.raises(RuntimeError, match="wire refused"):
        runtime.materialize_phase_requests()
    assert runtime._client == "live"
    assert runtime._output_rows == ["original"]



class _BootstrapDecision:
    def __init__(self, sample_id):
        self.supporting_facet_ids = ("facet-" + sample_id,)
        self.selected_value_ids = ("value-" + sample_id,)


class _BootstrapProvider:
    def __init__(self, failing=None):
        self.failing = failing

    def candidates(self, request, *, k):
        sample_id = request["query_state"].query_sample_id
        if sample_id == self.failing:
            raise RuntimeError("provider failed for " + sample_id)
        return sample_id

    def fuse(self, rankings, *, k, policy_id):
        return _BootstrapDecision(rankings[0])


def _bootstrap_spec():
    return SimpleNamespace(
        phase="slots",
        k=2,
        fuse_policy="fuse",
        expose_facets=True,
    )


def _bootstrap_inputs():
    queries = {
        "s1": {"content": (1.0,)},
        "s2": {"content": (2.0,)},
        "s3": {},
    }
    packets = {
        sid: {"packet_id": "packet-" + sid, "sha256": "a" * 64}
        for sid in queries
    }
    return queries, packets


def test_bootstrap_selection_parallel_matches_serial_with_missing_queries():
    queries, packets = _bootstrap_inputs()
    serial = phase_supply.build_bootstrap_selection(
        _bootstrap_spec(),
        provider=_BootstrapProvider(),
        query_vectors_by_sample=queries,
        speech_packet_bindings=packets,
        split_identity_hash="b" * 64,
        workers=1,
    )
    parallel = phase_supply.build_bootstrap_selection(
        _bootstrap_spec(),
        provider=_BootstrapProvider(),
        query_vectors_by_sample=queries,
        speech_packet_bindings=packets,
        split_identity_hash="b" * 64,
        workers=2,
    )
    assert serial == parallel == (
        {"s1": ("facet-s1",), "s2": ("facet-s2",)},
        {"s1": ("value-s1",), "s2": ("value-s2",)},
    )


def test_bootstrap_selection_parallel_propagates_provider_failure():
    queries, packets = _bootstrap_inputs()
    with pytest.raises(RuntimeError, match="provider failed for s2"):
        phase_supply.build_bootstrap_selection(
            _bootstrap_spec(),
            provider=_BootstrapProvider(failing="s2"),
            query_vectors_by_sample=queries,
            speech_packet_bindings=packets,
            split_identity_hash="b" * 64,
            workers=2,
        )


@pytest.mark.parametrize("workers", [0, 21, True, "2"])
def test_bootstrap_selection_rejects_invalid_worker_count(workers):
    queries, packets = _bootstrap_inputs()
    with pytest.raises(phase_supply.PhaseSupplyError, match="1 through 20"):
        phase_supply.build_bootstrap_selection(
            _bootstrap_spec(),
            provider=_BootstrapProvider(),
            query_vectors_by_sample=queries,
            speech_packet_bindings=packets,
            split_identity_hash="b" * 64,
            workers=workers,
        )


def test_generation_lease_caps_parallel_workers_at_eight():
    assert phase_supply._validate_bootstrap_workers(20, lease_metadata_present=True) == 8

@pytest.mark.parametrize("workers", [1, 2])
def test_bootstrap_does_not_retain_parent_provider_after_completion(workers):
    import gc
    import weakref

    queries, packets = _bootstrap_inputs()
    provider = _BootstrapProvider()
    reference = weakref.ref(provider)
    phase_supply.build_bootstrap_selection(
        _bootstrap_spec(), provider=provider,
        query_vectors_by_sample=queries, speech_packet_bindings=packets,
        split_identity_hash="b" * 64, workers=workers,
    )
    del provider
    gc.collect()
    assert reference() is None



def test_runtime_source_audio_bindings_keep_packet_descriptor_unchanged(tmp_path):
    runtime, _binding, _program = setup_runtime(tmp_path)
    packet_bindings = {
        "s1": {"packet_id": "packet/s1", "sha256": "b" * 64}
    }
    runtime._samples = [
        SimpleNamespace(
            sample_id="s1",
            audio_ref=SimpleNamespace(sha256="a" * 64),
        )
    ]
    runtime.speech_packet_bindings = lambda: packet_bindings

    assert runtime.source_audio_bindings() == {
        "s1": {
            "packet_id": "packet/s1",
            "packet_sha256": "b" * 64,
            "source_audio_sha256": "a" * 64,
        }
    }
    assert packet_bindings == {
        "s1": {"packet_id": "packet/s1", "sha256": "b" * 64}
    }


def test_segmented_source_binding_is_part_of_prepared_artifact_identity(tmp_path):
    runtime, binding, _program = setup_runtime(tmp_path)
    source_bindings = {
        "s1": {
            "packet_id": "p1",
            "packet_sha256": "b" * 64,
            "source_audio_sha256": "a" * 64,
        }
    }
    binding["supply_for_phase"] = SimpleNamespace(
        source_audio_bindings=source_bindings
    )
    spec = SimpleNamespace(
        as_json=lambda: {
            "query_source": {"kind": phase_supply.SEALED_SEGMENT_VECTORS_KIND}
        },
        query_source={"kind": phase_supply.SEALED_SEGMENT_VECTORS_KIND},
    )

    inputs = runtime._phase_seed_inputs(binding, spec, "d" * 64)
    assert inputs["sources"]["source_audio_bindings"] == source_bindings


@pytest.mark.parametrize("fail", [False, True])
def test_materialization_restores_registered_plan_and_phase_state(tmp_path, fail):
    runtime, binding, _program = setup_runtime(tmp_path)
    original = {
        "_plan": object(), "_client": object(), "_output_rows": ["original"],
        "_binding": object(), "_phase_program_material": binding,
        "_phase_tool_dispatcher": object(), "_phase_tool_trace_sink": object(),
        "_phase_review_receipt": {"original": True},
        "_phase_material_receipt": {"original": True},
        "_phase_supply_receipt": {"original": True},
        "_phase_summaries": ("original",), "_wire_check_active": False,
        "_live_speech_config": object(), "_live_speech_source_bindings": object(),
    }
    for name, value in original.items():
        setattr(runtime, name, value)
    def wire(**kwargs):
        for name in original:
            setattr(runtime, name, object())
        kwargs["request_payload_observer"]({"sample_id": "s1"})
        if fail:
            raise RuntimeError("synthetic dispatch failed")
    runtime.wire_check = wire
    if fail:
        with pytest.raises(RuntimeError, match="synthetic dispatch failed"):
            runtime.materialize_phase_requests()
    else:
        runtime.materialize_phase_requests()
    assert all(getattr(runtime, name) is value for name, value in original.items())


@pytest.mark.parametrize("dispatch_fails", [False, True])
def test_real_materialization_preserves_plan_used_by_serve(tmp_path, dispatch_fails):
    import json
    from test_flight_runtime import _make_runtime, _git, _FakeGate
    from test_rails_frozen_core_client import (
        _World, _speech_feature_world, _binding as payload_binding,
    )
    from test_rails_runner import _FakeAdapter, _knowledge_snapshot
    from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
    from speech_aware_evidence_acquisition.rails.phase_runner import run_program
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    world = _World(tmp_path)
    feature_root, _, packets = _speech_feature_world(world, tmp_path)
    policy = "phase-direct-only-v1"
    phases = default_phase_program(policy).phase_names()
    gate = _FakeGate()
    runtime = _make_runtime(
        tmp_path, happy_path=True, gate=gate,
        config_kwargs={
            "arm": "speech-feature-query", "policy": policy,
            "model_extra": {"speech_feature_root": str(feature_root)},
            "baseline_extra": {"phase_material": {
                phase: {"instruction_template": f"probes/{phase}.txt",
                        "predecessor_binding": "none"} for phase in phases}},
        },
        adapter_cls=lambda _lock, _root: _FakeAdapter(samples=tuple(world.samples)),
        client_factory=FrozenCoreClient, phase_runner=run_program,
        payload_binding_factory=lambda **_kw: payload_binding(world),
    )
    (runtime._repo_root / "configs/dataset/d.json").write_text(
        json.dumps({"carrier_lock_key": "fake-carrier", "split_id": "all"}))
    for phase in phases:
        prompt = runtime._repo_root / f"configs/probes/{phase}.txt"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("Transcribe the speech.")
    _git(runtime._repo_root, "add", "-A")
    _git(runtime._repo_root, "commit", "-q", "-m", "Bind synthetic single-phase fixture")
    runtime._load_knowledge_snapshot = _knowledge_snapshot
    runtime.speech_packet_bindings = lambda: packets
    runtime._speech_feature_root = lambda: feature_root
    runtime.preflight()
    plan = runtime._plan
    if dispatch_fails:
        original_runner = runtime._phase_runner
        opened = {}
        provider = Mock()

        def fail_after_real_dispatch(**kwargs):
            original_runner(**kwargs)
            opened.update(client=kwargs["core_client"], plan=kwargs["plan"])
            runtime._live_speech_provider = provider
            raise RuntimeError("dispatch failed after opening scratch attempt")

        runtime._phase_runner = fail_after_real_dispatch
        with pytest.raises(RuntimeError, match="dispatch failed after opening scratch attempt"):
            runtime.materialize_phase_requests()
        assert opened["client"]._closed is True
        provider.close.assert_called_once()
        from speech_aware_evidence_acquisition.core.bundle.finalize import abort_attempt_if_opened
        assert abort_attempt_if_opened(
            runtime._data_root, opened["plan"].run_id, opened["plan"].attempt_id,
            reason="test confirms scratch attempt was already aborted",
        ) is False
    else:
        payloads = runtime.materialize_phase_requests()
        assert len(payloads) == len(world.samples)
    assert runtime._plan is plan
    assert runtime._client is None
    runtime.preprocess()
    runtime.serve()
    assert runtime._plan is plan


def test_materialization_isolates_live_provider_and_trace_sink(tmp_path):
    runtime, binding, _program = setup_runtime(tmp_path)
    provider, sink = Mock(), Mock()
    binding["trace_sink"] = sink
    runtime._phase_program_material = binding
    runtime._live_speech_provider = provider

    def wire(**kwargs):
        assert runtime._live_speech_provider is None
        assert "trace_sink" not in runtime._phase_program_material
        assert runtime._phase_program_material["knowledge_snapshot"] is binding["knowledge_snapshot"]
        kwargs["request_payload_observer"]({"sample_id": "s1"})

    runtime.wire_check = wire
    runtime.materialize_phase_requests()
    assert runtime._phase_program_material is binding
    assert runtime._live_speech_provider is provider
    assert not hasattr(runtime, "_phase_tool_dispatcher")
    provider.close.assert_not_called()
    assert not sink.mock_calls
