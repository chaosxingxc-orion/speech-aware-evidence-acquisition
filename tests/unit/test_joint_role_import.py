"""Exact role import and original custody use only synthetic policies and assets."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    SystemTextPolicyBundle, PolicyError, import_exact_role_texts, cumulative_sources,
    assert_roster_disjoint,
)
from speech_aware_evidence_acquisition.rails import architecture_natural_registration as joint
from speech_aware_evidence_acquisition.rails import local_node_panel as local
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.core.preparation import digest


def parents():
    d = {"schema":"saea-system-text-policy-bundle-v3", "parent_ids":[],
        "seed_config_sha256":"a"*64, "construction_instruction":"Retain bounded source knowledge.",
        "role_text":{r:"Original " + r + " instruction." for r in ("perception","solver","reviewer","planner")},
        "supply":{"mode":"targeted","value_limit":2},
        "knowledge":{k:{"relpath":k+".json","sha256":"b"*64} for k in ("snapshot","release")},
        "construction_receipt":None,"cumulative_sources":[{"kind":"knowledge","sha256":"c"*64,"sample_ids":["slurp:train:ancestor"]}],
        "optimizer_experience":[], "context_layout":{"native_role_query_placement":None},
        "node_context":{"tool_schema_rendering":"per-role","reviewer_history_scope":"latest-solver-and-local-tools"}}
    seed = SystemTextPolicyBundle.from_json(d)
    donors = {}
    for role, sha in (("solver","d"),("reviewer","e")):
        doc = seed.as_json();doc["parent_ids"] = [seed.bundle_id]
        doc["role_text"][role] = "Selected exact " + role + " instruction.\n"
        doc["cumulative_sources"] = cumulative_sources([seed],[{"kind":"feedback","sha256":sha*64,"sample_ids":["slurp:train:"+role]}])
        donors[role] = SystemTextPolicyBundle.from_json(doc,parents=[seed])
    decision = {"schema":"saea-root-local-to-joint-development-decision-v1",
        "status":"SOURCE_ENGINEERING_APPROVED_RUNTIME_HELD", "owner_decision":227,"semantic_proposal_calls":0,
        "full_seed_bundle_id":seed.bundle_id,"donors":{r:{"role":r,"bundle_id":donors[r].bundle_id} for r in donors}}
    exposure = [{"kind":"selection","sha256":"f"*64,"sample_ids":["slurp:train:rejected-family-member"]}]
    return seed, donors, decision, exposure


@pytest.mark.parametrize("roles", [["solver"],["reviewer"],["solver","reviewer"]])
def test_exact_role_masks_preserve_full_seed_and_all_parent_exposure(roles):
    seed, donors, decision, exposure = parents()
    before = (seed.as_json(),{r:b.as_json() for r,b in donors.items()})
    child = import_exact_role_texts(seed,donors,roles=roles,decision=decision,selection_sources=exposure)
    value = child.as_json()
    assert value["parent_ids"] == [seed.bundle_id,donors["solver"].bundle_id,donors["reviewer"].bundle_id]
    assert value["cumulative_sources"] == cumulative_sources([seed,*donors.values()],exposure)
    for key in set(value)-{"parent_ids","cumulative_sources","role_text"}:assert value[key] == seed.as_json()[key]
    for role in value["role_text"]:
        assert value["role_text"][role] == (donors[role] if role in roles else seed).as_json()["role_text"][role]
    assert before == (seed.as_json(),{r:b.as_json() for r,b in donors.items()})
    with pytest.raises(PolicyError,match="overlaps"):
        assert_roster_disjoint(value["cumulative_sources"],["slurp:train:rejected-family-member"])


@pytest.mark.parametrize("fault",["foreign-donor","missing-donor","wrong-seed","duplicate-mask","perception-mask","empty-mask",
    "context-layout","node-context","knowledge","experience","construction","supply","foreign-role-text","missing-seed-parent","conflicting-exposure","held-owner","proposal-spend"])
def test_foreign_scope_and_conflicting_imports_are_refused(fault):
    seed,donors,decision,exposure = parents();roles=["solver"]
    if fault == "missing-donor": donors.pop("reviewer")
    elif fault == "foreign-donor":decision["donors"]["solver"]["bundle_id"]="f"*64
    elif fault == "wrong-seed":decision["full_seed_bundle_id"]="f"*64
    elif fault == "duplicate-mask":roles=["solver","solver"]
    elif fault == "perception-mask":roles=["perception"]
    elif fault == "empty-mask":roles=[]
    elif fault == "held-owner":decision["owner_decision"]=228
    elif fault == "proposal-spend":decision["semantic_proposal_calls"]=1
    elif fault == "conflicting-exposure":exposure.append({"kind":"feedback","sha256":"d"*64,"sample_ids":["slurp:train:other"]})
    else:
        d=donors["solver"].as_json()
        if fault == "context-layout":d["context_layout"]["native_role_query_placement"]="before-speech-v1"
        elif fault == "node-context":d["node_context"]["reviewer_history_scope"]="full"
        elif fault == "knowledge":d["knowledge"]["release"]["sha256"]="f"*64
        elif fault == "experience":d["optimizer_experience"]=[{"relpath":"experience.json","sha256":"f"*64}]
        elif fault == "construction":d["construction_instruction"]="Different construction instruction."
        elif fault == "supply":d["supply"]["value_limit"]=1
        elif fault == "foreign-role-text":d["role_text"]["perception"]="Different upstream text."
        elif fault == "missing-seed-parent":d["parent_ids"]=[]
        # Construct an opaque already validated original only for fixed-field drift testing.
        donors["solver"]=SystemTextPolicyBundle(json.dumps(d,sort_keys=True))
        decision["donors"]["solver"]["bundle_id"]=donors["solver"].bundle_id
    with pytest.raises(PolicyError):import_exact_role_texts(seed,donors,roles=roles,decision=decision,selection_sources=exposure)


def test_equal_kind_hash_conflicting_sample_sets_are_not_overwritten():
    seed,donors,decision,exposure=parents()
    d=donors["reviewer"].as_json();d["cumulative_sources"].append({"kind":"feedback","sha256":"d"*64,"sample_ids":["slurp:train:foreign"]})
    donors["reviewer"]=SystemTextPolicyBundle.from_json(d,parents=[seed]);decision["donors"]["reviewer"]["bundle_id"]=donors["reviewer"].bundle_id
    with pytest.raises(PolicyError,match="conflicting ancestry"):
        import_exact_role_texts(seed,donors,roles=["solver","reviewer"],decision=decision,selection_sources=exposure)


def policy_fixture(root,texts):
    value={"policy":"shared-synthetic", "native_episode":{"review_loop":"on","consumption_module":{"components":[{
        "component_id":"knowledge-consumption-opportunity","params":{}}]}},"phase_material":{}}
    params=value["native_episode"]["consumption_module"]["components"][0]["params"]
    for role,text in texts.items():
        relative="synthetic/"+hashlib.sha256(text.encode()).hexdigest()+".txt"
        path=root/"configs"/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        value["phase_material"][role]={"instruction_template":relative}
        params[role+"_template"]=relative
    return value


@pytest.mark.parametrize("fault",[None,"review-off","context","knowledge","scorer","wrong-text"])
def test_effective_policy_preserves_seed_topology_and_exact_texts(tmp_path,fault):
    seed,donors,_,_=parents()
    source=policy_fixture(tmp_path,seed.as_json()["role_text"])
    texts=seed.as_json()["role_text"];texts["solver"]=donors["solver"].as_json()["role_text"]["solver"]
    candidate=policy_fixture(tmp_path,texts)
    if fault == "review-off":candidate["native_episode"]["review_loop"]="off"
    elif fault == "context":candidate["native_episode"]["context_layout"]="different"
    elif fault == "knowledge":candidate["knowledge"]="different"
    elif fault == "scorer":candidate["scorers"]=["foreign"]
    elif fault == "wrong-text":texts["solver"]="Rewritten donor text."
    if fault:
        with pytest.raises(PolicyError):joint._joint_policy_projection(source,candidate,texts,repo_root=tmp_path)
    else:joint._joint_policy_projection(source,candidate,texts,repo_root=tmp_path)



def basis_fixture(tmp_path,monkeypatch,n=5):
    root,data=tmp_path/"repo",tmp_path/"data"
    seed,donors,decision,_=parents()
    ids=["slurp:train:row-"+str(i) for i in range(n)]
    def save(base,relative,value):
        path=base/relative;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,sort_keys=True)+"\n")
        return {"relpath":relative,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
    archive=SystemSearchArchive(data/"original/policy-archive")
    for bundle in [seed,*donors.values()]:archive.store_policy(bundle)
    def binding(bundle):
        path=data/"original/policy-archive/policies"/(bundle.bundle_id+".json")
        return {"schema":"saea-system-text-role-binding-v1","bundle_id":bundle.bundle_id,
            "bundle":{"relpath":path.relative_to(data).as_posix(),"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}}
    original={"cohorts":[{"sample_ids":ids}],"sampling":{"seed":42,"temperature":0},
        "execution":{"slot_count":4,"queue_depth":4},"contact_limits":{"model_per_trajectory":13,"fit_endpoints_per_model_contact":4}}
    original_pin=save(root,"original/population.json",original);monkeypatch.setattr(local,"SOURCE_POPULATION",original_pin)
    monkeypatch.setattr(joint,"load_population_config",lambda pin,**kwargs:deepcopy(original))
    source=policy_fixture(root,seed.as_json()["role_text"]);source_pin=save(root,"original/seed-policy.json",source)
    full_output={"facets":{},"values":{"perception":{sid:{"opaque":"original numeric carrier metadata"} for sid in ids+["slurp:train:outside"]}}}
    full_pin=save(data,"original/full400.json",{"output":full_output,"output_sha256":digest(full_output)})
    monkeypatch.setattr(joint,"JOINT_FULL_SUPPLY",full_pin)
    output={"facets":{},"values":{"perception":{sid:full_output["values"]["perception"][sid] for sid in ids}}}
    selected_pin=save(data,"original/n100.json",{"output":output,"output_sha256":digest(output)})
    receipt={"configured_sample_ids":ids,"runtime_sample_ids":list(reversed(ids)),"contacts":0,
        "output_equal":True,"warm_verified":True,"runtime_admission":False,"source_policy":source_pin,
        "source_prepared_phase_supply":full_pin,"prepared_phase_supply":selected_pin,
        "output_sha256":digest(output),"policy_binding":binding(seed)}
    receipt_pin=save(root,"original/seed-preparation.json",receipt);monkeypatch.setattr(local,"REVIEWER_SOURCE_RECEIPT",receipt_pin)
    donor_pins={}
    for role,bundle in donors.items():
        donor_pins[role]=save(root,"original/"+role+"-preparation.json",dict(deepcopy(receipt),policy_binding=binding(bundle)))
    monkeypatch.setattr(joint,"JOINT_DONOR_PREPARATIONS",donor_pins)
    decision.update(roster_basis=original_pin,analysis={"claims_benefit":False,"independent_validation":False,
        "runtime_adoption":False,"learner_export":False},rows_per_member=n,control_count=2,candidate_count=3,
        ordered_members=[{"id":"control","imports":[]},{"id":"control-aa","imports":[]},
        {"id":"solver-import","imports":["solver"]},{"id":"reviewer-import","imports":["reviewer"]},
        {"id":"joint-import","imports":["solver","reviewer"]}],
        prior_evidence=[save(root,"original/full-family-selection.json",{"synthetic":"complete root-visible original family"})])
    decision_pin=save(root,"original/decision.json",decision);monkeypatch.setattr(joint,"JOINT_SOURCE_DECISION",decision_pin)
    selection=cumulative_sources([],[{"kind":"selection","sha256":pin["sha256"],"sample_ids":ids}
        for pin in [decision_pin,*decision["prior_evidence"]]])
    population=deepcopy(original);cohort=population["cohorts"][0]
    cohort.update(control_ids=["control","control-aa"],candidate_ids=["solver-import","reviewer-import","joint-import"])
    members=[]
    for row in decision["ordered_members"]:
        bundle=import_exact_role_texts(seed,donors,roles=row["imports"],decision=decision,selection_sources=selection) if row["imports"] else seed
        policy=policy_fixture(root,bundle.as_json()["role_text"])
        members.append({"member_id":row["id"],"base_bundle_id":bundle.bundle_id,
            "execution_config":save(root,"members/"+row["id"]+".json",policy),
            "active_roles":["perception","solver","reviewer","planner"],"model_per_trajectory":13})
    population["architecture"]={"members":members}
    basis={"schema":joint.JOINT_BASIS_SCHEMA,"root_decision":decision_pin,"source_population":original_pin,
        "source_preparation_receipt":receipt_pin,"donor_preparation_receipts":donor_pins,"root_selection_sources":selection}
    basis_pin=save(root,"prospective/basis.json",basis)
    monkeypatch.setattr(joint,"default_phase_program",lambda value:None)
    monkeypatch.setattr(joint,"load_native_episode_config",lambda *args,**kwargs:SimpleNamespace(review_loop_enabled=True,max_contacts=13))
    return SimpleNamespace(root=root,data=data,population=population,basis=basis,basis_pin=basis_pin,
        save=save,receipt=receipt,decision=decision,donors=donors,seed=seed,output=output)


@pytest.mark.parametrize("n",[5,100])
def test_complete_configuration_derived_joint_basis_keeps_originals_and_exposure(tmp_path,monkeypatch,n):
    f=basis_fixture(tmp_path,monkeypatch,n)
    before={p:p.read_bytes() for base in (f.root,f.data) for p in base.rglob("*") if p.is_file()}
    bound=joint.require_joint_role_basis(f.basis_pin,f.population,repo_root=f.root,data_root=f.data)
    assert bound["output"] == f.output
    assert bound["policies"]["control"].bundle_id == bound["policies"]["control-aa"].bundle_id == f.seed.bundle_id
    assert set(bound["policies"]) == {r["id"] for r in f.decision["ordered_members"]}
    assert bound["cumulative_sources"] == cumulative_sources([f.seed,*f.donors.values()],f.basis["root_selection_sources"])
    assert before == {p:p.read_bytes() for base in (f.root,f.data) for p in base.rglob("*") if p.is_file()}


@pytest.mark.parametrize("fault",["partial-cohort","reordered-cohort","member-order","missing-candidate","wrong-control","foreign-bundle",
    "review-off","sampling","geometry","contact-cap","partial-selection","foreign-authority","partial-supply","changed-output","wrong-full-parent"])
def test_joint_basis_rejects_foreign_partial_or_changed_original_custody(tmp_path,monkeypatch,fault):
    f=basis_fixture(tmp_path,monkeypatch)
    cohort=f.population["cohorts"][0];member=f.population["architecture"]["members"][-1]
    if fault == "partial-cohort":cohort["sample_ids"].pop()
    elif fault == "reordered-cohort":cohort["sample_ids"].reverse()
    elif fault == "member-order":f.population["architecture"]["members"].reverse()
    elif fault == "missing-candidate":f.population["architecture"]["members"].pop()
    elif fault == "wrong-control":cohort["control_ids"]=["control","solver-import"]
    elif fault == "foreign-bundle":member["base_bundle_id"]="f"*64
    elif fault == "review-off":member["active_roles"]=["perception","solver"]
    elif fault == "sampling":f.population["sampling"]["seed"]=43
    elif fault == "geometry":f.population["execution"]["slot_count"]=8
    elif fault == "contact-cap":f.population["contact_limits"]["model_per_trajectory"]=26
    elif fault == "partial-selection":f.basis["root_selection_sources"].pop()
    elif fault == "foreign-authority":f.basis["root_decision"]["sha256"]="f"*64
    elif fault == "wrong-full-parent":
        f.receipt["source_prepared_phase_supply"]={"relpath":"original/foreign.json","sha256":"f"*64}
        new=f.save(f.root,"original/seed-preparation.json",f.receipt)
        monkeypatch.setattr(local,"REVIEWER_SOURCE_RECEIPT",new);f.basis["source_preparation_receipt"]=new
    else:
        path=f.data/f.receipt["prepared_phase_supply"]["relpath"];value=json.loads(path.read_text())
        if fault == "partial-supply":value["output"]["values"]["perception"].pop(cohort["sample_ids"][0])
        else:value["output"]["values"]["perception"][cohort["sample_ids"][0]]={"opaque":"changed"}
        value["output_sha256"]=digest(value["output"])
        f.receipt["prepared_phase_supply"]=f.save(f.data,path.relative_to(f.data).as_posix(),value)
        f.receipt["output_sha256"]=value["output_sha256"]
        new=f.save(f.root,"original/seed-preparation.json",f.receipt)
        monkeypatch.setattr(local,"REVIEWER_SOURCE_RECEIPT",new);f.basis["source_preparation_receipt"]=new
    f.basis_pin=f.save(f.root,"prospective/basis.json",f.basis)
    with pytest.raises((PolicyError,KeyError,ValueError)):
        joint.require_joint_role_basis(f.basis_pin,f.population,repo_root=f.root,data_root=f.data)
