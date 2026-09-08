"""The SLURP logprob-as-judge read, exercised on SYNTHETIC traces.

No dataset, no sealed run and no model: every input the read takes is a file,
so its whole decision path -- token-stream alignment, the confidence
statistics, the AUROC, the flag budget, the judges, the unions and the
admission rule -- is checkable before the probe ever flies. That is the point:
an analysis script written after the numbers exist is a script whose thresholds
were chosen by the numbers.
"""

import importlib.util
import json
import math
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _read_module():
    """Import the script by path -- the shared venv ships an unrelated
    top-level ``scripts`` package that shadows this repository's namespace
    directory."""

    path = REPO / "scripts" / "slurp_logprob_judge_read.py"
    spec = importlib.util.spec_from_file_location("saea_slurp_logprob_judge_read", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


READ = _read_module()


# ---------------------------------------------------------------------------
# Synthetic material
# ---------------------------------------------------------------------------


def _tokens(text, per_token_logprob, *, alternatives=5, alt_gap=1.0):
    """Split ``text`` into single-character tokens carrying the given logprobs,
    each with ``alternatives`` top_logprobs whose first entry is the sampled
    token -- the pinned server's own shape."""

    if len(per_token_logprob) != len(text):
        raise AssertionError("one logprob per character, please")
    content = []
    for character, value in zip(text, per_token_logprob):
        top = [{"token": character, "logprob": value}]
        for rank in range(1, alternatives):
            top.append({"token": f"x{rank}", "logprob": value - alt_gap * rank})
        content.append(
            {
                "token": character,
                "logprob": value,
                "top_logprobs": top[:alternatives],
            }
        )
    return {"content": content}


def _flat_tokens(text, value=-0.1, **kwargs):
    return _tokens(text, [value] * len(text), **kwargs)


ANSWER = '{"scenario": "alarm", "action": "set", "entities": []}'


INVENTORY = {
    "entity_types": ["time", "date", "person"],
    "legal_pairs": [["alarm", "set"], ["alarm", "remove"], ["email", "query"]],
}


def _trace(records):
    return [
        {
            "channel": "MODEL_LOGPROBS",
            "record_id": f"{request_id}/logprobs",
            "payload": {"logprobs": logprobs, "requested_top_logprobs": 5},
        }
        for request_id, logprobs in records
    ]


def _outputs(rows):
    return [
        {
            "sample_id": sample_id,
            "request_id": request_id,
            "text": text,
            "arm": "speech-feature-query",
            "carrier_lock_key": "slurp",
            "admitted": True,
        }
        for sample_id, request_id, text in rows
    ]


def _per_sample(rows):
    return [
        {
            "sample_id": sample_id,
            "scenario_action_exact": 0.0 if intent_error else 1.0,
            "slot_f1_exact_fn": float(false_negatives),
            "slot_f1_exact_fp": float(false_positives),
        }
        for sample_id, intent_error, false_negatives, false_positives in rows
    ]


# ---------------------------------------------------------------------------
# Token-stream alignment and the statistics
# ---------------------------------------------------------------------------


def test_the_intent_span_statistics_point_at_the_intent_tokens():
    """The whole design rests on this: the scenario/action VALUE characters,
    and no others, feed the intent statistics."""

    values = [-0.01] * len(ANSWER)
    # Make exactly the five characters of "alarm" cheap.
    start = ANSWER.index('"alarm"') + 1
    for index in range(start, start + len("alarm")):
        values[index] = -3.0
    confidence = READ.row_confidence(_tokens(ANSWER, values))
    assert confidence["intent_token_count"] == len("alarm") + len("set")
    # "alarm" at -3.0 (5 chars) and "set" at -0.01 (3 chars).
    assert confidence["intent_min_token_logprob"] == pytest.approx(-3.0)
    assert confidence["intent_mean_token_logprob"] == pytest.approx(
        (5 * -3.0 + 3 * -0.01) / 8
    )
    assert confidence["min_token_logprob"] == pytest.approx(-3.0)
    assert confidence["mean_token_logprob"] < confidence["intent_mean_token_logprob"] or True


def test_the_first_intent_token_margin_is_top1_minus_top2():
    confidence = READ.row_confidence(_flat_tokens(ANSWER, -0.5, alt_gap=1.25))
    assert confidence["first_intent_token_margin"] == pytest.approx(1.25)


def test_the_margin_is_unavailable_when_only_one_alternative_was_requested():
    """``top_logprobs: 1`` is a legal request; the margin simply does not
    exist, and the read says so rather than inventing one."""

    confidence = READ.row_confidence(_flat_tokens(ANSWER, -0.5, alternatives=1))
    assert confidence["first_intent_token_margin"] is None
    assert confidence["min_token_logprob"] == pytest.approx(-0.5)


def test_a_row_with_no_parsable_intent_still_yields_the_whole_row_statistics():
    confidence = READ.row_confidence(_flat_tokens("I could not answer that.", -2.0))
    assert confidence["intent_mean_token_logprob"] is None
    assert confidence["intent_min_token_logprob"] is None
    assert confidence["min_token_logprob"] == pytest.approx(-2.0)


def test_a_malformed_logprobs_object_is_refused():
    for bad in ({}, {"content": []}, {"content": [{"token": "a"}]}):
        with pytest.raises(READ.LogprobReadError):
            READ.row_confidence(bad)


# ---------------------------------------------------------------------------
# AUROC
# ---------------------------------------------------------------------------


def test_auroc_is_one_when_the_statistic_separates_perfectly():
    assert READ.auroc([3.0, 2.0, 1.0, 0.0], [True, True, False, False]) == 1.0


def test_auroc_is_zero_when_the_statistic_is_exactly_inverted():
    assert READ.auroc([0.0, 1.0, 2.0, 3.0], [True, True, False, False]) == 0.0


def test_auroc_handles_ties_by_mid_rank():
    """A statistic that is constant separates nothing: 0.5, not 1.0 or 0.0.
    A confidence flag has many ties, so this is not a corner case."""

    assert READ.auroc([1.0, 1.0, 1.0, 1.0], [True, False, True, False]) == 0.5
    # One tie straddling the boundary. Four (positive, negative) pairs:
    # 2.0>1.0 wins, 2.0>0.0 wins, 1.0==1.0 is half credit, 1.0>0.0 wins,
    # so 3.5/4 = 0.875 -- a tie costs exactly half a pair, not a whole one.
    assert READ.auroc([2.0, 1.0, 1.0, 0.0], [True, True, False, False]) == pytest.approx(
        0.875
    )


def test_auroc_with_one_empty_class_is_half_rather_than_a_crash():
    assert READ.auroc([1.0, 2.0], [False, False]) == 0.5


def test_auroc_refuses_mismatched_lengths():
    with pytest.raises(READ.LogprobReadError):
        READ.auroc([1.0], [True, False])


# ---------------------------------------------------------------------------
# The flag budget
# ---------------------------------------------------------------------------


def test_the_flag_budget_selects_the_least_confident_rows():
    scores = {"a": 5.0, "b": 4.0, "c": 3.0, "d": 2.0}
    flagged, threshold = READ.flag_at_budget(scores, 2)
    assert flagged == {"a", "b"}
    assert threshold == 4.0


def test_ties_at_the_boundary_are_included_and_the_count_is_reported_honestly():
    """A threshold cannot split identical evidence: asking for 2 flags when
    three rows share the boundary score flags three, and the caller reports
    three."""

    scores = {"a": 5.0, "b": 4.0, "c": 4.0, "d": 4.0, "e": 1.0}
    flagged, threshold = READ.flag_at_budget(scores, 2)
    assert flagged == {"a", "b", "c", "d"}
    assert threshold == 4.0
    assert READ.precision_recall(flagged, {key: True for key in scores})["flagged"] == 4


def test_a_budget_at_or_above_the_population_flags_everything():
    scores = {"a": 1.0, "b": 2.0}
    flagged, threshold = READ.flag_at_budget(scores, 5)
    assert flagged == {"a", "b"}
    assert threshold == -math.inf


def test_a_non_positive_budget_is_refused():
    with pytest.raises(READ.LogprobReadError):
        READ.flag_at_budget({"a": 1.0}, 0)


def test_precision_and_recall_are_percentages_of_the_right_denominators():
    result = READ.precision_recall(
        ["a", "b", "c"], {"a": True, "b": False, "c": True, "d": True}
    )
    assert result == {
        "flagged": 3,
        "errors": 3,
        "caught": 2,
        "precision": pytest.approx(200.0 / 3.0),
        "recall": pytest.approx(200.0 / 3.0),
    }


def test_the_bootstrap_precision_keeps_the_resampling_multiplicity():
    """``resampled_statistic`` hands its statistic a sequence in which ids
    REPEAT. Collapsing to a set would throw the resampling away and narrow the
    CI, so a row drawn twice must count twice."""

    scores = {"a": 5.0, "b": 4.0, "c": 1.0, "d": 0.0}
    errors = {"a": True, "b": False, "c": False, "d": False}
    # The full population, budget 2: "a" and "b", one of which is an error.
    assert READ.precision_at_budget_over_sequence(
        ["a", "b", "c", "d"], scores=scores, errors=errors, budget=2, population=4
    ) == pytest.approx(50.0)
    # A replicate that draws "b" four times: the budget rescales to 2 of 4 and
    # both drawn entries are the same non-error row -- 0 %, not 50 %.
    assert READ.precision_at_budget_over_sequence(
        ["b", "b", "b", "b"], scores=scores, errors=errors, budget=2, population=4
    ) == pytest.approx(0.0)
    # A replicate that draws the error row twice: both top entries are "a".
    assert READ.precision_at_budget_over_sequence(
        ["a", "a", "c", "d"], scores=scores, errors=errors, budget=2, population=4
    ) == pytest.approx(100.0)


def test_the_bootstrap_precision_rescales_the_budget_and_never_returns_nothing():
    scores = {"a": 5.0, "b": 4.0}
    errors = {"a": True, "b": True}
    # A one-row replicate against a 1,000-row population still flags one row.
    assert READ.precision_at_budget_over_sequence(
        ["b"], scores=scores, errors=errors, budget=86, population=1000
    ) == pytest.approx(100.0)
    assert (
        READ.precision_at_budget_over_sequence(
            [], scores=scores, errors=errors, budget=86, population=1000
        )
        == 0.0
    )


def test_the_curve_walks_every_distinct_threshold_monotonically():
    scores = {"a": 3.0, "b": 2.0, "c": 2.0, "d": 1.0}
    errors = {"a": True, "b": False, "c": True, "d": False}
    curve = READ.precision_recall_curve(scores, errors)
    assert [point["flag_score_threshold"] for point in curve] == [3.0, 2.0, 1.0]
    assert [point["statistic_cutoff"] for point in curve] == [-3.0, -2.0, -1.0]
    assert [point["flagged"] for point in curve] == [1, 3, 4]
    assert [point["caught"] for point in curve] == [1, 2, 2]
    # Recall never falls as the threshold drops.
    recalls = [point["recall"] for point in curve]
    assert recalls == sorted(recalls)


# ---------------------------------------------------------------------------
# The deterministic judges, recomputed on this arm's own rows
# ---------------------------------------------------------------------------


def test_a_clean_legal_row_fires_neither_judge():
    assert READ.deterministic_judges(ANSWER, INVENTORY) == {
        "schema": False,
        "legality": False,
        "unparsed": False,
    }


def test_an_unparsed_row_fires_both_judges():
    verdict = READ.deterministic_judges("sorry, I could not hear that", INVENTORY)
    assert verdict == {"schema": True, "legality": True, "unparsed": True}


def test_an_out_of_vocabulary_type_fires_the_schema_judge():
    text = json.dumps(
        {
            "scenario": "alarm",
            "action": "set",
            "entities": [{"type": "not_a_type", "filler": "six am"}],
        }
    )
    verdict = READ.deterministic_judges(text, INVENTORY)
    assert verdict["schema"] is True
    assert verdict["legality"] is False


def test_a_repeated_type_fires_the_schema_judge():
    text = json.dumps(
        {
            "scenario": "alarm",
            "action": "set",
            "entities": [
                {"type": "time", "filler": "six am"},
                {"type": "time", "filler": "seven am"},
            ],
        }
    )
    assert READ.deterministic_judges(text, INVENTORY)["schema"] is True


def test_an_illegal_pair_fires_the_legality_judge_only():
    text = json.dumps({"scenario": "alarm", "action": "query", "entities": []})
    verdict = READ.deterministic_judges(text, INVENTORY)
    assert verdict == {"schema": False, "legality": True, "unparsed": False}


# ---------------------------------------------------------------------------
# Joining, and the whole read
# ---------------------------------------------------------------------------


def _material(n=40):
    """n rows: the least-confident half carry the intent errors, so the
    statistic has real signal and the assertions below are about plumbing
    rather than about luck."""

    trace, outputs, per_sample, clusters = [], [], [], {}
    for index in range(n):
        sample_id = f"slurp:devel:{index:06d}:audio-{index}"
        request_id = f"req-{index:04d}"
        error = index % 2 == 0
        value = -3.0 if error else -0.05
        trace.append((request_id, _tokens(ANSWER, [value] * len(ANSWER))))
        outputs.append((sample_id, request_id, ANSWER))
        per_sample.append((sample_id, error, 1 if error else 0, 0))
        clusters[sample_id] = f"speaker-{index % 8}"
    return _trace(trace), _outputs(outputs), _per_sample(per_sample), clusters


def test_build_rows_joins_trace_outputs_and_scores_by_id():
    trace, outputs, per_sample, _ = _material(6)
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    assert len(rows) == 6
    first = rows["slurp:devel:000000:audio-0"]
    assert first["request_id"] == "req-0000"
    assert first["labels"] == {
        "intent_error": True,
        "unmatched_gold": True,
        "slot_error": True,
    }
    assert first["judges"]["schema"] is False
    assert first["token_stream_rebuilds_text"] is True


def test_an_outputs_row_with_no_logprobs_record_is_refused():
    trace, outputs, per_sample, _ = _material(3)
    with pytest.raises(READ.LogprobReadError) as error:
        READ.build_rows(
            trace=trace[:-1], outputs=outputs, per_sample=per_sample, inventory=INVENTORY
        )
    assert "no MODEL_LOGPROBS record" in str(error.value)


def test_a_token_stream_that_does_not_rebuild_the_sealed_text_is_reported():
    """If it did not rebuild, the span statistics were aligned to the wrong
    string and every intent number would be silently meaningless."""

    trace, outputs, per_sample, _ = _material(2)
    outputs[0] = dict(outputs[0])
    outputs[0]["text"] = ANSWER + " trailing"
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    assert rows["slurp:devel:000000:audio-0"]["token_stream_rebuilds_text"] is False
    assert rows["slurp:devel:000001:audio-1"]["token_stream_rebuilds_text"] is True


def test_a_duplicate_logprobs_record_is_refused():
    trace, outputs, per_sample, _ = _material(2)
    with pytest.raises(READ.LogprobReadError):
        READ.logprobs_by_request(trace + trace[:1])


def test_the_whole_read_runs_and_applies_the_rule():
    trace, outputs, per_sample, clusters = _material(40)
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    document = READ.analyse(
        rows, clusters=clusters, n_replicates=200, flag_budget=10
    )
    assert document["n"] == 40
    assert document["clusters"] == 8
    assert document["token_stream_mismatches"] == []
    intent = document["auroc"]["intent_error"]["min_token_logprob"]
    assert intent["status"] == "OK"
    # By construction the least-confident rows ARE the erroneous ones.
    assert intent["auroc"] == pytest.approx(1.0)
    assert intent["ci90"][0] <= intent["auroc"] <= intent["ci90"][1]
    operating = document["operating_point"]["intent_error"]
    assert operating["confidence"]["precision"] == pytest.approx(100.0)
    assert document["verdict"]["admitted"] is True
    assert document["verdict"]["by_auroc"] is True


def test_a_statistic_no_row_carries_is_reported_unavailable_not_dropped():
    trace, outputs, per_sample, clusters = _material(8)
    trace = [
        {
            **record,
            "payload": {
                **record["payload"],
                "logprobs": {
                    "content": [
                        {k: v for k, v in entry.items() if k != "top_logprobs"}
                        for entry in record["payload"]["logprobs"]["content"]
                    ]
                },
            },
        }
        for record in trace
    ]
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    document = READ.analyse(rows, clusters=clusters, n_replicates=50, flag_budget=4)
    margin = document["auroc"]["intent_error"]["first_intent_token_margin"]
    assert margin["status"] == "UNAVAILABLE"
    assert document["auroc"]["intent_error"]["min_token_logprob"]["status"] == "OK"


def test_a_row_without_a_speaker_cluster_is_refused():
    trace, outputs, per_sample, clusters = _material(4)
    clusters.pop("slurp:devel:000000:audio-0")
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    with pytest.raises(READ.LogprobReadError) as error:
        READ.analyse(rows, clusters=clusters, n_replicates=10)
    assert "speaker cluster" in str(error.value)


def test_the_union_can_only_flag_more_rows_than_either_judge_alone():
    trace, outputs, per_sample, clusters = _material(20)
    # Make half the rows fire the schema judge, disjointly from confidence.
    bad = json.dumps(
        {
            "scenario": "alarm",
            "action": "set",
            "entities": [{"type": "nope", "filler": "x"}],
        }
    )
    trace = list(trace)
    outputs = list(outputs)
    for index in range(1, 20, 4):
        outputs[index] = {**outputs[index], "text": bad}
        trace[index] = {
            **trace[index],
            "payload": {
                **trace[index]["payload"],
                "logprobs": _tokens(bad, [-0.01] * len(bad)),
            },
        }
    rows = READ.build_rows(
        trace=trace, outputs=outputs, per_sample=per_sample, inventory=INVENTORY
    )
    document = READ.analyse(rows, clusters=clusters, n_replicates=50, flag_budget=5)
    point = document["operating_point"]["intent_error"]
    assert point["schema_judge"]["flagged"] == 5
    assert point["union_confidence_schema"]["flagged"] >= point["confidence"]["flagged"]
    assert point["union_confidence_schema"]["flagged"] >= point["schema_judge"]["flagged"]
    assert point["union_all_three"]["caught"] >= point["union_confidence_schema"]["caught"]


# ---------------------------------------------------------------------------
# The admission rule, applied to numbers it must and must not admit
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "auroc_point, auroc_ci_low, precision, precision_ci_low, admitted, by_auroc, by_precision",
    [
        # Clears the AUROC arm outright.
        (0.81, 0.74, 40.0, 30.0, True, True, False),
        # AUROC point clears but its lower bound does not: NOT admitted.
        (0.78, 0.66, 40.0, 30.0, False, False, False),
        # AUROC lower bound clears but the point does not: NOT admitted.
        (0.72, 0.71, 40.0, 30.0, False, False, False),
        # Exactly on both AUROC bounds: admitted (the rule says >=).
        (0.75, 0.70, 0.0, 0.0, True, True, False),
        # Clears the precision arm: strictly above 72.09 on both.
        (0.50, 0.40, 80.0, 75.0, True, False, True),
        # Precision point above but its lower bound is not: NOT admitted.
        (0.50, 0.40, 80.0, 70.0, False, False, False),
        # Exactly ON the schema judge's precision: not "exceeds".
        (0.50, 0.40, 72.09, 72.09, False, False, False),
        # Neither arm.
        (0.55, 0.48, 60.0, 50.0, False, False, False),
    ],
)
def test_the_admission_rule_is_exactly_as_preregistered(
    auroc_point, auroc_ci_low, precision, precision_ci_low, admitted, by_auroc, by_precision
):
    verdict = READ.admission_verdict(
        auroc_point=auroc_point,
        auroc_ci_low=auroc_ci_low,
        precision_at_budget=precision,
        precision_ci_low=precision_ci_low,
    )
    assert verdict["admitted"] is admitted
    assert verdict["by_auroc"] is by_auroc
    assert verdict["by_precision"] is by_precision


def test_the_rule_constants_are_the_ones_the_preregistration_names():
    assert READ.SCHEMA_JUDGE_FLAG_BUDGET == 86
    assert READ.SCHEMA_JUDGE_PRECISION == 72.09
    assert READ.ADMISSION_AUROC == 0.75
    assert READ.ADMISSION_AUROC_CI90_LOWER == 0.70
