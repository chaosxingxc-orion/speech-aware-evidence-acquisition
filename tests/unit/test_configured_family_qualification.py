"""Configured complete-family qualification never opens partial score evidence."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

@pytest.fixture
def case(tmp_path, monkeypatch):
    spec=importlib.util.spec_from_file_location("configured_qualification_reader",Path(__file__).resolve().parents[2]/"scripts/analysis/system_text_pilot_read.py")
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    root=tmp_path/"repo";data=tmp_path/"data";root.mkdir()
    def save(path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value));return reader.pin(path)
    def rp(name,value):
        p=save(root/name,value);return {"relpath":name,"sha256":p["sha256"]}
    ids=["a","b","c"]
    members={c:{"run_id":"run-"+c,"attempt_id":"attempt-"+c,"config_hash":"config-"+c} for c in ["seed","seed-aa","candidate"]}
    recipe={"family_id":"family","sample_ids":ids,"required_rows_per_member":len(ids),"expected_members":{c:m["run_id"] for c,m in members.items()},"run_ids":{"read":"READ"},"analysis_roster":rp("roster.json",{"items":[{"sample_id":i} for i in ids]})}
    protocol={"protocol":"synthetic"}
    reg={"family_id":"family","member_bindings":members,"expected_members":recipe["expected_members"],"read_id":"READ","protocol":rp("protocol.json",protocol)}
    recipe["context_learning_registration"]=rp("registration.json",reg)
    recipe_pin=rp("recipe.json",recipe)
    frozen={"passed":True,"contacts":0,"commit":"a"*40,"members":[{"member":c,"config_hash":m["config_hash"]} for c,m in members.items()]}
    paths={};bundles={};binding=[];metadata=[];jobpins=[]
    for c,m in members.items():
        ap=data/"attempts"/m["run_id"]/(m["attempt_id"]+".json")
        save(ap,{"state":"FINALIZED","actual":{"calls":5}});paths[c]=ap
        mp=data/"runs"/m["run_id"]/m["attempt_id"]/"manifest.json"
        manifest={"run_id":m["run_id"],"attempt":{"attempt_id":m["attempt_id"]},"config":{"config_hash":m["config_hash"]},"study_commit":frozen["commit"]}
        mpin=save(mp,manifest);binding.append({"candidate_id":c,"config":{"manifest":mpin}})
        metadata.append((manifest,{"job_id":m["attempt_id"]}))
        jobpins.append(save(mp.with_name("job.json"),{"status":"succeeded"}))
        bundles[str(mp)]=SimpleNamespace(attempt_state="FINALIZED",outputs_rows=[{} for _ in ids],manifest=manifest,split_ids=set(ids))
    monkeypatch.setattr(reader.context_learning,"_validate_scope",lambda *a,**k:None)
    monkeypatch.setattr(reader,"source_bindings",lambda *a:(binding,jobpins))
    monkeypatch.setattr(reader,"preflight_family",lambda *a:metadata)
    monkeypatch.setattr(reader,"verify_bundle",lambda p:bundles[str(p)])
    return SimpleNamespace(reader=reader,root=root,data=data,save=save,rp=rp,recipe=recipe,reg=reg,recipe_pin=recipe_pin,frozen=frozen,paths=paths,binding=binding,bundles=bundles,metadata=metadata,jobpins=jobpins)

def call(c):
    return c.reader.qualify_registered_context_family(recipe_pin=c.recipe_pin,repo_root=c.root,data_root=c.data,frozen_check=c.frozen)

def test_complete_family_uses_registered_counts_and_never_signs(case):
    c=case
    result=call(c)
    assert result["status"]=="ALL_MEMBERS_OPERATIONALLY_QUALIFIED"
    assert len(result["members"])==len(c.reg["member_bindings"])
    assert sum(m["rows"] for m in result["members"])==len(c.paths)*len(c.recipe["sample_ids"])
    assert result["root_read_signed_by_this_function"] is False
    assert result["quality_values_reported"] is False

@pytest.mark.parametrize("state",[None,"OPENED","ABORTED"])
def test_incomplete_family_waits_before_any_score_or_bundle_access(case,monkeypatch,state):
    c=case
    if state is None:c.paths["candidate"].unlink()
    else:c.save(c.paths["candidate"],{"state":state})
    monkeypatch.setattr(c.reader,"source_bindings",lambda *a:pytest.fail("opened score metadata early"))
    monkeypatch.setattr(c.reader,"verify_bundle",lambda *a:pytest.fail("opened output bundle early"))
    assert call(c)["status"]=="WAIT"

@pytest.mark.parametrize("fault",["frozen_failed","frozen_contacts","frozen_missing","frozen_extra","frozen_duplicate","frozen_config","commit","rows","ids","attempt","run","config","seal"])
def test_changed_or_incomplete_seal_identity_refuses(case,fault):
    c=case;b=c.bundles[next(iter(c.bundles))]
    if fault=="frozen_failed":c.frozen["passed"]=False
    elif fault=="frozen_contacts":c.frozen["contacts"]=1
    elif fault=="frozen_missing":c.frozen["members"].pop()
    elif fault=="frozen_extra":c.frozen["members"].append({"member":"unknown","config_hash":"x"})
    elif fault=="frozen_duplicate":c.frozen["members"].append(c.frozen["members"][0])
    elif fault=="frozen_config":c.frozen["members"][0]["config_hash"]="other"
    elif fault=="commit":b.manifest["study_commit"]="b"*40
    elif fault=="rows":b.outputs_rows.pop()
    elif fault=="ids":b.split_ids={"other"}
    elif fault=="attempt":b.manifest["attempt"]["attempt_id"]="other"
    elif fault=="run":b.manifest["run_id"]="other"
    elif fault=="config":b.manifest["config"]["config_hash"]="other"
    else:b.attempt_state="OPENED"
    with pytest.raises(PolicyError):call(c)

def test_changed_job_receipt_during_verify_refuses(case,monkeypatch):
    c=case;original=c.reader.verify_bundle
    def changed(p):
        Path(c.jobpins[0]["path"]).write_text("{}")
        return original(p)
    monkeypatch.setattr(c.reader,"verify_bundle",changed)
    with pytest.raises(PolicyError):call(c)

def test_changed_attempt_during_verify_refuses(case,monkeypatch):
    c=case;original=c.reader.verify_bundle
    def changed(p):
        c.save(c.paths["seed"],{"state":"OPENED"});return original(p)
    monkeypatch.setattr(c.reader,"verify_bundle",changed)
    with pytest.raises(PolicyError):call(c)

def test_scope_validation_precedes_operational_access(case,monkeypatch):
    c=case
    def refuse(*a,**k):raise PolicyError("configuration drift")
    monkeypatch.setattr(c.reader.context_learning,"_validate_scope",refuse)
    monkeypatch.setattr(c.reader,"source_bindings",lambda *a:pytest.fail("sources opened"))
    with pytest.raises(PolicyError,match="configuration drift"):call(c)
