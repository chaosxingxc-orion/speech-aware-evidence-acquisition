"""Prospective K16 reports retain all branches and the same-family null."""
from copy import deepcopy
import pytest
from test_context_learning_read import fixture
from speech_aware_evidence_acquisition.analysis.system_context_read import analyze
from speech_aware_evidence_acquisition.rails.system_text_policy import canonical, PolicyError
from speech_aware_evidence_acquisition.rails.system_text_feedback import CompleteSystemFeedback
from speech_aware_evidence_acquisition.rails.hashing import content_hash

def population(tmp_path):
    d, r, g, p, roster, s = fixture(tmp_path)
    ids = ["seed", "seed-aa"] + [f"branch-{i:02d}" for i in range(1, 17)]
    original = {c: c if c in ids[:2] else "abcd"[(i-2)%4] for i,c in enumerate(ids)}
    g["member_bindings"] = {c: {**deepcopy(g["member_bindings"][old]), "run_id": "run-"+c,
        "attempt_id": "attempt-"+c, "bundle_id":content_hash("seed" if c=="seed-aa" else c)} for c,old in original.items()}
    g["expected_members"] = {c:b["run_id"] for c,b in g["member_bindings"].items()}
    r["expected_members"] = g["expected_members"]
    d["summaries"] = {c:deepcopy(d["summaries"][old]) for c,old in original.items()}
    by_source = {v["candidate_id"]:v for v in d["feedback"]["sources"]}
    d["feedback"]["sources"] = [{**deepcopy(by_source[old]), **g["member_bindings"][c],
        "candidate_id":c} for c,old in original.items()]
    for group in d["feedback"]["groups"]:
        members = {m["candidate_id"]:m for m in group["members"]}
        group["members"] = [{**deepcopy(members[old]), "candidate_id":c} for c,old in original.items()]
    g["registration_sha256"] = content_hash({k:v for k,v in g.items() if k!="registration_sha256"})
    d["registration_sha256"] = g["registration_sha256"]
    p.update(K=16, N=20, candidate_members=ids[2:], algorithms=["tf-grpo-context-diversity"],
        population_authorization={"relpath":"owner-k16.json","sha256":"a"*64})
    return d,r,g,p,roster,s

def call(parts):
    d,r,g,p,roster,s=parts
    return analyze(CompleteSystemFeedback(canonical(d)),recipe=r,registration=g,protocol=p,roster=roster,supplement=s)

def test_all_sixteen_branches_and_null_are_described(tmp_path):
    report=call(population(tmp_path))
    assert len(report["measured_rows"])==len(report["official_summaries"])==18
    assert len(report["branches"]["context"]["comparisons"])==33
    for i in range(1,17):
        assert f"branch-{i:02d}-minus-parent" in report["branches"]["context"]["comparisons"]
    assert all(r["candidate_id"]!="seed-aa" for r in report["measured_frontier"])
    assert report["optimizer_feedback_allowed"] is False
    assert report["contacts_added"]=={"model":0,"scorer":0}

@pytest.mark.parametrize("fault",["missing-authority","bad-pin","wrong-K","wrong-N","wrong-algorithm","reordered","subset","summary","source","row"])
def test_population_refuses_unscoped_or_incomplete_report(tmp_path,fault):
    parts=population(tmp_path); d,r,g,p,roster,s=parts
    if fault=="missing-authority":p.pop("population_authorization")
    elif fault=="bad-pin":p["population_authorization"]={}
    elif fault=="wrong-K":p["K"]=8
    elif fault=="wrong-N":p["N"]=80
    elif fault=="wrong-algorithm":p["algorithms"]=["gepa"]
    elif fault=="reordered":p["candidate_members"].reverse()
    elif fault=="subset":p["candidate_members"].pop()
    elif fault=="summary":d["summaries"].pop("branch-16")
    elif fault=="source":d["feedback"]["sources"].pop()
    elif fault=="row":d["feedback"]["groups"][0]["members"].pop()
    with pytest.raises(PolicyError):call(parts)

def test_legacy_population_does_not_silently_resize(tmp_path):
    parts=fixture(tmp_path);parts[3]["K"]=16
    with pytest.raises(PolicyError):call(parts)
