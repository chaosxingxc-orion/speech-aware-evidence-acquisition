"""Unit tests for the Earnings-22 DEV semantic error taxonomy.

Synthetic pairs only. Nothing here reads the sealed outputs, the reference layer
or the segment table: the flight-level identity gate against the sealed S/D/I
totals lives in ``build_receipts`` and is exercised by the runner, while these
tests pin the pieces it is built from.
"""

from __future__ import annotations

import random
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (
    ALL_RULES,
    AUTHORIZED_FOLD_RULES,
    CATEGORIES,
    GAP_BINS,
    IMPACT_NEUTRAL_CATEGORIES,
    IMPACT_NEUTRAL_RULES,
    READ_SAMPLE_SEED,
    ErrorSpan,
    ScoredSpan,
    UtteranceContext,
    agentic_error_rate,
    align_spans,
    build_entity_inventory,
    classify_span,
    gap_bins,
    normalized_tokens,
    semantic_impact,
    stratified_sample,
    tag_anchor_indices,
    truncation_stems,
)
from speech_aware_evidence_acquisition.scoring import align


def make_context(
    reference: str,
    hypothesis: str,
    *,
    sample_id: str = "4453225-1",
    call: str = "4453225",
    previous: str = "",
    following: str = "",
    entities: frozenset[str] = frozenset(),
    duration_s: float = 5.0,
) -> UtteranceContext:
    return UtteranceContext(
        sample_id=sample_id,
        call=call,
        raw_reference=reference,
        raw_hypothesis=hypothesis,
        ref_tokens=normalized_tokens(reference),
        hyp_tokens=normalized_tokens(hypothesis),
        duration_s=duration_s,
        stems=truncation_stems(reference),
        tag_anchors=tag_anchor_indices(reference),
        previous_tokens=normalized_tokens(previous),
        next_tokens=normalized_tokens(following),
        entity_forms=entities,
    )


def classify_all(context: UtteranceContext) -> list[tuple[str, str, ErrorSpan]]:
    alignment = align_spans(context.ref_tokens, context.hyp_tokens)
    return [(*classify_span(span, context), span) for span in alignment.spans]


def rules_of(context: UtteranceContext) -> list[str]:
    return [rule for _, rule, _ in classify_all(context)]


# ---------------------------------------------------------------------------
# The identity gate: the aligner is the frozen aligner
# ---------------------------------------------------------------------------


def test_align_spans_reproduces_the_frozen_aligner_on_random_pairs():
    rng = random.Random(20260906)
    vocabulary = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]
    for _ in range(400):
        ref = [rng.choice(vocabulary) for _ in range(rng.randint(0, 12))]
        hyp = [rng.choice(vocabulary) for _ in range(rng.randint(0, 12))]
        frozen = align(ref, hyp)
        measured = align_spans(ref, hyp)
        assert (measured.substitutions, measured.deletions, measured.insertions) == (
            frozen.substitutions,
            frozen.deletions,
            frozen.insertions,
        )
        assert measured.reference_length == frozen.reference_length


def test_align_spans_merges_adjacent_same_typed_operations():
    alignment = align_spans(["a", "b", "c", "d"], ["a", "x", "y", "d"])
    assert [span.op for span in alignment.spans] == ["SUB"]
    span = alignment.spans[0]
    assert span.ref_tokens == ("b", "c") and span.hyp_tokens == ("x", "y")
    assert span.ref_left == ("a",) and span.ref_right == ("d",)


def test_align_spans_keeps_different_operations_in_different_spans():
    alignment = align_spans(["a", "b", "c"], ["a", "x", "b", "c"])
    assert [span.op for span in alignment.spans] == ["INS"]
    alignment = align_spans(["a", "b", "c"], ["a", "c"])
    assert [(span.op, span.ref_tokens) for span in alignment.spans] == [("DEL", ("b",))]


def test_insertion_charges_one_reference_word_and_deletion_charges_its_own():
    insertion = align_spans(["a"], ["a", "b"]).spans[0]
    deletion = align_spans(["a", "b"], ["a"]).spans[0]
    assert insertion.reference_word_charge == 1
    assert deletion.reference_word_charge == 1
    substitution = align_spans(["a", "b", "c"], ["a", "x", "y"]).spans[0]
    assert substitution.reference_word_charge == 2


# ---------------------------------------------------------------------------
# Rule 1: format / convention equivalents
# ---------------------------------------------------------------------------


def test_merge_compound_fires_across_the_span_boundary():
    context = make_context("in the U.S. and Europe", "in the US and Europe")
    assert "format-convention/merge-compound" in rules_of(context)


def test_merge_compound_does_not_fire_on_a_genuinely_missing_word():
    context = make_context("go back 2 to 3 years", "go back 23 years")
    assert "format-convention/merge-compound" not in rules_of(context)


def test_symbol_only_covers_a_difference_of_layout_punctuation_alone():
    context = replace(
        make_context("placeholder", "placeholder"),
        ref_tokens=("we", "grew", "b.c", "again"),
        hyp_tokens=("we", "grew", "bc", "again"),
    )
    assert rules_of(context) == ["format-convention/symbol-only"]


def test_a_sign_flip_is_never_a_format_equivalence():
    context = make_context("gone from minus 18 to minus 5", "gone from 18 to 5")
    assert not any(rule.startswith("format-convention/") for rule in rules_of(context))


def test_a_dropped_percent_sign_is_never_a_format_equivalence():
    context = make_context("a tier one at 14.9 percent", "a tier one at 14.9")
    assert not any(rule.startswith("format-convention/") for rule in rules_of(context))


def test_a_token_with_no_alphanumeric_character_is_a_stray_punctuation_token():
    context = make_context("move to the presentation ..", "move to the presentation")
    assert "format-convention/stray-punctuation-token" in rules_of(context)


# ---------------------------------------------------------------------------
# Rule 2: reference-style conventions
# ---------------------------------------------------------------------------


def test_empty_reference_is_named_rather_than_dropped():
    context = make_context("Um.", "Thank you.")
    assert context.reference_empty
    assert set(rules_of(context)) == {"reference-convention/empty-reference"}


def test_an_insertion_where_a_tag_was_removed_is_a_redacted_region():
    context = make_context("we saw <inaudible> growth", "we saw double digit growth")
    assert "reference-convention/redacted-region" in rules_of(context)


def test_a_truncated_word_stem_is_a_reference_convention():
    context = make_context("the Co- Covid conditions", "the Covid conditions")
    assert truncation_stems("the Co- Covid conditions") == frozenset({"co"})
    assert "reference-convention/false-start-stem" in rules_of(context)


def test_a_repeated_reference_word_the_model_says_once_is_a_reference_convention():
    context = make_context("we are a a big player", "we are a big player")
    assert "reference-convention/reference-repetition" in rules_of(context)


def test_a_mixed_deletion_of_a_repetition_and_a_stem_is_still_a_reference_convention():
    context = make_context("averaging the, the ha- two halves", "averaging the two halves")
    rules = rules_of(context)
    assert any(rule.startswith("reference-convention/") for rule in rules)


def test_a_content_deletion_is_not_a_reference_convention():
    context = make_context("we cut the dividend twice", "we cut twice")
    assert not any(rule.startswith("reference-convention/") for rule in rules_of(context))


def test_one_backchannel_spelled_as_another_is_a_reference_convention():
    context = make_context("Yep.", "Yeah.")
    assert rules_of(context) == ["reference-convention/backchannel-variant"]


def test_a_discourse_phrase_deletion_is_named_separately_from_a_filler():
    context = make_context("prices are, you know, still moving", "prices are still moving")
    assert "reference-convention/discourse-phrase" in rules_of(context)


# ---------------------------------------------------------------------------
# Rule 3: segmentation artifacts
# ---------------------------------------------------------------------------


def test_a_tail_run_the_next_utterance_carries_is_a_neighbour_bleed():
    context = make_context(
        "welcome to the results presentation.",
        "welcome to the results presentation. Thanks so much for joining us.",
        following="Thanks so much for joining us.",
    )
    assert "segmentation-artifact/neighbour-bleed" in rules_of(context)


def test_the_same_tail_run_without_a_matching_neighbour_is_a_runaway():
    context = make_context(
        "welcome to the results presentation.",
        "welcome to the results presentation. Thanks so much for joining us.",
        following="A completely different sentence about pricing.",
    )
    assert "model-behaviour/runaway-tail" in rules_of(context)


def test_one_or_two_words_past_the_reference_end_are_a_boundary_continuation():
    context = make_context("of the last year", "of the last year next slide")
    assert "segmentation-artifact/boundary-continuation" in rules_of(context)


def test_one_or_two_words_before_the_reference_start_are_a_boundary_onset():
    context = make_context("we thought that would help", "and we thought that would help")
    assert "segmentation-artifact/boundary-onset" in rules_of(context)


# ---------------------------------------------------------------------------
# Rules 4 and 5: named entities and domain vocabulary
# ---------------------------------------------------------------------------


def test_a_call_entity_that_comes_back_wrong_is_a_named_entity_error():
    context = make_context(
        "let Mohammed elaborate",
        "let Mohamed elaborate",
        entities=frozenset({"mohammed"}),
    )
    assert rules_of(context) == ["named-entity/call-inventory"]


def test_a_pinned_domain_term_that_comes_back_wrong_is_a_domain_term_error():
    context = make_context("the normalized EBITDA line", "the normalized ebita line")
    assert rules_of(context) == ["domain-term/pinned-lexicon"]


def test_the_entity_inventory_refuses_pronouns_function_words_and_domain_terms():
    inventory = build_entity_inventory(
        {
            "4453225": [
                "We think I should ask about IT spend.",
                "The US EBITDA line and Aspen delivered.",
                "Aspen and Aspen again, the US result was IT driven.",
            ]
        }
    )
    forms = inventory["4453225"]
    assert "aspen" in forms
    assert "i" not in forms and "it" not in forms and "us" not in forms
    assert "ebitda" not in forms


def test_a_long_insertion_containing_an_entity_is_not_charged_as_an_entity_error():
    context = make_context(
        "we are done here",
        "we are done here and Aspen will report again next quarter",
        entities=frozenset({"aspen"}),
        following="Something else entirely.",
    )
    assert "named-entity/call-inventory" not in rules_of(context)


# ---------------------------------------------------------------------------
# Rule 6: model behaviour
# ---------------------------------------------------------------------------


def test_a_non_latin_script_hypothesis_is_model_behaviour():
    context = make_context("Sorry.", "Sorry. " + chr(0x5BF9) * 3)
    assert "model-behaviour/non-english-script" in rules_of(context)


def test_a_three_times_repeated_ngram_is_a_hypothesis_loop():
    context = make_context(
        "that is all from my side",
        "that is all from my side let us now let us now let us now",
        following="A completely different sentence.",
    )
    assert "model-behaviour/hypothesis-loop" in rules_of(context)


def test_a_phrase_the_hypothesis_says_twice_is_a_hypothesis_repetition():
    context = make_context(
        "out of the ordinary to our clients today",
        "out of the ordinary to our clients our clients today",
    )
    assert "model-behaviour/hypothesis-repetition" in rules_of(context)


def test_a_hypothesis_repetition_is_impact_neutral_even_when_it_carries_a_number():
    context = make_context(
        "we grew by 19% last year",
        "we grew by 19% by 19% last year",
    )
    scored = [
        ScoredSpan(
            sample_id=context.sample_id,
            call=context.call,
            category=category,
            rule=rule,
            content_impact=semantic_impact(span, context),
            impact="NONE"
            if category in IMPACT_NEUTRAL_CATEGORIES or rule in IMPACT_NEUTRAL_RULES
            else semantic_impact(span, context),
            span=span,
        )
        for category, rule, span in classify_all(context)
    ]
    assert any(item.rule == "model-behaviour/hypothesis-repetition" for item in scored)
    assert all(item.impact == "NONE" for item in scored)


def test_a_hypothesis_under_half_the_reference_length_is_a_truncation():
    context = make_context(
        "we expect the market to recover through the second half of next year",
        "we expect",
    )
    assert "model-behaviour/truncation" in rules_of(context)


# ---------------------------------------------------------------------------
# Rule 7 and the named residual
# ---------------------------------------------------------------------------


def test_a_string_near_substitution_is_acoustic_misrecognition():
    context = make_context("the outcome was better", "the outcomes was better")
    assert rules_of(context) == ["acoustic-misrecognition/string-near"]


def test_a_swap_of_two_function_words_is_named_apart_from_a_content_substitution():
    context = make_context("a lot of information on this slide", "a lot of information on the slide")
    assert rules_of(context) == ["other/function-word-swap"]


def test_an_unrelated_content_substitution_falls_to_the_named_residual():
    context = make_context("commercial pharma this year", "commercial farming this year")
    assert rules_of(context) == ["other/substituted-content-word"]


def test_every_rule_the_cascade_can_return_is_declared():
    for context in (
        make_context("in the U.S. and Europe", "in the US and Europe"),
        make_context("Um.", "Thank you."),
        make_context("we are a a big player", "we are a big player"),
        make_context("of the last year", "of the last year next slide"),
        make_context("commercial pharma this year", "commercial farming this year"),
    ):
        for _, rule, _ in classify_all(context):
            assert rule in ALL_RULES


# ---------------------------------------------------------------------------
# Impact, the sample, the rate and the bins
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("reference", "hypothesis", "expected"),
    [
        ("we grew by 19% last year", "we grew by 90% last year", "HIGH"),
        ("we will not proceed today", "we will proceed today", "HIGH"),
        ("the margin improved sharply", "the margin improved slightly", "LOW"),
        ("a lot of information on this", "a lot of information on the", "NONE"),
    ],
)
def test_semantic_impact_reads_numbers_negations_and_content(reference, hypothesis, expected):
    context = make_context(reference, hypothesis)
    spans = align_spans(context.ref_tokens, context.hyp_tokens).spans
    assert [semantic_impact(span, context) for span in spans] == [expected]


def test_semantic_impact_is_high_when_a_call_entity_moves():
    context = make_context("let Mohammed answer", "let Mohamed answer", entities=frozenset({"mohammed"}))
    span = align_spans(context.ref_tokens, context.hyp_tokens).spans[0]
    assert semantic_impact(span, context) == "HIGH"


def _fixture_spans(count: int, call: str) -> list[ScoredSpan]:
    spans: list[ScoredSpan] = []
    for index in range(count):
        span = align_spans(["a", "b", "c"], ["a", "x", "c"]).spans[0]
        spans.append(
            ScoredSpan(
                sample_id=f"{call}-{index}",
                call=call,
                category="acoustic-misrecognition",
                rule="acoustic-misrecognition/string-near",
                content_impact="HIGH",
                impact="HIGH",
                span=span,
            )
        )
    return spans


def test_the_read_sample_is_deterministic_call_stratified_and_sized():
    scored = _fixture_spans(600, "4453225") + _fixture_spans(400, "4469088")
    first = stratified_sample(scored, seed=READ_SAMPLE_SEED, size=100)
    second = stratified_sample(scored, seed=READ_SAMPLE_SEED, size=100)
    assert [item.sample_id for item in first] == [item.sample_id for item in second]
    assert len(first) == 100
    assert sum(1 for item in first if item.call == "4453225") == 60
    assert sum(1 for item in first if item.call == "4469088") == 40
    other = stratified_sample(scored, seed=READ_SAMPLE_SEED + 1, size=100)
    assert [item.sample_id for item in first] != [item.sample_id for item in other]


def test_the_read_sample_returns_everything_when_the_pool_is_smaller_than_the_draw():
    scored = _fixture_spans(10, "4453225")
    assert len(stratified_sample(scored, size=1500)) == 10


def test_the_agentic_error_rate_is_high_impact_reference_mass_over_reference_words():
    scored = _fixture_spans(3, "4453225")
    rate = agentic_error_rate(scored, 300)
    assert rate["high_impact_spans"] == 3
    assert rate["high_impact_reference_word_mass"] == 3
    assert rate["agentic_error_rate_percent"] == pytest.approx(1.0)


def test_the_agentic_error_rate_ignores_impact_neutral_categories():
    scored = _fixture_spans(2, "4453225")
    neutral = [
        ScoredSpan(
            sample_id=item.sample_id,
            call=item.call,
            category="segmentation-artifact",
            rule="segmentation-artifact/neighbour-bleed",
            content_impact="HIGH",
            impact="NONE",
            span=item.span,
        )
        for item in scored
    ]
    assert agentic_error_rate(neutral, 200)["high_impact_spans"] == 0
    strict = agentic_error_rate(
        neutral, 200, neutral_categories=frozenset({"format-convention", "reference-convention"})
    )
    assert strict["high_impact_spans"] == 2


def test_the_four_bins_partition_every_declared_rule_exactly_once():
    seen: list[str] = []
    for rules in GAP_BINS.values():
        seen.extend(rules)
    assert sorted(seen) == sorted(ALL_RULES)
    assert len(seen) == len(set(seen))
    assert set(AUTHORIZED_FOLD_RULES) <= set(GAP_BINS["scoring-convention"])


def test_gap_bins_reports_no_unassigned_rule_for_a_real_classification():
    context = make_context("in the U.S. and Europe", "in the US and Europe")
    scored = [
        ScoredSpan(
            sample_id=context.sample_id,
            call=context.call,
            category=category,
            rule=rule,
            content_impact="NONE",
            impact="NONE",
            span=span,
        )
        for category, rule, span in classify_all(context)
    ]
    report = gap_bins(scored, 100)
    assert report["unassigned_rules"] == []
    assert report["unassigned_error_mass"] == 0


def test_every_category_a_rule_names_is_a_declared_category():
    assert {rule.split("/")[0] for rule in ALL_RULES} == set(CATEGORIES)
