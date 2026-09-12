"""Preserve registered roster selection across supported metadata forms."""

import pytest

from speech_aware_evidence_acquisition.rails.adapters.runtime_view import (
    RuntimeViewError,
    registered_population_ids,
)


@pytest.mark.parametrize("as_mapping", [False, True])
def test_population_metadata_does_not_redraw_a_bound_full_roster(as_mapping):
    rows = [{"dataset_fragment": "d", "count": 4000, "split_role": "discovery"}]
    populations = {"REGISTERED-4000": rows[0]} if as_mapping else rows
    assert registered_population_ids({"populations": populations}, "d") is None
    assert registered_population_ids({"populations": populations}, "different") is None


@pytest.mark.parametrize("as_mapping", [False, True])
def test_explicit_selection_is_exact_ordered_and_not_inferred_from_mapping_key(as_mapping):
    rows = [
        {"dataset_fragment": "other", "ids": ["foreign"]},
        {"dataset_fragment": "d", "ids": ["two", "one"]},
    ]
    populations = {"d": rows[0], "REGISTERED": rows[1]} if as_mapping else rows
    assert registered_population_ids({"populations": populations}, "d") == ("two", "one")


@pytest.mark.parametrize("as_mapping", [False, True])
def test_multiple_selections_for_one_dataset_refuse_even_if_identical(as_mapping):
    rows = [{"dataset_fragment": "d", "ids": ["one"]}] * 2
    populations = {"first": rows[0], "second": rows[1]} if as_mapping else rows
    with pytest.raises(RuntimeViewError, match="multiple"):
        registered_population_ids({"populations": populations}, "d")


@pytest.mark.parametrize("populations", [None, "d", 1, [None], ["d"], {"d": 1}])
def test_malformed_population_metadata_fails_with_a_contract_error(populations):
    with pytest.raises(RuntimeViewError, match="population"):
        registered_population_ids({"populations": populations}, "d")


@pytest.mark.parametrize("ids", [[], "", ["one", ""], ["one", None], ["one", "one"]])
@pytest.mark.parametrize("as_mapping", [False, True])
def test_explicit_invalid_selection_cannot_silently_fall_back_to_full_roster(ids, as_mapping):
    row = {"dataset_fragment": "d", "ids": ids}
    populations = {"registered": row} if as_mapping else [row]
    with pytest.raises(RuntimeViewError, match="population"):
        registered_population_ids({"populations": populations}, "d")


def test_absent_population_keeps_the_bound_dataset_roster():
    assert registered_population_ids({}, "d") is None
