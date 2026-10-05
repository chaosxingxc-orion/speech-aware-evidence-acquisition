"""Qualified K16 trial accounting preserves exact populations and business costs."""
from copy import deepcopy
import json
import pytest
from speech_aware_evidence_acquisition.rails import system_context_learning as learning
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_context_population_update import fixture, reserve, record

def setup(tmp_path, monkeypatch, configured=False):
    a, p, response = fixture(tmp_path)
    root = tmp_path / "repo"
    root.mkdir()
    data = tmp_path
    def pin(path, value, base):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        import hashlib
        return {"relpath": str(path.relative_to(base)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    old = {cid: {"bundle_id": x["bundle_id"], "run_id": "old-"+cid, "attempt_id": "old-attempt-"+cid}
           for cid, x in p["policies"].items()}
    old.update({c: {"bundle_id": "c"*64, "run_id": "old-"+c, "attempt_id": "old-attempt-"+c}
                for c in ["seed", "seed-aa"]})
    reg = {"member_bindings": old, "registration_sha256": "d"*64}
    old_recipe = {"context_learning_registration": pin(root/"old-reg.json", reg, root)}
    p.update(family_id="old-family", recipe=pin(root/"old-recipe.json",old_recipe,root),
             family_commitment={"registration_sha256":"d"*64},
             frozen_reference={"relpath":"reference.json","sha256":"e"*64},
             sampling={"temperature":0,"seed":20260913}, measurement_profile={"test_profile":"fixed"},
             business_measurements=[{"candidate_id":c,"mean_sample_seconds":1.} for c in p["policies"]])
    for group in p["groups"]:
        for m in group["members"]: m["utility"] = 1.
    if configured:
        from test_experiment_population_config import config
        from speech_aware_evidence_acquisition.rails.experiment_population import population_accounting
        cfg = config((len(p["policies"]),), len(p["groups"]))
        cfg["cohorts"][0].update(candidate_ids=list(p["policies"]), sample_ids=[g["sample_id"] for g in p["groups"]])
        ref = pin(a.root/"population.json", cfg, a.root)
        pin(root/"population.json", cfg, root)
        p.update(experiment_population=ref, population_cohort="cohort-0", budget=population_accounting(cfg,"cohort-0"))
    p["input_sha256"] = content_hash({k:v for k,v in p.items() if k!="input_sha256"})
    packet_path = a.root/"context-learning/inputs/population.json"
    packet_pin = pin(packet_path,p,data)
    response["input_sha256"] = p["input_sha256"]
    for row in response["branches"]: row["proposal"]["evidence"] = [p["input_sha256"]]
    reserve(a,p)
    result = record(a,p,response)
    result_path = a.root/"context-learning/populations/update-two/result.json"
    result_pin = pin(result_path,result,data)
    new = deepcopy(old)
    for row in result["records"]: new[row["candidate_id"]]["bundle_id"] = row["bundle_id"]
    for cid,b in new.items(): b.update(run_id="new-"+cid,attempt_id="new-attempt-"+cid)
    recipe = {"family_id":"new-family","sample_ids":[g["sample_id"] for g in p["groups"]]}
    registration = {"member_bindings":new,"registration_sha256":"f"*64}
    protocol = {"sampling":deepcopy(p["sampling"]),"measurement_profile":deepcopy(p["measurement_profile"]),
                "frozen_reference":deepcopy(p["frozen_reference"]),"iteration":2,
                "learning_update":{"algorithm":p["algorithm"],"iteration":2,
                    "source_packet":packet_pin,"original_update_record":result_pin}}
    if configured:
        for document in (recipe, registration, protocol):
            document.update(experiment_population=ref, population_cohort="cohort-0")
    groups=deepcopy(p["groups"])
    for group in groups:
        for m in group["members"]:m["utility"]=2.
    business=[{"candidate_id":c,"mean_sample_seconds":9.} for c in p["policies"]]
    trial=({"complete":"synthetic"},recipe,registration,protocol,list(p["policies"]),
           ["seed","seed-aa"],deepcopy(p["reference"]))
    calls=[]
    def qualify(*args, **kwargs):
        calls.append((args,kwargs))
        return trial
    monkeypatch.setattr(learning,"_qualified_feedback",qualify)
    monkeypatch.setattr(learning,"_candidate_groups",lambda *args:groups)
    monkeypatch.setattr(learning,"measured_rows",lambda *args,**kwargs:business)
    request={"bindings":[{"synthetic":True}],"recipe_pin":{"relpath":"new-recipe.json","sha256":"a"*64}}
    return a,p,root,data,request,trial,groups,calls

def call(parts):
    a,p,root,data,request,*_=parts
    return learning.qualify_context_population_trial(a,input_sha256=p["input_sha256"],
        request=request,repo_root=root,data_root=data)

def test_full_320_pairing_reports_signal_without_automatic_adoption(tmp_path,monkeypatch):
    parts=setup(tmp_path,monkeypatch)
    out=call(parts)
    assert out["utility_before"]==320. and out["utility_after"]==640.
    assert out["utility_increased"] is True and out["root_review_required"] is True
    assert out["business_after"][0]["mean_sample_seconds"]==9.
    assert out["formal_adoption"] is False and out["runtime_admission"] is False
    assert len(out["after_groups"])==20 and len(parts[-1])==1
    assert not (parts[0].root/"context-learning/populations/update-two/evaluation.json").exists()


@pytest.mark.parametrize("drift", [False, True])
def test_config_identity_survives_successor_qualification(tmp_path, monkeypatch, drift):
    parts = setup(tmp_path, monkeypatch, configured=True)
    if drift:
        parts[5][3]["population_cohort"] = "different"
        with pytest.raises(PolicyError): call(parts)
    else:
        report = call(parts)
        assert report["experiment_population"] == parts[1]["experiment_population"]

@pytest.mark.parametrize("utility",[1.,0.,-2.])
def test_equal_or_lower_utility_never_signals_retention(tmp_path,monkeypatch,utility):
    parts=setup(tmp_path,monkeypatch)
    for g in parts[6]:
        for m in g["members"]:m["utility"]=utility
    assert call(parts)["utility_increased"] is False

@pytest.mark.parametrize("fault",["request-reward","source-packet","result-pin","invalid-slot","same-family",
    "candidate-subset","controls","roster","reference","sampling","profile","child","control-policy",
    "old-run","old-attempt","short-group","short-members","reordered-members","nan","iteration","algorithm"])
def test_refuse_unbound_or_mixed_trial(tmp_path,monkeypatch,fault):
    parts=setup(tmp_path,monkeypatch)
    a,p,root,data,request,trial,groups,_=parts
    _,recipe,reg,proto,candidates,controls,reference=trial
    if fault=="request-reward":request["reward"]=100.
    elif fault=="source-packet":proto["learning_update"]["source_packet"]["sha256"]="0"*64
    elif fault=="result-pin":proto["learning_update"]["original_update_record"]["sha256"]="0"*64
    elif fault=="invalid-slot":
        q=a.root/"context-learning/populations/update-two/result.json"
        doc=json.loads(q.read_text());doc["records"][0]["status"]="invalid";q.write_text(json.dumps(doc))
    elif fault=="same-family":recipe["family_id"]=p["family_id"]
    elif fault=="candidate-subset":candidates.pop()
    elif fault=="controls":controls.pop()
    elif fault=="roster":recipe["sample_ids"].reverse()
    elif fault=="reference":reference["sample_ids"].append("slurp:train:other")
    elif fault=="sampling":proto["sampling"]["temperature"]=1
    elif fault=="profile":proto["measurement_profile"]={}
    elif fault=="child":reg["member_bindings"]["branch-01"]["bundle_id"]="0"*64
    elif fault=="control-policy":reg["member_bindings"]["seed"]["bundle_id"]="0"*64
    elif fault=="old-run":reg["member_bindings"]["branch-01"]["run_id"]="old-branch-01"
    elif fault=="old-attempt":reg["member_bindings"]["branch-01"]["attempt_id"]="old-attempt-branch-01"
    elif fault=="short-group":groups.pop()
    elif fault=="short-members":groups[0]["members"].pop()
    elif fault=="reordered-members":groups[0]["members"].reverse()
    elif fault=="nan":groups[0]["members"][0]["utility"]=float("nan")
    elif fault=="iteration":proto["iteration"]=3
    elif fault=="algorithm":proto["learning_update"]["algorithm"]="gepa"
    with pytest.raises((ValueError,FileNotFoundError)):call(parts)

def test_shared_read_failure_stops_before_group_or_cost_access(tmp_path,monkeypatch):
    parts=setup(tmp_path,monkeypatch)
    def closed(*args,**kwargs):raise PolicyError("Full-family READ is closed")
    def forbidden(*args,**kwargs):raise AssertionError("Result access after closed READ")
    monkeypatch.setattr(learning,"_qualified_feedback",closed)
    monkeypatch.setattr(learning,"_candidate_groups",forbidden)
    monkeypatch.setattr(learning,"measured_rows",forbidden)
    with pytest.raises(PolicyError,match="READ is closed"):call(parts)
