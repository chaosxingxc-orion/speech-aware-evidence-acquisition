"""NX programme E1, Perception node (2026-10-10): the consumption module's ``template`` column
kind naming the Perception node.

Columns with ``node: perception`` compile into ONE ``roles.perception.template_variants`` block
(one arm per column, the twin ``aa``, the delivering arm ``lock`` last), parsed by the rails' own
``parse_perception_template_variants`` before writing; the contact term is 2 (K - 1) over the
review-off graph (each non-delivering arm is one Perception and one level-2 Solver contact).
Model-free throughout.
"""

from __future__ import annotations

import copy
import dataclasses

import pytest

from test_consumption_module_review_off import review_off_block
from test_consumption_module_template_columns import FIT, SHA

from speech_aware_evidence_acquisition.rails import consumption_module as cm
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)


def _column(name, sha, *, tokens=400):
    return {
        "column_id": name, "kind": "template", "node": "perception",
        "template": {"relpath": f"configs/probes/nx/{name}.txt", "sha256": sha},
        "template_tokens": tokens,
    }


def _block(*, names=("p1", "p2"), twin=True):
    block = review_off_block()
    block["columns"] = [_column(n, SHA["abcdef"[i]]) for i, n in enumerate(names)]
    block["template_frame"] = {
        "max_supplied_items": 48, "delivering_template_tokens": 380,
        "twin": twin, "fit_estimate": dict(FIT),
    }
    return block


def test_perception_template_columns_compile_to_one_block_at_the_perception_node():
    composed = cm.compile_module(_block(), carrier_module_hooks())
    values = composed.values()
    block = values["native_episode"]["roles"]["perception"]["template_variants"]
    assert block["node"] == "perception"
    assert [(a["arm_id"], a.get("deliver"), a.get("replicate_of")) for a in block["arms"]] == [
        ("p1", None, None), ("p2", None, None), ("aa", None, "lock"), ("lock", True, None),
    ]
    assert block["arms"][3] == {"arm_id": "lock", "deliver": True, "template_tokens": 380}
    assert "template_variants" not in values["native_episode"]["roles"]["solver"]
    # review-off graph 2 + 2 (K - 1), K = 4 -> 8.
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c8", 8)


def test_a_perception_template_block_without_a_twin_is_refused_at_compile_time():
    with pytest.raises(cm.ConsumptionModuleConfigError, match="exactly one twin"):
        cm.compile_module(_block(twin=False), carrier_module_hooks())


def test_the_compiled_block_loads_through_the_runtime_loader_and_verifies():
    block = _block()
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    parsed = load_native_episode_config(values, default_phase_program(values["policy"]))
    assert parsed.max_contacts == composed.program_ceiling == 8
    group = parsed.perception_branch_group
    assert group.is_template and group.level == 2
    assert group.branch_ids == ("p1", "p2", "aa", "lock")
    cm.verify_declared_module(block, values)
    edited = copy.deepcopy(values)
    edited["native_episode"]["roles"]["perception"]["template_variants"]["arms"][0][
        "instruction_template"]["sha256"] = SHA["f"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)


def test_the_compiler_applies_the_perception_parsers_refusals_before_writing():
    block = _block()
    block["columns"][1]["template"]["sha256"] = SHA["a"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="name the same template"):
        cm.compile_module(block, carrier_module_hooks())
    block = _block()
    block["columns"][0]["template"]["relpath"] = "configs/baseline/x.txt"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="outside the allowed template roots"):
        cm.compile_module(block, carrier_module_hooks())
    block = _block()
    block["columns"][0]["template_tokens"] = 9000
    with pytest.raises(cm.ConsumptionModuleConfigError, match="exceeds"):
        cm.compile_module(block, carrier_module_hooks())


def test_a_carrier_without_the_perception_frame_refuses_the_column():
    hooks = dataclasses.replace(carrier_module_hooks(), perception_template_variant_frame=None)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="perception_template_variant_frame"):
        cm.compile_module(_block(), hooks)


def test_solver_and_perception_template_columns_cannot_share_a_block():
    block = _block()
    block["columns"].append({**_column("t9", SHA["f"]), "node": "solver"})
    with pytest.raises(cm.ConsumptionModuleConfigError, match="one node"):
        cm.parse_consumption_module_block(block)


def test_the_v4_perception_receipt_is_a_registered_node_receipt():
    receipt = cm.module_header_receipt(
        cm.compile_module(_block(), carrier_module_hooks()),
        node_receipts=[{"schema": "saea-perception-branch-arms-v4", "pointer": "perception_branches"}],
    )
    cm.validate_module_header_receipt(receipt)
    assert receipt["program_ceiling"] == 8
