"""``rails.phase_review`` and the Reviewer seam on
``rails.controllers.EvidenceAgentController`` (owner Decision 11-B change #1
/ 11-C, 2026-09-08).

Three things are proved here, and the first is the one that matters most:

1. **Byte identity.** A controller built without ``review_for_phase`` is
   today's controller, and a controller built WITH one sends exactly the same
   bytes -- same contact, same instruction, same transition, same successor
   ``QueryState`` hash. The Reviewer criticises; it does not steer.
2. **Fail-closed config.** ``phase_review`` is parsed against the program the
   way ``phase_supply`` is, and ``on_flag: "loop"`` is refused BY NAME with
   the two ``rails.runner`` rails that would have to move first.
3. **Traced verdicts.** Every reviewed row lands one ``REVIEW`` trace record,
   hashed like every other record, and the run outcome carries the flag
   counts per judge.

No model, no GPU, no network: every test drives the controller directly with
a synthetic ``AgentRuntimeContext``.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import TraceRecord
from speech_aware_evidence_acquisition.core import judges as cj
from speech_aware_evidence_acquisition.core.base import (
    JUDGES,
    JudgeFlag,
    JudgeVerdict,
)
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import phase_review as pr
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext

_SHA_A = "a" * 64
_SHA_B = "b" * 64

_NUMERIC = cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1
_ALIGNMENT = cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1


def _query_state(*, sample_id: str = "s1", loop_step: int = 0, agent_state_ids=()) -> QueryState:
    return QueryState(
        query_id=f"run:{sample_id}:step{loop_step}",
        query_sample_id=sample_id,
        speech_packet_id=f"speech/{sample_id}",
        speech_packet_sha256=_SHA_A,
        use_split_identity_hash=_SHA_A,
        loop_step=loop_step,
        agent_state_ids=agent_state_ids,
    ).validate()


def _context(query_state: QueryState, *, contact_index: int = 0, agent_states=()) -> AgentRuntimeContext:
    return AgentRuntimeContext(
        sample_id=query_state.query_sample_id,
        knowledge_snapshot_sha256=_SHA_B,
        catalog_facet_ids=(),
        catalog_value_ids=(),
        query_state=query_state,
        task_contract="fake task contract",
        agent_states=agent_states,
        prior_response_sha256s=(),
        contact_index=contact_index,
    )


def _material_for_phase(name, ctx):
    return PhaseMaterial(
        instruction=f"Do {name} for {ctx.sample_id}",
        response_format=None,
        contact_id=f"c-{name}-{ctx.sample_id}",
        purpose=name,
    )


def _run_two_phases(controller, *, sample_id="s1", responses=("draft answer", "revised answer")):
    qs0 = _query_state(sample_id=sample_id)
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    advance0 = controller.advance(ctx0, contact0, responses[0])
    contact1 = advance0.next_contact
    ctx1 = _context(
        advance0.next_query_state, contact_index=1, agent_states=advance0.new_agent_states
    )
    advance1 = controller.advance(ctx1, contact1, responses[1])
    return contact0, advance0, contact1, advance1


def _advance_fingerprint(contact, advance) -> str:
    """Everything a wave puts on the wire or in the trace, as one string."""

    return json.dumps(
        {
            "contact": contact.as_json(),
            "transition": advance.transition.as_json(),
            "next_query_state": (
                None
                if advance.next_query_state is None
                else advance.next_query_state.content_hash()
            ),
            "next_contact": (
                None if advance.next_contact is None else advance.next_contact.as_json()
            ),
            "new_agent_states": [
                artifact.as_json() for artifact in advance.new_agent_states
            ],
            "final_response_contact_id": advance.final_response_contact_id,
        },
        sort_keys=True,
    )


# ---------------------------------------------------------------------------
# 1. Config: parsed against the program, fail-closed, like phase_supply.
# ---------------------------------------------------------------------------


def _program():
    return rc.default_phase_program("phase-draft-revise-v1")


def test_absent_or_empty_phase_review_reviews_nothing():
    program = _program()
    assert pr.load_phase_review_specs({}, program) == {}
    assert pr.load_phase_review_specs({"phase_review": {}}, program) == {}
    assert pr.load_phase_review_specs({"phase_review": None}, program) == {}


def test_a_declared_block_resolves_its_judges_and_defaults_on_flag_to_record():
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )
    assert list(specs) == ["draft"]
    assert specs["draft"].judges == (_NUMERIC,)
    assert specs["draft"].on_flag == pr.DEFAULT_ON_FLAG == "record"
    rendered = specs["draft"].as_json()
    assert rendered["judge_versions"][_NUMERIC] == JUDGES.resolve(_NUMERIC).version


@pytest.mark.parametrize(
    ("block", "match"),
    [
        ("not-an-object", "must be an object keyed by phase name"),
        ({"ghost": {"judges": [_NUMERIC]}}, "does not declare"),
        ({"draft": "not-an-object"}, "must be an object"),
        ({"draft": {"judges": [_NUMERIC], "nope": 1}}, "unknown key"),
        ({"draft": {"judges": []}}, "non-empty list"),
        ({"draft": {"judges": _NUMERIC}}, "must be a list"),
        ({"draft": {"judges": [_NUMERIC, _NUMERIC]}}, "repeats"),
        ({"draft": {"judges": ["ghost-judge"]}}, "unknown judge"),
        ({"draft": {"judges": [_NUMERIC], "on_flag": "shout"}}, "on_flag must be one of"),
        (
            {"draft": {"judges": [_NUMERIC], "params": {"other-judge": {}}}},
            "does not review",
        ),
        (
            {"draft": {"judges": [_NUMERIC], "params": {_NUMERIC: "not-an-object"}}},
            "must be an object",
        ),
    ],
)
def test_a_malformed_phase_review_block_is_refused(block, match):
    with pytest.raises(pr.PhaseReviewError, match=match):
        pr.load_phase_review_specs({"phase_review": block}, _program())


def test_on_flag_loop_is_refused_by_name_with_the_two_runner_rails_that_block_it():
    with pytest.raises(pr.PhaseReviewError) as error:
        pr.load_phase_review_specs(
            {"phase_review": {"draft": {"judges": [_NUMERIC], "on_flag": "loop"}}},
            _program(),
        )
    message = str(error.value)
    assert "_validate_new_agent_states" in message
    assert "schedule_wave" in message
    assert pr.LOOP_REFUSAL_REASON in message


def test_build_review_for_phase_returns_none_when_nothing_is_reviewed():
    assert pr.build_review_for_phase({}) is None


# ---------------------------------------------------------------------------
# 2. Byte identity: the default is today's behaviour, and so is a review.
# ---------------------------------------------------------------------------


def test_the_default_controller_records_no_verdicts_at_all():
    controller = rc.EvidenceAgentController(
        program=_program(), material_for_phase=_material_for_phase
    )
    _run_two_phases(controller)
    assert controller.review_verdicts == {}


def test_a_reviewed_trajectory_sends_byte_identical_waves_to_an_unreviewed_one():
    """Owner Decision 11-C, as a property of the harness: criticism steers
    nothing, so a judge's admission receipt is one config key against its null
    arm rather than a second code path."""

    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}, "revise": {"judges": [_NUMERIC]}}},
        _program(),
    )
    # A draft carrying a malformed figure, so the judge really does flag.
    responses = ("the figure was 1234.5.6 exactly", "the figure was 1234.5.6 again")

    plain = rc.EvidenceAgentController(
        program=_program(), material_for_phase=_material_for_phase
    )
    plain_waves = _run_two_phases(plain, responses=responses)

    reviewer = pr.build_review_for_phase(specs)
    reviewed = rc.EvidenceAgentController(
        program=_program(),
        material_for_phase=_material_for_phase,
        review_for_phase=reviewer,
    )
    reviewed_waves = _run_two_phases(reviewed, responses=responses)

    assert _advance_fingerprint(plain_waves[0], plain_waves[1]) == _advance_fingerprint(
        reviewed_waves[0], reviewed_waves[1]
    )
    assert _advance_fingerprint(plain_waves[2], plain_waves[3]) == _advance_fingerprint(
        reviewed_waves[2], reviewed_waves[3]
    )
    # ... and the review really happened, on both phases, with real flags.
    assert set(reviewed.review_verdicts) == {"draft", "revise"}
    assert all(
        verdicts[0].flagged for verdicts in reviewed.review_verdicts.values()
    )


# ---------------------------------------------------------------------------
# 3. The seam itself: called once per phase, on the sealed bytes.
# ---------------------------------------------------------------------------


def test_review_is_called_once_per_phase_with_the_sealed_response_and_state():
    seen: list[tuple[str, str, tuple[str, ...], int]] = []

    def review(phase_name, context, response_text):
        seen.append(
            (
                phase_name,
                response_text,
                tuple(state.state_kind for state in context.agent_states),
                context.contact_index,
            )
        )
        return ()

    controller = rc.EvidenceAgentController(
        program=_program(),
        material_for_phase=_material_for_phase,
        review_for_phase=review,
    )
    _run_two_phases(controller, responses=("first", "second"))

    assert seen == [
        ("draft", "first", ("phase:draft",), 0),
        ("revise", "second", ("phase:draft", "phase:revise"), 1),
    ]


def test_the_review_context_carries_the_just_sealed_state_and_the_prior_query_state():
    captured: list[AgentRuntimeContext] = []

    def review(phase_name, context, response_text):
        captured.append(context)
        return ()

    controller = rc.EvidenceAgentController(
        program=_program(),
        material_for_phase=_material_for_phase,
        review_for_phase=review,
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    controller.advance(ctx0, contact0, "first")

    assert captured[0].query_state.content_hash() == qs0.content_hash()
    assert captured[0].agent_states[-1].content == "first"
    assert captured[0].prior_response_sha256s[-1:] != ()


@pytest.mark.parametrize(
    "returned",
    ["a rewritten draft", {"text": "a rewritten draft"}, ["not a verdict"], 7],
)
def test_a_review_that_does_not_return_verdicts_is_refused(returned):
    controller = rc.EvidenceAgentController(
        program=_program(),
        material_for_phase=_material_for_phase,
        review_for_phase=lambda *_: returned,
    )
    qs0 = _query_state()
    ctx0 = _context(qs0)
    contact0 = controller.initial_contact(ctx0)
    with pytest.raises(rc.RailsControllersError, match="JudgeVerdict"):
        controller.advance(ctx0, contact0, "first")


def test_an_uncallable_review_for_phase_is_refused_at_construction():
    with pytest.raises(rc.RailsControllersError, match="review_for_phase"):
        rc.EvidenceAgentController(
            program=_program(),
            material_for_phase=_material_for_phase,
            review_for_phase="not callable",
        )


def test_a_judge_signing_someone_elses_id_is_refused():
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )

    class _Impostor:
        id = _NUMERIC
        version = "0.0.0"
        criticism_only = True

        def __call__(self, draft, material, state):
            return JudgeVerdict(judge_id="someone-else", version="0.0.0")

    reviewer = pr.build_review_for_phase(specs, judges={_NUMERIC: _Impostor()})
    with pytest.raises(pr.PhaseReviewError, match="one identity"):
        reviewer("draft", _context(_query_state()), "anything")


def test_a_judge_returning_something_other_than_a_verdict_is_refused_at_the_seam():
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )

    class _Loud:
        id = _NUMERIC
        version = "0.0.0"
        criticism_only = True

        def __call__(self, draft, material, state):
            return "here is a better answer"

    reviewer = pr.build_review_for_phase(specs, judges={_NUMERIC: _Loud()})
    with pytest.raises(pr.PhaseReviewError, match="never proposes a revision"):
        reviewer("draft", _context(_query_state()), "anything")


def test_config_params_win_over_injected_material_on_a_key_collision():
    specs = pr.load_phase_review_specs(
        {
            "phase_review": {
                "draft": {"judges": [_ALIGNMENT], "params": {_ALIGNMENT: {"max_span_tokens": 2}}}
            }
        },
        _program(),
    )
    seen: list[dict[str, object]] = []

    class _Spy:
        id = _ALIGNMENT
        version = "0.0.0"
        criticism_only = True

        def __call__(self, draft, material, state):
            seen.append(dict(material))
            return JudgeVerdict(judge_id=_ALIGNMENT, version="0.0.0")

    reviewer = pr.build_review_for_phase(
        specs,
        judges={_ALIGNMENT: _Spy()},
        extra_material={"draft": {_ALIGNMENT: {"max_span_tokens": 9, "min_anchor_ratio": 0.5}}},
    )
    reviewer("draft", _context(_query_state()), "anything")
    assert seen == [{"max_span_tokens": 2, "min_anchor_ratio": 0.5}]


def test_the_default_row_state_carries_the_predecessor_text():
    controller_states = ()
    context = _context(_query_state(), agent_states=controller_states)
    state = pr.default_state_for_review("draft", context)
    assert state["predecessor_text"] == ""
    assert state["sample_id"] == "s1"
    assert state["phase"] == "draft"


# ---------------------------------------------------------------------------
# 4. Traced verdicts: one REVIEW record per reviewed row, hashed.
# ---------------------------------------------------------------------------


def _reviewed_run(sample_ids=("s1", "s2")):
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )
    reviewer = pr.build_review_for_phase(specs)
    for sample_id in sample_ids:
        controller = rc.EvidenceAgentController(
            program=_program(),
            material_for_phase=_material_for_phase,
            review_for_phase=reviewer,
        )
        _run_two_phases(
            controller,
            sample_id=sample_id,
            responses=("the figure was 1234.5.6 exactly", "clean"),
        )
    return specs, reviewer


def test_one_review_record_per_reviewed_row_in_sorted_order():
    _specs, reviewer = _reviewed_run(sample_ids=("s2", "s1"))
    sink = TraceBuffer("SAEA-TEST-RUN-V1")
    written = pr.emit_review_records(reviewer, sink)

    assert written == 2
    assert [record_id for _, record_id, _ in sink.records] == [
        "s1/draft/review",
        "s2/draft/review",
    ]
    for channel, _record_id, payload in sink.records:
        assert channel == "REVIEW"
        assert all(key.startswith("review_") for key in payload)


def test_a_review_record_is_a_valid_hashed_trace_record():
    _specs, reviewer = _reviewed_run(sample_ids=("s1",))
    sink = TraceBuffer("SAEA-TEST-RUN-V1")
    pr.emit_review_records(reviewer, sink)

    channel, record_id, payload = sink.records[0]
    digest = TraceRecord(channel=channel, record_id=record_id, payload=payload).content_hash()
    assert len(digest) == 64
    assert payload["review_phase"] == "draft"
    assert payload["review_sample_id"] == "s1"
    assert payload["review_on_flag"] == "record"
    assert payload["review_judge_ids"] == [_NUMERIC]
    assert payload["review_flags_total"] == 1
    assert payload["review_verdicts"][0]["judge_id"] == _NUMERIC
    assert len(payload["review_response_sha256"]) == 64


def test_emit_review_records_writes_nothing_for_an_unreviewed_run():
    sink = TraceBuffer("SAEA-TEST-RUN-V1")
    assert pr.emit_review_records(None, sink) == 0
    assert sink.records == []


def test_a_review_record_cannot_carry_a_replacement_draft():
    _specs, reviewer = _reviewed_run(sample_ids=("s1",))
    sink = TraceBuffer("SAEA-TEST-RUN-V1")
    pr.emit_review_records(reviewer, sink)
    rendered = json.dumps(sink.records[0][2])
    assert "1234.5.6" not in rendered


# ---------------------------------------------------------------------------
# 5. The run-outcome summary.
# ---------------------------------------------------------------------------


def test_the_receipt_summarizes_rows_reviewed_and_flags_per_judge():
    specs, reviewer = _reviewed_run()
    receipt = pr.phase_review_receipt(specs, reviewer)

    assert receipt["schema"] == pr.PHASE_REVIEW_SCHEMA
    assert receipt["criticism_only"] is True
    (phase,) = receipt["phases"]
    assert phase["spec"]["phase"] == "draft"
    assert phase["rows_reviewed"] == 2
    assert phase["rows_flagged"] == 2
    entry = phase["judges"][_NUMERIC]
    assert entry["rows_flagged"] == 2
    assert entry["flags"] == 2
    assert entry["by_severity"] == {"warn": 2}
    assert entry["version"] == JUDGES.resolve(_NUMERIC).version


def test_a_preflight_receipt_exists_before_any_row_is_reviewed():
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )
    receipt = pr.phase_review_receipt(specs)
    (phase,) = receipt["phases"]
    assert phase["rows_reviewed"] == 0
    assert phase["judges"][_NUMERIC]["flags"] == 0


def test_the_receipt_counts_block_and_warn_separately():
    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )

    class _Two:
        id = _NUMERIC
        version = "9.9.9"
        criticism_only = True

        def __call__(self, draft, material, state):
            return JudgeVerdict(
                judge_id=_NUMERIC,
                version=self.version,
                flags=(
                    JudgeFlag(code="a", severity="block", reason="r"),
                    JudgeFlag(code="b", severity="warn", reason="r"),
                ),
            )

    reviewer = pr.build_review_for_phase(specs, judges={_NUMERIC: _Two()})
    reviewer("draft", _context(_query_state()), "anything")
    (phase,) = pr.phase_review_receipt(specs, reviewer)["phases"]
    assert phase["judges"][_NUMERIC]["by_severity"] == {"block": 1, "warn": 1}


# ---------------------------------------------------------------------------
# 6. The flight-runtime guard: a direct arm may not declare a review block.
# ---------------------------------------------------------------------------


def test_a_fixed_policy_arm_declaring_phase_review_is_refused_before_any_contact():
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntime,
        FlightRuntimeError,
    )

    stub = SimpleNamespace(
        _composed=SimpleNamespace(
            values={"phase_review": {"draft": {"judges": [_NUMERIC]}}}
        )
    )
    with pytest.raises(FlightRuntimeError, match="would review nothing"):
        FlightRuntime._assert_phase_review_is_legal_for(stub, "fixed")
    # A phase-program policy is fine, and an unreviewed direct arm too.
    FlightRuntime._assert_phase_review_is_legal_for(stub, "phase-draft-revise-v1")
    FlightRuntime._assert_phase_review_is_legal_for(
        SimpleNamespace(_composed=SimpleNamespace(values={})), "fixed"
    )


# ---------------------------------------------------------------------------
# 7. rails.phase_runner: the seam threads through, and the records are written
#    ONCE, after the wave settles, by whoever owns the sink.
# ---------------------------------------------------------------------------


class _FakeAdapter:
    def serving_geometry(self):
        return {"slots": 3, "slot_tokens": 4096, "max_tokens": 256}


def _drive_solo(registry, policy_id, sample_id, response):
    controller = registry.resolve(policy_id)(sample_id)
    qs = _query_state(sample_id=sample_id)
    ctx = _context(qs)
    contact = controller.initial_contact(ctx)
    controller.advance(ctx, contact, response)
    return controller


def test_run_agent_phase_threads_the_reviewer_and_writes_one_record_per_row():
    from pathlib import Path

    from speech_aware_evidence_acquisition.rails import phase_runner as prn

    specs = pr.load_phase_review_specs(
        {"phase_review": {"draft": {"judges": [_NUMERIC]}}}, _program()
    )
    reviewer = pr.build_review_for_phase(specs)
    sink = TraceBuffer("SAEA-TEST-RUN-V1")

    def fake_runner(**kwargs):
        registry = kwargs["controller_registry"]
        policy_id = kwargs["controller_policy_id"]
        for sample_id in ("s2", "s1"):
            controller = _drive_solo(
                registry, policy_id, sample_id, "the figure was 1234.5.6 exactly"
            )
            assert set(controller.review_verdicts) == {"draft"}
        # Nothing has been written yet: the records are flushed after the wave.
        assert sink.records == []
        return SimpleNamespace(
            agent_executor_id="openjiuwen-workflow-v1",
            results=(
                SimpleNamespace(sample_id="s1", contacts=(object(),)),
                SimpleNamespace(sample_id="s2", contacts=(object(),)),
            ),
        )

    prn.run_agent_phase(
        phase_name="draft",
        program=_program(),
        adapter=_FakeAdapter(),
        plan=SimpleNamespace(),
        data_root=Path("."),
        core_client=SimpleNamespace(),
        split_id="all",
        knowledge_snapshot=SimpleNamespace(),
        speech_packet_bindings={
            "s1": {"packet_id": "speech/s1"},
            "s2": {"packet_id": "speech/s2"},
        },
        trace_sink=sink,
        decoding_params={},
        material_for_phase=_material_for_phase,
        review_for_phase=reviewer,
        agent_runner=fake_runner,
    )

    assert [record_id for _, record_id, _ in sink.records] == [
        "s1/draft/review",
        "s2/draft/review",
    ]


def test_run_agent_phase_refuses_an_uncallable_review_for_phase():
    from pathlib import Path

    from speech_aware_evidence_acquisition.rails import phase_runner as prn

    with pytest.raises(prn.PhaseRunnerError, match="review_for_phase"):
        prn.run_agent_phase(
            phase_name="draft",
            program=_program(),
            adapter=_FakeAdapter(),
            plan=SimpleNamespace(),
            data_root=Path("."),
            core_client=SimpleNamespace(),
            split_id="all",
            knowledge_snapshot=SimpleNamespace(),
            speech_packet_bindings={"s1": {"packet_id": "speech/s1"}},
            trace_sink=TraceBuffer("SAEA-TEST-RUN-V1"),
            decoding_params={},
            material_for_phase=_material_for_phase,
            review_for_phase="not callable",
            agent_runner=lambda **_: None,
        )
