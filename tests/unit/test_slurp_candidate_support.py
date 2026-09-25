from speech_aware_evidence_acquisition.analysis.slurp_candidate_support import candidate_sets


def test_preserves_original_order_and_appends_only_unseen_intents():
    result = candidate_sets(["b", "a", "b"], ["c", "c", "a", "d"], (3, 5))
    assert result["baseline"] == ["b", "a"]
    assert result["cap3"] == ["b", "a", "c"]
    assert result["cap5"] == ["b", "a", "c", "d"]
    assert result["union"] == ["b", "a", "c", "d"]


def test_frequency_ties_are_lexical_and_not_source_iteration_order():
    a = candidate_sets(["z"], ["b", "a", "c"], (2, 3))
    b = candidate_sets(["z"], ["c", "b", "a"], (2, 3))
    assert a == b
    assert a["cap2"] == ["z", "a"]


def test_empty_support_keeps_candidates_without_fabrication():
    assert candidate_sets(["a"], [], (5, 8)) == {
        "baseline": ["a"], "cap5": ["a"], "cap8": ["a"], "union": ["a"],
    }


def test_cap_cannot_remove_original_candidates():
    import pytest
    with pytest.raises(ValueError, match="remove"):
        candidate_sets(["a", "b", "c"], ["d"], (2,))
