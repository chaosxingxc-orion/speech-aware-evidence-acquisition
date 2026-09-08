"""Unit tests for ``reproduction.slurp_slot_normalizer``.

The rule under test is MF-10's slot-value normalizer -- the Whisper-normalizer
analogue for SLURP fillers, applied SYMMETRICALLY to gold and prediction before
the official distance blocks. Every test builds its own tiny stand-in
inventory, so nothing here reads the governed corpus, the sealed rows, or any
gold.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
from speech_aware_evidence_acquisition.reproduction.slurp_slot_normalizer import (
    LEADING_TOKEN_CANDIDATES,
    LEADING_TOKEN_MIN_WITNESSES,
    MERIDIEM_JOINS,
    SLURP_SLOT_NORMALIZER_ID,
    SLURP_SLOT_NORMALIZER_RULES,
    SLURP_SLU_NORMALIZED_SCORER_ID,
    SlurpSlotNormalizerError,
    build_slot_normalizer_inventory,
    learn_leading_prepositions,
    load_slot_normalizer_inventory,
    normalize_slot_entities,
    normalize_slot_value,
)

R0 = SLURP_SLOT_NORMALIZER_RULES[:1]
R01 = SLURP_SLOT_NORMALIZER_RULES[:2]
R012 = SLURP_SLOT_NORMALIZER_RULES[:3]
ALL_RULES = SLURP_SLOT_NORMALIZER_RULES


@dataclass(frozen=True)
class _Utterance:
    """The one attribute ``build_slot_normalizer_inventory`` reads."""

    entities: tuple[SlotEntity, ...]


def _inventory(*rows: tuple[str, str], min_witnesses: int = 1):
    return build_slot_normalizer_inventory(
        [_Utterance(entities=(SlotEntity(type=t, filler=f),)) for t, f in rows],
        min_witnesses=min_witnesses,
    )


# ---------------------------------------------------------------------------
# identity and rule ordering
# ---------------------------------------------------------------------------


def test_ids_are_pinned():
    assert SLURP_SLOT_NORMALIZER_ID == "saea-slurp-slot-normalizer-v1"
    assert SLURP_SLU_NORMALIZED_SCORER_ID == "slurp-slu-f1-normalized-v1"
    assert SLURP_SLOT_NORMALIZER_RULES == (
        "R0-case-whitespace",
        "R1-whisper-english",
        "R2-meridiem-join",
        "R3-train-leading-preposition",
    )


def test_rules_must_be_a_prefix_not_a_set():
    with pytest.raises(SlurpSlotNormalizerError):
        normalize_slot_value("x", "date", None, rules=("R2-meridiem-join",))
    with pytest.raises(SlurpSlotNormalizerError):
        normalize_slot_value(
            "x", "date", None, rules=("R1-whisper-english", "R0-case-whitespace")
        )


def test_r3_without_an_inventory_is_refused():
    with pytest.raises(SlurpSlotNormalizerError):
        normalize_slot_value("on wednesday", "date", None, rules=ALL_RULES)


def test_a_non_string_value_is_refused():
    with pytest.raises(SlurpSlotNormalizerError):
        normalize_slot_value(7, "date", None, rules=R0)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# R0 -- case and whitespace
# ---------------------------------------------------------------------------


def test_r0_folds_case_and_collapses_whitespace():
    assert normalize_slot_value("  Seven   AM ", "time", None, rules=R0) == "seven am"
    assert normalize_slot_value("SUNDAY", "date", None, rules=R0) == "sunday"
    assert normalize_slot_value("", "date", None, rules=R0) == ""


def test_r0_alone_closes_the_pure_casing_artefact():
    """MF-9 section 1.4: a pure case difference costs a word distance of 1.0."""

    gold = normalize_slot_value("i will always love you", "song_name", None, rules=R0)
    predicted = normalize_slot_value(
        "I Will Always Love You", "song_name", None, rules=R0
    )
    assert gold == predicted


# ---------------------------------------------------------------------------
# R1 -- the vendored Whisper English normalizer, and its guard
# ---------------------------------------------------------------------------


def test_r1_expands_number_words_symmetrically():
    assert normalize_slot_value("seven am", "time", None, rules=R01) == "7 am"
    assert normalize_slot_value("7 am", "time", None, rules=R01) == "7 am"


def test_r1_does_not_by_itself_align_the_spaced_meridiem():
    """The measurement R2 exists for: Whisper leaves ``a m`` split."""

    assert normalize_slot_value("six am", "time", None, rules=R01) == "6 am"
    assert normalize_slot_value("six a m", "time", None, rules=R01) == "6 a m"


def test_r1_never_empties_a_non_empty_value():
    """``hmm`` / ``uh`` / ``um`` / ``&`` are disfluency and symbol rules that
    are right for a transcript and wrong for a one-token slot value."""

    for value in ("hmm", "uh", "um", "&"):
        assert normalize_slot_value(value, "general_name", None, rules=R01) == value


def test_r1_keeps_an_empty_value_empty():
    assert normalize_slot_value("", "date", None, rules=R01) == ""


# ---------------------------------------------------------------------------
# R2 -- the meridiem join
# ---------------------------------------------------------------------------


def test_r2_joins_both_spellings_onto_the_corpus_form():
    """The corpus writes ``six am``; R1 makes that ``6 am``, and R2 brings the
    spaced spelling onto exactly that string rather than onto a third one."""

    assert normalize_slot_value("six a m", "time", None, rules=R012) == "6 am"
    assert normalize_slot_value("six am", "time", None, rules=R012) == "6 am"
    assert normalize_slot_value("three p m", "time", None, rules=R012) == "3 pm"
    assert normalize_slot_value("three pm", "time", None, rules=R012) == "3 pm"


def test_r2_aligns_the_period_spelling_through_r1():
    """``6 a.m.`` -> ``6 a m`` (R1) -> ``6 am`` (R2)."""

    assert normalize_slot_value("6 a.m.", "time", None, rules=R012) == "6 am"
    assert normalize_slot_value("6 a m", "time", None, rules=R012) == "6 am"


def test_r2_does_not_touch_a_word_that_merely_ends_in_a_or_p():
    assert normalize_slot_value("map merge", "general_name", None, rules=R012) == (
        "map merge"
    )
    assert normalize_slot_value("a monday", "date", None, rules=R012) == "a monday"


def test_meridiem_table_is_the_two_forms_and_nothing_else():
    assert dict(MERIDIEM_JOINS) == {"a m": "am", "p m": "pm"}


# ---------------------------------------------------------------------------
# R3 -- the TRAIN-learned leading-token strip
# ---------------------------------------------------------------------------


def test_learn_requires_the_corpus_to_witness_the_pair():
    admitted, _rejected, counts, _examples = learn_leading_prepositions(
        {"date": {"on monday", "monday", "on tuesday", "tuesday"}}, min_witnesses=2
    )
    assert admitted == ("on",)
    assert counts["on"] == 2


def test_learn_refuses_a_token_below_the_witness_floor():
    admitted, _rejected, _counts, _examples = learn_leading_prepositions(
        {"date": {"on monday", "monday"}}, min_witnesses=2
    )
    assert admitted == ()


def test_learn_counts_only_pairs_whose_remainder_is_the_same_type():
    admitted, _rejected, _counts, _examples = learn_leading_prepositions(
        {"date": {"on monday"}, "time": {"monday"}}, min_witnesses=1
    )
    assert admitted == ()


def test_learn_orders_by_descending_witness_count_then_name():
    admitted, _rejected, _counts, _examples = learn_leading_prepositions(
        {"date": {"on a", "a", "on b", "b", "at c", "c"}}, min_witnesses=1
    )
    assert admitted == ("on", "at")


def test_the_candidate_set_is_declared_and_the_corpus_only_confirms():
    """The defect the false-merge audit caught: the corpus witnesses `next`
    exactly as faithfully as it witnesses `the`, and stripping it merges
    `next week` with `last week`."""

    fillers = {
        "date": {
            "next week",
            "last week",
            "this week",
            "week",
            "the month",
            "month",
            "the year",
            "year",
            "the day",
            "day",
        }
    }
    admitted, rejected, counts, _examples = learn_leading_prepositions(
        fillers, min_witnesses=3
    )
    assert "next" not in admitted
    assert "the" in admitted
    assert "next" in rejected or counts.get("next", 0) < 3
    unrestricted, no_rejects, _c, _e = learn_leading_prepositions(
        fillers, min_witnesses=1, candidates=None
    )
    assert "next" in unrestricted
    assert no_rejects == ()


def test_the_candidate_set_is_the_declared_function_words():
    assert LEADING_TOKEN_CANDIDATES == (
        "a",
        "an",
        "at",
        "by",
        "for",
        "in",
        "of",
        "on",
        "the",
        "to",
    )


def test_learn_refuses_a_bad_floor():
    with pytest.raises(SlurpSlotNormalizerError):
        learn_leading_prepositions({}, min_witnesses=0)
    with pytest.raises(SlurpSlotNormalizerError):
        learn_leading_prepositions({}, min_witnesses=True)  # type: ignore[arg-type]


def test_r3_strips_only_when_the_remainder_is_a_train_filler_of_that_type():
    inventory = _inventory(
        ("date", "on monday"),
        ("date", "monday"),
        ("date", "on tuesday"),
        ("date", "tuesday"),
        min_witnesses=2,
    )
    assert inventory.leading_tokens == ("on",)
    assert normalize_slot_value("on monday", "date", inventory, rules=ALL_RULES) == (
        "monday"
    )
    # same leading token, remainder is not a TRAIN filler of this type
    assert normalize_slot_value("on venus", "date", inventory, rules=ALL_RULES) == (
        "on venus"
    )
    # same remainder, but the type has no such filler
    assert normalize_slot_value("on monday", "time", inventory, rules=ALL_RULES) == (
        "on monday"
    )


def test_r3_strips_at_most_one_token():
    inventory = _inventory(
        ("place_name", "the olive garden"),
        ("place_name", "olive garden"),
        ("place_name", "the red lion"),
        ("place_name", "red lion"),
        min_witnesses=2,
    )
    assert normalize_slot_value(
        "the olive garden", "place_name", inventory, rules=ALL_RULES
    ) == "olive garden"


def test_r3_leaves_a_single_token_value_alone():
    inventory = _inventory(
        ("date", "on monday"), ("date", "monday"), min_witnesses=1
    )
    assert normalize_slot_value("monday", "date", inventory, rules=ALL_RULES) == (
        "monday"
    )


# ---------------------------------------------------------------------------
# the inventory
# ---------------------------------------------------------------------------


def test_inventory_stores_normalized_forms_and_a_stable_identity():
    left = _inventory(("time", "Six A M"), ("time", "six am"))
    right = _inventory(("time", "six a m"), ("time", "SIX AM"))
    assert left.fillers["time"] == right.fillers["time"] == frozenset({"6 am"})
    assert left.source_identity_hash == right.source_identity_hash


def test_inventory_counts_utterances_not_mentions():
    inventory = _inventory(("date", "monday"), ("date", "tuesday"))
    assert inventory.utterance_count == 2
    assert inventory.distinct_fillers == 2
    assert inventory.entity_types == ("date",)


def test_inventory_json_carries_the_rejected_tokens_as_evidence():
    inventory = _inventory(
        ("date", "next week"),
        ("date", "last week"),
        ("date", "this week"),
        ("date", "week"),
        min_witnesses=1,
    )
    document = inventory.as_json()
    assert "next" in document["rejected_tokens"]
    assert "next" not in document["leading_tokens"]
    assert document["candidate_set"] == list(LEADING_TOKEN_CANDIDATES)
    assert document["rejected_token_witnesses"]["next"] >= 1
    assert "next week" in str(document["rejected_token_examples"]["next"])


def test_inventory_json_carries_the_rule_and_the_evidence():
    inventory = _inventory(
        ("date", "on monday"),
        ("date", "monday"),
        ("date", "on tuesday"),
        ("date", "tuesday"),
        min_witnesses=2,
    )
    document = inventory.as_json()
    assert document["normalizer_id"] == SLURP_SLOT_NORMALIZER_ID
    assert document["source_split"] == "train"
    assert document["min_witnesses"] == 2
    assert document["leading_tokens"] == ["on"]
    assert document["leading_token_witnesses"] == {"on": 2}
    assert document["leading_token_examples"]["on"]


def test_inventory_skips_blank_types_and_fillers():
    inventory = build_slot_normalizer_inventory(
        [
            _Utterance(
                entities=(
                    SlotEntity(type="", filler="monday"),
                    SlotEntity(type="date", filler="   "),
                    SlotEntity(type="date", filler="monday"),
                )
            )
        ]
    )
    assert inventory.fillers == {"date": frozenset({"monday"})}


def test_the_loader_refuses_any_split_but_train():
    with pytest.raises(SlurpSlotNormalizerError):
        load_slot_normalizer_inventory({}, __import__("pathlib").Path("."), source_split="devel")
    with pytest.raises(SlurpSlotNormalizerError):
        load_slot_normalizer_inventory({}, __import__("pathlib").Path("."), source_split="test")


def test_default_witness_floor_is_the_declared_one():
    assert LEADING_TOKEN_MIN_WITNESSES == 3


# ---------------------------------------------------------------------------
# whole-prediction normalization
# ---------------------------------------------------------------------------


def test_normalize_entities_preserves_length_order_and_type():
    inventory = _inventory(("date", "monday"))
    entities = (
        SlotEntity(type="date", filler="Monday"),
        SlotEntity(type="time", filler="Six A M"),
        SlotEntity(type="place_name", filler="Orlando"),
    )
    out = normalize_slot_entities(entities, inventory, rules=ALL_RULES)
    assert [e.type for e in out] == ["date", "time", "place_name"]
    assert [e.filler for e in out] == ["monday", "6 am", "orlando"]


def test_the_cache_is_a_memo_not_an_override():
    inventory = _inventory(("date", "monday"))
    cache: dict[tuple[str, str], str] = {}
    first = normalize_slot_entities(
        (SlotEntity(type="date", filler="Monday"),), inventory, cache=cache
    )
    second = normalize_slot_entities(
        (SlotEntity(type="date", filler="Monday"),), inventory, cache=cache
    )
    assert cache == {("date", "Monday"): "monday"}
    assert first == second


def test_the_normalizer_is_symmetric_on_the_mf9_surface_examples():
    """Every example MF-9 section 1.4 printed, gold and prediction alike."""

    inventory = _inventory(
        ("date", "on wednesday"),
        ("date", "wednesday"),
        ("date", "on friday"),
        ("date", "friday"),
        ("place_name", "the olive garden"),
        ("place_name", "olive garden"),
        ("place_name", "the red lion"),
        ("place_name", "red lion"),
        min_witnesses=2,
    )
    pairs = [
        ("time", "six am", "six a m"),
        ("time", "three pm", "three p m"),
        ("time", "ten am", "ten a m"),
        ("song_name", "i will always love you", "I Will Always Love You"),
        ("date", "wednesday", "on wednesday"),
        ("place_name", "olive garden", "the olive garden"),
    ]
    for entity_type, gold, predicted in pairs:
        assert normalize_slot_value(
            gold, entity_type, inventory, rules=ALL_RULES
        ) == normalize_slot_value(predicted, entity_type, inventory, rules=ALL_RULES)


def test_the_normalizer_does_not_align_a_genuinely_different_value():
    inventory = _inventory(("place_name", "orlando"), ("place_name", "boston"))
    assert normalize_slot_value(
        "orlando", "place_name", inventory, rules=ALL_RULES
    ) != normalize_slot_value("boston", "place_name", inventory, rules=ALL_RULES)
    assert normalize_slot_value(
        "hilary email issue", "news_topic", inventory, rules=R012
    ) != normalize_slot_value("hillary email issue", "news_topic", inventory, rules=R012)
