"""Unit tests for the Audio2Tool-style deterministic tool-call scorer (P0.B).

Metric definitions reimplemented from arXiv:2604.22821 (official eval scripts
unreleased): Tool Accuracy (predicted tool multiset matches ground truth),
Exact Match (tools and arguments both correct), Slot-F1 (parameter-level
micro-averaged P/R/F1). Interpretation choices are documented in the module
docstring; these tests are the executable record of those choices.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
    A2T_SCORER_VERSION,
    ToolCall,
    aggregate,
    parse_tool_calls_text,
    score_item,
)


def call(name, **arguments):
    return ToolCall(name=name, arguments=arguments)


class TestScoreItemSingleCall:
    def test_identical_call_scores_perfect(self):
        expected = [call("setLighting", room="kitchen", brightness=50)]
        predicted = [call("setLighting", room="kitchen", brightness=50)]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 1.0
        assert s.exact_match == 1.0
        assert s.slot_f1 == 1.0

    def test_right_tool_wrong_argument_value(self):
        expected = [call("setLighting", room="kitchen", brightness=50)]
        predicted = [call("setLighting", room="kitchen", brightness=80)]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 1.0
        assert s.exact_match == 0.0
        # one of two slot triples matches on both sides
        assert s.slot_precision == pytest.approx(0.5)
        assert s.slot_recall == pytest.approx(0.5)
        assert s.slot_f1 == pytest.approx(0.5)

    def test_wrong_tool_scores_zero(self):
        expected = [call("setLighting", room="kitchen")]
        predicted = [call("setThermostat", room="kitchen")]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 0.0
        assert s.exact_match == 0.0
        # slot triples are keyed by tool name, so nothing matches
        assert s.slot_f1 == 0.0

    def test_empty_prediction_scores_zero_not_nan(self):
        expected = [call("setLighting", room="kitchen")]
        s = score_item(expected, [])
        assert s.tool_accuracy == 0.0
        assert s.exact_match == 0.0
        assert s.slot_precision == 0.0
        assert s.slot_recall == 0.0
        assert s.slot_f1 == 0.0


class TestScoreItemMultiIntent:
    def test_both_expected_tools_predicted_in_any_order(self):
        expected = [call("setLighting", room="kitchen"), call("playMusic", genre="jazz")]
        predicted = [call("playMusic", genre="jazz"), call("setLighting", room="kitchen")]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 1.0
        assert s.exact_match == 1.0

    def test_predicting_only_one_of_two_tools_fails_item_accuracy(self):
        expected = [call("setLighting", room="kitchen"), call("playMusic", genre="jazz")]
        predicted = [call("setLighting", room="kitchen")]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 0.0
        assert s.exact_match == 0.0
        # predicted triples all correct -> precision 1.0; half of expected found
        assert s.slot_precision == pytest.approx(1.0)
        assert s.slot_recall == pytest.approx(0.5)

    def test_duplicate_expected_call_needs_duplicate_prediction(self):
        expected = [call("addItem", item="milk"), call("addItem", item="milk")]
        predicted = [call("addItem", item="milk")]
        s = score_item(expected, predicted)
        assert s.tool_accuracy == 0.0
        assert s.slot_recall == pytest.approx(0.5)


class TestCanonicalization:
    def test_string_values_compare_case_insensitively_after_strip(self):
        expected = [call("setSwitch", state="ON")]
        predicted = [call("setSwitch", state=" on ")]
        s = score_item(expected, predicted)
        assert s.exact_match == 1.0

    def test_int_and_float_of_equal_value_match(self):
        expected = [call("setLighting", brightness=50)]
        predicted = [call("setLighting", brightness=50.0)]
        assert score_item(expected, predicted).exact_match == 1.0

    def test_bool_is_not_the_number_one(self):
        expected = [call("setSwitch", state=True)]
        predicted = [call("setSwitch", state=1)]
        assert score_item(expected, predicted).exact_match == 0.0

    def test_bool_is_not_the_string_true(self):
        expected = [call("setSwitch", state=True)]
        predicted = [call("setSwitch", state="true")]
        assert score_item(expected, predicted).exact_match == 0.0

    def test_nested_argument_structures_compare_recursively(self):
        expected = [call("setScene", config={"rooms": ["kitchen", "hall"], "dim": 30})]
        predicted = [call("setScene", config={"dim": 30.0, "rooms": ["Kitchen", "hall"]})]
        assert score_item(expected, predicted).exact_match == 1.0

    def test_tool_names_compare_exactly_not_casefolded(self):
        expected = [call("setLighting")]
        predicted = [call("setlighting")]
        assert score_item(expected, predicted).tool_accuracy == 0.0


class TestAggregate:
    def test_means_and_micro_f1_over_two_items(self):
        perfect = score_item([call("a", x=1)], [call("a", x=1)])
        half = score_item(
            [call("b", x=1, y=2)],
            [call("b", x=1, y=3)],
        )
        agg = aggregate([perfect, half])
        assert agg.tool_accuracy == pytest.approx(1.0)
        assert agg.exact_match == pytest.approx(0.5)
        # micro slot counts: tp = 1 (item1) + 1 (item2 x) = 2; totals 3 and 3
        assert agg.slot_precision == pytest.approx(2 / 3)
        assert agg.slot_recall == pytest.approx(2 / 3)
        assert agg.n_items == 2

    def test_empty_aggregate_is_zero_not_nan(self):
        agg = aggregate([])
        assert agg.n_items == 0
        assert agg.tool_accuracy == 0.0
        assert agg.slot_f1 == 0.0


class TestParseToolCallsText:
    def test_parses_a_raw_json_array(self):
        calls, ok = parse_tool_calls_text(
            '[{"name": "setLighting", "arguments": {"room": "kitchen"}}]'
        )
        assert ok is True
        assert calls == [ToolCall(name="setLighting", arguments={"room": "kitchen"})]

    def test_parses_a_single_object_inside_a_json_fence(self):
        text = 'Sure!\n```json\n{"name": "playMusic", "arguments": {"genre": "jazz"}}\n```'
        calls, ok = parse_tool_calls_text(text)
        assert ok is True
        assert calls == [ToolCall(name="playMusic", arguments={"genre": "jazz"})]

    def test_missing_arguments_defaults_to_empty_dict(self):
        calls, ok = parse_tool_calls_text('[{"name": "stopMusic"}]')
        assert ok is True
        assert calls == [ToolCall(name="stopMusic", arguments={})]

    def test_garbage_fails_closed_to_empty(self):
        calls, ok = parse_tool_calls_text("I would turn on the lights for you.")
        assert calls == []
        assert ok is False

    def test_object_without_name_fails_closed(self):
        calls, ok = parse_tool_calls_text('[{"tool": "setLighting"}]')
        assert calls == []
        assert ok is False


def test_version_constant_is_pinned():
    assert A2T_SCORER_VERSION == "a2t-scorer-v1"
