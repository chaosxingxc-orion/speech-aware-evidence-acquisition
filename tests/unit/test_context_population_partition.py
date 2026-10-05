"""Two prospective K8 panels preserve every original policy and independent controls."""
import copy
import pytest
from test_context_population_scope import population, scope
from test_system_context_learning import pin, repin
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def partition(tmp_path, monkeypatch, panel="a"):
    f, _ = population(tmp_path, monkeypatch)
    parent = copy.deepcopy(f.registration)
    owner = {"schema": "saea-owner-template-k8-partition-v1", "resolution": {
        "K": 8, "N": 20, "panels": 2, "candidate_trajectories": 320,
        "control_trajectories": 80, "total_scientific_trajectories": 400,
        "preserve_all_original_templates": True, "independent_panel_controls": True,
        "no_between_panel_policy_update": True}}
    f.protocol["population_partition"] = {"schema": "saea-template-population-partition-v1",
        "panel": panel, "authorization": pin(f.root, "split-owner.json", owner),
        "parent_registration": pin(f.root, "parent-registration.json", parent)}
    start = 1 if panel == "a" else 9
    candidates = [f"branch-{i:02d}" for i in range(start, start+8)]
    f.protocol.update(K=8, candidate_members=candidates)
    f.registration["member_bindings"] = {c:copy.deepcopy(parent["member_bindings"][c])
        for c in candidates+["seed", "seed-aa"]}
    f.registration["expected_members"] = {c:b["run_id"] for c,b in f.registration["member_bindings"].items()}
    f.recipe["expected_members"] = copy.deepcopy(f.registration["expected_members"])
    repin(f)
    return f, owner, parent


@pytest.mark.parametrize("panel", ["a", "b"])
def test_exact_disjoint_k8_panels_pass(tmp_path, monkeypatch, panel):
    f, _, _ = partition(tmp_path, monkeypatch, panel)
    assert scope(f) == (f.protocol["candidate_members"], ["seed", "seed-aa"])


@pytest.mark.parametrize("fault", ["no-owner", "owner-schema", "owner-budget", "owner-control", "owner-update",
    "changed-owner", "bad-panel", "boolean-panel", "missing-parent", "changed-parent", "parent-hash",
    "parent-subset", "policy-substitution", "swapped-half", "reordered", "missing-control", "K16", "missing-original-owner"])
def test_partition_refuses_ambiguous_or_changed_scope(tmp_path, monkeypatch, fault):
    f, owner, parent = partition(tmp_path, monkeypatch)
    part=f.protocol["population_partition"]
    if fault=="no-owner":part.pop("authorization")
    elif fault=="owner-schema":owner["schema"]="other"
    elif fault=="owner-budget":owner["resolution"]["total_scientific_trajectories"]=360
    elif fault=="owner-control":owner["resolution"]["independent_panel_controls"]=False
    elif fault=="owner-update":owner["resolution"]["no_between_panel_policy_update"]=False
    elif fault=="bad-panel":part["panel"]="c"
    elif fault=="boolean-panel":part["panel"]=True
    elif fault=="missing-parent":part.pop("parent_registration")
    elif fault=="parent-hash":parent["registration_sha256"]="0"*64
    elif fault=="parent-subset":parent["member_bindings"].pop("branch-16")
    elif fault=="policy-substitution":f.registration["member_bindings"]["branch-01"]["bundle_id"]="1"*64
    elif fault=="swapped-half":part["panel"]="b"
    elif fault=="reordered":f.protocol["candidate_members"].reverse()
    elif fault=="missing-control":f.protocol["control_members"]=[]
    elif fault=="K16":f.protocol["K"]=16
    elif fault=="missing-original-owner":f.protocol.pop("population_authorization")
    if fault.startswith("owner-"):part["authorization"]=pin(f.root,"split-owner.json",owner)
    if fault.startswith("parent-"):part["parent_registration"]=pin(f.root,"parent-registration.json",parent)
    repin(f)
    if fault=="changed-owner":(f.root/"split-owner.json").write_text("{}")
    if fault=="changed-parent":(f.root/"parent-registration.json").write_text("{}")
    with pytest.raises((PolicyError, KeyError)):scope(f)


@pytest.mark.parametrize("panel", ["a", "b"])
def test_complete_k8_report_retains_own_null_and_all_eight(tmp_path, panel):
    from test_context_population_read import population as report_population, call
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    parts = report_population(tmp_path)
    d,r,g,p,roster,s = parts
    p["population_partition"] = {"schema": "saea-template-population-partition-v1", "panel":panel,
        "authorization":{"relpath":"split.json","sha256":"a"*64},
        "parent_registration":{"relpath":"parent.json","sha256":"b"*64}}
    start = 1 if panel=="a" else 9
    candidates=[f"branch-{i:02d}" for i in range(start,start+8)]
    ids=candidates+["seed","seed-aa"]
    p.update(K=8,candidate_members=candidates)
    g["member_bindings"]={c:b for c,b in g["member_bindings"].items() if c in ids}
    g["expected_members"]={c:b["run_id"] for c,b in g["member_bindings"].items()}
    r["expected_members"]=g["expected_members"]
    d["summaries"]={c:v for c,v in d["summaries"].items() if c in ids}
    d["feedback"]["sources"]=[v for v in d["feedback"]["sources"] if v["candidate_id"] in ids]
    for group in d["feedback"]["groups"]:
        group["members"]=[v for v in group["members"] if v["candidate_id"] in ids]
    g["registration_sha256"]=content_hash({k:v for k,v in g.items() if k!="registration_sha256"})
    d["registration_sha256"]=g["registration_sha256"]
    report=call(parts)
    assert len(report["official_summaries"])==10
    assert len(report["branches"]["context"]["comparisons"])==17
    assert report["optimizer_feedback_allowed"] is False
    d["feedback"]["groups"][0]["members"].pop()
    with pytest.raises(PolicyError):call(parts)
