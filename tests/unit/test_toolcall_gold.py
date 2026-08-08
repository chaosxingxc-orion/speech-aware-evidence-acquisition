"""Gold-side Audio2Tool call parsing (P1 scaffold): manifest entry -> ToolCall tuple.

Shapes covered here were each observed in the real tier manifests
(docs/readiness/2026-08-08-p1-engineering-notes.md records the survey):
call-strings with kwargs, bare names, domain-dotted names, CONCATENATED
call-strings inside one ``additional_tool_calls`` element, JSON-stringified
``extracted_params`` values, and a call-string whose args disagree with
``extracted_params`` (the call-string wins when parseable).
"""

import pytest

from speech_aware_evidence_acquisition.reproduction.toolcall_gold import (
    A2T_GOLD_VERSION,
    GoldParseError,
    coerce_param_value,
    expected_tool_calls_for_entry,
    parse_call_segments,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ToolCall


def test_gold_version_constant_is_pinned():
    assert A2T_GOLD_VERSION == "a2t-gold-v1"


class TestCoerceParamValue:
    def test_json_number_string_becomes_number(self):
        assert coerce_param_value("1.0") == 1.0
        assert coerce_param_value("68") == 68

    def test_json_list_string_becomes_list(self):
        assert coerce_param_value('["Weekdays"]') == ["Weekdays"]

    def test_json_bool_string_becomes_bool(self):
        assert coerce_param_value("true") is True

    def test_plain_string_stays_string(self):
        assert coerce_param_value("living_room_sensor") == "living_room_sensor"
        assert coerce_param_value("06:30") == "06:30"
        assert coerce_param_value("Armed_Away") == "Armed_Away"

    def test_non_string_passes_through(self):
        assert coerce_param_value(3) == 3
        assert coerce_param_value(None) is None


class TestParseCallSegments:
    def test_single_call_with_kwargs(self):
        segments = parse_call_segments("getAirQuality(deviceId='living_room_sensor')")
        assert segments == [("getAirQuality", {"deviceId": "living_room_sensor"})]

    def test_zero_arg_call(self):
        assert parse_call_segments("setLighting()") == [("setLighting", {})]

    def test_bare_name(self):
        assert parse_call_segments("setSecurityMode") == [("setSecurityMode", None)]

    def test_domain_dotted_name_is_stripped(self):
        segments = parse_call_segments("smart_home.setApplianceMode(deviceId='washer_1', mode='Normal')")
        assert segments == [("setApplianceMode", {"deviceId": "washer_1", "mode": "Normal"})]

    def test_concatenated_calls_split(self):
        # Observed verbatim shape (tier3 id 2560): two calls glued in ONE string.
        segments = parse_call_segments(
            "setTargetTemperature(temperature=68.0)setLighting(on=false, deviceId='bedroom_light')"
        )
        assert segments[0] == ("setTargetTemperature", {"temperature": 68.0})
        # `false` is not a Python literal: unparseable kwargs fall back to the
        # bare-identifier string form rather than dropping the call.
        assert segments[1][0] == "setLighting"
        assert segments[1][1]["deviceId"] == "bedroom_light"
        assert segments[1][1]["on"] == "false"

    def test_list_and_typed_values(self):
        segments = parse_call_segments("setAlarm(time='06:30', label='Gym', repeat=['Weekdays'])")
        assert segments == [
            ("setAlarm", {"time": "06:30", "label": "Gym", "repeat": ["Weekdays"]})
        ]

    def test_unbalanced_parens_fail_closed_to_unparsed_args(self):
        segments = parse_call_segments("setLighting(deviceId='x'")
        assert segments == [("setLighting", None)]

    def test_empty_text_yields_no_segments(self):
        assert parse_call_segments("") == []
        assert parse_call_segments("   ") == []


class TestExpectedToolCallsForEntry:
    def test_tier1_shape_zero_arg_call(self):
        entry = {
            "tool_name": "setLighting",
            "expected_tool_call": "setLighting()",
            "extracted_params": {},
            "additional_tool_calls": None,
        }
        assert expected_tool_calls_for_entry(entry) == (ToolCall("setLighting", {}),)

    def test_tier2_shape_call_string_args_win(self):
        entry = {
            "tool_name": "getAirQuality",
            "expected_tool_call": "getAirQuality(deviceId='living_room_sensor')",
            "extracted_params": {"deviceId": "living_room_sensor"},
            "additional_tool_calls": None,
        }
        (call,) = expected_tool_calls_for_entry(entry)
        assert call == ToolCall("getAirQuality", {"deviceId": "living_room_sensor"})

    def test_call_string_args_beat_incomplete_extracted_params(self):
        # Observed (tier5 id 2007): extracted_params {} while the call string
        # carries deviceId='monitor_1' -- the call string is authoritative.
        entry = {
            "tool_name": "getAirQuality_diag",
            "expected_tool_call": "smart_home.getAirQuality_diag(deviceId='monitor_1')",
            "extracted_params": {},
            "additional_tool_calls": None,
        }
        (call,) = expected_tool_calls_for_entry(entry)
        assert call.arguments == {"deviceId": "monitor_1"}

    def test_bare_primary_falls_back_to_coerced_extracted_params(self):
        entry = {
            "tool_name": "setSecurityMode",
            "expected_tool_call": "setSecurityMode",
            "extracted_params": {"mode": "Armed_Away", "level": "2"},
            "additional_tool_calls": None,
        }
        (call,) = expected_tool_calls_for_entry(entry)
        assert call.name == "setSecurityMode"
        assert call.arguments == {"mode": "Armed_Away", "level": 2}

    def test_json_stringified_extracted_params_are_coerced(self):
        entry = {
            "tool_name": "setAlarm",
            "expected_tool_call": "setAlarm",
            "extracted_params": {"time": "06:30", "repeat": '["Weekdays"]'},
            "additional_tool_calls": None,
        }
        (call,) = expected_tool_calls_for_entry(entry)
        assert call.arguments == {"time": "06:30", "repeat": ["Weekdays"]}

    def test_additional_calls_bare_and_concatenated(self):
        entry = {
            "tool_name": "setSecurityMode",
            "expected_tool_call": "setSecurityMode",
            "extracted_params": {"mode": "Armed_Away"},
            "additional_tool_calls": [
                "setTargetTemperature(temperature=68.0)setColor(color='blue')",
                "calibrateThermostat",
            ],
        }
        calls = expected_tool_calls_for_entry(entry)
        assert [call.name for call in calls] == [
            "setSecurityMode",
            "setTargetTemperature",
            "setColor",
            "calibrateThermostat",
        ]
        assert calls[1].arguments == {"temperature": 68.0}
        assert calls[2].arguments == {"color": "blue"}
        # Bare additional names carry no argument record anywhere in the
        # manifest -- documented data limitation, scored as {}.
        assert calls[3].arguments == {}

    def test_missing_tool_name_fails_closed(self):
        with pytest.raises(GoldParseError):
            expected_tool_calls_for_entry(
                {"expected_tool_call": "x()", "extracted_params": {}}
            )

    def test_blank_tool_name_fails_closed(self):
        with pytest.raises(GoldParseError):
            expected_tool_calls_for_entry(
                {"tool_name": " ", "expected_tool_call": "x()", "extracted_params": {}}
            )

    def test_malformed_extracted_params_fails_closed(self):
        with pytest.raises(GoldParseError):
            expected_tool_calls_for_entry(
                {
                    "tool_name": "setLighting",
                    "expected_tool_call": "setLighting",
                    "extracted_params": "not-a-mapping",
                }
            )

    def test_call_string_name_mismatch_keeps_tool_name_and_falls_back(self):
        # tool_name is the identity authority for the PRIMARY call; a call
        # string naming something else cannot silently rename it.
        entry = {
            "tool_name": "setLighting",
            "expected_tool_call": "somethingElse(deviceId='x')",
            "extracted_params": {"deviceId": "light_1"},
            "additional_tool_calls": None,
        }
        (call,) = expected_tool_calls_for_entry(entry)
        assert call.name == "setLighting"
        assert call.arguments == {"deviceId": "light_1"}
