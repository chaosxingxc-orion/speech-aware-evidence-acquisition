"""Unit tests for ``analysis.slurp_slot_vocabulary``.

The subject is MF-10's TRAIN-only slot-type classification and the vocabulary
cards it licenses. Every test builds its own tiny counts table, so nothing here
reads the governed corpus, MF-9's receipts, the sealed rows, or any gold.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.analysis.slurp_slot_vocabulary import (
    CARD_HEADER,
    CLOSED_MAX_NOVELTY,
    CLOSED_MIN_VERBATIM_PCT,
    CONTAINMENT_MIN_LENGTH,
    OPEN_MAX_VERBATIM_PCT,
    OPEN_MIN_NOVELTY,
    SLOT_CLASS_CLOSED,
    SLOT_CLASS_MIXED,
    SLOT_CLASS_OPEN,
    SLOT_CLASSES,
    TOKEN_PROXY_FACTOR,
    SlotVocabularyError,
    build_vocabulary_card,
    classify_slot_types,
    containment_collisions,
    derange_card_mapping,
    price_intent_cards,
    render_card_set,
    token_proxy,
)


# ---------------------------------------------------------------------------
# the stated token proxy
# ---------------------------------------------------------------------------


def test_token_proxy_is_whitespace_words_times_the_stated_factor():
    assert TOKEN_PROXY_FACTOR == 1.3
    assert token_proxy("") == 0
    assert token_proxy("one") == 2  # ceil(1 * 1.3)
    assert token_proxy("one two three four five six seven eight nine ten") == 13


def test_token_proxy_refuses_a_non_string():
    with pytest.raises(SlotVocabularyError):
        token_proxy(7)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# the classification rule
# ---------------------------------------------------------------------------


def test_thresholds_are_the_declared_ones_and_cannot_overlap():
    assert (CLOSED_MAX_NOVELTY, CLOSED_MIN_VERBATIM_PCT) == (0.10, 85.0)
    assert (OPEN_MIN_NOVELTY, OPEN_MAX_VERBATIM_PCT) == (0.35, 60.0)
    assert CLOSED_MAX_NOVELTY < OPEN_MIN_NOVELTY
    assert OPEN_MAX_VERBATIM_PCT < CLOSED_MIN_VERBATIM_PCT
    assert SLOT_CLASSES == (SLOT_CLASS_CLOSED, SLOT_CLASS_MIXED, SLOT_CLASS_OPEN)


def test_a_small_reused_vocabulary_dev_gold_stays_inside_is_closed():
    stats = classify_slot_types(
        {"transport_type": {"train": 60, "bus": 30, "taxi": 10}},
        {"transport_type": (31, 100.0)},
    )
    assert stats[0].slot_class == SLOT_CLASS_CLOSED
    assert stats[0].distinct_fillers == 3
    assert stats[0].train_mentions == 100
    assert stats[0].novelty_ratio == pytest.approx(0.03)


def test_a_new_form_per_mention_is_open_even_on_perfect_coverage():
    forms = {f"name-{n}": 1 for n in range(40)}
    stats = classify_slot_types({"person": forms}, {"person": (56, 99.0)})
    assert stats[0].slot_class == SLOT_CLASS_OPEN


def test_poor_dev_coverage_alone_is_enough_to_be_open():
    forms = {f"topic-{n}": 20 for n in range(5)}  # novelty 0.05, very closed
    stats = classify_slot_types({"news_topic": forms}, {"news_topic": (27, 40.7)})
    assert stats[0].novelty_ratio == pytest.approx(0.05)
    assert stats[0].slot_class == SLOT_CLASS_OPEN


def test_the_middle_ground_is_reported_as_mixed_not_forced():
    forms = {f"f-{n}": 5 for n in range(20)}  # novelty 0.2, neither rule fires
    stats = classify_slot_types({"food_type": forms}, {"food_type": (42, 66.7)})
    assert stats[0].slot_class == SLOT_CLASS_MIXED


def test_a_type_with_no_dev_gold_is_classified_on_train_alone_and_says_so():
    stats = classify_slot_types({"joke_type": {"funny": 40, "silly": 10}}, {})
    assert stats[0].dev_gold_mentions == 0
    assert stats[0].dev_verbatim_share_pct is None
    assert stats[0].slot_class == SLOT_CLASS_CLOSED
    assert "train-only" in stats[0].class_basis


def test_types_are_sorted_by_descending_train_mentions_then_name():
    stats = classify_slot_types(
        {"b": {"x": 5}, "a": {"x": 5}, "c": {"x": 9}},
        {},
    )
    assert [stat.entity_type for stat in stats] == ["c", "a", "b"]


def test_classify_refuses_an_empty_table_or_a_zero_count_type():
    with pytest.raises(SlotVocabularyError):
        classify_slot_types({}, {})
    with pytest.raises(SlotVocabularyError):
        classify_slot_types({"date": {"monday": 0}}, {})


def test_stats_json_carries_every_input_so_a_reader_can_reclassify():
    stats = classify_slot_types({"date": {"monday": 9, "friday": 1}}, {"date": (159, 90.57)})
    document = stats[0].as_json()
    assert document["train_mentions"] == 10
    assert document["distinct_train_fillers"] == 2
    assert document["novelty_ratio"] == 0.2
    assert document["dev_verbatim_share_pct"] == 90.57
    assert document["slot_class"] == SLOT_CLASS_MIXED


# ---------------------------------------------------------------------------
# the cards
# ---------------------------------------------------------------------------


def test_a_card_carries_every_form_ordered_by_count_then_name():
    card = build_vocabulary_card("timeofday", {"morning": 40, "evening": 40, "noon": 9})
    assert card.forms == (("evening", 40), ("morning", 40), ("noon", 9))
    assert card.train_mentions == 89
    assert card.text == "- timeofday: evening (40); morning (40); noon (9)"
    assert card.char_count == len(card.text)
    assert card.token_proxy == token_proxy(card.text)


def test_a_card_is_the_whole_vocabulary_never_a_sample():
    forms = {f"f{n}": 1 for n in range(37)}
    card = build_vocabulary_card("date", forms)
    assert len(card.forms) == 37
    assert card.as_json()["distinct_forms"] == 37


def test_an_empty_card_is_refused():
    with pytest.raises(SlotVocabularyError):
        build_vocabulary_card("date", {})


def test_a_rendered_card_set_carries_the_header_once():
    cards = [
        build_vocabulary_card("date", {"monday": 2}),
        build_vocabulary_card("time", {"nine am": 3}),
    ]
    text = render_card_set(cards)
    assert text.startswith(CARD_HEADER)
    assert text.count(CARD_HEADER) == 1
    assert text.splitlines()[1:] == [cards[0].text, cards[1].text]
    assert render_card_set([]) == ""


# ---------------------------------------------------------------------------
# per-intent pricing
# ---------------------------------------------------------------------------


def test_an_intent_is_priced_on_the_closed_types_its_block_lists():
    cards = {
        "date": build_vocabulary_card("date", {"monday": 2}),
        "time": build_vocabulary_card("time", {"nine am": 3}),
    }
    priced = price_intent_cards(
        {"alarm_set": ["date", "time", "person"], "audio_volume": ["person"]}, cards
    )
    by_intent = {cost.intent: cost for cost in priced}
    assert by_intent["alarm_set"].closed_types == ("date", "time")
    assert by_intent["alarm_set"].token_proxy > 0
    # an intent whose block lists no carded type costs nothing at all
    assert by_intent["audio_volume"].closed_types == ()
    assert by_intent["audio_volume"].token_proxy == 0
    assert by_intent["audio_volume"].char_count == 0


def test_pricing_is_sorted_and_carries_the_full_block_for_context():
    cards = {"date": build_vocabulary_card("date", {"monday": 2})}
    priced = price_intent_cards({"b_x": ["date"], "a_y": ["date"]}, cards)
    assert [cost.intent for cost in priced] == ["a_y", "b_x"]
    assert priced[0].as_json()["block_types"] == ["date"]


# ---------------------------------------------------------------------------
# the twin
# ---------------------------------------------------------------------------


def test_the_twin_rotates_within_an_intent_and_keeps_the_multiset():
    mapping = derange_card_mapping(
        {"alarm_set": ["date", "time", "timeofday"]}, ["date", "time", "timeofday"]
    )
    assert set(mapping) == {"date", "time", "timeofday"}
    assert set(mapping.values()) == {"date", "time", "timeofday"}
    assert all(key != value for key, value in mapping.items())


def test_the_twin_pools_singleton_intents_the_way_ku_s3_does():
    mapping = derange_card_mapping(
        {"a_one": ["date"], "b_one": ["time"], "c_one": ["timeofday"]},
        ["date", "time", "timeofday"],
    )
    assert set(mapping.values()) == {"date", "time", "timeofday"}
    assert all(key != value for key, value in mapping.items())


def test_the_twin_never_hands_a_type_its_own_vocabulary():
    mapping = derange_card_mapping(
        {"i1": ["a", "b"], "i2": ["b", "c"], "i3": ["c"], "i4": ["d"]},
        ["a", "b", "c", "d"],
    )
    assert all(key != value for key, value in mapping.items())
    assert set(mapping) == {"a", "b", "c", "d"}


def test_a_lone_carded_type_cannot_be_deranged():
    with pytest.raises(SlotVocabularyError):
        derange_card_mapping({"i1": ["a"]}, ["a"])


def test_the_twin_is_a_pure_function_of_its_inputs():
    blocks = {"i2": ["b", "a"], "i1": ["a", "c"], "i3": ["c", "b"]}
    first = derange_card_mapping(blocks, ["a", "b", "c"])
    second = derange_card_mapping(dict(reversed(list(blocks.items()))), ["c", "b", "a"])
    assert first == second


# ---------------------------------------------------------------------------
# containment
# ---------------------------------------------------------------------------


def test_containment_uses_the_same_eight_character_floor_the_runner_does():
    assert CONTAINMENT_MIN_LENGTH == 8
    instruction = "answer with the entity types this intent uses, e.g. tomorrow morning"
    hits = containment_collisions(["tomorrow morning", "friday", "nine am"], instruction)
    assert hits == ("tomorrow morning",)


def test_containment_reports_each_colliding_payload_once_and_sorted():
    instruction = "aaaaaaaa bbbbbbbb aaaaaaaa"
    assert containment_collisions(
        ["aaaaaaaa", "bbbbbbbb", "aaaaaaaa"], instruction
    ) == ("aaaaaaaa", "bbbbbbbb")


def test_containment_refuses_a_non_string_instruction():
    with pytest.raises(SlotVocabularyError):
        containment_collisions(["x"], None)  # type: ignore[arg-type]
