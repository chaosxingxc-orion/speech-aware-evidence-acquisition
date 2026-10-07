"""Bind a prospective review-off graph in the compiler, never by later mutation."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from speech_aware_evidence_acquisition.rails.phase_material import (
    PhaseMaterialError, load_phase_material_specs,
)
from test_consumption_module import _block
from test_solver_tool_access import MODE, TARGET


@pytest.mark.parametrize("label", ["seed", "review-off", "solver-lookup"])
def test_real_seed_handoff_contract_compiles_through_both_runtime_loaders(label):
    root = Path(__file__).resolve().parents[2]
    original = json.loads((root / "docs/readiness/2026-10-07-slurp-simple-consumption-direction-v1"
                          / f"prepared-{label}-policy-v1.json").read_text())
    block = original["native_episode"]["consumption_module"]
    values = cm.compile_module(block, carrier_module_hooks()).values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    program = default_phase_program(values["policy"])
    native = load_native_episode_config(values, program)
    material = load_phase_material_specs(values, program)
    assert native.review_loop_enabled is (label == "seed")
    assert material["reviewer"].response_format_id == (
        "saea-slot-review-handoff-v1" if label == "seed" else None
    )
    for role in ("perception", "solver", "reviewer", "planner"):
        assert material[role].instruction_template == original["phase_material"][role]["instruction_template"]
    for role in ("perception", "solver"):
        bad = deepcopy(values)
        bad["phase_material"][role]["response_format_id"] = "unregistered-output-contract"
        with pytest.raises(PhaseMaterialError, match="exactly one authority"):
            load_phase_material_specs(bad, program)
    bad_block = deepcopy(block)
    component = next(c for c in bad_block["components"]
                     if c["component_id"] == cm.KNOWLEDGE_CONSUMPTION_OPPORTUNITY)
    component["params"]["reviewer_response_format_id"] = "unregistered-output-contract"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="unregistered Reviewer"):
        cm.compile_module(bad_block, carrier_module_hooks())


def review_off_block(*, tool=False):
    block = _block()
    block["review_loop"] = "off"
    if tool:
        block["solver_tool_access"] = MODE
        block["components"] = [c for c in block["components"] if c["component_id"] != cm.KNOWLEDGE_CONSUMPTION_OPPORTUNITY]
        block["components"].append({
            "component_id": cm.KNOWLEDGE_CONSUMPTION_OPPORTUNITY, "state": "on",
            "admitted_by": "Prospective bounded architecture comparison only.",
            "record": "docs/readiness/2026-10-07-slurp-simple-consumption-direction-v1/README.md",
            "params": {"mode": "targeted", "store_id": "slot-contracts",
                       "reviewer_template": "probes/slurp_native_role_reviewer_slot_issues_v1.txt",
                       "planner_template": "probes/slurp_native_role_planner_slot_lookup_v1.txt",
                       "solver_template": "probes/prospective_solver_contract.txt"},
        })
    return block


def test_review_off_profile_is_not_the_historical_module_off_arm():
    assert cm.is_module_off_block(_block())
    assert not cm.is_module_off_block(review_off_block())


def test_plain_review_off_preserves_declared_constant_schema_rendering():
    block = review_off_block()
    context = next(c for c in block["components"] if c["component_id"] == cm.NODE_CONTEXT_PRESENTATION)
    context.update(state="on", admitted_by="Preserve the exact seed node context.",
                   record="docs/readiness/2026-10-07-slurp-simple-consumption-direction-v1/README.md",
                   params={"tool_schema_rendering": "constant"})
    values = cm.compile_module(block, carrier_module_hooks()).values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    assert values["native_episode"]["tool_schema_rendering"] == "constant"
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.max_contacts == 2 and parsed.tool_schema_rendering == "constant"
    values["native_episode"].pop("consumption_module")
    with pytest.raises(ValueError, match="constant"):
        load_native_episode_config(values, default_phase_program(values["policy"]))


@pytest.mark.parametrize("tool", [False, True])
def test_compiler_emits_bound_review_off_graph_and_verifier_refuses_later_edits(tool):
    hooks = carrier_module_hooks()
    before = cm.compile_module(_block(), hooks).values()
    block = review_off_block(tool=tool)
    compiled = cm.compile_module(block, hooks)
    values = compiled.values()
    values["native_episode"]["consumption_module"] = block
    native = values["native_episode"]
    assert native["max_revisions"] == 0 and native["review_loop"] == "off"
    assert native["roles"]["reviewer"]["max_iterations"] == 0
    assert native["roles"]["planner"]["max_iterations"] == 0
    assert native["roles"]["solver"]["max_iterations"] == (2 if tool else 1)
    assert values["phase_material"]["perception"] == before["phase_material"]["perception"]
    assert values["knowledge_stores"] == before["knowledge_stores"]
    if tool:
        assert native["solver_tool_access"] == MODE
        assert native["tool_iteration_policy"] == "reserve-final-report"
        assert values["phase_tools"]["solver"]["allowed_tools"] == [TARGET]
    else:
        assert values["phase_material"]["solver"] == before["phase_material"]["solver"]
        assert native.get("tool_schema_rendering") == before["native_episode"].get("tool_schema_rendering")
        assert values["phase_tools"] == {}
    parsed = load_native_episode_config({**values, "carrier_lock_key": "slurp"},
                                        default_phase_program(values["policy"]))
    assert parsed.max_contacts == compiled.program_ceiling == (3 if tool else 2)
    assert not parsed.review_loop_enabled
    cm.verify_declared_module(block, values)
    assert compiled.config_block_sha256 != cm.compile_module(_block(), hooks).config_block_sha256
    values["native_episode"]["roles"]["solver"]["max_iterations"] = 7
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, values)


@pytest.mark.parametrize("change", [
    lambda b: b.update(review_loop="on"),
    lambda b: b.update(review_loop=None),
    lambda b: b.pop("review_loop"),
    lambda b: b.update(solver_tool_access="on"),
    lambda b: b["components"][-1]["params"].pop("solver_template"),
    lambda b: b["components"][-1]["params"].update(store_id="intent-boundaries"),
    lambda b: b["components"][-1]["params"].update(mode="reread"),
    lambda b: b["components"].pop(),
])
def test_invalid_profile_cannot_gain_solver_authority(change):
    block = deepcopy(review_off_block(tool=True))
    change(block)
    with pytest.raises(cm.ConsumptionModuleConfigError):
        cm.compile_module(block, carrier_module_hooks())
