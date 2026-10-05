"""A complete source join must qualify every cohort before reading any quality."""
from copy import deepcopy
from types import SimpleNamespace
import hashlib
import json
import pytest
from test_experiment_population_config import config
from speech_aware_evidence_acquisition.analysis import abstract_population_sources as subject
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def pin(root, name, value, external=False):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value))
    return {("path" if external else "relpath"): str(p) if external else name,
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    root, data = tmp_path / "repo", tmp_path / "data"
    root.mkdir(); data.mkdir()
    cfg = config((3, 2), 2)
    cp = pin(root, "population.json", cfg)
    calls, families, authorities = [], [], {}
    for c in cfg["cohorts"]:
        cid = c["cohort_id"]
        ids = c["control_ids"] + c["candidate_ids"]
        bindings = {x: {"run_id": cid + "-" + x, "attempt_id": "attempt-" + x}
                    for x in ids}
        reg = {"member_bindings": bindings, "expected_members": {x:v["run_id"] for x,v in bindings.items()}}
        protocol = {"candidate_members": c["candidate_ids"], "control_members": c["control_ids"]}
        reg["protocol"] = pin(root, cid + "-protocol.json", protocol)
        recipe = {"family_id": cid, "sample_ids": c["sample_ids"],
                  "expected_members": reg["expected_members"],
                  "context_learning_registration": pin(root, cid + "-reg.json", reg)}
        rp = pin(root, cid + "-recipe.json", recipe)
        frozen = pin(data, cid + "-frozen.json", {"commit": cid}, True)
        saved = pin(data, cid + "-family.json", {"bindings": [{"candidate_id": x} for x in ids]}, True)
        for x,v in bindings.items():
            pin(data, "attempts/"+v["run_id"]+"/"+v["attempt_id"]+".json", {"state":"FINALIZED"}, True)
        families.append({"cohort_id": cid, "recipe": rp, "frozen_check": frozen, "saved_family": saved})
        authorities[cid] = {"read_run_id": cid + "-READ", "ledger_row_sha256": cid}
    manifest = {"schema":"saea-abstract-population-source-registration-v1",
                "status":"ROOT_REGISTERED", "scope":"abstract-feedback-source-join-only",
                "runtime_admission":False, "projection_config":cp, "families":families}
    mp = pin(root, "sources.json", manifest)
    def scope(recipe, reg, protocol, **kwargs):
        return protocol["candidate_members"], protocol["control_members"]
    monkeypatch.setattr(subject.learning, "_validate_scope", scope)
    def authority(spec, **kwargs):
        calls.append(("authority", spec["family_id"]))
        return deepcopy(authorities[spec["family_id"]])
    def qualify(**kwargs):
        cid = kwargs["frozen_check"]["commit"]
        calls.append(("qualify", cid))
        return {"status":"ALL_MEMBERS_OPERATIONALLY_QUALIFIED", "members":[],
                "attempt_metadata_pins":[], "job_metadata_pins":[]}
    monkeypatch.setattr(subject, "_reader", lambda root: SimpleNamespace(
        CLI=SimpleNamespace(require_read_registration=authority),
        qualify_registered_context_family=qualify))
    def feedback(bindings, **kwargs):
        cid = kwargs["recipe_pin"]["relpath"].replace("-recipe.json", "")
        calls.append(("quality", cid))
        return {"private_evidence":cid}
    monkeypatch.setattr(subject.learning, "_qualified_feedback", feedback)
    return SimpleNamespace(root=root, data=data, cfg=cfg, manifest=manifest, pin=mp,
                           calls=calls, authorities=authorities)


def run(s):
    return subject.read_registered_population_sources(
        source_registration_pin=s.pin, repo_root=s.root, data_root=s.data)


def rewrite(s):
    s.pin = pin(s.root, "sources.json", s.manifest)


def test_every_family_is_qualified_before_first_quality_read(setup):
    s=setup; out=run(s)
    assert list(out["private_families"]) == [c["cohort_id"] for c in s.cfg["cohorts"]]
    assert out["learner_exported"] is False and out["model_contacts"] == out["scorer_contacts"] == 0
    first = next(i for i,x in enumerate(s.calls) if x[0]=="quality")
    assert [x for x in s.calls[:first] if x[0]=="qualify"] == [("qualify", c["cohort_id"]) for c in s.cfg["cohorts"]]


@pytest.mark.parametrize("fault", ["draft", "missing_family", "extra_family", "duplicate_family", "wrong_order",
    "wrong_members", "wrong_roster", "changed_source", "outside_data", "unsigned_last", "open_last", "missing_attempt"])
def test_refusal_before_any_quality_read(setup, fault):
    s=setup; last=s.manifest["families"][-1]; cid=last["cohort_id"]
    if fault=="draft": s.manifest["status"]="DRAFT"
    elif fault=="missing_family": s.manifest["families"].pop()
    elif fault=="extra_family": s.manifest["families"].append(deepcopy(last))
    elif fault=="duplicate_family": s.manifest["families"][0]=deepcopy(last)
    elif fault=="wrong_order": s.manifest["families"].reverse()
    elif fault in {"wrong_members", "wrong_roster"}:
        rp=s.root/last["recipe"]["relpath"]; r=json.loads(rp.read_text())
        if fault=="wrong_roster": r["sample_ids"].reverse()
        else:
            regp=s.root/r["context_learning_registration"]["relpath"]; reg=json.loads(regp.read_text())
            pp=s.root/reg["protocol"]["relpath"]; p=json.loads(pp.read_text());p["candidate_members"].reverse()
            reg["protocol"]=pin(s.root, pp.name,p); r["context_learning_registration"]=pin(s.root,regp.name,reg)
        last["recipe"]=pin(s.root,rp.name,r)
    elif fault=="changed_source": (s.data/(cid+"-frozen.json")).write_text("{}")
    elif fault=="outside_data": last["saved_family"]=pin(s.root,"outside.json",{},True)
    elif fault=="unsigned_last": s.authorities.pop(cid)
    else:
        p=next((s.data/"attempts"/(cid+"-seed")).glob("*.json"))
        if fault=="open_last": p.write_text('{"state":"OPENED"}')
        else: p.unlink()
    rewrite(s)
    with pytest.raises((PolicyError, KeyError, FileNotFoundError)):
        run(s)
    assert not any(x[0]=="quality" for x in s.calls)
    if fault in {"unsigned_last","open_last","missing_attempt"}:
        assert not any(x[0]=="qualify" for x in s.calls)


def test_source_change_during_last_qualification_prevents_all_quality(setup, monkeypatch):
    s=setup; original=subject._reader(s.root)
    def qualify(**kwargs):
        q=original.qualify_registered_context_family(**kwargs)
        if kwargs["frozen_check"]["commit"]==s.cfg["cohorts"][-1]["cohort_id"]:
            (s.root/"population.json").write_text("{}")
        return q
    monkeypatch.setattr(subject,"_reader",lambda root:SimpleNamespace(CLI=original.CLI,qualify_registered_context_family=qualify))
    with pytest.raises(PolicyError): run(s)
    assert not any(x[0]=="quality" for x in s.calls)


def test_authority_change_during_qualification_prevents_all_quality(setup, monkeypatch):
    s=setup; original=subject._reader(s.root)
    def qualify(**kwargs):
        q=original.qualify_registered_context_family(**kwargs)
        s.authorities[s.cfg["cohorts"][0]["cohort_id"]]["ledger_row_sha256"]="changed"
        return q
    monkeypatch.setattr(subject,"_reader",lambda root:SimpleNamespace(CLI=original.CLI,qualify_registered_context_family=qualify))
    with pytest.raises(PolicyError,match="authority changed"): run(s)
    assert not any(x[0]=="quality" for x in s.calls)


@pytest.mark.parametrize("fault", ["scope", "extra_manifest", "extra_source", "bad_external_pin", "duplicate_identity"])
def test_ambiguous_source_contracts_are_refused(setup, fault):
    s=setup
    if fault=="scope": s.manifest["scope"]="runtime"
    elif fault=="extra_manifest": s.manifest["secret"]="not allowed"
    elif fault=="extra_source": s.manifest["families"][0]["secret"]="not allowed"
    elif fault=="bad_external_pin": s.manifest["families"][0]["frozen_check"]["extra"]=True
    else:
        last=s.manifest["families"][-1];p=s.root/last["recipe"]["relpath"];r=json.loads(p.read_text())
        r["family_id"]=s.cfg["cohorts"][0]["cohort_id"];last["recipe"]=pin(s.root,p.name,r)
    rewrite(s)
    with pytest.raises(PolicyError):run(s)
    assert not any(x[0]=="quality" for x in s.calls)


def test_later_qualification_wait_does_not_read_earlier_quality(setup, monkeypatch):
    s=setup; original=subject._reader(s.root)
    def qualify(**kwargs):
        q=original.qualify_registered_context_family(**kwargs)
        if kwargs["frozen_check"]["commit"]==s.cfg["cohorts"][-1]["cohort_id"]:
            q["status"]="WAIT"
        return q
    monkeypatch.setattr(subject,"_reader",lambda root:SimpleNamespace(CLI=original.CLI,qualify_registered_context_family=qualify))
    with pytest.raises(PolicyError,match="all source families"):run(s)
    assert not any(x[0]=="quality" for x in s.calls)


def test_source_changes_during_feedback_never_return_partial_export(setup, monkeypatch):
    s=setup
    def read(*args,**kwargs):
        (s.data/(s.cfg["cohorts"][0]["cohort_id"]+"-frozen.json")).write_text("{}")
        return {"private":"never returned"}
    monkeypatch.setattr(subject.learning,"_qualified_feedback",read)
    with pytest.raises(PolicyError,match="external source changed"):run(s)


def test_real_shared_reader_loads_without_source_or_model_contact():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]
    reader=subject._reader(root)
    assert callable(reader.qualify_registered_context_family)
    assert callable(reader.CLI.require_read_registration)



def test_job_metadata_change_during_qualification_prevents_all_quality(setup, monkeypatch):
    s=setup;original=subject._reader(s.root)
    job=pin(s.data,"official-job.json",{"status":"succeeded"},True)
    def qualify(**kwargs):
        q=original.qualify_registered_context_family(**kwargs)
        q["job_metadata_pins"]=[job]
        if kwargs["frozen_check"]["commit"]==s.cfg["cohorts"][-1]["cohort_id"]:
            (s.data/"official-job.json").write_text('{"status":"failed"}')
        return q
    monkeypatch.setattr(subject,"_reader",lambda root:SimpleNamespace(CLI=original.CLI,qualify_registered_context_family=qualify))
    with pytest.raises(PolicyError,match="external source changed"):run(s)
    assert not any(x[0]=="quality" for x in s.calls)
