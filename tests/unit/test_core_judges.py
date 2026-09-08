"""``core.judges``: the judges that already existed, registered behind the
``Judge`` protocol (owner Decision 11-B change #2, 2026-09-08).

Every test drives a judge on a SYNTHETIC draft -- no model, no GPU, no
network, no sealed run directory. What is asserted is (a) the judge flags what
the frozen function it wraps already decided, (b) it is stateless and
deterministic, (c) its verdict is criticism only: no flag, reason or field of
any verdict here carries a replacement for what it criticises.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core import judges as cj
from speech_aware_evidence_acquisition.core.base import (
    JUDGES,
    JudgeError,
    JudgeVerdict,
    assert_judge,
)

_ALL_IDS = (
    cj.SLURP_LEGAL_LABEL_JUDGE_V1,
    cj.SLURP_SLOT_SCHEMA_JUDGE_V1,
    cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1,
    cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1,
    cj.REPLAY_LOGPROB_JUDGE_V1,
    cj.ROSTER_BAND_JUDGE_V1,
    cj.E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1,
)

_INVENTORY = {
    "alarm": ["set", "query", "remove"],
    "email": ["query", "sendemail"],
}


def _slu(scenario: str, action: str, entities: list[dict[str, str]] | None = None) -> str:
    return json.dumps(
        {"scenario": scenario, "action": action, "entities": entities or []}
    )


# ---------------------------------------------------------------------------
# 1. Registration: every judge resolves, is identified, and is criticism only.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("judge_id", _ALL_IDS)
def test_every_judge_is_registered_identified_and_criticism_only(judge_id):
    judge = JUDGES.resolve(judge_id)
    assert assert_judge(judge, name=judge_id) is judge
    assert judge.criticism_only is True
    # A receipt-able version: a preregistration and an admission receipt both
    # quote it, so it must be a real, non-empty string.
    assert isinstance(judge.version, str) and judge.version.strip()


def test_the_registered_ids_are_exactly_the_ones_this_module_names():
    assert set(_ALL_IDS) <= set(JUDGES.names())


# ---------------------------------------------------------------------------
# 2. SLURP legal-label judge -- flags an illegal label, never names a legal one.
# ---------------------------------------------------------------------------


def test_legal_label_judge_passes_a_legal_pair():
    judge = JUDGES.resolve(cj.SLURP_LEGAL_LABEL_JUDGE_V1)
    verdict = judge(_slu("alarm", "set"), {"actions_by_scenario": _INVENTORY}, {})
    assert verdict.score == 1.0
    assert verdict.flags == ()


@pytest.mark.parametrize(
    ("draft", "code", "field_ref"),
    [
        ("not json at all", "unparsed_response", "$"),
        (_slu("alarm", ""), "missing_label", "intent"),
        (_slu("weather", "query"), "illegal_scenario", "intent.scenario"),
        (_slu("alarm", "sendemail"), "illegal_action_for_scenario", "intent.action"),
    ],
)
def test_legal_label_judge_flags_each_illegal_shape(draft, code, field_ref):
    judge = JUDGES.resolve(cj.SLURP_LEGAL_LABEL_JUDGE_V1)
    verdict = judge(draft, {"actions_by_scenario": _INVENTORY}, {})
    assert verdict.score == 0.0
    assert [flag.code for flag in verdict.flags] == [code]
    assert verdict.flags[0].field_ref == field_ref
    assert verdict.flags[0].severity == "block"


def test_legal_label_judge_never_names_the_nearest_legal_pair():
    """Decision 11-C: the projection post-processor repairs, the judge does
    not. A flag that named the nearest legal label would be the revision."""

    judge = JUDGES.resolve(cj.SLURP_LEGAL_LABEL_JUDGE_V1)
    verdict = judge(_slu("alarm", "sendemail"), {"actions_by_scenario": _INVENTORY}, {})
    rendered = json.dumps(verdict.as_json())
    for legal_action in ("set", "query", "remove"):
        assert f'"{legal_action}"' not in rendered


def test_legal_label_judge_fails_closed_without_an_inventory():
    judge = JUDGES.resolve(cj.SLURP_LEGAL_LABEL_JUDGE_V1)
    with pytest.raises(JudgeError, match="actions_by_scenario"):
        judge(_slu("alarm", "set"), {}, {})


# ---------------------------------------------------------------------------
# 3. SLURP slot schema judge -- MF-9's definition, verbatim.
# ---------------------------------------------------------------------------


def test_schema_judge_passes_a_frame_inside_its_own_block():
    judge = JUDGES.resolve(cj.SLURP_SLOT_SCHEMA_JUDGE_V1)
    draft = _slu(
        "alarm",
        "set",
        [{"type": "time", "filler": "seven am"}, {"type": "date", "filler": "sunday"}],
    )
    verdict = judge(draft, {}, {"allowed_types": ["time", "date"]})
    assert verdict.flags == ()
    assert verdict.score == 1.0


def test_schema_judge_fires_on_unparsed_on_a_block_illegal_type_and_on_a_repeat():
    judge = JUDGES.resolve(cj.SLURP_SLOT_SCHEMA_JUDGE_V1)
    state = {"allowed_types": ["time", "date"]}

    unparsed = judge("```not json```", {}, state)
    assert [flag.code for flag in unparsed.flags] == ["unparsed_response"]
    assert unparsed.score == 0.0

    illegal = judge(
        _slu("alarm", "set", [{"type": "person", "filler": "todd"}]), {}, state
    )
    assert [flag.code for flag in illegal.flags] == ["block_illegal_slot_type"]
    assert illegal.flags[0].field_ref == "entities[0].type"

    repeated = judge(
        _slu(
            "alarm",
            "set",
            [{"type": "time", "filler": "seven"}, {"type": "time", "filler": "eight"}],
        ),
        {},
        state,
    )
    assert [flag.code for flag in repeated.flags] == ["duplicate_slot_type"]
    assert repeated.flags[0].field_ref == "entities[1].type"
    assert repeated.score == 0.5


def test_schema_judge_reads_the_rows_own_block_from_state_over_material():
    judge = JUDGES.resolve(cj.SLURP_SLOT_SCHEMA_JUDGE_V1)
    draft = _slu("alarm", "set", [{"type": "time", "filler": "seven"}])
    assert judge(draft, {"allowed_types": ["date"]}, {"allowed_types": ["time"]}).flags == ()
    assert judge(draft, {"allowed_types": ["time"]}, {"allowed_types": ["date"]}).flags


# ---------------------------------------------------------------------------
# 4. Earnings numeric-format judge -- gold-free, over the draft alone.
# ---------------------------------------------------------------------------


def test_numeric_format_judge_passes_well_formed_figures():
    judge = JUDGES.resolve(cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1)
    verdict = judge("revenue of 1234 dollars in 2024", {}, {})
    assert verdict.flags == ()
    assert verdict.score == 1.0


def test_numeric_format_judge_flags_a_digit_bearing_token_of_no_numeric_shape():
    """A fused figure ("1234.5.6") normalizes to one digit-bearing token that
    matches none of currency / percent / ordinal / decimal / year / integer --
    ``numeric_kind`` calls it ``other``, and that is the mismatch."""

    judge = JUDGES.resolve(cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1)
    verdict = judge("the figure was 1234.5.6 exactly", {}, {})
    assert [flag.code for flag in verdict.flags] == ["numeric_format_mismatch"]
    flag = verdict.flags[0]
    assert flag.span == (3, 4)
    assert verdict.score == 0.0


def test_numeric_format_judge_scores_one_on_a_draft_with_no_figures():
    judge = JUDGES.resolve(cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1)
    verdict = judge("thank you all for joining the call", {}, {})
    assert verdict.score == 1.0
    assert verdict.flags == ()


# ---------------------------------------------------------------------------
# 5. Substitution-only alignment judge -- the refusal table, as flags.
# ---------------------------------------------------------------------------


def test_alignment_judge_is_silent_on_a_clean_substitution():
    judge = JUDGES.resolve(cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    predecessor = "we heard from calp about the quarter and the guidance was raised"
    response = "we heard from culp about the quarter and the guidance was raised"
    verdict = judge(response, {}, {"predecessor_text": predecessor})
    assert verdict.flags == ()
    assert verdict.score == pytest.approx(11 / 12)


def test_alignment_judge_flags_a_refusal_by_its_frozen_reason_name():
    from speech_aware_evidence_acquisition.core.repair_alignment import REFUSAL_REASONS

    judge = JUDGES.resolve(cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    verdict = judge("", {}, {"predecessor_text": "some words here"})
    codes = [flag.code for flag in verdict.flags]
    assert codes == ["refused:empty_response"]
    assert verdict.flags[0].severity == "block"
    assert "empty_response" in REFUSAL_REASONS


def test_alignment_judge_flags_rejected_opcode_classes():
    judge = JUDGES.resolve(cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    predecessor = "alpha bravo charlie delta echo foxtrot golf hotel india juliet"
    # One inserted token against an otherwise identical response.
    response = "alpha bravo charlie delta echo EXTRA foxtrot golf hotel india juliet"
    verdict = judge(response, {}, {"predecessor_text": predecessor})
    assert "rejected_insertion" in [flag.code for flag in verdict.flags]


def test_alignment_judge_delivers_no_text_of_any_kind():
    """It wraps the delivery post-processor and throws the delivery away."""

    judge = JUDGES.resolve(cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    predecessor = "we heard from calp about the quarter and the guidance was raised"
    response = "we heard from culp about the quarter and the guidance was raised"
    rendered = json.dumps(judge(response, {}, {"predecessor_text": predecessor}).as_json())
    assert "culp" not in rendered and "calp" not in rendered


def test_alignment_judge_fails_closed_without_a_predecessor():
    judge = JUDGES.resolve(cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    with pytest.raises(JudgeError, match="predecessor_text"):
        judge("anything", {}, {})


# ---------------------------------------------------------------------------
# 6. Replay decode-confidence judge -- core.replay_signals.flag_spans, wrapped.
# ---------------------------------------------------------------------------


def test_replay_judge_flags_the_same_spans_the_frozen_function_returns():
    from speech_aware_evidence_acquisition.core.replay_signals import flag_spans

    judge = JUDGES.resolve(cj.REPLAY_LOGPROB_JUDGE_V1)
    draft = "one two three four five"
    scores = [-0.1, -3.0, -3.5, -0.2, -0.1]
    verdict = judge(draft, {"low_threshold": -1.0, "min_run": 2}, {"word_scores": scores})
    expected = flag_spans(draft.split(), scores, -1.0, 2)
    assert [flag.span for flag in verdict.flags] == [tuple(span) for span in expected]
    assert all(flag.code == "low_confidence_span" for flag in verdict.flags)
    assert verdict.score == pytest.approx(0.6)


def test_replay_judge_is_silent_when_nothing_falls_below_the_floor():
    judge = JUDGES.resolve(cj.REPLAY_LOGPROB_JUDGE_V1)
    verdict = judge(
        "one two three", {"low_threshold": -9.0}, {"word_scores": [-0.1, -0.2, -0.3]}
    )
    assert verdict.flags == ()
    assert verdict.score == 1.0


def test_replay_judge_fails_closed_when_its_signal_was_never_wired():
    judge = JUDGES.resolve(cj.REPLAY_LOGPROB_JUDGE_V1)
    with pytest.raises(JudgeError, match="word_scores"):
        judge("one two", {"low_threshold": -1.0}, {})


# ---------------------------------------------------------------------------
# 7. Roster-band judge -- the near-miss detector, without the candidate.
# ---------------------------------------------------------------------------


def test_roster_band_judge_flags_a_near_miss_span():
    judge = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)
    draft = "we heard from Bradey about the quarter"
    verdict = judge(draft, {"candidate_terms": ["Dr. Todd Brady"]}, {})
    assert [flag.code for flag in verdict.flags] == ["roster_band_near_miss"]
    assert verdict.flags[0].span == (3, 4)
    assert verdict.score < 1.0


def test_roster_band_judge_never_names_the_candidate_it_matched():
    judge = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)
    draft = "we heard from Bradey about the quarter"
    rendered = json.dumps(
        judge(draft, {"candidate_terms": ["Dr. Todd Brady"]}, {}).as_json()
    )
    assert "brady" not in rendered.lower()
    assert "todd" not in rendered.lower()


def test_roster_band_judge_is_silent_with_no_candidate_in_band():
    judge = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)
    verdict = judge("we heard from Brady about the quarter", {"candidate_terms": ["Brady"]}, {})
    assert verdict.flags == ()
    assert verdict.score == 1.0


def test_roster_band_judge_fails_closed_without_candidates():
    judge = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)
    with pytest.raises(JudgeError, match="candidate_terms"):
        judge("anything at all", {}, {})


# ---------------------------------------------------------------------------
# 8. Cross-cutting: stateless, deterministic, criticism only.
# ---------------------------------------------------------------------------


_CASES = (
    (cj.SLURP_LEGAL_LABEL_JUDGE_V1, _slu("alarm", "sendemail"), {"actions_by_scenario": _INVENTORY}, {}),
    (
        cj.SLURP_SLOT_SCHEMA_JUDGE_V1,
        _slu("alarm", "set", [{"type": "person", "filler": "x"}]),
        {},
        {"allowed_types": ["time"]},
    ),
    (cj.EARNINGS_NUMERIC_FORMAT_JUDGE_V1, "the figure was 1234.5.6 exactly", {}, {}),
    (
        cj.E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1,
        "",
        {},
        {"predecessor_text": "some words here"},
    ),
    (
        cj.REPLAY_LOGPROB_JUDGE_V1,
        "one two three four five",
        {"low_threshold": -1.0, "min_run": 2},
        {"word_scores": [-0.1, -3.0, -3.5, -0.2, -0.1]},
    ),
    (
        cj.ROSTER_BAND_JUDGE_V1,
        "we heard from Bradey about the quarter",
        {"candidate_terms": ["Dr. Todd Brady"]},
        {},
    ),
)


@pytest.mark.parametrize(("judge_id", "draft", "material", "state"), _CASES)
def test_every_judge_is_deterministic_across_repeated_calls(judge_id, draft, material, state):
    judge = JUDGES.resolve(judge_id)
    first = judge(draft, dict(material), dict(state))
    second = judge(draft, dict(material), dict(state))
    assert first.as_json() == second.as_json()


@pytest.mark.parametrize(("judge_id", "draft", "material", "state"), _CASES)
def test_every_verdict_is_a_validated_criticism_only_verdict(judge_id, draft, material, state):
    judge = JUDGES.resolve(judge_id)
    verdict = judge(draft, dict(material), dict(state))
    assert isinstance(verdict, JudgeVerdict)
    verdict.validate()
    assert verdict.judge_id == judge_id
    payload = verdict.as_json()
    assert set(payload) == {"judge_id", "version", "score", "flags", "reasons"}
    # Nothing in the verdict reproduces the draft it criticises.
    assert draft.strip() == "" or draft not in json.dumps(payload)
