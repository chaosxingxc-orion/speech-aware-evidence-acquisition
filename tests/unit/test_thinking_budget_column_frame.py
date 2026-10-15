"""NX-T R2 (2026-10-15): the per-node REASONING-BUDGET column rides the NX-T R1 arm kind.

``reasoning_budget_tokens`` / ``answer_reserve_tokens`` were already legal keys of a ``thinking_policy``; the one harness addition is the OPTIONAL
``thinking_frame.delivering_arm_id`` (a budget round names its delivering arm ``budget-3072`` instead of the carrier hook's ``both-on``). Model-free.
"""

from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.core import reasoning_knobs as rk
from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import carrier_module_hooks
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import load_native_episode_config
from test_consumption_module_review_off import review_off_block

FIT = {"slot_tokens": 24576, "completion_ceiling": 4096, "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120}
GUARD = "refuse-think-marker-in-content"
CAP = 4096


def _policy(budget: int) -> dict:
    return {"perception": {"reasoning_budget_tokens": budget, "answer_reserve_tokens": CAP - budget},
            "solver": {"reasoning_budget_tokens": budget, "answer_reserve_tokens": CAP - budget}}


def _block(*, twin=False, delivering=None, budgets=(1536, 2048)) -> dict:
    block = review_off_block()
    block["columns"] = [{"column_id": f"budget-{b}", "kind": "thinking", "node": "perception", "thinking_policy": _policy(b)} for b in budgets]
    block["thinking_frame"] = {"max_supplied_items": 48, "twin": twin, "fit_estimate": dict(FIT)}
    if delivering is not None:
        block["thinking_frame"]["delivering_arm_id"] = delivering
    return block


def test_without_the_optional_key_the_delivering_arm_is_the_carrier_default():
    composed = cm.compile_module(_block(), carrier_module_hooks())
    arms = composed.values()["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == ["budget-1536", "budget-2048", "both-on"]
    assert arms[-1] == {"arm_id": "both-on", "deliver": True}


def test_a_budget_round_names_its_delivering_arm_and_has_no_twin():
    composed = cm.compile_module(_block(delivering="budget-3072"), carrier_module_hooks())
    arms = composed.values()["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == ["budget-1536", "budget-2048", "budget-3072"]
    assert arms[-1] == {"arm_id": "budget-3072", "deliver": True}
    assert all("replicate_of" not in a for a in arms)
    # review-off graph 2 + 2 (K - 1), K = 3 -> 6.
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c6", 6)


def test_a_twin_replicates_the_named_delivering_arm():
    composed = cm.compile_module(_block(twin=True, delivering="budget-3072"), carrier_module_hooks())
    arms = composed.values()["native_episode"]["roles"]["perception"]["thinking_variants"]["arms"]
    assert arms[-2] == {"arm_id": "both-on-twin", "replicate_of": "budget-3072"}
    assert composed.program_ceiling == 8


@pytest.mark.parametrize("bad", ["", "  ", 3, None])
def test_the_optional_key_is_a_non_empty_string(bad):
    block = _block()
    block["thinking_frame"]["delivering_arm_id"] = bad
    with pytest.raises(cm.ConsumptionModuleConfigError, match="delivering_arm_id|keys must be exactly"):
        cm.compile_module(block, carrier_module_hooks())


def test_other_frame_keys_stay_refused():
    block = _block()
    block["thinking_frame"]["cap"] = 1
    with pytest.raises(cm.ConsumptionModuleConfigError, match="keys must be exactly"):
        cm.compile_module(block, carrier_module_hooks())
    block = _block()
    del block["thinking_frame"]["twin"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="keys must be exactly"):
        cm.compile_module(block, carrier_module_hooks())


def test_a_candidate_named_like_the_delivering_arm_is_refused_by_the_parser():
    block = _block(budgets=(1536, 2048), delivering="budget-2048")
    with pytest.raises(cm.ConsumptionModuleConfigError, match="distinct"):
        cm.compile_module(block, carrier_module_hooks())


def test_the_budget_block_loads_through_the_runtime_loader_and_verifies():
    block = _block(delivering="budget-3072")
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    values.update(reasoning_content_guard=GUARD, reasoning_budget_tokens=3072, answer_reserve_tokens=1024, enable_thinking=True,
                  decoding_params={"temperature": 0, "seed": 20260913, "max_tokens": CAP})
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.max_contacts == composed.program_ceiling == 6
    assert parsed.perception_branch_group.is_thinking and not parsed.perception_branch_group.has_twin
    assert parsed.perception_branch_group.delivering_branch.branch_id == "budget-3072"
    cm.verify_declared_module(block, values)


def test_a_budget_arm_keeps_the_cap_and_moves_only_the_budget_and_the_reserve():
    base = {"temperature": 0, "seed": 20260913, "max_tokens": CAP, "thinking_budget_tokens": 3072, "chat_template_kwargs": {"enable_thinking": True}}
    policy = _policy(1536)
    for node in ("perception", "solver"):
        out = rk.resolve_node_decoding(base, policy, node, cap=CAP)
        assert out["thinking_budget_tokens"] == 1536 and out["max_tokens"] == CAP
        assert {k: v for k, v in out.items() if k not in ("thinking_budget_tokens",)} == {k: v for k, v in base.items() if k != "thinking_budget_tokens"}
        assert rk.fallback_reserve(out) == CAP - 1536
    # the default reserve (1,024) would move the cap to budget + 1,024: the budget round states its reserve instead.
    assert rk.resolve_node_decoding(base, {"solver": {"reasoning_budget_tokens": 1536}}, "solver", cap=CAP)["max_tokens"] == 2560
    with pytest.raises(rk.ReasoningKnobError, match="exceeds the geometry cap"):
        rk.resolve_node_decoding(base, {"solver": {"reasoning_budget_tokens": 3500}}, "solver", cap=CAP)


def test_the_frame_key_does_not_change_the_default_block_bytes():
    plain, named = _block(), _block(delivering="both-on")
    a = cm.compile_module(plain, carrier_module_hooks()).values()["native_episode"]["roles"]["perception"]["thinking_variants"]
    b = cm.compile_module(named, carrier_module_hooks()).values()["native_episode"]["roles"]["perception"]["thinking_variants"]
    assert copy.deepcopy(a) == copy.deepcopy(b)
