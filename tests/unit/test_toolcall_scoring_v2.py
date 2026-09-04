"""Unit tests for ``reproduction.toolcall_scoring_v2`` (slice C3c,
``a2t-scorer-v2``): the S1 study's adopted V2e semantics -- ordered tool
accuracy, default-valued-extra-key stripping, numeric/boolean string
coercion -- as a standalone, real ``ToolCall``-level scorer, plus the
registry-drift fail-closed contract and the v1-untouched guarantee.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
    A2T_SCORER_VERSION,
    ToolCall,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring_v2 import (
    A2T_SCORER_V2_VERSION,
    ItemScoreV2,
    RegistryDriftError,
    aggregate_v2,
    build_registry_defaults,
    parse_argument_defaults,
    score_item_v2,
)


def _call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(name=name, arguments=dict(arguments))


# ---------------------------------------------------------------------------
# v1 stays untouched (a hard rule of this slice, not merely an assumption).
# ---------------------------------------------------------------------------


def test_v1_scorer_version_is_unchanged():
    assert A2T_SCORER_VERSION == "a2t-scorer-v1"


def test_v2_scorer_version_constant():
    assert A2T_SCORER_V2_VERSION == "a2t-scorer-v2"


# ---------------------------------------------------------------------------
# parse_argument_defaults / build_registry_defaults (moved here from the S1
# study module -- light coverage; the study's own test suite already covers
# this exhaustively, and stays green unchanged importing these back).
# ---------------------------------------------------------------------------


def test_parse_argument_defaults_quoted_string_and_float():
    assert parse_argument_defaults("zone='Driver', temperature=20.0") == {
        "zone": "Driver",
        "temperature": 20.0,
    }


def test_build_registry_defaults_keys_by_tool_name():
    rows = [
        {"tool_name": "setFanSpeed", "argument_defaults": "level=5"},
        {"tool_name": "setLighting", "argument_defaults": ""},
    ]
    assert build_registry_defaults(rows) == {"setFanSpeed": {"level": 5}, "setLighting": {}}


# ---------------------------------------------------------------------------
# tool_accuracy_ordered vs. tool_accuracy_multiset.
# ---------------------------------------------------------------------------


class TestToolAccuracyOrderedVsMultiset:
    def test_reordered_calls_flip_ordered_but_not_multiset(self):
        expected = (_call("setLighting", state="On"), _call("setFanSpeed", level=5))
        predicted = (_call("setFanSpeed", level=5), _call("setLighting", state="On"))
        registry = {"setLighting": {}, "setFanSpeed": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.tool_accuracy_multiset == 1.0
        assert item.tool_accuracy_ordered == 0.0
        assert isinstance(item, ItemScoreV2)

    def test_matching_order_scores_both_accuracies_one(self):
        expected = (_call("setLighting", state="On"), _call("setFanSpeed", level=5))
        registry = {"setLighting": {}, "setFanSpeed": {}}
        item = score_item_v2(expected, expected, registry_defaults=registry)
        assert item.tool_accuracy_ordered == 1.0
        assert item.tool_accuracy_multiset == 1.0
        assert item.exact_match == 1.0

    def test_exact_match_is_not_gated_by_ordered_tool_accuracy(self):
        # Reordered but otherwise identical calls: exact_match is the S1
        # study's adopted V2e rule -- a multiset comparison, independent of
        # tool_accuracy_ordered (module docstring's "Exact match" bullet).
        expected = (_call("setLighting", state="On"), _call("setFanSpeed", level=5))
        predicted = (_call("setFanSpeed", level=5), _call("setLighting", state="On"))
        registry = {"setLighting": {}, "setFanSpeed": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.tool_accuracy_ordered == 0.0
        assert item.exact_match == 1.0


# ---------------------------------------------------------------------------
# Default-valued extra-key stripping (V2b).
# ---------------------------------------------------------------------------


class TestDefaultKeyStripping:
    def test_default_valued_extra_key_is_stripped_and_becomes_exact(self):
        expected = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        registry = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 1.0
        assert item.extra_keys_stripped == 1

    def test_nondefault_extra_key_is_kept_and_stays_wrong(self):
        expected = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Passenger"),)
        registry = {"setZoneTemperature": {"zone": "Driver", "temperature": 20.0}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 0.0
        assert item.extra_keys_stripped == 0

    def test_missing_key_is_never_forgiven(self):
        expected = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        predicted = (_call("setZoneTemperature", temperature=22.0),)
        registry = {"setZoneTemperature": {"zone": "Driver"}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 0.0
        assert item.extra_keys_stripped == 0

    def test_stripping_never_touches_a_key_the_gold_call_itself_carries(self):
        # "zone" IS a gold key here (even though it also happens to equal
        # the registry default) -- it must never be dropped as an "extra".
        expected = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        registry = {"setZoneTemperature": {"zone": "Driver"}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.extra_keys_stripped == 0
        assert item.exact_match == 1.0

    def test_slot_f1_raw_is_lower_than_stripped_slot_f1(self):
        expected = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=22.0, zone="Driver"),)
        registry = {"setZoneTemperature": {"zone": "Driver"}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.slot_f1 == 1.0
        assert item.slot_f1_raw < 1.0


# ---------------------------------------------------------------------------
# Numeric/boolean string coercion (V2d).
# ---------------------------------------------------------------------------


class TestTypeCoercion:
    def test_numeric_string_matches_int_gold_value(self):
        expected = (_call("setFanSpeed", level=5),)
        predicted = (_call("setFanSpeed", level="5"),)
        registry = {"setFanSpeed": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 1.0
        assert item.coerced_values == 1

    def test_boolean_string_matches_bool_gold_value(self):
        expected = (_call("setSteeringWheelHeat", enabled=True),)
        predicted = (_call("setSteeringWheelHeat", enabled="true"),)
        registry = {"setSteeringWheelHeat": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 1.0
        assert item.coerced_values == 1

    def test_float_string_matches_int_gold_value(self):
        expected = (_call("setFanSpeed", level=1),)
        predicted = (_call("setFanSpeed", level="1.0"),)
        registry = {"setFanSpeed": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 1.0
        assert item.coerced_values == 1

    def test_genuinely_wrong_value_is_not_cured_by_coercion(self):
        expected = (_call("setZoneTemperature", temperature=22.0),)
        predicted = (_call("setZoneTemperature", temperature=25.0),)
        registry = {"setZoneTemperature": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.exact_match == 0.0
        assert item.coerced_values == 0

    def test_non_numeric_non_boolean_string_is_not_counted_as_coerced(self):
        expected = (_call("setLighting", zone="Driver"),)
        predicted = (_call("setLighting", zone="Driver"),)
        registry = {"setLighting": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.coerced_values == 0
        assert item.exact_match == 1.0


# ---------------------------------------------------------------------------
# Registry drift (fail-closed) vs. unknown predicted tool (tolerated).
# ---------------------------------------------------------------------------


class TestRegistryDrift:
    def test_gold_tool_name_absent_from_registry_raises(self):
        expected = (_call("setLighting", state="On"),)
        with pytest.raises(RegistryDriftError, match="setLighting"):
            score_item_v2(expected, expected, registry_defaults={})

    def test_gold_tool_name_present_with_no_defaults_does_not_raise(self):
        expected = (_call("setLighting", state="On"),)
        registry = {"setLighting": {}}
        item = score_item_v2(expected, expected, registry_defaults=registry)
        assert item.exact_match == 1.0

    def test_unknown_predicted_tool_never_matches_but_does_not_raise(self):
        expected = (_call("setLighting", state="On"),)
        predicted = (_call("neverRegisteredTool", state="On"),)
        registry = {"setLighting": {}}
        item = score_item_v2(expected, predicted, registry_defaults=registry)
        assert item.tool_accuracy_ordered == 0.0
        assert item.tool_accuracy_multiset == 0.0
        assert item.exact_match == 0.0

    def test_drift_check_scans_every_gold_call_not_only_the_first(self):
        expected = (_call("setLighting", state="On"), _call("unregisteredSecondCall"))
        registry = {"setLighting": {}}
        with pytest.raises(RegistryDriftError, match="unregisteredSecondCall"):
            score_item_v2(expected, expected, registry_defaults=registry)


# ---------------------------------------------------------------------------
# aggregate_v2.
# ---------------------------------------------------------------------------


class TestAggregateV2:
    def test_means_and_sums_over_two_items(self):
        registry = {"setLighting": {}}
        exact = _call("setLighting", state="On")
        wrong = _call("setLighting", state="Off")
        item_exact = score_item_v2((exact,), (exact,), registry_defaults=registry)
        item_wrong = score_item_v2((exact,), (wrong,), registry_defaults=registry)
        agg = aggregate_v2([item_exact, item_wrong])
        assert agg.n_items == 2
        assert agg.exact_match == 0.5
        assert agg.tool_accuracy_ordered == 1.0  # tool name always matches here
        assert agg.tool_accuracy_multiset == 1.0
        assert agg.slot_expected_total == 2
        assert agg.slot_true_positives == 1  # only the exact item's slot matched

    def test_empty_iterable_is_all_zero(self):
        agg = aggregate_v2([])
        assert agg.n_items == 0
        assert agg.exact_match == 0.0
        assert agg.tool_accuracy_ordered == 0.0
        assert agg.slot_f1 == 0.0
        assert agg.slot_f1_raw == 0.0
