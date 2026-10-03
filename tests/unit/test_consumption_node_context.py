"""Opt-in node presentation compiles without changing tool authority or old bytes."""
import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "configs/baseline/slurp-native-stage3-context-matrix-n20-legacy-trajectory-primary-v1.json"
COMPONENT = "node-context-presentation"
RECORD = "docs/receipts/owner/2026-10-03-sample-latency-quality-node-context.json"


def baseline():
    return json.loads(BASE.read_text())


def runtime_values(fragment):
    name = BASE.stem
    cell = json.loads((ROOT / "configs/experiment" / (name + ".json")).read_text())["cells"][0]
    values = compose(ROOT, cell["model_fragment"], cell["dataset_fragment"],
                     cell["baseline_fragment"], name).values
    return {**values, **fragment}


def entry(params=None, state="on"):
    return {"component_id": COMPONENT, "state": state, "admitted_by": "model-free-test",
            "record": RECORD, "params": params or {"tool_schema_rendering": "per-role"}}


def block_with(params=None, state="on"):
    block = baseline()["native_episode"]["consumption_module"]
    block["components"].append(entry(params, state))
    return block


def compile_block(block, hooks=None):
    hooks = hooks or cm.resolve_carrier_hooks(block["profile"], repo_root=ROOT)
    return cm.compile_module(block, hooks, repo_root=ROOT)


@pytest.mark.parametrize("params", [
    {"tool_schema_rendering": "per-role"},
    {"tool_schema_rendering": "constant"},
    {"reviewer_history_scope": "latest-solver-and-local-tools"},
    {"reviewer_history_scope": "full"},
    {"tool_schema_rendering": "per-role", "reviewer_history_scope": "latest-solver-and-local-tools"},
])
def test_only_declared_context_leaves_change_and_runtime_accepts(params):
    original = baseline()
    block = block_with(params)
    composed = compile_block(block)
    result = composed.apply_to(original)
    expected = cm.policy_owned_values(original)
    if "tool_schema_rendering" in params:
        expected["native_episode"]["tool_schema_rendering"] = params["tool_schema_rendering"]
    if "reviewer_history_scope" in params:
        expected["native_episode"]["roles"]["reviewer"]["history_scope"] = params["reviewer_history_scope"]
    assert cm.policy_owned_values(result) == expected
    result["native_episode"]["consumption_module"] = block
    cm.verify_declared_module(block, result, repo_root=ROOT)
    old = load_native_episode_config(runtime_values(original), default_phase_program(original["policy"]))
    new = load_native_episode_config(runtime_values(result), default_phase_program(result["policy"]))
    assert result["policy"] == original["policy"]
    assert result["phase_tools"] == original["phase_tools"]
    assert result["phase_material"] == original["phase_material"]
    assert result["knowledge_stores"] == original["knowledge_stores"]
    assert result["native_episode"]["deliver_normaliser"] == original["native_episode"]["deliver_normaliser"]
    assert new.max_revisions == old.max_revisions
    assert [(r.role_kind, r.max_iterations, r.tool_names) for r in new.roles] == [
        (r.role_kind, r.max_iterations, r.tool_names) for r in old.roles]
    assert original == baseline()


def test_disabled_component_keeps_historical_compiled_bytes():
    original = baseline()["native_episode"]["consumption_module"]
    old = compile_block(original)
    off = compile_block(block_with(state="off"))
    assert off.values_on_roster_of(baseline()) == old.values_on_roster_of(baseline())


def test_component_order_cannot_override_presentation():
    block = block_with({"tool_schema_rendering": "per-role", "reviewer_history_scope": "full"})
    expected = compile_block(block).values_on_roster_of(baseline())
    block["components"].reverse()
    assert compile_block(block).values_on_roster_of(baseline()) == expected


@pytest.mark.parametrize("params", [
    {}, {"tool_schema_rendering": None}, {"tool_schema_rendering": True},
    {"tool_schema_rendering": []}, {"tool_schema_rendering": "hidden-all"},
    {"reviewer_history_scope": None}, {"reviewer_history_scope": []},
    {"reviewer_history_scope": "drop-everything"}, {"solver_history_scope": "full"},
    {"allowed_tools": ["unregistered"]}, {"max_revisions": 10},
])
def test_undeclared_or_invalid_context_options_are_refused(params):
    block = block_with()
    block["components"][-1]["params"] = params
    with pytest.raises(cm.ConsumptionModuleConfigError):
        compile_block(block)


def test_module_guard_still_refuses_effective_config_drift():
    block = block_with()
    result = compile_block(block).apply_to(baseline())
    result["native_episode"]["consumption_module"] = block
    result["native_episode"]["tool_schema_rendering"] = "constant"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="blocks differ"):
        cm.verify_declared_module(block, result, repo_root=ROOT)


def test_context_display_is_not_dependent_on_knowledge_tool_component():
    block = {"module_id": cm.CONSUMPTION_MODULE_ID, "profile": "slurp", "lock": "v2.1",
             "components": [entry()]}
    compiled = compile_block(block)
    values = compiled.values_on_roster_of(baseline())
    assert values["native_episode"]["tool_schema_rendering"] == "per-role"
    assert "phase_tools" not in values


def test_inherited_context_leaves_can_be_explicitly_changed():
    block = block_with({"tool_schema_rendering": "per-role", "reviewer_history_scope": "full"})
    hooks = cm.resolve_carrier_hooks("slurp", repo_root=ROOT)
    layer = copy.deepcopy(hooks.lock_versions["v2.1"]())
    layer["native_episode"]["tool_schema_rendering"] = "constant"
    layer["native_episode"]["roles"]["reviewer"]["history_scope"] = "latest-solver-and-local-tools"
    hooks = replace(hooks, lock_versions={**hooks.lock_versions, "v2.1": lambda: copy.deepcopy(layer)})
    values = compile_block(block, hooks).values_on_roster_of(baseline())
    assert values["native_episode"]["tool_schema_rendering"] == "per-role"
    assert values["native_episode"]["roles"]["reviewer"]["history_scope"] == "full"


def test_native_presentation_does_not_release_a_direct_carrier():
    block = {"module_id": cm.CONSUMPTION_MODULE_ID, "profile": "earnings", "components": [entry()]}
    with pytest.raises(cm.ConsumptionModuleConfigError, match="direct layer"):
        compile_block(block)
