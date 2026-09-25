"""Synthetic official-feedback checks."""
import copy
import math
import pytest
from speech_aware_evidence_acquisition.analysis.official_metric_feedback import (
    FeedbackError, align_feedback_groups, answers_disagree, extract_official_feedback,
    extract_parse_format_status, frozen_baseline_f1, group_centered_advantages,
    pooled_f1, utility,
)

def row(sid, tp, fp, fn, intent=1.0):
    return {"sample_id": sid, "slu_f1_word_tp": tp/2, "slu_f1_char_tp": tp/2,
            "slu_f1_word_fp": fp/2, "slu_f1_char_fp": fp/2,
            "slu_f1_word_fn": fn/2, "slu_f1_char_fn": fn/2,
            "scenario_action_exact": intent}

def test_empty_gold_fp_is_visible_despite_row_f1_tie():
    a, b = (extract_official_feedback(row("u", 0, fp, 0)) for fp in (0, 2))
    assert pooled_f1([a]) == pooled_f1([b]) == 0
    assert utility(a, .6) == 0
    assert utility(b, .6) == pytest.approx(-1.2)
    assert answers_disagree({"scenario":"a","action":"b","entities":[]},
                            {"scenario":"a","action":"b","entities":[{"type":"date","filler":"today"}]})
    assert answers_disagree({"scenario":"a","action":"b","entities":[]},
                            {"scenario":"a","action":"c","entities":[]})

def test_frozen_baseline_utility_sign_matches_pooled_change():
    base = [extract_official_feedback(row("u1",4,1,1)),extract_official_feedback(row("u2",1,2,1))]
    new = [extract_official_feedback(row("u1",4,0,1)),extract_official_feedback(row("u2",2,2,1))]
    f0 = frozen_baseline_f1(base)
    assert sum(utility(x,f0) for x in base) == pytest.approx(0)
    assert sum(utility(x,f0) for x in new) > 0
    assert pooled_f1(new) > pooled_f1(base)

def test_alignment_complete_groups_centered_and_pure():
    variants = {"a":[row("u2",1,1,1),row("u1",2,0,0)],
                "b":[row("u1",1,1,0),row("u2",1,0,0)]}
    original=copy.deepcopy(variants)
    groups=align_feedback_groups(("u1","u2"),variants)
    assert tuple(groups)==("u1","u2")
    assert set(groups["u1"])=={"a","b"}
    advantages=group_centered_advantages(groups,.5)
    assert all(sum(g.values())==pytest.approx(0) for g in advantages.values())
    assert variants==original

def test_reject_partial_duplicate_and_wrong_identity():
    with pytest.raises(FeedbackError):
        align_feedback_groups(("u1","u2"),{"a":[row("u1",1,0,0)]})
    with pytest.raises(FeedbackError):
        align_feedback_groups(("u1",),{"a":[row("u1",1,0,0),row("u1",1,0,0)]})
    with pytest.raises(FeedbackError):
        align_feedback_groups(("u1",),{"a":[row("other",1,0,0)]})

@pytest.mark.parametrize("bad",[-1,math.nan,math.inf,True,"1"])
def test_reject_invalid_numeric(bad):
    item=row("u",1,0,0)
    item["slu_f1_char_tp"]=bad
    with pytest.raises(FeedbackError):
        extract_official_feedback(item)
    with pytest.raises(FeedbackError):
        utility(extract_official_feedback(row("u",1,0,0)),bad)

def test_missing_bindings_and_status():
    item=row("u",1,0,0)
    del item["scenario_action_exact"]
    with pytest.raises(FeedbackError):
        extract_official_feedback(item)
    assert extract_parse_format_status({"parse_status":"ok","format_status":"valid"})==("ok","valid")
    assert extract_parse_format_status({"parse_status":"malformed"})==("malformed","unreported")
    with pytest.raises(FeedbackError):
        extract_parse_format_status({})
    with pytest.raises(FeedbackError):
        answers_disagree({"scenario":"a","action":"b","entities":[]},{"scenario":"a"})


def test_empty_answer_and_entity_order_are_canonical():
    empty = {"scenario":"","action":"","entities":[]}
    assert not answers_disagree(empty, dict(empty))
    left = {"scenario":"a","action":"b","entities":[
        {"type":"date","filler":"today"},{"type":"place","filler":"home"}]}
    right = {"scenario":"a","action":"b","entities":list(reversed(left["entities"]))}
    assert not answers_disagree(left,right)
