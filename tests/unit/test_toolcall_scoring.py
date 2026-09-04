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
    A2T_PARSE_VERSION,
    A2T_SCORER_VERSION,
    ToolCall,
    aggregate,
    parse_call_string_calls,
    parse_tool_calls_text,
    score_item,
)
from speech_aware_evidence_acquisition.reproduction.audio2tool_official.parse import (
    parse_tool_call as official_parse_tool_call,
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


class TestParseCallStringContract:
    """The released Audio2Tool protocol's own output contract.

    The published prompt asks for ``tool_name(param1=value1, ...)``, so every
    row of a faithful replication is a call string. Before 2026-09-04 this
    parse read only the JSON array the repository's reconstructed prompt
    asked for, and reported 0.0 with 400 parse failures on its own
    paper-facing run.
    """

    def test_single_call_with_arguments(self):
        calls, ok = parse_tool_calls_text('setLighting(room="kitchen", brightness=50)')
        assert ok is True
        assert calls == [ToolCall(name="setLighting", arguments={"room": "kitchen", "brightness": 50})]

    def test_call_without_arguments(self):
        calls, ok = parse_tool_calls_text("stopMusic()")
        assert ok is True
        assert calls == [ToolCall(name="stopMusic", arguments={})]

    def test_multi_call_string_keeps_order(self):
        calls, ok = parse_tool_calls_text("a(x=1); b()")
        assert ok is True
        assert calls == [
            ToolCall(name="a", arguments={"x": 1}),
            ToolCall(name="b", arguments={}),
        ]

    def test_multi_call_over_several_lines(self):
        text = "setTemperature(value=72)" + chr(10) + "setFanSpeed(level=high)"
        calls, ok = parse_tool_calls_text(text)
        assert ok is True
        assert [c.name for c in calls] == ["setTemperature", "setFanSpeed"]
        assert calls[1].arguments == {"level": "high"}

    def test_single_quotes_are_stripped_like_upstream(self):
        calls, _ = parse_tool_calls_text("setLighting(room='kitchen')")
        assert calls == [ToolCall(name="setLighting", arguments={"room": "kitchen"})]

    def test_boolean_and_float_values_are_coerced(self):
        calls, _ = parse_tool_calls_text("setState(enabled=true, level=0.5)")
        assert calls == [ToolCall(name="setState", arguments={"enabled": True, "level": 0.5})]

    def test_value_case_is_preserved_for_strings(self):
        calls, _ = parse_tool_calls_text("setMode(mode=Eco)")
        assert calls[0].arguments == {"mode": "Eco"}

    def test_upstream_regex_edge_case_value_stops_at_comma(self):
        # Upstream's argument regex captures ``[^,'"]+``, so a comma always
        # ends a value even inside what a human would read as one phrase.
        calls, _ = parse_tool_calls_text('sendMessage(text=hello, world)')
        assert calls[0].name == "sendMessage"
        assert calls[0].arguments == {"text": "hello"}

    def test_upstream_regex_edge_case_span_stops_at_first_paren(self):
        # ``(.*?)`` is non-greedy, so the FIRST closing paren ends the span:
        # "outer(inner(x=1)" is one match whose argument text is "inner(x=1",
        # and the trailing ")" starts no new span. Upstream reads the same
        # thing; this asserts the shared behaviour rather than a nicer one.
        calls, _ = parse_tool_calls_text("outer(inner(x=1))")
        assert calls == [ToolCall(name="outer", arguments={"x": 1})]
        assert official_parse_tool_call("outer(inner(x=1))")[0] == "outer"

    def test_span_does_not_run_across_a_newline(self):
        assert parse_call_string_calls("foo(" + chr(10) + "x=1)") == []

    def test_prose_with_a_parenthetical_is_read_as_a_call_like_upstream(self):
        # Documented, not desirable: the released parser has exactly this
        # behaviour, and the point of this branch is to read the same spans
        # the official scorer reads.
        calls, ok = parse_tool_calls_text("Use the tool (see above)")
        assert ok is True
        assert calls == [ToolCall(name="tool", arguments={})]

    def test_json_array_keeps_priority_over_a_call_shaped_span(self):
        text = '[{"name": "setLighting", "arguments": {"room": "kitchen"}}]'
        calls, ok = parse_tool_calls_text(text)
        assert ok is True
        assert calls == [ToolCall(name="setLighting", arguments={"room": "kitchen"})]

    def test_first_call_agrees_with_the_vendored_official_parser(self):
        for text in (
            'setLighting(room="kitchen", brightness=50)',
            "stopMusic()",
            "a(x=1); b()",
            "setState(enabled=true)",
        ):
            official_name, _, official_params = official_parse_tool_call(text)
            calls = parse_call_string_calls(text)
            assert calls, text
            assert calls[0].name == official_name
            assert {k: str(v) for k, v in calls[0].arguments.items()} == {
                k: str(v) for k, v in official_params.items()
            } or all(
                str(calls[0].arguments[k]).lower() == str(v).lower()
                for k, v in official_params.items()
            )

    def test_text_without_any_span_still_fails_closed(self):
        calls, ok = parse_tool_calls_text("I would turn on the lights for you.")
        assert (calls, ok) == ([], False)


def test_version_constant_is_pinned():
    assert A2T_SCORER_VERSION == "a2t-scorer-v1"


def test_parse_version_constant_is_pinned():
    assert A2T_PARSE_VERSION == "a2t-parse-v2-json-or-callstring"
