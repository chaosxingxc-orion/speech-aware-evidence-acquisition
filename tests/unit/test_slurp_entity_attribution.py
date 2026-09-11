import pytest
from speech_aware_evidence_acquisition.analysis.slurp_entity_attribution import attribute_parsed_rows, attribute_row
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity, score_slu

def entities(*pairs):
    return tuple(SlotEntity(t, v) for t, v in pairs)

def stats(gold, predicted):
    score = score_slu(gold_scenario="a", gold_action="b", gold_entities=gold,
                      predicted_scenario="a", predicted_action="b", predicted_entities=predicted)
    return score.as_metrics_dict()

def test_exact_and_all_loss_buckets_close():
    gold = entities(("city", "Paris"), ("date", "today"))
    predicted = entities(("city", "paris"), ("name", "today"), ("noise", "x"))
    row = attribute_row(gold, predicted)
    assert row["surface_pairs"] and row["type_swaps"]
    assert len(row["spurious"]) == 1 and len(row["missing"]) == 0

def test_official_rows_are_exactly_reconciled_and_roster_mismatch_refuses():
    gold = {"s": entities(("city", "Paris"))}
    predicted = {"s": entities(("city", "Lyon"))}
    official = {"s": stats(gold["s"], predicted["s"])}
    result = attribute_parsed_rows(gold, predicted, official)
    assert result["totals"]["tp"] == 2
    with pytest.raises(ValueError, match="IDs must match"):
        attribute_parsed_rows(gold, {}, official)
    bad = dict(official["s"])
    bad["slu_f1_word_tp"] += 1
    with pytest.raises(ValueError, match="does not match"):
        attribute_parsed_rows(gold, predicted, {"s": bad})

def test_empty_and_repeated_same_type_are_supported():
    gold = entities(("x", "one"), ("x", "two"))
    predicted = entities(("x", "too"))
    row = attribute_row(gold, predicted)
    assert row["predicted_count"] == 1 and row["gold_count"] == 2
    assert attribute_row((), ())["mass"] == 0
