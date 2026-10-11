"""NX programme E1: the consumption module's ``template`` column kind.

A ``columns`` entry of kind ``template`` is one arm of the node's
``template_variants`` block. The compiler builds the whole block (one arm per
column in column order, the twin, the delivering arm that carries no template),
parses it with the rails' own ``parse_template_variants`` before writing, adds
K - 1 to the ceiling and picks the program-family id. The config loader's
``verify_declared_module`` then holds a declared config to exactly that block.
Model-free throughout.
"""

from __future__ import annotations

import copy
import dataclasses
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import module_equivalence_proof as proof  # noqa: E402
from test_consumption_module_review_off import review_off_block  # noqa: E402

from speech_aware_evidence_acquisition.rails import consumption_module as cm  # noqa: E402
from speech_aware_evidence_acquisition.rails.adapters.slurp_module_hooks import (  # noqa: E402
    carrier_module_hooks,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program  # noqa: E402
from speech_aware_evidence_acquisition.rails.native_episode_config import (  # noqa: E402
    load_native_episode_config,
)

FIT = {
    "slot_tokens": 24576, "completion_ceiling": 640,
    "base_prompt_tokens": 9600, "tokens_per_supplied_item": 120,
}
PSV1 = "configs/baseline/slurp-native-stage3-psv1-fold-b-baseline-v1.json"
SHA = {name: name * 64 for name in "abcdef"}


def _column(name, sha, *, tokens=400, node="solver"):
    return {
        "column_id": name, "kind": "template", "node": node,
        "template": {"relpath": f"configs/probes/nx/{name}.txt", "sha256": sha},
        "template_tokens": tokens,
    }


def _template_block(*, names=("t1", "t2"), twin=True):
    block = review_off_block()
    block["columns"] = [_column(n, SHA["abcdef"[i]]) for i, n in enumerate(names)]
    block["template_frame"] = {
        "max_supplied_items": 48, "delivering_template_tokens": 380,
        "twin": twin, "fit_estimate": dict(FIT),
    }
    return block


def test_template_columns_compile_to_one_block_with_the_twin_and_the_lock_last():
    composed = cm.compile_module(_template_block(), carrier_module_hooks())
    values = composed.values()
    block = values["native_episode"]["roles"]["solver"]["template_variants"]
    assert block["node"] == "solver" and block["max_supplied_items"] == 48
    assert [(a["arm_id"], a.get("deliver"), a.get("replicate_of")) for a in block["arms"]] == [
        ("t1", None, None), ("t2", None, None), ("aa", None, "lock"), ("lock", True, None),
    ]
    assert block["arms"][0]["instruction_template"] == {
        "relpath": "configs/probes/nx/t1.txt", "sha256": SHA["a"],
    }
    assert block["arms"][3] == {"arm_id": "lock", "deliver": True, "template_tokens": 380}
    # review-off graph (perception 1 + solver 1) + (K - 1): K = 4 -> 5.
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c5", 5)
    assert values["policy"] == "phase-native-module-v1-c5"
    assert block["fit_estimate"] == FIT


def test_without_a_twin_the_ceiling_follows_the_arm_count():
    composed = cm.compile_module(_template_block(twin=False), carrier_module_hooks())
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c4", 4)
    arms = composed.values()["native_episode"]["roles"]["solver"]["template_variants"]["arms"]
    assert [a["arm_id"] for a in arms] == ["t1", "t2", "lock"]


def test_six_candidates_a_twin_and_the_lock_reach_the_family_bound():
    names = tuple(f"t{i}" for i in range(1, 7))
    composed = cm.compile_module(_template_block(names=names), carrier_module_hooks())
    assert (composed.program_id, composed.program_ceiling) == ("phase-native-module-v1-c9", 9)


def test_the_compiled_block_loads_through_the_runtime_loader_and_verifies():
    block = _template_block()
    composed = cm.compile_module(block, carrier_module_hooks())
    values = composed.values()
    values["carrier_lock_key"] = "slurp"
    values["native_episode"]["consumption_module"] = block
    program = default_phase_program(values["policy"])
    parsed = load_native_episode_config(values, program)
    assert parsed.max_contacts == composed.program_ceiling == 5
    group = parsed.supply_variant_group
    assert group.is_template and group.arm_ids == ("t1", "t2", "aa", "lock")
    assert not parsed.review_loop_enabled
    cm.verify_declared_module(block, values)
    # a later edit to the compiled block is refused by the verifier
    edited = copy.deepcopy(values)
    edited["native_episode"]["roles"]["solver"]["template_variants"]["arms"][0][
        "instruction_template"]["sha256"] = SHA["f"]
    with pytest.raises(cm.ConsumptionModuleConfigError, match="differ"):
        cm.verify_declared_module(block, edited)


def test_the_block_identity_binds_the_templates():
    a = cm.parse_consumption_module_block(_template_block())
    other = _template_block()
    other["columns"][0]["template"]["sha256"] = SHA["f"]
    b = cm.parse_consumption_module_block(other)
    assert a.block_sha256 != b.block_sha256
    assert [c.kind for c in a.columns] == ["template", "template"]
    assert a.template_columns == a.columns and a.branch_columns == ()


def test_the_module_off_arm_and_branch_only_blocks_are_unchanged():
    assert all(c.kind == "branch" for c in cm.parse_consumption_module_block(
        proof.psv_column_block(PSV1)).columns)
    assert not cm.is_module_off_block(_template_block())


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b["columns"][0].update(overrides={"a.b.c.d": 1}), "keys must be exactly"),
        (lambda b: b["columns"][0].update(toggle="top2-contrast"), "keys must be exactly"),
        (lambda b: b["columns"][0].pop("template_tokens"), "keys must be exactly"),
        (lambda b: (b["columns"][0].update(kind="bogus"), b.pop("review_loop")),
         "must be 'template', 'supply' or absent"),
        (lambda b: b["columns"][0]["template"].pop("sha256"), "relpath, sha256"),
        (lambda b: b["columns"][0]["template"].update(sha256="XYZ"), "64-hex"),
        (lambda b: b["columns"][0].update(template_tokens=0), "positive integer"),
        (lambda b: b["columns"][1].update(column_id="t1"), "ids must be distinct"),
        (lambda b: b["columns"][1].update(node="reviewer"), "one node"),
        (lambda b: b.pop("template_frame"), "template_frame is required"),
        (lambda b: b["template_frame"].update(extra=1), "keys must be exactly"),
        (lambda b: b["template_frame"].update(twin="yes"), "must be a bool"),
        (lambda b: b["template_frame"].update(max_supplied_items=0), "positive integer"),
        (lambda b: b.update(columns=[]), "no template column is"),
    ],
)
def test_the_parse_refuses_a_malformed_template_column_or_frame(mutate, message):
    block = _template_block()
    mutate(block)
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.parse_consumption_module_block(block)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b["columns"][0]["template"].update(relpath="configs/baseline/x.txt"),
         "outside the allowed template roots"),
        (lambda b: b["columns"][0]["template"].update(relpath="configs/probes/../x.txt"),
         "not a plain repository-relative path"),
        (lambda b: b["columns"][1]["template"].update(sha256=SHA["a"]),
         "name the same template"),
        (lambda b: b["columns"][0]["template"].update(
            relpath="configs/probes/slurp_native_role_solver_v2.txt"),
         "node's own locked template"),
        (lambda b: b["columns"][0].update(template_tokens=9000), "exceeds"),
        (lambda b: b["columns"][0].update(node="reviewer") or b["columns"][1].update(node="reviewer"),
         "admits template variants only at 'solver'"),
        (lambda b: b["columns"].extend(_column(f"x{i}", SHA["a"], tokens=400) for i in range(5)),
         "between 1 and 6"),
    ],
)
def test_the_compiler_applies_the_rails_own_refusals_before_writing(mutate, message):
    block = _template_block()
    mutate(block)
    # the columns of the over-long case reuse digests; make every digest distinct first
    for index, column in enumerate(block["columns"]):
        if message == "between 1 and 6":
            column["template"]["sha256"] = f"{index:x}".rjust(64, "0")
    with pytest.raises(cm.ConsumptionModuleConfigError, match=message):
        cm.compile_module(block, carrier_module_hooks())


def test_a_carrier_without_the_hook_refuses_a_template_column():
    hooks = dataclasses.replace(carrier_module_hooks(), template_variant_frame=None)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="template_variant_frame"):
        cm.compile_module(_template_block(), hooks)


def test_a_twin_needs_the_carriers_twin_arm_id():
    frame = dict(carrier_module_hooks().template_variant_frame, twin_arm_id=None)
    hooks = dataclasses.replace(carrier_module_hooks(), template_variant_frame=frame)
    with pytest.raises(cm.ConsumptionModuleConfigError, match="no twin arm id"):
        cm.compile_module(_template_block(twin=True), hooks)
    # without a twin the id is never needed
    cm.compile_module(_template_block(twin=False), hooks)


def test_template_columns_cannot_share_a_block_with_perception_branch_columns():
    block = proof.psv_column_block(PSV1)
    block["columns"].append(_column("t1", SHA["a"]))
    block["template_frame"] = {
        "max_supplied_items": 48, "delivering_template_tokens": 380,
        "twin": True, "fit_estimate": dict(FIT),
    }
    with pytest.raises(cm.ConsumptionModuleConfigError, match="beside Perception-branch columns"):
        cm.parse_consumption_module_block(block)


def test_a_perception_branch_column_is_still_refused_under_the_review_off_profile():
    block = proof.psv_column_block(PSV1)
    block["review_loop"] = "off"
    with pytest.raises(cm.ConsumptionModuleConfigError, match="does not support branch columns"):
        cm.parse_consumption_module_block(block)


def test_the_v4_receipt_schema_is_a_registered_node_receipt():
    receipt = cm.module_header_receipt(
        cm.compile_module(_template_block(), carrier_module_hooks()),
        node_receipts=[{"schema": "saea-supply-variant-arms-v4", "pointer": "supply_variants"}],
    )
    cm.validate_module_header_receipt(receipt)
    assert receipt["program_ceiling"] == 5
