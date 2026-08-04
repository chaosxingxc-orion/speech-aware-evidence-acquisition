"""E0 D3: the frozen scoring stack behaves exactly as receipted (golden vectors)."""

import pytest

from speech_aware_evidence_acquisition.scoring import (
    align,
    flag_transitions,
    normalize_text_v1,
    qa_exact_match,
    qa_token_f1,
    score_entities,
    token_transitions,
    tokens_v1,
)


class TestNormalizeV1:
    def test_entity_rich_normalization(self):
        assert (
            normalize_text_v1("The CFO, Mr. O’Brien — said: ‘EBITDA up 12%’")
            == "the cfo mr o'brien said ebitda up 12"
        )

    def test_intra_word_apostrophe_survives_and_quotes_do_not(self):
        assert normalize_text_v1("don't 'quote' O’Brien’s") == "don't quote o'brien's"

    def test_dashes_and_punctuation_become_spaces(self):
        assert tokens_v1("Semi-annual  results…") == ["semi", "annual", "results"]

    def test_nfkc_and_casefold(self):
        assert normalize_text_v1("ＦＵＬＬ－ｗｉｄｔｈ Ｑ２") == "full width q2"

    def test_empty_and_type_errors(self):
        assert normalize_text_v1("") == ""
        assert tokens_v1("   ") == []
        with pytest.raises(TypeError):
            normalize_text_v1(None)  # type: ignore[arg-type]


class TestWer:
    def test_substitution_and_insertion(self):
        result = align(
            ["the", "quick", "brown", "fox"], ["the", "quik", "brown", "fox", "jumps"]
        )
        assert (result.hits, result.substitutions, result.deletions, result.insertions) == (
            3,
            1,
            0,
            1,
        )
        assert result.wer == 0.5
        assert result.ref_hit_mask == (True, False, True, True)

    def test_deletion(self):
        result = align(["a", "b", "c"], ["a", "c"])
        assert result.deletions == 1
        assert result.ref_hit_mask == (True, False, True)

    def test_empty_reference_conventions(self):
        assert align([], []).wer == 0.0
        assert align([], ["x"]).errors == 1

    def test_deterministic_repeated_alignment(self):
        ref = ["a", "b", "a", "b", "a"]
        hyp = ["b", "a", "b", "a", "b"]
        first = align(ref, hyp)
        for _ in range(5):
            again = align(ref, hyp)
            assert again == first


class TestEntity:
    def test_multiset_semantics_prevent_double_credit(self):
        score = score_entities(
            ["Q2 revenue", "O’Brien", "O’Brien"], ["o'brien", "q2 revenue", "acme"]
        )
        assert score.true_positives == 2
        assert score.precision == pytest.approx(2 / 3)
        assert score.recall == pytest.approx(2 / 3)

    def test_repeating_one_correct_entity_does_not_inflate_recall(self):
        score = score_entities(["acme"], ["acme", "acme", "acme"])
        assert score.true_positives == 1
        assert score.recall == 1.0
        assert score.precision == pytest.approx(1 / 3)

    def test_empty_sides(self):
        empty = score_entities([], [])
        assert (empty.precision, empty.recall, empty.f1) == (0.0, 0.0, 0.0)


class TestQa:
    def test_exact_match_normalized(self):
        assert qa_exact_match("The CFO.", ["CFO", "the cfo"])
        assert not qa_exact_match("the ceo", ["CFO"])

    def test_token_f1_best_over_answers(self):
        assert qa_token_f1("revenue rose 12 percent", ["revenue rose 12"]) == pytest.approx(
            6 / 7
        )
        assert qa_token_f1("no overlap", ["totally different"]) == 0.0

    def test_requires_answers(self):
        with pytest.raises(ValueError):
            qa_exact_match("x", [])
        with pytest.raises(ValueError):
            qa_token_f1("x", [])


class TestTransitions:
    def test_token_level(self):
        counts = token_transitions(
            ["a", "b", "c", "d"], ["a", "x", "c", "d"], ["a", "b", "c", "x"]
        )
        assert counts.correct_to_correct == 2
        assert counts.correct_to_wrong == 1
        assert counts.wrong_to_correct == 1
        assert counts.wrong_to_wrong == 0
        assert counts.units == 4

    def test_item_level_flags(self):
        counts = flag_transitions([True, False, True], [True, True, False])
        assert (counts.correct_to_wrong, counts.wrong_to_correct) == (1, 1)

    def test_unit_list_mismatch_fails_closed(self):
        with pytest.raises(ValueError):
            flag_transitions([True], [True, False])
