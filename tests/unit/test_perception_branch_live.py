"""LIVE (fake-transport, real graph) proof of the Perception-branch wiring (same-flight instrument
phase 2, merge set C, item 2/5: rails.runner's fork, messages, settle and receipt-sealing wiring).

Structurally ``tests/unit/test_stage3_supply_variant_interleaving.py``'s own live-harness section
(section 5, "The live graph") twin, over ``roles.perception.branches`` instead of
``roles.solver.supply_variants``: the SAME ``_ActualEpisodeHarness`` fake llama-server-shaped
transport, driving the REAL ``rails.runner._invoke_native_role_episode`` graph end to end, with a
fake ``perception_branch_seeds`` mapping in place of a real knowledge-store router (mirroring how
the VAR2 tests fake ``supply_variant_for_phase`` instead of loading a real store).

Zero model, real server, GPU or network contact: ``_ActualEpisodeHarness`` dials a local fake HTTP
process whose every response is composed by this test's own ``_branch_output`` callback.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_perception_branch_receipt,
)
from speech_aware_evidence_acquisition.rails.supply_variants import (
    PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    parse_perception_branches,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import ACTIONS, PHASES, _ActualEpisodeHarness

FIT = {
    "slot_tokens": 24576,
    "completion_ceiling": 640,
    "base_prompt_tokens": 9600,
    "tokens_per_supplied_item": 120,
}
#: A value id already resolvable in the harness's own default (synthetic) snapshot -- the SAME id
#: test_stage3_supply_variant_interleaving.py's own live tests already render successfully.
SEED_VALUE = "value:dim-light"


def _perception_group(level=1):
    return parse_perception_branches(
        {
            "level": level,
            "fit_estimate": dict(FIT),
            "branches": [
                {
                    "branch_id": "B", "max_supplied_items": 4,
                    "overrides": {"knowledge_stores.train-exemplars.phase_supply.perception.k": 30},
                },
                {"branch_id": "T", "replicate_of": "A", "max_supplied_items": 4},
                {"branch_id": "A", "deliver": True, "max_supplied_items": 4},
            ],
        },
        first_phase_id="perception",
        declared_stores=("train-exemplars",),
    )


def _perception_live_config(*, group, max_contacts):
    """The review-off shape (Reviewer/Planner 0) with a branched Perception."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-perception-branch-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            NativeEpisodeRole(
                phase_id=phase,
                role_kind=phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                tool_names=(),
                perception_branches=(group if phase == "perception" else None),
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _branch_output(key):
    """Perception's own output varies by TURN (one text per branch); every other phase keeps the
    VAR2 harness's own convention (one text per visit)."""

    sample_id, phase, visit, turn = key
    if phase == "perception":
        return f"perception-branch-turn-{turn}:{sample_id}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_three_branch_visit_spends_three_contacts_and_delivers_branch_as_own_text(tmp_path):
    group = _perception_group()
    # Perception (3 branches) + Solver 1 visit = 4.
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4, planner_actions=(),
    )
    harness.config = _perception_live_config(group=group, max_contacts=4)
    sample_id = harness.samples[0].sample_id
    harness.perception_branch_seeds = {"B": {sample_id: (SEED_VALUE,)}}
    harness._output = _branch_output
    try:
        summary = harness.run()
    finally:
        harness.close()

    result = summary.results[0]
    # Branches B, T, A (3) plus the ordinary Solver visit (1).
    assert len(result.contacts) == 4

    receipt = result.native_episode_receipt["perception_branches"]
    assert receipt["schema"] == PERCEPTION_BRANCH_RECEIPT_SCHEMA
    assert receipt["level"] == 1
    assert receipt["delivered_branch_id"] == "A"
    assert [row["branch_id"] for row in receipt["branches"]] == ["B", "T", "A"]
    assert receipt["branches"][0]["supplied_value_ids"] == [SEED_VALUE]
    assert receipt["branches"][1]["supplied_value_ids"] == []
    assert receipt["branches"][2]["supplied_value_ids"] == []
    assert len({row["contact_id"] for row in receipt["branches"]}) == 3
    validate_perception_branch_receipt(
        receipt, branch_ids=group.branch_ids,
        delivered_branch_id=group.delivering_branch.branch_id,
        twin_branch_id=group.twin_branch.branch_id, phase_id="perception",
        level=group.level,
    )

    # ONE Perception state registered for the whole visit -- A's own text,
    # never B's or T's.
    perception_states = [
        state for state in result.agent_states if state.state_kind == "phase:perception"
    ]
    assert len(perception_states) == 1
    assert perception_states[0].content == f"perception-branch-turn-3:{sample_id}"
    assert "perception-branch-turn-1" not in perception_states[0].content
    assert "perception-branch-turn-2" not in perception_states[0].content

    # ONE wave for the whole branch group, naming all three contacts as
    # alternatives of one another -- exactly the shape run_perception_branch_arms
    # assembles (design section 3).
    waves = [wave.as_json() for wave in result.waves]
    assert waves[0]["fanout_semantics"] == "action_alternatives"
    assert waves[0]["batch_id"].endswith(":branches")
    assert len(waves[0]["contact_plans"]) == 3
    assert len({
        plan["query_state_sha256"] for plan in waves[0]["contact_plans"]
    }) == 1


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_non_a_branch_text_never_reaches_the_solvers_own_history(tmp_path):
    """AT-P3's live half: mutating a non-A branch's own output must never change what the
    downstream Solver actually sees."""

    group = _perception_group()
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4, planner_actions=(),
    )
    harness.config = _perception_live_config(group=group, max_contacts=4)
    sample_id = harness.samples[0].sample_id
    harness.perception_branch_seeds = {"B": {sample_id: (SEED_VALUE,)}}

    def output(key):
        _sample_id, phase, _visit, turn = key
        if phase == "perception":
            return "MUTATED-NON-A-NOTE" if turn in (1, 2) else f"a-own-answer:{sample_id}"
        return f"{phase}-analysis:{sample_id}:visit:{key[2]}"

    harness._output = output
    try:
        harness.run()
    finally:
        harness.close()

    requests = [
        payload["payload"]
        for channel, _record_id, payload in harness.trace.records
        if channel == "MODEL_REQUEST"
    ]
    # Perception's 3 branches, then the Solver's own single contact.
    assert len(requests) == 4
    solver_request = requests[-1]
    history_text = "\n".join(
        part.get("text", "") for turn in solver_request["history"]
        for part in (turn.get("content") if isinstance(turn.get("content"), list) else [])
        if isinstance(part, dict)
    )
    assert "MUTATED-NON-A-NOTE" not in history_text
    assert "MUTATED-NON-A-NOTE" not in json_dump_safe(solver_request)


def json_dump_safe(payload) -> str:
    import json

    return json.dumps(payload, default=str)
