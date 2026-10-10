"""Level-2 Perception-branch Solver render defect (2026-10-09): a branch's own first-visit Solver
contact must RENDER its own note and the supply that note implies.

The defect (docs/readiness/2026-10-09-slurp-psv-level2-render-defect-v1.md): ``rails.runner``
built the branch Solver's messages over a note-swapped view but read the exposed history
(``agent_state``), the role/node context compilers and the Solver-phase supply from the ROW's own
context, which carries A's note and A's supply. Every level-2 branch column flown in P-SV-1..4 was
therefore an A/A replicate of A's Solver request.

Model-free: the same ``_ActualEpisodeHarness`` fake transport the supply-variant and
template-variant live proofs use, a multi-row walk through the production graph, with a fake
Solver-phase supply that is a pure function of the Perception note it reads.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict

import pytest

import test_native_episode_runner as harness_module
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness
from test_perception_branch_live import _perception_group, _perception_live_config
from test_perception_branch_presentation_live import VALUE_X, VALUE_Y, _intent_snapshot
from test_rails_controllers import _phase_supply

from dataclasses import replace

ROWS = 2  # the shared fake world (test_rails_frozen_core_client._World) holds two rows


def _note_values(note: str) -> tuple[str, ...]:
    """The fake Solver-phase supply: a pure function of the Perception note."""

    return (VALUE_X,) if "alpha" in note else (VALUE_Y,)


def _assert_view_binds_its_own_note(context):
    """The branch artifact the runner hands the binding must satisfy its own binding: run the
    REAL hypothesis parser over it. The fake notes are not hypothesis documents, so only the
    source-response SHA-256 refusal is a failure here (it is the first check, before content)."""

    from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
        SlurpIntentHypothesisError, parse_slurp_intent_hypothesis_state,
    )

    artifact = [
        s for s in context.agent_states if s.state_kind == "phase:perception"
    ][-1]
    assert artifact.source_response_sha256 == hashlib.sha256(
        artifact.content.encode("utf-8")
    ).hexdigest()
    try:
        parse_slurp_intent_hypothesis_state(
            artifact, expected_sample_id=context.sample_id,
            legal_intent_ids={"x"}, max_candidates=1,
        )
    except SlurpIntentHypothesisError as error:
        assert "source response SHA-256" not in str(error), error



def _rebound(state, content):
    """The defect's history re-read: A's note, bound to its own bytes as A's sealed state is."""

    return replace(
        state, content=content,
        source_response_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )



def _perception_note(context) -> str:
    return [
        state for state in context.agent_states if state.state_kind == "phase:perception"
    ][-1].content


def _output(key):
    sample_id, phase, visit, turn = key
    if phase == "perception":
        # Branch order B, T, A -> turns 1, 2, 3. B's note differs from A's; T repeats A's.
        return f"beta-note:{sample_id}" if turn == 1 else f"alpha-note:{sample_id}"
    if phase == "solver":
        return f"solver-answer:{sample_id}:{turn}"
    return f"{phase}-analysis:{sample_id}:visit:{visit}"


def _history_text(request) -> str:
    # The history is structured, so compare the serialised history plus supplied evidence: a
    # note present on the wire is found (a history-only scan would be vacuous).
    return json.dumps(
        {
            # Only the sealed-state entries, without the ids that name a contact or a branch position.
            "states": [
                {key: h[key] for key in ("state_kind", "content", "content_sha256")}
                for h in request["history"] if "state_kind" in h
            ],
            "supplied_evidence": request["supplied_evidence"],
        },
        default=str, sort_keys=True,
    )


def _build(tmp_path, monkeypatch, *, branched=True, resolver="own-note"):
    group = _perception_group(level=2) if branched else None
    contacts = 6 if branched else 2
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=ROWS, max_revisions=0, max_contacts=contacts, planner_actions=(),
    )
    # Review-off shape; ``group=None`` is the unbranched control.
    harness.config = _perception_live_config(group=group, max_contacts=contacts)
    harness.program = replace(
        harness.program,
        phases=tuple(
            replace(phase, knowledge="supplied") if phase.name == "solver" else phase
            for phase in harness.program.phases
        ),
    )

    def supply(phase, context):
        if phase != "solver":
            return None
        return _phase_supply(
            context, value_ids=_note_values(_perception_note(context)),
            facet_ids=("operation:dim",),
        )

    def branch_supply(*, branch_id, phase_id, context):
        assert phase_id == "solver"
        _assert_view_binds_its_own_note(context)
        if resolver == "a-supply":
            # The defect's supply: the delivering note's, whatever the branch's own note says.
            note = "alpha-note"
        else:
            note = _perception_note(context)
        return _phase_supply(
            context, value_ids=_note_values(note), facet_ids=("operation:dim",),
        )

    real_binding = harness_module.NativeEpisodeRunBinding

    def bind(**kwargs):
        extra = {"supply_for_phase": supply}
        if branched:
            extra["perception_branch_solver_supply"] = branch_supply
        return real_binding(**kwargs, **extra)

    monkeypatch.setattr(harness_module, "NativeEpisodeRunBinding", bind)
    if branched:
        harness.perception_branch_seeds = {
            "B": {sample.sample_id: (VALUE_X,) for sample in harness.samples},
        }
    harness._output = _output
    return group, harness


def _solver_requests_by_row(harness):
    by_row = defaultdict(list)
    for channel, _record_id, payload in harness.trace.records:
        if channel != "MODEL_REQUEST":
            continue
        request = payload["payload"]
        by_row[request["sample_id"]].append(request)
    return by_row


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_branch_solver_renders_its_own_note_and_supply_and_twin_equals_a(tmp_path, monkeypatch):
    group, harness = _build(tmp_path, monkeypatch)
    try:
        summary = harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()
    assert len(summary.results) == ROWS
    by_row = _solver_requests_by_row(harness)
    assert len(by_row) == ROWS
    for result in summary.results:
        sample_id = result.sample_id
        requests = by_row[sample_id]
        # Perception B, T, A then the Solver's B, T, A.
        assert len(requests) == 6
        b_request, t_request, a_request = requests[3:]
        b_ids = [item["evidence_id"] for item in b_request["supplied_evidence"]]
        a_ids = [item["evidence_id"] for item in a_request["supplied_evidence"]]
        # B's Solver carries B's own note in its history and the supply that note implies.
        assert f"beta-note:{sample_id}" in _history_text(b_request)
        assert f"alpha-note:{sample_id}" not in _history_text(b_request)
        assert b_ids == [VALUE_Y]
        # A's Solver is the ordinary construction: A's own note and A's own supply.
        assert a_ids == [VALUE_X]
        assert f"beta-note:{sample_id}" not in _history_text(a_request)
        # The twin repeats A's request on every field the AT2 proof compares.
        for field in (
            "decoding_params", "task_instruction", "tool_schemas", "speech_feature_parts",
            "speech_packet_sha256", "query_source", "key_representation_id",
            "matcher_policy_id", "sample_id", "supplied_evidence",
        ):
            assert t_request[field] == a_request[field], field
        # The provenance row names the request's own message id; compare what it hashes.
        assert [p["sha256"] for p in t_request["evidence_provenance"]] == [
            p["sha256"] for p in a_request["evidence_provenance"]
        ]
        assert _history_text(t_request) == _history_text(a_request)
        # The receipt records what each column actually rendered.
        rows = {row["branch_id"]: row for row in result.native_episode_receipt["perception_branches"]["branches"]}
        assert rows["B"]["candidate_supply_value_ids"] == [VALUE_Y]
        assert rows["A"]["candidate_supply_value_ids"] == [VALUE_X]
        assert rows["T"]["candidate_supply_value_ids"] == [VALUE_X]
        # Custody is A's: the row's sealed state and final supply never carry B's.
        assert tuple(result.final_query_state.retrieved_value_ids) == (VALUE_X,)
        perception_states = [s for s in result.agent_states if s.state_kind == "phase:perception"]
        assert [s.content for s in perception_states] == [f"alpha-note:{sample_id}"]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_delivering_column_is_byte_identical_to_the_unbranched_plan_request(tmp_path, monkeypatch):
    _group_, harness = _build(tmp_path / "branched", monkeypatch)
    try:
        branched = harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()
    branched_by_row = _solver_requests_by_row(harness)
    # Unbranched control: same rows, same outputs (A's note), no branch group.
    monkeypatch.undo()
    _none, control = _build(tmp_path / "control", monkeypatch, branched=False)
    control._output = lambda key: (
        f"alpha-note:{key[0]}" if key[1] == "perception"
        else f"solver-answer:{key[0]}:3" if key[1] == "solver"
        else f"{key[1]}-analysis:{key[0]}:visit:{key[2]}"
    )
    try:
        control.run(snapshot=_intent_snapshot())
    finally:
        control.close()
    control_by_row = _solver_requests_by_row(control)
    for result in branched.results:
        a_request = branched_by_row[result.sample_id][-1]
        plan_request = control_by_row[result.sample_id][-1]
        for field in ("supplied_evidence", "decoding_params", "query_source", "sample_id"):
            assert a_request[field] == plan_request[field], field
        assert _history_text(a_request) == _history_text(plan_request)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_a_branch_column_that_replicates_a_is_refused_at_seal_by_name(tmp_path, monkeypatch):
    """The recurrence guard: reproduce the defect (the exposed history read from A's context) and
    require the seal to refuse the row by name."""

    from speech_aware_evidence_acquisition.rails import native_episode_config as config_module

    real_select = config_module.select_native_role_history

    def defective_select(*, role, solver_phase_id, states, local_tool_result_ids):
        # The defect: the history is read from A's note whatever view was handed in.
        states = tuple(
            _rebound(state, state.content.replace("beta-note", "alpha-note"))
            if state.state_kind == "phase:perception" else state
            for state in states
        )
        return real_select(
            role=role, solver_phase_id=solver_phase_id, states=states,
            local_tool_result_ids=local_tool_result_ids,
        )

    monkeypatch.setattr(config_module, "select_native_role_history", defective_select)
    _group_, harness = _build(tmp_path, monkeypatch, resolver="a-supply")
    try:
        with pytest.raises(Exception, match="replicated branch A's rendered request"):
            harness.run(snapshot=_intent_snapshot())
    finally:
        harness.close()
