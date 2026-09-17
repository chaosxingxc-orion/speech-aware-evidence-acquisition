"""E2b (SLURP v2 base program M2 live wiring): grouped Solver sampling
through the actual shared rails.runner episode invocation -- no network or
model.

Complements ``test_native_group_solver.py`` (the pure aggregation function)
and the graph-level tests added to ``test_ojw_native_episode.py``
(``GroupedSolverRoleNode`` at the "solver" graph position) with the full
contact-counting, cost/FIT and outputs-row proof this program's live wiring
adds: ``rails.runner._invoke_native_role_episode`` building a Solver
``contact_context`` provider that tags ``sample_index``, constructing
``MeteredNativeSpeechRequest(solver_role_id=..., solver_sampling=...)``, and
wrapping the Solver ``NativeRoleNode`` in a ``GroupedSolverRoleNode`` in
place of the plain node -- through the SAME ``_ActualEpisodeHarness`` fake
transport ``test_native_episode_runner.py`` already uses.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.native_commit_replay import replay_row
from speech_aware_evidence_acquisition.core.base import COMMIT_POLICIES
from speech_aware_evidence_acquisition.rails import commit_policies as _commit_policies  # noqa: F401
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeConfig,
    NativeEpisodeRole,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_solver_group_receipt,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

# pytest module-scoped autouse fixture (spawns the fake llama-server-shaped
# process the transport dials): must be IMPORTED into this module's own
# namespace, exactly as test_native_episode_runner.py itself does, or
# _base_url() reads an empty _live dict. Not called directly here.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import (
    ACTIONS,
    PHASES,
    _ActualEpisodeHarness,
    _review_off_config,
)

ANSWERS = [
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six am"}]},
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six a m"}]},
    {"scenario": "alarm", "action": "cancel", "entities": []},
]
DECODING_OVERRIDES = {"temperature": 0.7, "seed_offset": 0}
# min_support 3: the intent plurality (2 "set" vs 1 "cancel") still wins,
# but the "six am"/"six a m" entity cluster (support 2) is dropped -- the
# replay test below recovers it at min_support 2 over the SAME sealed data.
COMMIT = {
    "policy": "saea-commit-plurality-support-v1",
    "min_support": 3,
    "similarity_threshold": 0.8,
}


def _grouped_output(key):
    """Solver visits get one of ANSWERS per grouped sample (indexed by
    ``turn``, the harness's own 1-based within-visit contact counter);
    every other phase keeps ``_ActualEpisodeHarness``'s own scripted shape."""

    sample_id, phase, visit, turn = key
    if phase == "solver":
        return json.dumps(ANSWERS[turn - 1], ensure_ascii=False, sort_keys=True)
    if phase == "planner":
        return "ACCEPT"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _grouped_role(phase, *, max_iterations, samples, decoding_overrides, commit):
    return NativeEpisodeRole(
        phase_id=phase,
        role_kind=phase,
        max_iterations=max_iterations,
        tool_names=(),
        samples=(samples if phase == "solver" else 1),
        decoding_overrides=(decoding_overrides if phase == "solver" else None),
        commit=(commit if phase == "solver" else None),
    )


def _grouped_review_off_config(*, max_contacts, samples, decoding_overrides, commit):
    """The E1 review-off shape (reviewer/planner max_iterations 0) with a
    grouped Solver role."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            _grouped_role(
                phase,
                max_iterations=0 if phase in {"reviewer", "planner"} else 1,
                samples=samples, decoding_overrides=decoding_overrides, commit=commit,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _grouped_review_revise_config(
    *, max_contacts, samples, decoding_overrides, commit, max_revisions,
):
    """Cell B2 on the sealed ANCHOR: the review-loop-ON graph WITH a revision
    allowance, so a Planner REVISE routes back to the grouped Solver node and
    the whole five-sample visit runs again."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=max_revisions,
        actions=ACTIONS,
        roles=tuple(
            _grouped_role(
                phase, max_iterations=1,
                samples=samples, decoding_overrides=decoding_overrides, commit=commit,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


def _grouped_review_loop_config(*, max_contacts, samples, decoding_overrides, commit):
    """The ordinary review-loop-on shape (every role visited once) with a
    grouped Solver role."""

    return NativeEpisodeConfig(
        episode_id="native-role-runner-proof-v1",
        max_revisions=0,
        actions=ACTIONS,
        roles=tuple(
            _grouped_role(
                phase, max_iterations=1,
                samples=samples, decoding_overrides=decoding_overrides, commit=commit,
            )
            for phase in PHASES
        ),
        max_contacts=max_contacts,
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_grouped_solver_review_off_makes_exactly_one_plus_n_contacts(tmp_path):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4, planner_actions=(),
    )
    harness.config = _grouped_review_off_config(
        max_contacts=4, samples=3, decoding_overrides=DECODING_OVERRIDES, commit=COMMIT,
    )
    harness._output = _grouped_output
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    # 1 Perception contact + 3 grouped Solver samples = 4; the shared cost
    # accounting (client.close()'s own request_count) counts every real
    # dispatch, not the graph's own visit count.
    assert close_summary["request_count"] == 4
    result = summary.results[0]
    assert len(result.contacts) == 4

    assert result.solver_group is not None
    validate_solver_group_receipt(result.solver_group, samples=3)
    assert [record["sample_index"] for record in result.solver_group["samples"]] == [0, 1, 2]
    assert len({record["seed"] for record in result.solver_group["samples"]}) == 3
    assert {record["temperature"] for record in result.solver_group["samples"]} == {0.7}
    assert result.solver_group["delivered"]["intent_support"] == 2
    assert result.solver_group["commit_policy_id"] == "saea-commit-plurality-support-v1"

    # native_episode_receipt is unaffected: solver_group is a SIBLING field.
    receipt = result.native_episode_receipt
    assert "solver_group" not in receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == ["perception", "solver"]

    # The delivered text is the COMMIT policy's aggregated answer, not any
    # one raw sample's response text (min_support 3 drops the 2-of-3 entity
    # cluster; the intent plurality still wins 2 "set" votes to 1 "cancel").
    payload = json.loads(result.final_response_text)
    assert (payload["scenario"], payload["action"]) == ("alarm", "set")
    assert payload["entities"] == []
    # This is exactly what a real Solver contact's raw text looks like too
    # (parse_slu_response-compatible), so the scorer parses it unchanged.
    assert set(payload) == {"scenario", "action", "entities"}

    # core.flight.runtime seals solver_group as a top-level sibling of
    # native_episode_receipt in the run's outputs rows (AgentLoopResult.
    # as_json() carries both under the SAME contract this row mirrors).
    row = {
        "sample_id": result.sample_id,
        "final_response_text": result.final_response_text,
        "native_episode_receipt": dict(receipt),
        "solver_group": dict(result.solver_group),
    }

    # analysis.native_commit_replay reads this exact sealed shape (E2, item
    # 5) and reproduces the SAME delivered answer under the SAME parameters,
    # zero model contact.
    policy = COMMIT_POLICIES.resolve("saea-commit-plurality-support-v1")
    same_params = replay_row(
        row, policy=policy, commit_params={"min_support": 3, "similarity_threshold": 0.8},
    )
    assert json.loads(same_params["final_response_text"]) == payload
    assert same_params["replayed_intent_support"] == 2

    # ...and CHANGES it at min_support 2: the "six am"/"six a m" cluster
    # (support 2) now clears the bar.
    relaxed = replay_row(
        row, policy=policy, commit_params={"min_support": 2, "similarity_threshold": 0.8},
    )
    relaxed_payload = json.loads(relaxed["final_response_text"])
    assert (relaxed_payload["scenario"], relaxed_payload["action"]) == ("alarm", "set")
    assert len(relaxed_payload["entities"]) == 1
    assert relaxed_payload["entities"][0]["type"] == "time"
    assert relaxed_payload["entities"][0]["filler"] in {"six am", "six a m"}
    assert relaxed_payload != payload


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_grouped_solver_review_loop_on_makes_one_plus_n_plus_reviewer_plus_planner_contacts(
    tmp_path,
):
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=6,
        planner_actions=("ACCEPT",),
    )
    harness.config = _grouped_review_loop_config(
        max_contacts=6, samples=3, decoding_overrides=DECODING_OVERRIDES, commit=COMMIT,
    )
    harness._output = _grouped_output
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    # Perception 1 + Solver group 3 + Reviewer 1 + Planner 1 = 6.
    assert close_summary["request_count"] == 6
    result = summary.results[0]
    assert len(result.contacts) == 6
    validate_solver_group_receipt(result.solver_group, samples=3)
    receipt = result.native_episode_receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    assert receipt["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"}
    ]
    # Reviewer and Planner are each VISITED once per round whatever N is: the
    # grouped Solver visit is one graph node, so it advances the graph once.
    # What they READ is a different question, and the answer is the N raw
    # samples -- see
    # test_grouped_solver_revise_resamples_and_the_reviewer_reads_every_raw_sample
    # below, which renders the actual Reviewer request.
    assert harness.material_visits[("s1", "reviewer")] == 1
    assert harness.material_visits[("s1", "planner")] == 1


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_samples_one_solver_is_byte_identical_to_the_pre_e2b_shape(tmp_path):
    """Regression (E2b deliverable g): a samples-1 (the historical default,
    and every config before this program) Solver role produces no
    solver_group, no sample_index binding and no contact-count change --
    this is exactly ``test_review_loop_off_runs_exactly_two_contacts_and_
    skips_by_configuration``'s own fixture, plus the new field's absence."""

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=2, planner_actions=(),
    )
    harness.config = _review_off_config(max_contacts=2)
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 2
    result = summary.results[0]
    assert len(result.contacts) == 2
    assert result.final_response_text == "solver-answer:s1:visit:1"
    assert result.solver_group is None
    assert "solver_group" not in result.as_json()

@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_grouped_solver_revise_resamples_and_the_reviewer_reads_every_raw_sample(
    tmp_path,
):
    """Cell B2 re-based on the sealed dual-store ANCHOR (2026-09-17): what the
    review-loop-ON graph actually does around a grouped Solver visit.

    Two facts, both proved here through the same fake transport, because the
    re-based registration's one-factor statement depends on them:

    1. A Planner REVISE routes back to the grouped Solver node, so the WHOLE
       N-sample visit runs again: two Solver visits cost 2*N contacts, not
       N + 1. The graph ceiling for this fixture is
       ``1 + (1+1)*(1*3 + 1 + 1) = 11``, the same formula
       ``rails.native_episode_config`` resolves to 19 for the registered cell
       (samples 5, reviewer 3, planner 1, max_revisions 1).

    2. The Reviewer and the Planner read **every raw sample**, not the
       committed answer. Agent states are registered per CONTACT by the shared
       metered request path, so one grouped Solver visit leaves N separate
       ``kind=phase:solver`` states in the episode history; the commit policy's
       aggregate is the grouped node's ``actor_output`` -- the DELIVERED answer
       -- and never a history state. This is the opposite of what the
       review-off base made it easy to assume, and it is registered as a known
       request difference rather than changed here: suppressing or replacing
       per-contact states is a production change that owes its own engineering
       item.
    """

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=1, max_contacts=11,
        planner_actions=("REVISE", "ACCEPT"),
    )
    harness.config = _grouped_review_revise_config(
        max_contacts=11, samples=3, decoding_overrides=DECODING_OVERRIDES,
        commit=COMMIT, max_revisions=1,
    )

    def _revise_then_accept(key):
        """``_grouped_output`` with the Planner routing REVISE on its first
        visit and ACCEPT on its second."""

        _sample_id, phase, visit, _turn = key
        if phase == "planner":
            return "REVISE" if visit == 1 else "ACCEPT"
        return _grouped_output(key)

    harness._output = _revise_then_accept
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    # Perception 1 + (Solver group 3 + Reviewer 1 + Planner 1) twice = 11.
    assert close_summary["request_count"] == 11
    result = summary.results[0]
    assert len(result.contacts) == 11
    receipt = result.native_episode_receipt
    assert [visit["stage"] for visit in receipt["role_visits"]] == [
        "perception", "solver", "review", "planner",
        "solver", "review", "planner",
    ]
    assert [route["action"] for route in receipt["planner_routes"]] == ["REVISE", "ACCEPT"]

    # (1) The REVISE route re-sampled the WHOLE group: two Solver visits, each
    # of three real contacts, and the Reviewer/Planner one contact per visit.
    assert harness.material_visits[("s1", "solver")] == 2
    assert harness.material_visits[("s1", "reviewer")] == 2
    assert harness.material_visits[("s1", "planner")] == 2
    solver_contacts = sorted(key for key in harness.dispatched if key[1] == "solver")
    assert solver_contacts == [
        ("s1", "solver", 1, 1), ("s1", "solver", 1, 2), ("s1", "solver", 1, 3),
        ("s1", "solver", 2, 1), ("s1", "solver", 2, 2), ("s1", "solver", 2, 3),
    ]

    # The sealed custody belongs to the DELIVERED (second) Solver visit and
    # carries all three of its raw samples with three distinct seeds.
    validate_solver_group_receipt(result.solver_group, samples=3)
    assert [record["sample_index"] for record in result.solver_group["samples"]] == [0, 1, 2]
    assert len({record["seed"] for record in result.solver_group["samples"]}) == 3

    # (2) The first round's Reviewer and Planner requests carry ONE
    # ``kind=phase:solver`` agent state PER SAMPLE, each holding that sample's
    # own raw text -- and no state holding the committed aggregate.
    committed = json.dumps(
        {"scenario": "alarm", "action": "set", "entities": []},
        ensure_ascii=False, sort_keys=True,
    )
    raw_sample_texts = [
        json.dumps(answer, ensure_ascii=False, sort_keys=True) for answer in ANSWERS
    ]
    assert committed not in raw_sample_texts
    for phase in ("reviewer", "planner"):
        parts = [
            part["text"]
            for message in harness.prepared[("s1", phase, 1, 1)]["rendered"]["messages"]
            for part in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if part.get("type") == "text"
        ]
        solver_states = [text for text in parts if "kind=phase:solver]" in text]
        assert len(solver_states) == 3
        for text, raw in zip(solver_states, raw_sample_texts, strict=True):
            assert text.endswith(raw)
        assert not any(text.endswith(committed) for text in parts)

    # The DELIVERED answer is still the second visit's committed aggregate, in
    # the same parse_slu_response-compatible shape: the commit policy governs
    # delivery even though it does not govern what the next role reads.
    assert result.final_response_text == committed
    payload = json.loads(result.final_response_text)
    assert (payload["scenario"], payload["action"]) == ("alarm", "set")
    assert payload["entities"] == []
