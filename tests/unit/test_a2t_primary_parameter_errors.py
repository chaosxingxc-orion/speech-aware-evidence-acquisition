from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_primary_parameter_errors import (
    PrimaryParameterError,
    diagnose_primary_parameters,
)


def test_retains_simultaneous_error_types_and_emits_no_values():
    predicted = {
        " Mode ": " ECO ",
        "temperature": "20.0",
        "zone": "Passenger",
        "volume": 3,
    }
    reference = {"mode": "eco", "temperature": 20, "enabled": True}
    defaults = {" ZONE ": " passenger ", "volume": 2}

    result = diagnose_primary_parameters(predicted, reference, defaults)

    assert result == {
        "correct_keys": ["mode"],
        "missing_keys": ["enabled"],
        "extra_keys": ["volume", "zone"],
        "wrong_value_keys": ["temperature"],
        "correct_normalized_key_count": 1,
        "predicted_normalized_key_count": 4,
        "reference_normalized_key_count": 3,
        "param_exact": False,
        "extra_keys_matching_declared_defaults": ["zone"],
        "wrong_keys_equal_under_repo_coercion": ["temperature"],
        "predicted_normalized_key_collision_count": 0,
        "reference_normalized_key_collision_count": 0,
        "default_normalized_key_collision_count": 0,
    }
    assert "20.0" not in repr(result)
    assert "Passenger" not in repr(result)


def test_empty_mappings_are_exact():
    assert diagnose_primary_parameters({}, {}, {}) == {
        "correct_keys": [],
        "missing_keys": [],
        "extra_keys": [],
        "wrong_value_keys": [],
        "correct_normalized_key_count": 0,
        "predicted_normalized_key_count": 0,
        "reference_normalized_key_count": 0,
        "param_exact": True,
        "extra_keys_matching_declared_defaults": [],
        "wrong_keys_equal_under_repo_coercion": [],
        "predicted_normalized_key_collision_count": 0,
        "reference_normalized_key_collision_count": 0,
        "default_normalized_key_collision_count": 0,
    }


def test_official_key_value_normalization_defines_equality_and_sorted_keys():
    result = diagnose_primary_parameters(
        {" Zeta ": " VALUE ", "alpha": True},
        {"zeta": "value", " ALPHA ": " true "},
        {},
    )

    assert result["correct_keys"] == ["alpha", "zeta"]
    assert result["wrong_value_keys"] == []
    assert result["param_exact"] is True


def test_reports_normalized_key_collisions_without_mutating_inputs():
    predicted = {" A ": 1, "a": 2}
    reference = {" A ": 1, "a": 2}
    defaults = {" X ": 1, "x": 2}
    before = copy.deepcopy((predicted, reference, defaults))

    result = diagnose_primary_parameters(predicted, reference, defaults)

    assert (predicted, reference, defaults) == before
    assert result["correct_keys"] == ["a"]
    assert result["predicted_normalized_key_count"] == 1
    assert result["reference_normalized_key_count"] == 1
    assert result["predicted_normalized_key_collision_count"] == 1
    assert result["reference_normalized_key_collision_count"] == 1
    assert result["default_normalized_key_collision_count"] == 1
    assert result["param_exact"] is True


def test_numeric_format_mismatch_is_only_a_repo_coercion_diagnostic():
    result = diagnose_primary_parameters(
        {"integer": "1.0", "float": "2"},
        {"integer": 1, "float": 2.0},
        {},
    )

    assert result["wrong_value_keys"] == ["float", "integer"]
    assert result["wrong_keys_equal_under_repo_coercion"] == ["float", "integer"]
    assert result["param_exact"] is False


@pytest.mark.parametrize("argument", ["predicted", "reference", "defaults"])
def test_rejects_non_mapping_arguments(argument: str):
    values = {"predicted": {}, "reference": {}, "defaults": {}}
    values[argument] = []

    with pytest.raises(PrimaryParameterError, match=argument):
        diagnose_primary_parameters(**values)


@pytest.mark.parametrize("bad_key", [1, True, None, "", "   "])
@pytest.mark.parametrize("argument", ["predicted", "reference", "defaults"])
def test_rejects_malformed_keys(argument: str, bad_key: object):
    values = {"predicted": {}, "reference": {}, "defaults": {}}
    values[argument] = {bad_key: "value"}

    with pytest.raises(PrimaryParameterError, match="key"):
        diagnose_primary_parameters(**values)
