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
