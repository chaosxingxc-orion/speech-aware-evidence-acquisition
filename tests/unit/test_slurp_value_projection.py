"""Unit tests for ``reproduction.slurp_value_projection``.

The rule under test is MF-9's TRAIN-only value projection: the same-type
sibling of the admitted legal-label projection. Every test builds its own
tiny stand-in inventory, so nothing here reads the governed corpus, the
sealed rows, or any gold.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
from speech_aware_evidence_acquisition.reproduction.slurp_value_projection import (
    SLURP_VALUE_PROJECTION_ID,
    VALUE_BRANCH_CASE_FOLD,
    VALUE_BRANCH_EMPTY,
    VALUE_BRANCH_EXACT,
    VALUE_BRANCH_NO_INVENTORY,
    VALUE_BRANCH_PROJECTED,
    VALUE_BRANCH_TOO_FAR,
    VALUE_BRANCHES,
    SlurpValueProjectionError,
    branch_counts,
    build_value_projection_inventory,
    load_value_projection_inventory,
    nearest_surface_form,
    normalize_filler,
    project_slot_value,
    project_slu_entities,
)


@dataclass(frozen=True)
class _Utterance:
    """The one attribute ``build_value_projection_inventory`` reads."""

    entities: tuple[SlotEntity, ...]


def _inventory(*rows: tuple[str, str]):
    """An inventory over ``(type, filler)`` mentions, repeats meaningful."""

    return build_value_projection_inventory(
        [_Utterance(entities=(SlotEntity(type=t, filler=f),)) for t, f in rows]
    )


# ---------------------------------------------------------------------------
# normalization
# ---------------------------------------------------------------------------


def test_normalize_folds_case_and_collapses_whitespace():
    assert normalize_filler("  Seven   AM ") == "seven am"
    assert normalize_filler("SUNDAY") == "sunday"
    assert normalize_filler("") == ""
    assert normalize_filler("   ") == ""


# ---------------------------------------------------------------------------
# the inventory
# ---------------------------------------------------------------------------


def test_inventory_groups_by_type_and_counts_mentions():
    inventory = _inventory(
        ("time", "seven am"),
        ("time", "seven am"),
        ("time", "nine am"),
        ("date", "sunday"),
    )
    assert inventory.entity_types == ("date", "time")
    assert inventory.distinct_fillers == 3
    assert inventory.counts[("time", "seven am")] == 2
    # ordered by descending mention count, so the tie-break is readable off
    # the inventory itself.
    assert inventory.fillers["time"] == ("seven am", "nine am")


def test_inventory_orders_equal_counts_lexicographically():
    inventory = _inventory(("date", "monday"), ("date", "friday"))
    assert inventory.fillers["date"] == ("friday", "monday")


def test_inventory_normalizes_and_drops_empty_fillers():
    inventory = _inventory(("date", "  SUNDAY  "), ("date", "   "), ("", "x"))
    assert inventory.fillers == {"date": ("sunday",)}


def test_inventory_identity_hash_is_content_addressed():
    left = _inventory(("date", "sunday"), ("time", "nine am"))
    right = _inventory(("time", "nine am"), ("date", "sunday"))
    other = _inventory(("date", "monday"), ("time", "nine am"))
    assert left.source_identity_hash == right.source_identity_hash
    assert left.source_identity_hash != other.source_identity_hash


def test_inventory_json_reports_shape_without_carrying_it():
    document = _inventory(("date", "sunday"), ("time", "nine am")).as_json()
    assert document["projection_id"] == SLURP_VALUE_PROJECTION_ID
    assert document["source_split"] == "train"
    assert document["entity_types"] == 2
    assert document["distinct_fillers"] == 2
    assert document["fillers_per_type"] == {"date": 1, "time": 1}
    assert "sunday" not in repr(document["fillers_per_type"])


def test_load_refuses_a_split_that_is_not_train():
    with pytest.raises(SlurpValueProjectionError, match="only from TRAIN"):
        load_value_projection_inventory({}, __file__, source_split="devel")


# ---------------------------------------------------------------------------
# the rule
# ---------------------------------------------------------------------------


def test_exact_match_is_unchanged_and_named_exact():
    inventory = _inventory(("date", "sunday"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="sunday"), inventory, threshold=0.0
    )
    assert outcome.branch == VALUE_BRANCH_EXACT
    assert outcome.changed is False
    assert outcome.distance == 0.0
    assert outcome.projected_filler == "sunday"


def test_case_fold_fires_at_threshold_zero():
    """The normalization half of the repair, and it needs no rewriting half."""

    inventory = _inventory(("date", "sunday"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="Sunday"), inventory, threshold=0.0
    )
    assert outcome.branch == VALUE_BRANCH_CASE_FOLD
    assert outcome.changed is True
    assert outcome.distance == 0.0
    assert outcome.projected_filler == "sunday"


def test_near_miss_projects_only_above_its_own_distance():
    inventory = _inventory(("date", "tomorrow"))
    entity = SlotEntity(type="date", filler="tomorow")
    # one deletion over max(8, 7) characters
    assert nearest_surface_form(inventory, "date", "tomorow") == ("tomorrow", 1 / 8)
    below = project_slot_value(entity, inventory, threshold=0.1)
    assert below.branch == VALUE_BRANCH_TOO_FAR
    assert below.changed is False
    assert below.projected_filler == "tomorow"
    above = project_slot_value(entity, inventory, threshold=0.2)
    assert above.branch == VALUE_BRANCH_PROJECTED
    assert above.changed is True
    assert above.projected_filler == "tomorrow"


def test_threshold_is_inclusive_at_the_exact_distance():
    inventory = _inventory(("date", "tomorrow"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="tomorow"), inventory, threshold=1 / 8
    )
    assert outcome.branch == VALUE_BRANCH_PROJECTED


def test_unknown_type_is_left_alone():
    inventory = _inventory(("date", "sunday"))
    outcome = project_slot_value(
        SlotEntity(type="person", filler="Alice"), inventory, threshold=0.4
    )
    assert outcome.branch == VALUE_BRANCH_NO_INVENTORY
    assert outcome.changed is False
    assert outcome.projected_filler == "Alice"


def test_empty_filler_is_left_alone():
    inventory = _inventory(("date", "sunday"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="   "), inventory, threshold=0.4
    )
    assert outcome.branch == VALUE_BRANCH_EMPTY
    assert outcome.distance is None
    assert outcome.changed is False


def test_the_rule_never_rewrites_a_slot_type():
    inventory = _inventory(("date", "sunday"), ("time", "sunday"))
    projected, outcomes = project_slu_entities(
        (SlotEntity(type="time", filler="Sunday"),), inventory, threshold=0.4
    )
    assert projected[0].type == "time"
    assert projected[0].filler == "sunday"
    assert outcomes[0].entity_type == "time"


def test_ties_break_on_the_larger_train_count_then_lexicographically():
    # "moday" is one edit from both "monday" and "friday"? no -- build an
    # explicit tie: "xy" is distance 1/2 from both "ay" and "by".
    inventory = _inventory(("date", "by"), ("date", "by"), ("date", "ay"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="xy"), inventory, threshold=0.5
    )
    assert outcome.projected_filler == "by"  # the more frequent of the two
    balanced = _inventory(("date", "by"), ("date", "ay"))
    outcome = project_slot_value(
        SlotEntity(type="date", filler="xy"), balanced, threshold=0.5
    )
    assert outcome.projected_filler == "ay"  # equal counts, lexicographic


def test_entities_keep_their_order_and_their_count():
    inventory = _inventory(("date", "sunday"), ("time", "nine am"))
    entities = (
        SlotEntity(type="time", filler="Nine AM"),
        SlotEntity(type="date", filler="Sunday"),
        SlotEntity(type="person", filler="Alice"),
    )
    projected, outcomes = project_slu_entities(entities, inventory, threshold=0.0)
    assert len(projected) == len(entities) == len(outcomes)
    assert [entity.type for entity in projected] == ["time", "date", "person"]
    assert [entity.filler for entity in projected] == ["nine am", "sunday", "Alice"]


def test_threshold_must_be_a_number_in_range():
    inventory = _inventory(("date", "sunday"))
    entity = SlotEntity(type="date", filler="sunday")
    for bad in (True, "0.2", None, -0.1, 1.5):
        with pytest.raises(SlurpValueProjectionError):
            project_slot_value(entity, inventory, threshold=bad)


# ---------------------------------------------------------------------------
# the memo a sweep uses
# ---------------------------------------------------------------------------


def test_nearest_cache_reproduces_the_uncached_answer():
    inventory = _inventory(("date", "tomorrow"), ("date", "today"))
    entities = (SlotEntity(type="date", filler="Tomorow"),)
    cache: dict[tuple[str, str], tuple[str, float] | None] = {}
    for threshold in (0.0, 0.1, 0.2, 0.3, 0.4):
        cached, _ = project_slu_entities(
            entities, inventory, threshold=threshold, nearest_cache=cache
        )
        plain, _ = project_slu_entities(entities, inventory, threshold=threshold)
        assert cached == plain
    assert cache == {("date", "tomorow"): ("tomorrow", 1 / 8)}


def test_a_memo_from_the_wrong_type_is_refused():
    inventory = _inventory(("date", "sunday"), ("time", "nine am"))
    with pytest.raises(SlurpValueProjectionError, match="not a TRAIN surface form"):
        project_slot_value(
            SlotEntity(type="date", filler="sunday"),
            inventory,
            threshold=0.4,
            nearest=("nine am", 0.0),
        )


def test_nearest_surface_form_is_none_for_an_unknown_type():
    assert nearest_surface_form(_inventory(("date", "sunday")), "person", "alice") is None


# ---------------------------------------------------------------------------
# receipts
# ---------------------------------------------------------------------------


def test_branch_counts_zero_fill_every_branch():
    inventory = _inventory(("date", "sunday"))
    _, outcomes = project_slu_entities(
        (
            SlotEntity(type="date", filler="Sunday"),
            SlotEntity(type="person", filler="Alice"),
        ),
        inventory,
        threshold=0.0,
    )
    counts = branch_counts(outcomes)
    assert set(counts) == set(VALUE_BRANCHES)
    assert counts[VALUE_BRANCH_CASE_FOLD] == 1
    assert counts[VALUE_BRANCH_NO_INVENTORY] == 1
    assert counts[VALUE_BRANCH_EXACT] == 0
