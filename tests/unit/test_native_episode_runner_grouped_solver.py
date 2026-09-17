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

E2c (2026-09-17) adds the COMMIT half: one grouped Solver visit registers
exactly ONE ``phase:solver`` agent state, holding the committed answer, so
the Reviewer and the Planner read one draft exactly as they do on a
samples-1 (anchor) visit, while every raw sample stays in custody.
"""

from __future__ import annotations

import hashlib
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
    # What they READ is the ONE committed draft (E2c) -- see
    # test_grouped_solver_revise_resamples_and_the_reviewer_reads_the_committed_draft
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
def test_grouped_solver_revise_resamples_and_the_reviewer_reads_the_committed_draft(
    tmp_path,
):
    """Cell B2 re-based on the sealed dual-store ANCHOR, with E2c
    (2026-09-17): what the review-loop-ON graph does around a grouped Solver
    visit.

    Two facts, both proved here through the same fake transport, because the
    re-based registration's one-factor statement depends on them:

    1. A Planner REVISE routes back to the grouped Solver node, so the WHOLE
       N-sample visit runs again and RE-COMMITS: two Solver visits cost 2*N
       contacts, not N + 1. The graph ceiling for this fixture is
       ``1 + (1+1)*(1*3 + 1 + 1) = 11``, the same formula
       ``rails.native_episode_config`` resolves to 19 for the registered cell
       (samples 5, reviewer 3, planner 1, max_revisions 1). E2c does not
       touch that formula: the contacts are unchanged, only the ONE state
       they register is.

    2. The Reviewer and the Planner read the **committed draft**, not the N
       raw samples. Module M2 is sample-and-aggregate COMMIT, so the
       committed answer IS the Solver's draft: one grouped Solver visit
       registers exactly ONE ``kind=phase:solver`` state, carrying the commit
       policy's aggregate, in the same wire form a samples-1 (anchor) Solver
       state has. This test is the inverse of the pre-E2c
       ``...reads_every_raw_sample`` it replaces. The raw samples are not
       lost: they stay in custody as their own contacts, in the visit's one
       ``action_alternatives`` wave, and in ``solver_group`` -- proved by
       ``test_grouped_solver_keeps_every_raw_sample_in_custody`` below.
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

    # (2) The first round's Reviewer and Planner requests carry exactly ONE
    # ``kind=phase:solver`` agent state, holding the committed aggregate of
    # that round's group -- and no state holding any raw sample's own text.
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
        assert len(solver_states) == 1
        assert solver_states[0].endswith(committed)
        # Same wire form a samples-1 Solver state has: one
        # ``[agent state <id> kind=phase:solver] <answer>`` block.
        assert solver_states[0].startswith("[agent state ")
        assert not any(
            text.endswith(raw) for text in parts for raw in raw_sample_texts
        )

    # The second round re-samples AND re-commits: its Reviewer reads its own
    # group's committed draft, not the first round's state and not a sample.
    second_round = [
        part["text"]
        for message in harness.prepared[("s1", "reviewer", 2, 1)]["rendered"]["messages"]
        for part in (message["content"] if isinstance(message["content"], list) else [])
        if part.get("type") == "text"
    ]
    second_solver_states = [
        text for text in second_round if "kind=phase:solver]" in text
    ]
    assert len(second_solver_states) == 2
    assert all(text.endswith(committed) for text in second_solver_states)
    assert second_solver_states[0] != second_solver_states[1]

    # The DELIVERED answer is the second visit's committed aggregate, in the
    # same parse_slu_response-compatible shape -- and now it is also exactly
    # the draft that was reviewed.
    assert result.final_response_text == committed
    payload = json.loads(result.final_response_text)
    assert (payload["scenario"], payload["action"]) == ("alarm", "set")
    assert payload["entities"] == []

    # E2c registers ONE Solver state per VISIT: two visits, two states, both
    # committed -- exactly the shape a samples-1 episode of the same graph
    # leaves behind.
    solver_states = [
        state for state in result.agent_states
        if state.state_kind == "phase:solver"
    ]
    assert len(solver_states) == 2
    assert [state.content for state in solver_states] == [committed, committed]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_grouped_solver_keeps_every_raw_sample_in_custody(tmp_path):
    """E2c: registering ONE committed state loses no raw sample.

    Each of the N samples keeps its own contact record and its own metered
    cost; all N appear in the visit's ONE wave as an ``action_alternatives``
    batch with their own response digests; and their sample indices, seeds,
    temperatures, parse status and parsed answers stay in ``solver_group``,
    which is what ``analysis.native_commit_replay`` re-aggregates offline.
    """

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

    assert close_summary["request_count"] == 6
    result = summary.results[0]

    # Per CONTACT: six real contacts, three of them the Solver group's.
    assert len(result.contacts) == 6
    raw_sample_texts = [
        json.dumps(answer, ensure_ascii=False, sort_keys=True) for answer in ANSWERS
    ]

    # Per VISIT: one step. Four waves (perception, the Solver group, reviewer,
    # planner) and five transitions (four plus the terminal stop).
    assert len(result.waves) == 4
    assert len(result.transitions) == 5
    group_waves = [
        wave for wave in result.waves if wave.fanout_semantics == "action_alternatives"
    ]
    assert len(group_waves) == 1
    group_wave = group_waves[0]
    assert len(group_wave.contact_plans) == 3
    assert list(group_wave.response_sha256s) == [
        hashlib.sha256(text.encode("utf-8")).hexdigest() for text in raw_sample_texts
    ]
    # Every sample of the group binds the SAME QueryState: the group takes no
    # step between its samples, so the N sibling requests are independent
    # draws of one draft rather than a chain.
    assert {plan.query_state_sha256 for plan in group_wave.contact_plans} == {
        group_wave.query_state_sha256
    }
    assert len({plan.contact_id for plan in group_wave.contact_plans}) == 3
    assert len(group_wave.transition.new_agent_state_ids) == 1

    # The one registered Solver state is the committed answer.
    committed = json.dumps(
        {"scenario": "alarm", "action": "set", "entities": []},
        ensure_ascii=False, sort_keys=True,
    )
    solver_states = [
        state for state in result.agent_states if state.state_kind == "phase:solver"
    ]
    assert len(solver_states) == 1
    assert solver_states[0].content == committed
    assert solver_states[0].state_id == group_wave.transition.new_agent_state_ids[0]
    # The view seam: the committed content is sealed against REAL model bytes.
    assert solver_states[0].source_response_sha256 == hashlib.sha256(
        raw_sample_texts[-1].encode("utf-8")
    ).hexdigest()

    # The raw samples themselves, in full, in the sealed receipt.
    validate_solver_group_receipt(result.solver_group, samples=3)
    records = result.solver_group["samples"]
    assert [record["sample_index"] for record in records] == [0, 1, 2]
    assert len({record["seed"] for record in records}) == 3
    assert {record["temperature"] for record in records} == {0.7}
    assert [record["parse_status"] for record in records] == ["ok", "ok", "ok"]
    assert [record["parsed_answer"] for record in records] == [
        {
            "scenario": answer["scenario"],
            "action": answer["action"],
            "entities": list(answer["entities"]),
        }
        for answer in ANSWERS
    ]
    assert [
        contact["agent_contact_id"]
        for record in records
        for contact in record["contacts"]
    ] == [plan.contact_id for plan in group_wave.contact_plans]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_samples_one_solver_state_is_the_raw_draft_the_reviewer_reads(tmp_path):
    """E2c regression: the anchor's own configuration is untouched.

    A samples-1 Solver still seals its RAW response as the visit's one
    ``phase:solver`` state, still takes one single-fanout wave per contact,
    and the Reviewer still reads exactly that one raw draft.
    """

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    assert close_summary["request_count"] == 4
    result = summary.results[0]
    assert result.solver_group is None
    assert len(result.contacts) == 4
    assert len(result.waves) == 4
    assert {wave.fanout_semantics for wave in result.waves} == {"single"}
    assert all(len(wave.contact_plans) == 1 for wave in result.waves)

    raw = "solver-answer:s1:visit:1"
    solver_states = [
        state for state in result.agent_states if state.state_kind == "phase:solver"
    ]
    assert [state.content for state in solver_states] == [raw]
    for phase in ("reviewer", "planner"):
        exposed = [
            part["text"]
            for message in harness.prepared[("s1", phase, 1, 1)]["rendered"]["messages"]
            for part in (
                message["content"] if isinstance(message["content"], list) else []
            )
            if part.get("type") == "text" and "kind=phase:solver]" in part["text"]
        ]
        assert len(exposed) == 1
        assert exposed[0].endswith(raw)
