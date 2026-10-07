"""Derive authored Solver lookup indexes through the production runtime."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config, validate_solver_tool_access,
)
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools, PhaseToolError
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.task_adapter import CandidateInventory
from test_native_episode_config import program
from test_phase_native_tools import Custody
from test_released_target_index import _binding as authored_binding, LEGAL
from test_solver_tool_access import solver_values


def slot_binding(stores, data_root):
    """The fixture uses one real released store, with no automatic supply route."""
    store = stores.store("slot-contracts")
    return load_knowledge_store_binding({"knowledge_stores": {"slot-contracts": {
        "store_role": store.store_role, "snapshot": dict(store.snapshot_pin),
        "release": dict(store.release_pin),
    }}}, data_root=data_root)


def _binding(data_root):
    return slot_binding(authored_binding(data_root), data_root)


def runtime_for(values, stores, data_root):
    """Keep only lifecycle fixtures; the router and authored index are real."""
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._knowledge_store_binding = stores
    runtime._data_root = data_root
    inventory = CandidateInventory(LEGAL, "a" * 64, "task-adapter-candidate-contract-provider")
    runtime._adapter = SimpleNamespace(candidate_inventory=lambda: inventory)
    return runtime


def test_opted_in_solver_gets_the_fixed_authored_slot_index(tmp_path):
    stores = _binding(tmp_path)
    values, graph = solver_values(), program(ceiling=3)
    before = deepcopy(values)
    runtime = runtime_for(values, stores, tmp_path)
    runtime._resolve_phase_supply(graph, stores.composite_snapshot)
    router = runtime._knowledge_store_supply
    assert runtime._knowledge_store_router_options["on_demand_store_ids"] == ("slot-contracts",)
    assert set(router.slot_target_indices) == {"slot-contracts"}
    assert router.slot_target_indices["slot-contracts"].mappings == {
        "event_time": ("slot-contract:event_time",),
    }
    dispatcher = build_phase_tools(values, graph, snapshot=stores.composite_snapshot,
        knowledge_stores=stores, supply_for_store=router, tool_contact=Custody())
    validate_solver_tool_access(load_native_episode_config(values, graph), dispatcher.specs,
                                dispatcher=dispatcher)
    assert values == before


@pytest.mark.parametrize("mode", [None, "absent"])
def test_unopted_solver_does_not_gain_an_on_demand_index(tmp_path, mode):
    stores, values = _binding(tmp_path), solver_values()
    if mode == "absent":
        values["native_episode"].pop("solver_tool_access")
    else:
        values["native_episode"]["solver_tool_access"] = mode
    runtime = runtime_for(values, stores, tmp_path)
    with pytest.raises(FlightRuntimeError, match="no phase_supply"):
        runtime._resolve_phase_supply(program(ceiling=3), stores.composite_snapshot)
    assert not hasattr(runtime, "_knowledge_store_supply")
    with pytest.raises(ValueError):
        load_native_episode_config(values, program(ceiling=3))


@pytest.mark.parametrize("change", [
    lambda v: v["native_episode"].update(solver_tool_access="on"),
    lambda v: v["native_episode"]["roles"]["solver"].update(max_iterations=3),
    lambda v: v["native_episode"].update(tool_iteration_policy="react"),
    lambda v: v["phase_tools"]["solver"].update(source_authority_role="reviewer"),
    lambda v: v["phase_tools"]["solver"].update(knowledge_store_ids=["intent-boundaries"]),
    lambda v: v["phase_tools"]["solver"].update(knowledge_target_axis="task"),
    lambda v: v["phase_tools"]["solver"].update(candidate_limit=3),
])
def test_invalid_solver_authority_refuses_before_binding_a_router(tmp_path, change):
    stores, values = _binding(tmp_path), solver_values()
    change(values)
    runtime = runtime_for(values, stores, tmp_path)
    with pytest.raises((FlightRuntimeError, PhaseToolError)):
        runtime._resolve_phase_supply(program(ceiling=3), stores.composite_snapshot)
    assert not hasattr(runtime, "_knowledge_store_supply")


@pytest.mark.parametrize("role", ["reviewer", "planner"])
def test_historical_targeted_authorities_keep_their_authored_index(tmp_path, role):
    stores, values = _binding(tmp_path), solver_values()
    spec = values.pop("phase_tools")["solver"]
    spec["source_authority_role"] = role
    values.pop("native_episode")
    values["phase_tools"] = {role: spec}
    runtime = runtime_for(values, stores, tmp_path)
    runtime._resolve_phase_supply(program(), stores.composite_snapshot)
    assert runtime._knowledge_store_router_options["on_demand_store_ids"] == ("slot-contracts",)
    assert "slot-contracts" in runtime._knowledge_store_supply.slot_target_indices


def test_unauthorized_role_gets_no_target_index(tmp_path):
    stores, values = _binding(tmp_path), solver_values()
    spec = values.pop("phase_tools")["solver"]
    spec["source_authority_role"] = "perception"
    values.pop("native_episode")
    values["phase_tools"] = {"perception": spec}
    runtime = runtime_for(values, stores, tmp_path)
    with pytest.raises(FlightRuntimeError, match="no phase_supply"):
        runtime._resolve_phase_supply(program(), stores.composite_snapshot)
    assert not hasattr(runtime, "_knowledge_store_supply")
