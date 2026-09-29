"""Unit tests (fake core) for run_perception_branch_arms and
PerceptionBranchRoleNode (same-flight instrument phase 2, merge set C, item
5). These exercise the PURE orchestration function directly with stub async
invoke callables -- no model, server, GPU, or openjiuwen contact -- mirroring
the level of coverage the phase-1 twin (run_supply_variant_arms) has no
dedicated isolated test for either (it is exercised only through the full
live harness in tests/unit/test_stage3_supply_variant_interleaving.py); this
file closes that gap for both mechanisms' shared shape.

This repository tests async framework code with plain ``asyncio.run`` inside
ordinary (sync) test functions (see tests/unit/test_native_group_solver.py)
rather than a pytest-asyncio plugin; this module follows the same pattern.
"""

from __future__ import annotations

import asyncio

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw.native_supply_variants import (
    PerceptionBranchRoleNode,
    PerceptionBranchSolverRoleNode,
    SupplyVariantNodeError,
    run_perception_branch_arms,
    run_perception_branch_solver_arms,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PerceptionBranchError,
    parse_perception_branches,
    perception_branch_record,
)

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 512,
    "base_prompt_tokens": 4000,
    "tokens_per_supplied_item": 100,
}
STORE = "intent-boundaries"
SHA = "a" * 64


def _run(coro):
    return asyncio.run(coro)


def _group(level=1):
    return parse_perception_branches(
        {
            "level": level,
            "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 8,
                    "overrides": {f"knowledge_stores.{STORE}.phase_supply.perception.k": 16},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 8},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 8},
            ],
        },
        first_phase_id="perception",
        declared_stores=(STORE,),
    )


def _answer(role_id="perception", text="note text", contact_id="c0"):
    return {
        "role_id": role_id,
        "actor_output": text,
        "result_type": "answer",
        "execution_receipt": {
            "contacts": [{"contact_id": contact_id}],
        },
    }


def _record_factory(group):
    def record(branch_index: int, result) -> dict:
        branch = group.branch_at(branch_index)
        return perception_branch_record(
            branch=branch, branch_index=branch_index,
            contact_id=result["execution_receipt"]["contacts"][0]["contact_id"],
            request_sha256=SHA, response_text_sha256=SHA, note_sha256=SHA,
            note_parse_status="ok", candidate_intent_ids=("intent_a",),
            supplied_value_ids=("v1",),
        )
    return record


def test_a_delivers_last_and_becomes_the_actor_output():
    group = _group()
    calls: list[int] = []

    async def invoke_branch(index: int) -> dict:
        calls.append(index)
        branch = group.branch_at(index)
        return _answer(text=f"text-for-{branch.branch_id}", contact_id=f"c{index}")

    result = _run(run_perception_branch_arms(
        invoke_branch, group=group, branch_record=_record_factory(group), phase_id="perception",
    ))
    assert calls == [0, 1, 2]
    assert result["actor_output"] == "text-for-A"
    assert result["result_type"] == "answer"
    assert [c["contact_id"] for c in result["execution_receipt"]["contacts"]] == ["c0", "c1", "c2"]
    assert result["execution_receipt"]["final_contact"]["contact_id"] == "c2"
    receipt = result["perception_branches"]
    assert receipt["delivered_branch_id"] == "A"
    assert receipt["level"] == 1
    assert [row["branch_id"] for row in receipt["branches"]] == ["B", "T", "A"]


def test_non_a_notes_never_reach_the_delivered_output():
    group = _group()

    async def invoke_branch(index: int) -> dict:
        branch = group.branch_at(index)
        # Mutating B's or T's note text must never change what A delivers.
        text = "MUTATED NOTE" if branch.branch_id != "A" else "A's real answer"
        return _answer(text=text, contact_id=f"c{index}")

    result = _run(run_perception_branch_arms(
        invoke_branch, group=group, branch_record=_record_factory(group), phase_id="perception",
    ))
    assert result["actor_output"] == "A's real answer"
    assert "MUTATED NOTE" not in result["actor_output"]


def test_level_2_receipt_carries_the_declared_level():
    group = _group(level=2)

    async def invoke_branch(index: int) -> dict:
        return _answer(contact_id=f"c{index}")

    result = _run(run_perception_branch_arms(
        invoke_branch, group=group, branch_record=_record_factory(group), phase_id="perception",
    ))
    assert result["perception_branches"]["level"] == 2


def test_refuses_a_branch_answer_with_no_execution_receipt():
    group = _group()

    async def invoke_branch(index: int) -> dict:
        answer = _answer(contact_id=f"c{index}")
        del answer["execution_receipt"]
        return answer

    with pytest.raises(SupplyVariantNodeError, match="no execution receipt"):
        _run(run_perception_branch_arms(
            invoke_branch, group=group, branch_record=_record_factory(group), phase_id="perception",
        ))


def test_refuses_mismatched_role_ids_across_branches():
    group = _group()

    async def invoke_branch(index: int) -> dict:
        role_id = "perception" if index == 0 else "not-perception"
        return _answer(role_id=role_id, contact_id=f"c{index}")

    with pytest.raises(SupplyVariantNodeError, match="share one role_id"):
        _run(run_perception_branch_arms(
            invoke_branch, group=group, branch_record=_record_factory(group), phase_id="perception",
        ))


def test_refuses_a_record_naming_another_branch():
    group = _group()

    async def invoke_branch(index: int) -> dict:
        return _answer(contact_id=f"c{index}")

    def bad_record(branch_index, result):
        return {"branch_id": "not-a-real-branch"}

    with pytest.raises(SupplyVariantNodeError, match="names another branch"):
        _run(run_perception_branch_arms(
            invoke_branch, group=group, branch_record=bad_record, phase_id="perception",
        ))


def test_a_record_error_is_wrapped_with_the_branch_id():
    group = _group()

    async def invoke_branch(index: int) -> dict:
        return _answer(contact_id=f"c{index}")

    def raising_record(branch_index, result):
        raise PerceptionBranchError("synthetic failure")

    with pytest.raises(SupplyVariantNodeError, match="record is invalid"):
        _run(run_perception_branch_arms(
            invoke_branch, group=group, branch_record=raising_record, phase_id="perception",
        ))


def test_role_node_refuses_a_non_perception_inner():
    class _FakeSpec:
        role_kind = "solver"

    class _FakeInner:
        spec = _FakeSpec()

    with pytest.raises(SupplyVariantNodeError, match="inner Perception NativeRoleNode"):
        PerceptionBranchRoleNode(
            inner=_FakeInner(), group=_group(), branch_record=_record_factory(_group()),
        )


# ---------------------------------------------------------------------------
# LEVEL 2 (merge set C item 1): run_perception_branch_solver_arms and
# PerceptionBranchSolverRoleNode -- the Solver's own first-visit branch
# fan-out. Structurally this file's own tests above (run_perception_branch_
# arms/PerceptionBranchRoleNode) restated over the Solver's phase instead of
# Perception's; AT-P7 (design section 5): "A's level-2 column equals the
# sealed first Solver visit after the normaliser" is a RECEIPT-assembly
# property tests/unit/test_perception_branch_acceptance.py already covers on
# a fixture, and a RUNTIME property tests/unit/test_perception_branch_live.py
# now covers on a real graph; the tests below close the THIRD gap -- the pure
# orchestration function and node class themselves, no model, server, GPU or
# openjiuwen contact.
# ---------------------------------------------------------------------------


def _solver_record_factory(group):
    """Every branch's own Solver-column custody, keyed to its branch id --
    the shape ``rails.runner.read_perception_branch_solver_record`` returns,
    restated here as a bare stub so these tests need no runner closures."""

    def record(branch_index: int, result) -> dict:
        branch = group.branch_at(branch_index)
        contact_id = result["execution_receipt"]["contacts"][0]["contact_id"]
        return {
            "branch_id": branch.branch_id,
            "solver_contact_id": contact_id,
            "solver_request_sha256": SHA,
            "solver_response_text_sha256": SHA,
            "candidate_supply_value_ids": [],
        }
    return record


def test_solver_fanout_a_delivers_last_and_spends_k_contacts():
    group = _group(level=2)
    calls: list[int] = []

    async def invoke_branch(index: int) -> dict:
        calls.append(index)
        branch = group.branch_at(index)
        return _answer(role_id="solver", text=f"solver-for-{branch.branch_id}", contact_id=f"s{index}")

    result = _run(run_perception_branch_solver_arms(
        invoke_branch, group=group, branch_record=_solver_record_factory(group),
    ))
    assert calls == [0, 1, 2]
    assert result["role_id"] == "solver"
    assert result["actor_output"] == "solver-for-A"
    assert result["result_type"] == "answer"
    assert result["delivery_eligible"] is True
    assert [c["contact_id"] for c in result["execution_receipt"]["contacts"]] == ["s0", "s1", "s2"]
    assert result["execution_receipt"]["final_contact"]["contact_id"] == "s2"
    # Unlike run_supply_variant_arms/run_perception_branch_arms, no extra
    # custody key rides the returned result: the Solver's own state["latest_
    # solver"] capture needs no change for this route (design section 3).
    assert "supply_variants" not in result
    assert "perception_branches" not in result


def test_solver_fanout_calls_branch_record_for_every_branch_including_a():
    group = _group(level=2)
    seen: list[str] = []

    async def invoke_branch(index: int) -> dict:
        branch = group.branch_at(index)
        return _answer(role_id="solver", text=f"solver-for-{branch.branch_id}", contact_id=f"s{index}")

    def record(branch_index, result):
        branch = group.branch_at(branch_index)
        seen.append(branch.branch_id)
        return _solver_record_factory(group)(branch_index, result)

    _run(run_perception_branch_solver_arms(invoke_branch, group=group, branch_record=record))
    assert seen == ["B", "T", "A"]


def test_solver_fanout_non_a_branch_answers_never_become_the_delivered_output():
    group = _group(level=2)

    async def invoke_branch(index: int) -> dict:
        branch = group.branch_at(index)
        text = "MUTATED SOLVER ANSWER" if branch.branch_id != "A" else "A's real solver answer"
        return _answer(role_id="solver", text=text, contact_id=f"s{index}")

    result = _run(run_perception_branch_solver_arms(
        invoke_branch, group=group, branch_record=_solver_record_factory(group),
    ))
    assert result["actor_output"] == "A's real solver answer"
    assert "MUTATED SOLVER ANSWER" not in result["actor_output"]


def test_solver_fanout_refuses_a_branch_answer_with_no_execution_receipt():
    group = _group(level=2)

    async def invoke_branch(index: int) -> dict:
        answer = _answer(role_id="solver", contact_id=f"s{index}")
        del answer["execution_receipt"]
        return answer

    with pytest.raises(SupplyVariantNodeError, match="no execution receipt"):
        _run(run_perception_branch_solver_arms(
            invoke_branch, group=group, branch_record=_solver_record_factory(group),
        ))


def test_solver_fanout_refuses_mismatched_role_ids_across_branches():
    group = _group(level=2)

    async def invoke_branch(index: int) -> dict:
        role_id = "solver" if index == 0 else "not-solver"
        return _answer(role_id=role_id, contact_id=f"s{index}")

    with pytest.raises(SupplyVariantNodeError, match="share one role_id"):
        _run(run_perception_branch_solver_arms(
            invoke_branch, group=group, branch_record=_solver_record_factory(group),
        ))


def test_solver_fanout_refuses_a_record_naming_another_branch():
    group = _group(level=2)

    async def invoke_branch(index: int) -> dict:
        return _answer(role_id="solver", contact_id=f"s{index}")

    def bad_record(branch_index, result):
        return {"branch_id": "not-a-real-branch"}

    with pytest.raises(SupplyVariantNodeError, match="names another branch"):
        _run(run_perception_branch_solver_arms(
            invoke_branch, group=group, branch_record=bad_record,
        ))


def test_solver_role_node_refuses_a_non_solver_inner():
    class _FakeSpec:
        role_kind = "perception"

    class _FakeInner:
        spec = _FakeSpec()

    with pytest.raises(SupplyVariantNodeError, match="inner Solver NativeRoleNode"):
        PerceptionBranchSolverRoleNode(
            inner=_FakeInner(), group=_group(level=2),
            branch_record=_solver_record_factory(_group(level=2)),
        )
