"""Config-to-runtime finite supply binding with pinned synthetic artifacts."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.finite_action_policy import PolicySnapshot
from speech_aware_evidence_acquisition.rails.finite_supply_policy import (
    AGREEMENT_STATES, ALGORITHM_ID, FiniteSupplyPolicyError, build_finite_supply_policy,
)
from speech_aware_evidence_acquisition.rails.supply_variants import parse_supply_variant_knob
from test_finite_policy_artifacts import write_pin, schedule_doc
from test_finite_supply_policy import context
from test_native_episode_runner import _config, _program
from test_rails_controllers import _phase_supply
from test_slurp_intent_hypotheses import _payload, LEGAL


def inputs(tmp_path):
    snapshot = PolicySnapshot.create(
        actions=("default20", "examples10"), states=AGREEMENT_STATES, f0=0.58,
    )
    schedule = schedule_doc(snapshot, ids=("s1",), kind="epsilon-greedy", epsilon=0.0, quotas=())
    store_snapshot = SimpleNamespace(
        values=(SimpleNamespace(value_id="x", task_target="weather_query"),),
        content_hash=lambda: "c" * 64,
    )
    repo = Path(__file__).parents[2]
    old = json.loads((repo / "configs/baseline/slurp-native-stage3-f10-control-r01c-v1-baseline-v1.json").read_text())
    stores = {
        "train-exemplars": SimpleNamespace(
            store_id="train-exemplars", store_role="train-exemplars",
            phase_supply={"solver": {"k": 20}}, candidate_supply={}, snapshot=store_snapshot,
        ),
        "slot-contracts": SimpleNamespace(
            store_id="slot-contracts", store_role="slot-contracts",
            candidate_supply=old["knowledge_stores"]["slot-contracts"]["candidate_supply"],
        ),
    }
    binding = SimpleNamespace(store_ids=tuple(stores), store=stores.__getitem__)
    program = _program(max_contacts=7)
    program = replace(program, phases=tuple(
        replace(phase, knowledge="supplied") if phase.name == "solver" else phase
        for phase in program.phases
    ))
    native = _config(max_revisions=1, max_contacts=7)
    calls = []
    def router(store_id, phase, ctx):
        calls.append(("preview", store_id))
        return _phase_supply(ctx, value_ids=("x",))
    router.automatic_for_phase = lambda phase, ctx: _phase_supply(ctx, value_ids=("default20",))
    router.receipt = {"schema": "test-store-router"}
    def factory(action_id, knobs):
        calls.append(("build", action_id, tuple(k.path for k in knobs)))
        result = lambda *args: None
        result.automatic_for_phase = lambda phase, ctx: _phase_supply(ctx, value_ids=(action_id,))
        result.receipt = {"action_id": action_id}
        return result
    raw = {
        "schema": "saea-finite-supply-policy-config-v1", "algorithm_id": ALGORITHM_ID,
        "phase_id": "solver", "perception_phase": "perception",
        "preview_store": "train-exemplars", "preview_k": 20,
        "snapshot": write_pin(tmp_path, "snapshot.json", snapshot.as_json()),
        "schedule": write_pin(tmp_path, "schedule.json", schedule),
        "actions": [
            {"action_id": "default20", "overrides": {}},
            {"action_id": "examples10", "overrides": {
                "knowledge_stores.train-exemplars.phase_supply.solver.k": 10,
            }},
        ],
    }
    kwargs = dict(program=program, native_config=native, store_binding=binding,
                  default_router=router, action_router_factory=factory, data_root=tmp_path,
                  roster_ids=("s1",), split_identity_hash=schedule["split_identity_hash"],
                  legal_candidate_ids=LEGAL)
    return {"finite_supply_policy": raw}, kwargs, calls


def test_configuration_uses_same_candidate_projection_and_pinned_schedule(tmp_path):
    values, kwargs, calls = inputs(tmp_path)
    bound = build_finite_supply_policy(values, **kwargs)
    candidate = _payload()["candidates"][0]
    ctx = context(content=json.dumps({"candidates": [candidate, candidate]}))
    bound("solver", ctx)
    record = bound.receipt["decisions"]["s1"]
    assert record["candidates"] == ["weather_query"]
    assert record["state_id"] == "agree-ge-0.75"
    assert record["decision"]["action"] == "default20"
    assert calls[-1] == ("preview", "train-exemplars")
    assert "examples10" in bound.receipt["actions"]


@pytest.mark.parametrize("mutate,match", [
    (lambda raw: raw.update(unknown=True), "fields"),
    (lambda raw: raw.update(preview_k=10), "default20"),
    (lambda raw: raw.update(phase_id="reviewer"), "native Solver"),
    (lambda raw: raw["actions"].reverse(), "ordered"),
    (lambda raw: raw["actions"][1].update(overrides={
        "knowledge_stores.slot-contracts.candidate_supply.solver.max_total_values": 10
    }), "exemplar supply"),
])
def test_unsupported_config_refuses_before_any_callback(tmp_path, mutate, match):
    values, kwargs, calls = inputs(tmp_path)
    mutate(values["finite_supply_policy"])
    with pytest.raises(FiniteSupplyPolicyError, match=match):
        build_finite_supply_policy(values, **kwargs)
    assert not any(call[0] == "preview" for call in calls)


def test_flight_runtime_absence_is_identity_and_armed_path_receipts_decision(tmp_path):
    values, kwargs, _ = inputs(tmp_path)
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={})
    ordinary = kwargs["default_router"].automatic_for_phase
    assert runtime._finite_supply_policy_binding(None, None, ordinary, None) is ordinary
    runtime._composed = SimpleNamespace(values=values)
    runtime._knowledge_store_binding = kwargs["store_binding"]
    runtime._knowledge_store_supply = kwargs["default_router"]
    runtime._knowledge_store_router_options = {"legal_candidate_ids": LEGAL}
    runtime._data_root = tmp_path
    runtime._samples = (SimpleNamespace(sample_id="s1"),)
    runtime._plan = SimpleNamespace(split_identity_hash=kwargs["split_identity_hash"])
    runtime._phase_supply_receipt = kwargs["default_router"].receipt
    runtime._supply_action_router = lambda program, action_id, knobs: kwargs["action_router_factory"](action_id, knobs)
    sink = TraceBuffer("SAEA-finite-proof")
    bound = runtime._finite_supply_policy_binding(kwargs["native_config"], kwargs["program"], ordinary, sink)
    candidate = _payload()["candidates"][0]
    bound("solver", context(content=json.dumps({"candidates": [candidate]})))
    assert sink.records[0][0] == "SUPPLY"
    assert sink.records[0][2]["supply_action_decision"]["sample_id"] == "s1"
    assert runtime._phase_supply_receipt["finite_supply_policy"]["decisions"]["s1"]["decision"]["action"] == "default20"
    runtime._resume = object()
    with pytest.raises(FlightRuntimeError, match="complete registered round"):
        runtime._finite_supply_policy_binding(kwargs["native_config"], kwargs["program"], ordinary, sink)


def test_shared_action_factory_only_changes_existing_selection_knobs(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails import knowledge_stores
    runtime = object.__new__(FlightRuntime)
    original = {"knowledge_stores": {"train-exemplars": {"phase_supply": {"solver": {"k": 20}}}}}
    runtime._composed = SimpleNamespace(values=original)
    base = SimpleNamespace(composite_snapshot=SimpleNamespace(content_hash=lambda: "a" * 64))
    runtime._knowledge_store_binding = base
    runtime._knowledge_store_router_options = {"legal_candidate_ids": ("weather_query",)}
    runtime._data_root = tmp_path
    captured = []
    monkeypatch.setattr(knowledge_stores, "load_knowledge_store_binding",
                        lambda values, **kw: captured.append(copy.deepcopy(values)) or base)
    router = object()
    monkeypatch.setattr(knowledge_stores, "build_knowledge_store_supply", lambda *a, **kw: router)
    knob = parse_supply_variant_knob(
        "knowledge_stores.train-exemplars.phase_supply.solver.k", 10,
        phase_id="solver", first_phase_id="perception", declared_stores=("train-exemplars",),
    )
    assert runtime._supply_action_router(None, "examples10", (knob,)) is router
    assert captured[0]["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["k"] == 10
    assert original["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["k"] == 20
    monkeypatch.setattr(knowledge_stores, "load_knowledge_store_binding",
                        lambda *a, **kw: SimpleNamespace(composite_snapshot=SimpleNamespace(content_hash=lambda: "b" * 64)))
    with pytest.raises(FlightRuntimeError, match="changed"):
        runtime._supply_action_router(None, "examples10", (knob,))
