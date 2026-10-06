"""Configured search proposals preserve frozen scope, lineage and spent slots."""
import copy
import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.rails import system_search_learning as search
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError, SystemTextPolicyBundle, TextPolicyUpdateProposal, apply_text_proposal,
    compile_system_text_policy,
)
from test_system_text_policy import seed_document, ROOT, BASE
from test_system_context_learning import pin
from test_experiment_population_config import config


def setup(tmp_path, k=4, algorithm="bounded-multiparent-aggregate-v1"):
    archive = SystemSearchArchive(tmp_path / "archive")
    parents=[]
    for i in range(2):
        d=seed_document()
        d.update(schema="saea-system-text-policy-bundle-v3",
                 context_layout={"native_role_query_placement":None},
                 node_context={"tool_schema_rendering":"constant","reviewer_history_scope":"full"})
        d["role_text"]["perception"]=f"Preserve original speech evidence, variant {i}."
        d["cumulative_sources"].append({"kind":"feedback","sha256":str(i+1)*64,
                                         "sample_ids":[f"slurp:train:{i+1}"]})
        parent=SystemTextPolicyBundle.from_json(d);archive.store_policy(parent);parents.append(parent)
    population=config((k,),n=3)
    slots=[]
    for i,cid in enumerate(population["cohorts"][0]["candidate_ids"]):
        mode="fixed" if algorithm=="fixed-parent-aggregate-v1" else ("recombine" if i==0 else "local")
        slots.append({"candidate_id":cid,"cohort_id":"cohort-0","mode":mode,
                      "parent_bundle_ids":[p.bundle_id for p in parents[:2 if mode=="recombine" else 1]]})
    d={"schema":"saea-search-update-registration-v1","status":"ROOT_REGISTERED",
       "batch_id":"search-test","algorithm":algorithm,"iteration":1,
       "experiment_population":pin(tmp_path,"population.json",population),
       "qualified_input_sha256":"a"*64,"actor_input_sha256":"b"*64,
       "slots":slots,"evidence_record_ids":["c"*64],
       "cumulative_sources":[{"kind":"feedback","sha256":"d"*64,"sample_ids":["slurp:train:7"]}]}
    ref=pin(tmp_path,"registration.json",d)
    return archive,parents,population,d,ref


def response(d,population):
    return {"schema":"saea-search-update-response-v1","registration_sha256":content_hash(d),
            "actor_input_sha256":d["actor_input_sha256"],**{k:population["proposer"][k] for k in ("model","reasoning_effort")},
            "usage":{"provider_contacts":None,"input_tokens":None,"output_tokens":None},
            "proposals":[{"schema":"saea-search-policy-update-proposal-v1","algorithm":d["algorithm"],
               "iteration":d["iteration"],"candidate_id":s["candidate_id"],"mode":s["mode"],
               "parent_ids":s["parent_bundle_ids"],"changes":{"role_text":{"solver":"Revise only when supported by evidence."}},
               "rationale":"Reduce unsupported revisions.","hypotheses":["Selective revision reduces damage."],
               "evidence":["c"*64]} for s in d["slots"]]}


def reserve(f):
    return search.reserve_search_update(f[0],registration_pin=f[4],repo_root=f[0].root.parent)


def record(f,r):
    return search.record_search_update(f[0],registration_pin=f[4],repo_root=f[0].root.parent,response_document=r)


@pytest.mark.parametrize("k",[2,5,8])
def test_configured_batch_materializes_all_and_preserves_both_ancestries(tmp_path,k):
    f=setup(tmp_path,k);a,parents,pop,d,ref=f
    reservation=reserve(f)
    assert reservation["proposal_slots"]==k and not reservation["runtime_admission"]
    r=response(d,pop);r["proposals"][-1]["changes"]={}
    result=record(f,r)
    assert len(result["records"])==k
    assert result["records"][-1]["status"]=="no-change"
    child=a.load_policy(result["records"][0]["bundle_id"])
    assert child.as_json()["parent_ids"]==[p.bundle_id for p in parents]
    assert {"1"*64,"2"*64,"d"*64} <= {s["sha256"] for s in child.as_json()["cumulative_sources"]}
    assert child.as_json()["knowledge"]==parents[0].as_json()["knowledge"]
    baseline=json.loads((ROOT/BASE).read_text())
    assert compile_system_text_policy(baseline,child,repo_root=ROOT,output_root=tmp_path/"out",enabled=False)==baseline
    compiled=compile_system_text_policy(baseline,child,repo_root=ROOT,output_root=tmp_path/"out")
    assert compiled["policy"]==baseline["policy"]
    with pytest.raises(PolicyError):reserve(f)
    with pytest.raises(PolicyError):record(f,r)


def test_fixed_arm_uses_same_recorder_and_materializer(tmp_path):
    f=setup(tmp_path,algorithm="fixed-parent-aggregate-v1");reserve(f)
    result=record(f,response(f[3],f[2]))
    assert all(r["status"]=="materialized-policy" for r in result["records"])


@pytest.mark.parametrize("fault",["count","position","model","capsule","unknown-field","malformed"])
def test_bad_envelope_spends_every_slot_and_keeps_original(tmp_path,fault):
    f=setup(tmp_path);reserve(f);r=response(f[3],f[2])
    if fault=="count":r["proposals"].pop()
    elif fault=="position":r["proposals"].reverse()
    elif fault=="model":r["model"]="different"
    elif fault=="capsule":r["actor_input_sha256"]="e"*64
    elif fault=="unknown-field":r["raw_cases"]=[]
    else:r="unparseable response"
    result=record(f,r)
    assert result["status"]=="invalid-envelope"
    assert len(result["records"])==4 and all(x["status"]=="invalid" for x in result["records"])
    raw=json.loads((f[0].root/"context-learning/search-updates/search-test/response.json").read_text())
    assert raw["response_document"]==r
    with pytest.raises(PolicyError):record(f,response(f[3],f[2]))


@pytest.mark.parametrize("fault",["knowledge","temperature","parent","evidence","mode","non-english","algorithm"])
def test_invalid_individual_does_not_get_replaced(tmp_path,fault):
    f=setup(tmp_path);reserve(f);r=response(f[3],f[2]);p=r["proposals"][0]
    if fault=="knowledge":p["changes"]["knowledge"]={}
    elif fault=="temperature":p["changes"]["sampling"]={"temperature":1}
    elif fault=="parent":p["parent_ids"].reverse()
    elif fault=="evidence":p["evidence"]=["e"*64]
    elif fault=="mode":p["mode"]="local"
    elif fault=="non-english":p["rationale"]="\u4e2d\u6587"
    else:p["algorithm"]="gepa"
    result=record(f,r)
    assert result["records"][0]["status"]=="invalid"
    assert all(x["status"]=="materialized-policy" for x in result["records"][1:])


def test_no_reservation_no_response_write(tmp_path):
    f=setup(tmp_path)
    with pytest.raises(PolicyError):record(f,response(f[3],f[2]))
    assert not (f[0].root/"context-learning/search-updates").exists()


@pytest.mark.parametrize("fault",["duplicate","different-mode","missing-slot","population-drift","wrong-stage","bad-source","bad-iteration"])
def test_registration_refused_before_spending(tmp_path,fault):
    f=setup(tmp_path);d=f[3]
    if fault=="duplicate":d["slots"][1]=copy.deepcopy(d["slots"][0])
    elif fault=="different-mode":d["algorithm"]="fixed-parent-aggregate-v1"
    elif fault=="missing-slot":d["slots"].pop()
    elif fault=="population-drift":(tmp_path/"population.json").write_text("{}")
    elif fault=="wrong-stage":d["status"]="DRAFT"
    elif fault=="bad-source":d["cumulative_sources"][0]["sample_ids"]=["slurp:test:1"]
    else:d["iteration"]=True
    f=(*f[:4],pin(tmp_path,"registration.json",d))
    with pytest.raises(PolicyError):reserve(f)
    assert not (f[0].root/"context-learning/search-updates").exists()


def test_recombine_rejects_different_fixed_knowledge_before_spending(tmp_path):
    f=setup(tmp_path);d=f[1][1].as_json();d["supply"]["value_limit"]=1
    other=SystemTextPolicyBundle.from_json(d);f[0].store_policy(other)
    f[3]["slots"][0]["parent_bundle_ids"][1]=other.bundle_id
    f=(*f[:4],pin(tmp_path,"registration.json",f[3]))
    with pytest.raises(PolicyError,match="fixed"):reserve(f)


def test_historical_baseline_schema_does_not_accept_new_algorithm(tmp_path):
    f=setup(tmp_path);p=response(f[3],f[2])["proposals"][0]
    with pytest.raises(PolicyError):TextPolicyUpdateProposal.from_context_json(p)


def test_effectively_identical_edit_remains_no_change_with_new_exposure(tmp_path):
    f=setup(tmp_path);reserve(f);r=response(f[3],f[2])
    r["proposals"][0]["changes"]={"role_text":{"solver":f[1][0].as_json()["role_text"]["solver"]}}
    result=record(f,r)
    entry=result["records"][0]
    assert entry["status"]=="no-change"
    child=f[0].load_policy(entry["bundle_id"])
    assert len(child.as_json()["parent_ids"])==2
    assert "d"*64 in {s["sha256"] for s in child.as_json()["cumulative_sources"]}


def test_reject_different_substrate_across_single_parent_slots(tmp_path):
    f=setup(tmp_path,algorithm="fixed-parent-aggregate-v1")
    d=f[1][1].as_json();d["supply"]["value_limit"]=1
    other=SystemTextPolicyBundle.from_json(d);f[0].store_policy(other)
    f[3]["slots"][1]["parent_bundle_ids"]=[other.bundle_id]
    f=(*f[:4],pin(tmp_path,"registration.json",f[3]))
    with pytest.raises(PolicyError,match="fixed"):reserve(f)


@pytest.mark.parametrize("key",["knowledge","construction_receipt","optimizer_experience"])
def test_materializer_refuses_out_of_scope_optional_overrides(tmp_path,key):
    f=setup(tmp_path);payload=response(f[3],f[2])["proposals"][0]
    proposal=TextPolicyUpdateProposal.from_search_json(payload)
    with pytest.raises(PolicyError,match="override"):
        apply_text_proposal(proposal,parents=f[1],added_sources=[],**{key:{}})


def test_response_registration_drift_cannot_rebind_reservation(tmp_path):
    f=setup(tmp_path);reserve(f)
    f[3]["actor_input_sha256"]="f"*64
    f=(*f[:4],pin(tmp_path,"registration.json",f[3]))
    with pytest.raises(PolicyError,match="reservation"):
        record(f,response(f[3],f[2]))


def test_bad_usage_bool_spends_batch_without_fabricated_cost(tmp_path):
    f=setup(tmp_path);reserve(f);r=response(f[3],f[2])
    r["usage"]["provider_contacts"]=True
    result=record(f,r)
    assert result["status"]=="invalid-envelope" and result["usage"] is None


def test_storage_failure_preserves_response_and_refuses_retry(tmp_path,monkeypatch):
    f=setup(tmp_path);reserve(f);r=response(f[3],f[2])
    def fail(bundle):raise OSError("synthetic storage failure")
    monkeypatch.setattr(f[0],"store_policy",fail)
    with pytest.raises(OSError):record(f,r)
    base=f[0].root/"context-learning/search-updates/search-test"
    assert (base/"response.json").exists() and not (base/"result.json").exists()
    with pytest.raises(PolicyError):record(f,r)
