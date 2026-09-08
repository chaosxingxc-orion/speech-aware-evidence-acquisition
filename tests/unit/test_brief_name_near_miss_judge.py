"""``core.judges.BriefNameNearMissJudge`` -- the E21-LOOP-1 Reviewer's new
deterministic judge.

Every test drives the judge on a SYNTHETIC draft and a SYNTHETIC brief: no
model, no GPU, no network, no sealed run directory, no ConEC file. What is
asserted is (a) the near-miss rule -- within a small edit distance of a
PERSON/ORG brief entry and NOT equal to it; (b) that it never names the entry
it matched (owner Decision 11-C); (c) that it is deterministic, stateless and
fail-closed; and (d) that it is a different object from
``roster-band-flag-v1``, which ranks by rarity and truncates to a budget.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core import judges as cj
from speech_aware_evidence_acquisition.core.base import JUDGES, JudgeError

PERSON = ["Maureen Mulholland", "Brett Ponton", "Dr. Todd Brady"]
ORG = ["Oppenheimer", "BMO Capital Markets"]
MATERIAL = {"person_terms": PERSON, "org_terms": ORG}


def _judge():
    return JUDGES.resolve(cj.E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1)


def _codes(verdict):
    return [flag.code for flag in verdict.flags]


def _spans(verdict):
    return [flag.span for flag in verdict.flags]


# ---------------------------------------------------------------------------
# 1. The rule: near, but not equal.
# ---------------------------------------------------------------------------


def test_a_corrupted_person_name_is_flagged_at_its_own_span():
    verdict = _judge()("we heard from Bradey about the quarter", MATERIAL, {})
    assert _codes(verdict) == ["brief_person_name_near_miss"]
    assert _spans(verdict) == [(3, 4)]
    assert verdict.flags[0].severity == "warn"
    assert verdict.flags[0].field_ref == "transcript"


def test_a_corrupted_org_name_is_flagged_with_its_own_class_code():
    verdict = _judge()("a question from Opponheimer please", MATERIAL, {})
    assert _codes(verdict) == ["brief_org_name_near_miss"]
    assert _spans(verdict) == [(3, 4)]


def test_an_exact_brief_form_is_never_flagged():
    """The whole "but not equal" half of the rule: a draft that already
    carries the brief's own spelling is right, and a judge that criticised it
    would flag every correctly transcribed name in the call."""

    verdict = _judge()("we heard from Brady and from Oppenheimer", MATERIAL, {})
    assert verdict.flags == ()
    assert verdict.score == 1.0


def test_an_unrelated_word_is_never_flagged():
    verdict = _judge()("revenue grew across every operating segment", MATERIAL, {})
    assert verdict.flags == ()


def test_a_two_word_window_matches_a_brief_bigram():
    verdict = _judge()("thanks Brett Pontin for that", MATERIAL, {})
    assert _codes(verdict) == ["brief_person_name_near_miss"]
    assert _spans(verdict) == [(1, 3)]


def test_the_band_ceiling_is_enforced_in_both_directions():
    judge = _judge()
    draft = "we heard from Bradey about the quarter"
    assert judge(draft, {**MATERIAL, "max_distance": 0.25}, {}).flags
    assert judge(draft, {**MATERIAL, "max_distance": 0.05}, {}).flags == ()


def test_short_words_never_anchor_a_query():
    """At three characters a single substitution is already a third of the
    form, so a floor is what keeps the judge from flagging function words."""

    judge = _judge()
    verdict = judge("bmo was on the call", {"person_terms": [], "org_terms": ["BMO"]}, {})
    assert verdict.flags == ()


def test_flags_are_non_overlapping_and_ascending():
    draft = "Marine Mulholand asked Brett Pontin about Opponheimer"
    verdict = _judge()(draft, MATERIAL, {})
    spans = _spans(verdict)
    assert spans == sorted(spans)
    for earlier, later in zip(spans, spans[1:]):
        assert earlier[1] <= later[0]


# ---------------------------------------------------------------------------
# 2. Decision 11-C: criticism only.
# ---------------------------------------------------------------------------


def test_the_judge_never_names_the_brief_entry_it_matched():
    verdict = _judge()("we heard from Bradey and Opponheimer", MATERIAL, {})
    rendered = json.dumps(verdict.as_json()).lower()
    for entry in ("brady", "todd", "oppenheimer", "mulholland", "ponton", "bmo"):
        assert entry not in rendered


def test_the_verdict_carries_only_the_span_the_class_and_the_distance():
    verdict = _judge()("we heard from Bradey about it", MATERIAL, {})
    payload = verdict.as_json()
    assert payload["judge_id"] == cj.E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1
    flag = payload["flags"][0]
    assert set(flag) == {"code", "severity", "reason", "field_ref", "span"}
    assert flag["span"] == [3, 4]


# ---------------------------------------------------------------------------
# 3. Determinism, statelessness and the fail-closed door.
# ---------------------------------------------------------------------------


def test_the_judge_is_deterministic_and_stateless():
    judge = _judge()
    draft = "Marine Mulholand asked Opponheimer"
    first = judge(draft, MATERIAL, {}).as_json()
    _other = judge("something else entirely", MATERIAL, {})
    second = judge(draft, MATERIAL, {}).as_json()
    assert first == second


@pytest.mark.parametrize("missing", ["person_terms", "org_terms"])
def test_the_judge_fails_closed_without_either_class(missing):
    material = {key: value for key, value in MATERIAL.items() if key != missing}
    with pytest.raises(JudgeError, match=missing):
        _judge()("anything at all", material, {})


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_an_out_of_range_band_is_refused(bad):
    with pytest.raises(JudgeError, match="max_distance"):
        _judge()("anything at all", {**MATERIAL, "max_distance": bad}, {})


def test_a_non_sequence_term_list_is_refused():
    with pytest.raises(JudgeError, match="person_terms"):
        _judge()("anything", {"person_terms": "Brady", "org_terms": ORG}, {})


def test_state_overrides_material_for_the_per_row_signal():
    judge = _judge()
    verdict = judge(
        "we heard from Bradey about it",
        {"person_terms": [], "org_terms": []},
        {"person_terms": PERSON, "org_terms": ORG},
    )
    assert _codes(verdict) == ["brief_person_name_near_miss"]


def test_an_empty_brief_criticises_nothing():
    verdict = _judge()("Bradey and Opponheimer", {"person_terms": [], "org_terms": []}, {})
    assert verdict.flags == ()
    assert verdict.score == 1.0


# ---------------------------------------------------------------------------
# 4. It is not the roster-band judge.
# ---------------------------------------------------------------------------


def test_it_is_not_truncated_to_a_budget_the_way_the_roster_band_judge_is():
    """``roster-band-flag-v1`` keeps its top ``max_spans`` (default 4) by
    rarity-weighted score. The near-miss judge selects by DISTANCE alone and
    keeps every non-overlapping match, because its flag count is what prices
    the loop's contact budget."""

    person = [f"Aaronson{index}" for index in range(6)]
    draft = " ".join(f"Aaronsen{index}" for index in range(6))
    near_miss = _judge()(draft, {"person_terms": person, "org_terms": []}, {})
    band = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)(
        draft, {"candidate_terms": person}, {}
    )
    assert len(near_miss.flags) == 6
    assert len(band.flags) == 4


def test_the_two_judges_carry_different_ids_and_flag_codes():
    near_miss = _judge()("we heard from Bradey", MATERIAL, {})
    band = JUDGES.resolve(cj.ROSTER_BAND_JUDGE_V1)(
        "we heard from Bradey", {"candidate_terms": ["Dr. Todd Brady"]}, {}
    )
    assert near_miss.judge_id != band.judge_id
    assert {flag.code for flag in near_miss.flags}.isdisjoint(
        {flag.code for flag in band.flags}
    )
