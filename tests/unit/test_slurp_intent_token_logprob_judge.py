"""``core.judges.SlurpIntentTokenLogprobJudge`` -- the LP-2 label-token flag.

Every test here drives the judge on a SYNTHETIC ``MODEL_LOGPROBS`` record: no
model, no GPU, no network, no sealed run directory, no gold label. What is
asserted is (a) the judge finds the scenario/action label tokens by span in
the token stream and nothing else, (b) JSON punctuation cannot enter the
statistic however unconfident it is, (c) the frozen threshold's boundary is
INCLUSIVE, (d) a missing or malformed logprobs record is a loud refusal rather
than a quiet "nothing to criticise", and (e) the verdict is criticism only --
no flag, reason or field carries a replacement label, and the ``top_logprobs``
alternatives (which are exactly what a repair would substitute) never leave
the judge.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.core import judges as cj
from speech_aware_evidence_acquisition.core.base import (
    JUDGES,
    JudgeError,
    JudgeVerdict,
    assert_judge,
)

JUDGE = cj.SlurpIntentTokenLogprobJudge()

#: A confident token, well clear of either frozen floor.
CONFIDENT = -0.0001


def _record(tokens: list[tuple[str, float]], *, top_k: int = 5) -> dict[str, object]:
    """A synthetic ``MODEL_LOGPROBS`` payload in the pinned build's own shape.

    The alternatives are deliberately given plausible LABEL text -- a repair's
    substitute -- so that a judge which leaked one would be visible in the
    criticism-only assertions below.
    """

    return {
        "logprobs": {
            "content": [
                {
                    "token": token,
                    "logprob": logprob,
                    "top_logprobs": [
                        {"token": token, "logprob": logprob},
                        *(
                            {"token": f"alt{index}", "logprob": logprob - 1.0 - index}
                            for index in range(top_k - 1)
                        ),
                    ],
                }
                for token, logprob in tokens
            ]
        },
        "logprobs_sha256": "0" * 64,
        "requested_top_logprobs": top_k,
    }


def _answer(
    *,
    scenario_logprobs: list[float],
    action_logprobs: list[float],
    punctuation_logprob: float = CONFIDENT,
) -> tuple[str, dict[str, object]]:
    """A four-part SLURP answer whose label tokens carry the given logprobs.

    ``scenario`` is spelled one token per character so a test can put an
    arbitrary number of logprobs on it; the punctuation, the key names and the
    empty entity list all share ``punctuation_logprob``, which is what a test
    drives to prove they are excluded.
    """

    scenario = "abcdefgh"[: len(scenario_logprobs)]
    action = "vwxyz"[: len(action_logprobs)]
    tokens: list[tuple[str, float]] = [('{"scenario": "', punctuation_logprob)]
    tokens += list(zip(scenario, scenario_logprobs))
    tokens += [('", "action": "', punctuation_logprob)]
    tokens += list(zip(action, action_logprobs))
    tokens += [('", "entities": []}', punctuation_logprob)]
    draft = "".join(token for token, _logprob in tokens)
    return draft, _record(tokens)


def _run(draft: str, record: dict[str, object], **material: object) -> JudgeVerdict:
    return JUDGE(draft, dict(material), {"logprobs": record})


# ---------------------------------------------------------------------------
# Identity and registration
# ---------------------------------------------------------------------------


def test_the_judge_is_registered_and_passes_the_registry_door() -> None:
    entry = JUDGES.resolve(cj.SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1)
    assert entry.id == cj.SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1
    assert entry.criticism_only is True
    assert_judge(entry, name=cj.SLURP_INTENT_TOKEN_LOGPROB_JUDGE_V1)


def test_the_frozen_floors_are_the_probe_receipts_own_86_flag_cutoffs() -> None:
    """The two constants are quoted, not derived, and the test says from where.

    ``docs/checks/speech-aware-evidence-acquisition/
    2026-09-09-slurp-logprob-judge-probe-v1/verdict/result-summary.json``,
    field ``successor_diagnostic_NOT_PREREGISTERED.operating_points``.
    """

    assert cj.SLURP_INTENT_MEAN_TOKEN_LOGPROB_FLOOR == -0.2675283079346116
    assert cj.SLURP_INTENT_MIN_TOKEN_LOGPROB_FLOOR == -0.5693119168281555
    assert cj.SLURP_INTENT_LOGPROB_FLOORS == {
        "intent_mean_token_logprob": cj.SLURP_INTENT_MEAN_TOKEN_LOGPROB_FLOOR,
        "intent_min_token_logprob": cj.SLURP_INTENT_MIN_TOKEN_LOGPROB_FLOOR,
    }
    assert cj.SLURP_INTENT_LOGPROB_DEFAULT_STATISTIC == "intent_mean_token_logprob"


# ---------------------------------------------------------------------------
# The label tokens are found, and only the label tokens
# ---------------------------------------------------------------------------


def test_the_statistic_is_the_label_tokens_and_no_others() -> None:
    draft, record = _answer(
        scenario_logprobs=[-1.0, -3.0], action_logprobs=[-2.0], punctuation_logprob=-9.0
    )
    measured = JUDGE.statistics(draft, record)
    assert measured["label_token_count"] == 3
    assert measured["located_fields"] == ("action", "scenario")
    assert measured["intent_mean_token_logprob"] == pytest.approx(-2.0)
    assert measured["intent_min_token_logprob"] == pytest.approx(-3.0)
    # The minimum is a scenario token; the punctuation at -9.0 is far lower and
    # is not the answer, which is the whole point of the successor.
    assert measured["least_confident_field"] == "scenario"


def test_json_punctuation_cannot_flag_a_row_however_unconfident_it_is() -> None:
    """The predecessor's failure mode, made unreachable by construction.

    491 of the probe's 1,000 rows put their least-confident token on JSON
    punctuation -- ``" []"`` on 208 of them -- and that is what sank
    ``min_token_logprob`` to 51.16 % precision. Here the punctuation decodes at
    -9.0, far below either frozen floor, and the row is still not flagged.
    """

    draft, record = _answer(
        scenario_logprobs=[CONFIDENT, CONFIDENT],
        action_logprobs=[CONFIDENT],
        punctuation_logprob=-9.0,
    )
    verdict = _run(draft, record)
    assert verdict.flags == ()
    assert verdict.score == pytest.approx(math.exp(CONFIDENT))


def test_a_low_confidence_label_flags_and_names_the_field_not_a_label() -> None:
    draft, record = _answer(scenario_logprobs=[CONFIDENT], action_logprobs=[-2.5])
    verdict = _run(draft, record)
    assert [flag.code for flag in verdict.flags] == ["low_intent_label_confidence"]
    flag = verdict.flags[0]
    assert flag.field_ref == "intent.action"
    assert flag.severity == "warn"
    assert verdict.score == pytest.approx(math.exp((CONFIDENT + -2.5) / 2.0))


def test_the_two_statistics_can_disagree_and_the_choice_is_declared() -> None:
    """One confident label token and one hesitant one: the minimum flags, the
    mean does not. A judge with a hidden statistic would hide this."""

    draft, record = _answer(
        scenario_logprobs=[CONFIDENT, CONFIDENT], action_logprobs=[-0.7]
    )
    assert _run(draft, record).flags == ()
    flagged = _run(draft, record, statistic="intent_min_token_logprob")
    assert [flag.code for flag in flagged.flags] == ["low_intent_label_confidence"]
    assert flagged.flags[0].field_ref == "intent.action"


# ---------------------------------------------------------------------------
# The threshold boundary
# ---------------------------------------------------------------------------


def test_the_threshold_boundary_is_inclusive_and_ties_are_flagged() -> None:
    """A threshold cannot split identical evidence, so the boundary belongs to
    the flagged side -- the same rule the probe's own flag budget used when it
    landed on exactly 86 rows."""

    floor = cj.SLURP_INTENT_MEAN_TOKEN_LOGPROB_FLOOR
    draft, record = _answer(scenario_logprobs=[floor], action_logprobs=[floor])
    on_the_line = _run(draft, record)
    assert [flag.code for flag in on_the_line.flags] == ["low_intent_label_confidence"]

    draft, record = _answer(
        scenario_logprobs=[floor / 2.0], action_logprobs=[floor / 2.0]
    )
    assert _run(draft, record).flags == ()


def test_a_caller_may_move_the_threshold_but_not_off_the_logprob_scale() -> None:
    draft, record = _answer(scenario_logprobs=[-0.10], action_logprobs=[-0.10])
    assert _run(draft, record).flags == ()
    assert _run(draft, record, threshold=-0.05).flags[0].code == (
        "low_intent_label_confidence"
    )
    with pytest.raises(JudgeError, match="finite logprob floor"):
        _run(draft, record, threshold=0.5)
    with pytest.raises(JudgeError, match="finite logprob floor"):
        _run(draft, record, threshold=float("-inf"))


def test_an_unknown_statistic_is_refused_by_name() -> None:
    draft, record = _answer(scenario_logprobs=[-1.0], action_logprobs=[-1.0])
    with pytest.raises(JudgeError, match="must be one of"):
        _run(draft, record, statistic="min_token_logprob")


# ---------------------------------------------------------------------------
# Refusals: a missing or unusable record is loud
# ---------------------------------------------------------------------------


def test_a_missing_logprobs_record_refuses_rather_than_passing_the_row() -> None:
    draft, _record_unused = _answer(
        scenario_logprobs=[-1.0], action_logprobs=[-1.0]
    )
    with pytest.raises(JudgeError, match="needs 'logprobs'"):
        JUDGE(draft, {}, {"sample_id": "slurp:devel:1:2"})


def test_a_record_without_a_content_list_refuses() -> None:
    draft, _unused = _answer(scenario_logprobs=[-1.0], action_logprobs=[-1.0])
    with pytest.raises(JudgeError, match="no 'content' list"):
        _run(draft, {"logprobs": {"tokens": []}})
    with pytest.raises(JudgeError, match="non-empty 'content' list"):
        _run(draft, {"logprobs": {"content": []}})


def test_a_content_entry_without_a_numeric_logprob_refuses() -> None:
    draft, record = _answer(scenario_logprobs=[-1.0], action_logprobs=[-1.0])
    record["logprobs"]["content"][1].pop("logprob")  # type: ignore[index]
    with pytest.raises(JudgeError, match="no numeric logprob"):
        _run(draft, record)


def test_a_non_mapping_logprobs_value_refuses() -> None:
    draft, _unused = _answer(scenario_logprobs=[-1.0], action_logprobs=[-1.0])
    with pytest.raises(JudgeError, match="MODEL_LOGPROBS record"):
        _run(draft, "content")  # type: ignore[arg-type]


def test_all_three_record_shapes_are_accepted_and_agree() -> None:
    draft, payload = _answer(scenario_logprobs=[-1.0], action_logprobs=[-2.0])
    whole_record = {
        "channel": "MODEL_LOGPROBS",
        "record_id": "req-1/logprobs",
        "payload": payload,
    }
    inner = payload["logprobs"]
    assert (
        JUDGE.statistics(draft, whole_record)
        == JUDGE.statistics(draft, payload)
        == JUDGE.statistics(draft, inner)  # type: ignore[arg-type]
    )


def test_a_stream_that_is_not_a_prefix_of_the_draft_refuses() -> None:
    """A confidence statistic aligned to a different string is not a
    measurement of this draft, so the judge stops instead of scoring it."""

    draft, record = _answer(scenario_logprobs=[-1.0], action_logprobs=[-1.0])
    with pytest.raises(JudgeError, match="not a prefix"):
        _run(draft.replace('"scenario"', '"scenariX"'), record)


def test_a_trailing_stop_word_trim_is_tolerated_because_the_build_does_it() -> None:
    """``send_final_response`` drops the trailing tokens matching a stop word
    from ``probs_output`` (server-context.cpp:2340-2352), so the stream can be
    a proper PREFIX of the sealed text. The label spans sit before any such
    trim, and the probe measured zero mismatches on 1,000 rows -- this is the
    documented case, and it is admitted rather than refused."""

    draft, record = _answer(scenario_logprobs=[-1.0], action_logprobs=[-2.0])
    measured = JUDGE.statistics(draft + "\n<|im_end|>", record)
    assert measured["reconstructed_prefix_only"] is True
    assert measured["intent_mean_token_logprob"] == pytest.approx(-1.5)


# ---------------------------------------------------------------------------
# The row whose label cannot be located at all
# ---------------------------------------------------------------------------


def test_an_answer_with_no_locatable_label_is_flagged_under_its_own_code() -> None:
    tokens = [("I", -0.2), (" think", -0.4), (" it", -0.3), (" is", -0.1)]
    draft = "".join(token for token, _logprob in tokens)
    verdict = _run(draft, _record(tokens))
    assert [flag.code for flag in verdict.flags] == ["intent_label_tokens_not_located"]
    assert verdict.flags[0].field_ref == "intent"
    assert verdict.score is None


def test_a_scenario_without_a_quoted_string_value_is_not_located() -> None:
    tokens = [('{"scenario": ', -0.1), ("null", -0.2), (', "action": ', -0.1), ("null}", -0.2)]
    draft = "".join(token for token, _logprob in tokens)
    measured = JUDGE.statistics(draft, _record(tokens))
    assert measured["located_fields"] == ()
    assert measured["intent_mean_token_logprob"] is None


def test_one_located_field_is_enough_to_measure() -> None:
    tokens = [('{"scenario": "', -0.1), ("alarm", -0.9), ('"}', -0.1)]
    draft = "".join(token for token, _logprob in tokens)
    measured = JUDGE.statistics(draft, _record(tokens))
    assert measured["located_fields"] == ("scenario",)
    assert measured["intent_mean_token_logprob"] == pytest.approx(-0.9)


# ---------------------------------------------------------------------------
# Criticism only, and determinism
# ---------------------------------------------------------------------------


def test_no_verdict_field_carries_a_label_or_an_alternative() -> None:
    """The row's own label text and every ``top_logprobs`` alternative are
    exactly what a repair would substitute. Neither may appear anywhere in the
    verdict -- not in a reason, not in a field reference, not in a code."""

    tokens = [
        ('{"scenario": "', CONFIDENT),
        ("takeaway", -3.0),
        ('", "action": "', CONFIDENT),
        ("order", -1.0),
        ('", "entities": []}', CONFIDENT),
    ]
    draft = "".join(token for token, _logprob in tokens)
    verdict = _run(draft, _record(tokens))
    rendered = repr(verdict.as_json())
    assert "takeaway" not in rendered
    assert "order" not in rendered
    assert "alt1" not in rendered
    assert verdict.flags[0].field_ref == "intent.scenario"


def test_the_judge_is_deterministic_and_stateless() -> None:
    draft, record = _answer(scenario_logprobs=[-0.4], action_logprobs=[-0.9])
    first = _run(draft, record)
    second = _run(draft, record)
    assert first.as_json() == second.as_json()


def test_every_verdict_validates_under_the_criticism_only_type() -> None:
    cases = [
        _answer(scenario_logprobs=[CONFIDENT], action_logprobs=[CONFIDENT]),
        _answer(scenario_logprobs=[-4.0], action_logprobs=[-4.0]),
    ]
    for draft, record in cases:
        verdict = _run(draft, record)
        assert verdict.validate() is verdict
        for flag in verdict.flags:
            assert len(flag.reason) <= 240
            assert flag.span is None
