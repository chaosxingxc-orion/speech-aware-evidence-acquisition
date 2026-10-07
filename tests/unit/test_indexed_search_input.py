"""Lossless custody and bounded primary view for template search."""
from copy import deepcopy
import pytest
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.indexed_search_input import prepare_indexed_search_input, verify_indexed_search_input


def draft():
    rows=[]
    for i in range(3):
        r={"candidate_id": str(i), "evaluated_iteration": 2, "cohort":"a", "source_batch":"a", "sample_order_sha256":"a"*64, "sample_count":20, "disposition":"rejected", "is_active_parent":False,
           "business":{"slu_f1":.4,"intent":.8}, "selection":{"criterion":"sum"}, "comparators":["aa"], "template":{"role_text":{"solver":"Keep evidence."}},
           "terminal":{"utility":[20,0,-1,-.05,-2,1,.3]}, "node_statistics":{"solver":{"visits":20,"output_features":{"strict_schema":[20,0,19,.95,0,1,.2]},"performance":{"prefill_ms":[20,0,200,10,2,30,8]}}},
           "process":None if i==0 else {"rates":[[1,2,3,1,.5,[.1,.9],.3,.7]],"support":[[2,3,3,0,.66,[.2,.9],.66,.66]],"transitions":{"net":-1}}}
        r["record_id"]=content_hash(r);rows.append(r)
    actor={"feedback":{"records":rows,"comparators":[{"id":"aa","business":{"slu_f1":.5},"process":{"detail":None}}],"process_encoding":{"metric_order":["review_error_detection"],"support_order":["gold_intent_in_initial_candidates"],"rate_fields":["numerator","denominator","eligible","unknown","value","ci95_wilson","lower_missing_bound","upper_missing_bound"]},"statistic_columns":["count","missing","sum","mean","min","max","std"],"limitations":["Optimization only."],"observed_populations":[{"iteration":2,"candidate_records":3}],"schema":"aggregate"},"parent_templates":{"p":{"role_text":{"solver":"Keep evidence."}}},"slots":[{"candidate_id":"a"}],"instructions":"English only."}
    d={"schema":"saea-search-input-draft-v1","actor_view":actor,"registration_draft":{"status":"DRAFT"},"learner_exported":False,"runtime_admission":False,"proposal_allocation_granted":False}
    d["draft_sha256"]=content_hash(d);return d


def test_roundtrip_all_history_controls_and_missingness():
    d=draft();before=deepcopy(d);p=prepare_indexed_search_input(d,max_primary_bytes=100000)
    assert verify_indexed_search_input(p)==d["actor_view"]
    assert d==before
    rows=p["primary"]["feedback"]["records"]
    assert len(rows)==3 and rows[0]["process_summary"] is None
    assert p["primary"]["feedback"]["rate_vectors"][rows[1]["process_summary"]["rates"]["review_error_detection"]]==[1,2,3,1,.5,[.1,.9],.3,.7]
    assert rows[1]["process_summary"]==rows[2]["process_summary"]
    assert len(p["primary"]["feedback"]["rate_vectors"])==2
    assert rows[1]["node_summary"]["solver"][3]==[20,0,19,.95,0,1,.2]
    assert p["primary"]["feedback"]["node_summary_columns"][3]=="strict_schema"
    assert "template" in p["detail_documents"][rows[0]["detail_ref"]]
    assert p["primary"]["parent_templates"]==d["actor_view"]["parent_templates"]
    assert not p["runtime_admission"]


@pytest.mark.parametrize("damage",["record","duplicate","draft","status"])
def test_reject_unqualified_or_modified_draft(damage):
    d=draft()
    if damage=="record":d["actor_view"]["feedback"]["records"][0]["business"]["slu_f1"]=1
    if damage=="duplicate":d["actor_view"]["feedback"]["records"].append(deepcopy(d["actor_view"]["feedback"]["records"][0]))
    if damage=="status":d["registration_draft"]["status"]="ROOT_REGISTERED"
    if damage!="draft":d["draft_sha256"]=content_hash({k:v for k,v in d.items() if k!="draft_sha256"})
    else:d["draft_sha256"]="0"*64
    with pytest.raises(ValueError):prepare_indexed_search_input(d,max_primary_bytes=100000)


def test_primary_budget_and_no_silent_truncation():
    with pytest.raises(ValueError,match="budget"):prepare_indexed_search_input(draft(),max_primary_bytes=100)


@pytest.mark.parametrize("target",["primary","detail","missing"])
def test_roundtrip_rejects_custody_tamper(target):
    p=prepare_indexed_search_input(draft(),max_primary_bytes=100000)
    if target=="primary":p["primary"]["instructions"]="Changed"
    elif target=="detail":next(iter(p["detail_documents"].values()))["business"]={}
    else:p["detail_documents"].pop(next(iter(p["detail_documents"])))
    with pytest.raises(ValueError):verify_indexed_search_input(p)


@pytest.mark.parametrize("damage", ["primary", "missing", "unreferenced", "detail"])
def test_resealed_envelope_cannot_change_source_or_summary(damage):
    p=prepare_indexed_search_input(draft(),max_primary_bytes=100000)
    if damage=="primary":p["primary"]["feedback"]["records"][0]["node_summary"]["solver"][0]=999
    elif damage=="missing":p["detail_documents"].pop(next(iter(p["detail_documents"])))
    elif damage=="unreferenced":p["detail_documents"][content_hash({"extra":1})]={"extra":1}
    else:next(iter(p["detail_documents"].values()))["business"]={}
    p["package_sha256"]=content_hash({k:v for k,v in p.items() if k!="package_sha256"})
    with pytest.raises(ValueError):verify_indexed_search_input(p)
