"""Matched-input process contrasts preserve uncertainty and do not grant READ."""
from copy import deepcopy
import pytest
from test_abstract_process_feedback import fixture
from speech_aware_evidence_acquisition.analysis.paired_process_diagnostics import compare_process_rows


def inputs():
    rows=deepcopy(fixture()[0]["families"]["part"]["a"]["rows"])
    for i,row in enumerate(rows):
        row.update(sample_id="private-"+str(i),scenario="PRIVATE_SCENARIO",gold_empty=False,
                   draft_entity_correct=False,final_entity_correct=bool(i),draft_full_correct=False,
                   final_full_correct=bool(i),review_valid=True,review_alarm=True,revised=True)
    return {"baseline":rows,"candidate":deepcopy(rows),"sample_ids":[r["sample_id"] for r in rows],
            "bootstrap":{"n_replicates":200,"seed":42,"ci_level":0.95}}


def test_identical_paired_rows_have_zero_delta_even_with_reordered_storage():
    a=inputs();a["candidate"].reverse();out=compare_process_rows(**a)
    assert out["metrics"]["entity_repair_event"]["difference"]==0
    assert out["metrics"]["entity_repair_event"]["paired_bootstrap"]["ci_low"]==0
    assert out["metrics"]["entity_repair_event"]["paired_bootstrap"]["ci_high"]==0
    assert "PRIVATE" not in str(out) and "private-" not in str(out)
    assert out["independent_inputs"]==2 and not out["causal_credit"]


def test_all_repairs_and_harms_have_opposite_known_paired_effects():
    a=inputs()
    for b,c in zip(a["baseline"],a["candidate"]):
        b.update(draft_entity_correct=False,final_entity_correct=True)
        c.update(draft_entity_correct=True,final_entity_correct=False)
    out=compare_process_rows(**a)["metrics"]
    assert out["entity_repair_event"]["difference"]==-1
    assert out["entity_harm_event"]["difference"]==1
    assert out["entity_net_transition"]["difference"]==-2


def test_missing_endpoints_are_not_failures_or_zero_denominators():
    a=inputs()
    a["candidate"][0]["final_entity_correct"]=None
    out=compare_process_rows(**a)["metrics"]["entity_repair_event"]
    assert out["paired_known"]==1 and out["paired_unknown"]==1
    assert out["difference"]==0 and out["population_missing_bounds"]==[-0.5,0.5]
    a["candidate"][1]["final_entity_correct"]=None
    out=compare_process_rows(**a)["metrics"]["entity_repair_event"]
    assert out["difference"] is None and out["paired_bootstrap"] is None
    assert out["population_missing_bounds"]==[-1,1]


def test_review_unavailable_is_distinct_from_no_alarm():
    a=inputs();a["candidate"][0].update(review_valid=False,review_alarm=None)
    out=compare_process_rows(**a)["metrics"]
    assert out["error_alarm_event"]["paired_unknown"]==1
    assert out["review_valid"]["difference"]==-0.5


@pytest.mark.parametrize("fault",["missing","duplicate","foreign","scenario","gold","raw","integer-flag","bad-bootstrap","bad-seed","bad-count","empty"])
def test_invalid_comparisons_refused(fault):
    a=inputs()
    if fault=="missing":a["candidate"].pop()
    elif fault=="duplicate":a["candidate"][1]["sample_id"]=a["candidate"][0]["sample_id"]
    elif fault=="foreign":a["candidate"][0]["sample_id"]="foreign"
    elif fault=="scenario":a["candidate"][0]["scenario"]="other"
    elif fault=="gold":a["candidate"][0]["gold_empty"]=True
    elif fault=="raw":a["candidate"][0]["raw_text"]="PRIVATE"
    elif fault=="integer-flag":a["candidate"][0]["review_alarm"]=1
    elif fault=="bad-bootstrap":a["bootstrap"]["ci_level"]=1
    elif fault=="bad-seed":a["bootstrap"]["seed"]=True
    elif fault=="bad-count":a["bootstrap"]["n_replicates"]=0
    else:a["sample_ids"]=[]
    with pytest.raises((ValueError,RuntimeError)):compare_process_rows(**a)
