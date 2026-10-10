"""Duration-only architecture budget proofs never invoke a model or tokenizer."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.rails.architecture_audio_budget import (
    derive_manual_architecture_audio_budget, require_manual_architecture_audio_budget,
)
ROOT = Path(__file__).resolve().parents[2]

def configured(label="seed", count=100):
    stem=f"slurp-native-stage3-simple-consumption-{label}-n{count}-"+("v2" if count==20 else "v1")
    # Read the registered fragment directly: decision 243 (2026-10-10) retired the unflown review-off,
    # solver-lookup and seed-aa N100 cells (readiness superseded), which campaign loading refuses by design;
    # the budget arithmetic below is proven against their unchanged registered bytes.
    import json
    c=json.loads((ROOT/"configs/experiment"/f"{stem}.json").read_text(encoding="utf-8"))["cells"][0]
    return deepcopy(compose(ROOT,c["model_fragment"],c["dataset_fragment"],c["baseline_fragment"],stem).values)

@pytest.mark.parametrize("label,contacts,minimum", [("seed",13,3820),("seed-aa",13,3820),("review-off",2,588),("solver-lookup",3,882)])
def test_actual_immutable_duration_metadata_and_parsed_roles(label,contacts,minimum):
    values=configured(label)
    report=derive_manual_architecture_audio_budget(values)
    assert report["max_contacts_per_sample"] == contacts
    assert report["required_integer_audio_seconds"] == minimum
    values["execution_plan"]["planned_speech_audio_seconds"]=max(1500,minimum)
    assert require_manual_architecture_audio_budget(values) == report

@pytest.mark.parametrize("label",["seed","seed-aa"])
def test_original_n100_budget_is_refused(label):
    with pytest.raises(ValueError,match="cumulative speech-audio"):
        require_manual_architecture_audio_budget(configured(label))

@pytest.mark.parametrize("label",["seed","seed-aa","review-off","solver-lookup"])
def test_original_n20_and_reduced_n100_remain_adequate(label):
    assert require_manual_architecture_audio_budget(configured(label,20))["required_integer_audio_seconds"] <= 1500
    if label in ("review-off","solver-lookup"):
        assert require_manual_architecture_audio_budget(configured(label))["required_integer_audio_seconds"] <= 1500

@pytest.mark.parametrize("durations",[[0.1],[0.1,0.2],[1.01,2.02,3.03,4.04]])
def test_variable_roster_and_integer_rounding(durations):
    values=configured("review-off"); ids=[f"fixture-{i}" for i in range(len(durations))]
    values["populations"][0]["ids"]=ids;values["population"]["count"]=len(ids)
    rows=[dict(sample_id=sid,audio_seconds=s) for sid,s in zip(ids,durations)]
    report=derive_manual_architecture_audio_budget(values,rows)
    import math
    assert report["required_integer_audio_seconds"] == math.ceil(math.fsum(s*2 for s in durations))
    values["execution_plan"]["planned_speech_audio_seconds"]=report["required_integer_audio_seconds"]
    require_manual_architecture_audio_budget(values,rows)
    values["execution_plan"]["planned_speech_audio_seconds"]-=1
    with pytest.raises(ValueError,match="cumulative speech-audio"):
        require_manual_architecture_audio_budget(values,rows)

@pytest.mark.parametrize("bad",[None,True,"1",0,-1,float("nan"),float("inf")])
def test_invalid_durations_refused(bad):
    values=configured();rows=deepcopy(values["items"]);rows[0]["audio_seconds"]=bad
    with pytest.raises(ValueError,match="duration"):
        derive_manual_architecture_audio_budget(values,rows)

@pytest.mark.parametrize("mutation",["missing","duplicate","foreign","missing-id","missing-duration","nonmapping","empty","count","configured-duplicate"])
def test_exact_roster_refused(mutation):
    values=configured(); rows=deepcopy(values["items"])
    if mutation=="missing":rows.pop()
    elif mutation=="duplicate":rows.append(deepcopy(rows[0]))
    elif mutation=="foreign":rows[0]["sample_id"]="foreign"
    elif mutation=="missing-id":rows[0].pop("sample_id")
    elif mutation=="missing-duration":rows[0].pop("audio_seconds")
    elif mutation=="nonmapping":rows[0]=None
    elif mutation=="empty":rows=[]
    elif mutation=="count":values["population"]["count"]+=1
    else:values["populations"][0]["ids"].append(values["populations"][0]["ids"][0])
    with pytest.raises(ValueError):derive_manual_architecture_audio_budget(values,rows)

@pytest.mark.parametrize("key,value",[("prepared_execution_units",{"slice":True}),("native_contact_fit",{"max_speech_packets":2})])
def test_unknown_audio_geometry_refused(key,value):
    values=configured();values[key]=value
    with pytest.raises(ValueError,match="whole-utterance"):
        derive_manual_architecture_audio_budget(values)

@pytest.mark.parametrize("limit",[True,1500.0,None,-1])
def test_registered_cap_must_be_a_positive_integer(limit):
    values=configured();values["execution_plan"]["planned_speech_audio_seconds"]=limit
    with pytest.raises(ValueError):require_manual_architecture_audio_budget(values)

def test_nongenerative_and_unrelated_modes_are_unchanged():
    assert require_manual_architecture_audio_budget({"carrier_lock_key":"earnings21-original"}) is None
    values=configured();values["family_budget"]["official_complete_scoring_jobs"]=0
    assert require_manual_architecture_audio_budget(values,[]) is None

def test_actual_preflight_refuses_before_plan_gate_or_attempt(tmp_path,monkeypatch):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    values=configured();rt=object.__new__(FlightRuntime)
    rt._require_prior_stages=lambda stage:None
    rt._prepare=lambda:(values,"slurp","fixture-split","fixture-identity")
    rt._composed=SimpleNamespace(values=values);rt._adapter=object()
    rt._samples=tuple(SimpleNamespace(sample_id=row["sample_id"],audio_seconds=row["audio_seconds"]) for row in values["items"])
    def forbidden(*args,**kwargs):raise AssertionError("No plan/gate/attempt may follow inadequate audio budget")
    rt._build_execution_plan=forbidden
    with pytest.raises(ValueError,match="cumulative speech-audio"):
        rt.preflight()
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize("label",["seed","seed-aa"])
def test_actual_author_member_prewrite_refuses_old_audio(tmp_path,label):
    # seed is still a ready cell, so the authoring prewrite refuses on the audio budget; seed-aa was retired by
    # decision 243 (2026-10-10, readiness superseded) and is refused even earlier, at campaign loading.
    expected = "cumulative speech-audio" if label == "seed" else "explicit scientific readiness"
    import importlib.util,json
    path=ROOT/"scripts/analysis/author_manual_architecture_package.py"
    spec=importlib.util.spec_from_file_location("audio_author",path);author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
    descriptor=json.loads((ROOT/"docs/readiness/2026-10-07-slurp-simple-consumption-n100-preparation-v1/capacity-prepared-members-v1.json").read_bytes())
    receipt=next(row["preparation_receipts"]["generation"] for row in descriptor["members"] if row["label"]==label)
    stage={"control_members":[label],"candidate_members":[]}
    with pytest.raises(ValueError,match=expected):
        author._member_inputs({"preparation_receipts":{label:receipt}},stage,ROOT)
    assert not list(tmp_path.iterdir())

@pytest.mark.parametrize("adequate",[False,True])
def test_actual_named_registration_branch_checks_audio_before_prerequisites(monkeypatch,adequate):
    import importlib.util
    from speech_aware_evidence_acquisition.rails import architecture_natural_registration as api
    import speech_aware_evidence_acquisition.core.config as configs
    path=ROOT/"scripts/checks/flight_registration_check.py"
    spec=importlib.util.spec_from_file_location("audio_named_gate",path);checker=importlib.util.module_from_spec(spec)
    import sys
    monkeypatch.setitem(sys.modules,spec.name,checker);spec.loader.exec_module(checker)
    values=configured(); stem="slurp-native-stage3-simple-consumption-seed-n100-v1"
    cell,=load_campaign_cells(ROOT,stem); calls=[]
    if adequate: values["execution_plan"]["planned_speech_audio_seconds"]=3820
    monkeypatch.setattr(configs,"compose",lambda *a,**k:SimpleNamespace(values=values))
    monkeypatch.setattr(api,"require_architecture_n20_registration",lambda *a,**k:calls.append("authority"))
    report=SimpleNamespace(experiment=stem,run_id=cell.run_id,run_ids={},findings=[])
    checker._check_registered_supply_binding(report,values,SimpleNamespace(repo_root=ROOT),"absent-audio-fixture",{},cell=cell.document,fragment=values,data_root=ROOT)
    if adequate:
        assert calls==["authority"] and not report.findings
    else:
        assert calls==[] and any("cumulative speech-audio" in finding.message for finding in report.findings)

@pytest.mark.parametrize("label",["seed","review-off","solver-lookup"])
def test_actual_runtime_advances_only_after_adequate_loaded_durations(label):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    values=configured(label);values["execution_plan"]["planned_speech_audio_seconds"]=max(1500,derive_manual_architecture_audio_budget(values)["required_integer_audio_seconds"])
    rt=object.__new__(FlightRuntime);rt._require_prior_stages=lambda stage:None
    rt._prepare=lambda:(values,"slurp","fixture-split","fixture-identity")
    rt._composed=SimpleNamespace(values=values);rt._adapter=object()
    rt._samples=tuple(SimpleNamespace(sample_id=row["sample_id"],audio_seconds=row["audio_seconds"]) for row in values["items"])
    def stop(*a,**k):raise RuntimeError("advanced-after-audio-guard")
    rt._build_execution_plan=stop
    with pytest.raises(RuntimeError,match="advanced-after-audio-guard"):rt.preflight()

def test_loaded_duration_cannot_be_hidden_by_config_metadata():
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    values=configured();values["execution_plan"]["planned_speech_audio_seconds"]=3820
    rt=object.__new__(FlightRuntime);rt._require_prior_stages=lambda stage:None
    rt._prepare=lambda:(values,"slurp","fixture-split","fixture-identity")
    rt._composed=SimpleNamespace(values=values);rt._adapter=object()
    rt._samples=tuple(SimpleNamespace(sample_id=row["sample_id"],audio_seconds=row["audio_seconds"]*2) for row in values["items"])
    rt._build_execution_plan=lambda *a,**k:pytest.fail("Inadequate actual loaded durations advanced to plan")
    with pytest.raises(ValueError,match="cumulative speech-audio"):rt.preflight()

@pytest.mark.parametrize("rows",[None,"not-metadata",{},[]])
def test_missing_row_sequence_refused(rows):
    values=configured();values["items"]=rows
    with pytest.raises(ValueError,match="duration metadata"):derive_manual_architecture_audio_budget(values)

@pytest.mark.parametrize("mutation",["carrier","multiple-rosters","invalid-roster","native","overflow"])
def test_unknown_contract_or_overflow_refused(mutation):
    values=configured()
    if mutation=="carrier":values["carrier_lock_key"]="unknown"
    elif mutation=="multiple-rosters":values["populations"].append(deepcopy(values["populations"][0]))
    elif mutation=="invalid-roster":values["populations"]=[None]
    elif mutation=="native":values.pop("native_episode")
    else:
        for row in values["items"]:row["audio_seconds"]=1e308
    with pytest.raises(ValueError):derive_manual_architecture_audio_budget(values)

@pytest.mark.parametrize("packets",[True,0,None,1.0])
def test_packet_bound_must_be_exactly_one_integer(packets):
    values=configured();values["native_contact_fit"]["max_speech_packets"]=packets
    with pytest.raises(ValueError,match="whole-utterance"):derive_manual_architecture_audio_budget(values)

def test_unrelated_runtime_does_not_read_diagnostic_audio_fields():
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    class Sample:
        sample_id="unrelated"
        @property
        def audio_seconds(self):raise AssertionError("Unrelated audio semantics must be untouched")
    values={};rt=object.__new__(FlightRuntime);rt._require_prior_stages=lambda stage:None
    rt._prepare=lambda:(values,"unrelated","fixture-split","fixture-identity")
    rt._composed=SimpleNamespace(values=values);rt._adapter=object();rt._samples=(Sample(),)
    def stop(*a,**k):raise RuntimeError("unchanged-plan-construction")
    rt._build_execution_plan=stop
    with pytest.raises(RuntimeError,match="unchanged-plan-construction"):rt.preflight()

@pytest.mark.parametrize("key",["prepared_speech_observations","live_speech_observations"])
def test_additional_observation_semantics_are_not_extrapolated(key):
    values=configured();values[key]={"unknown":"slice-or-extra-audio"}
    with pytest.raises(ValueError,match="whole-utterance"):derive_manual_architecture_audio_budget(values)

def test_finite_individual_durations_cannot_overflow_the_sum():
    values=configured("review-off")
    for row in values["items"]:row["audio_seconds"]=1e307
    with pytest.raises(ValueError,match="not finite"):derive_manual_architecture_audio_budget(values)

@pytest.mark.parametrize("adequate",[False,True])
def test_real_runtime_adapter_samples_preserve_order_and_precontact_outcome(monkeypatch,adequate):
    from speech_aware_evidence_acquisition.rails.adapters import slurp_runtime
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    values=configured(); rows=list(reversed(values["items"]))
    # Only media verification is replaced; real adapter samples and namespace checks execute.
    monkeypatch.setattr(slurp_runtime,"load_runtime_view",lambda *a,**k:rows)
    samples=slurp_runtime.roster_samples(values,ROOT,limit_sample_ids=values["populations"][0]["ids"])
    assert [s.sample_id for s in samples]==[row["sample_id"] for row in rows]
    if adequate:values["execution_plan"]["planned_speech_audio_seconds"]=3820
    rt=object.__new__(FlightRuntime);rt._require_prior_stages=lambda stage:None
    rt._prepare=lambda:(values,"slurp","fixture-split","fixture-identity")
    rt._composed=SimpleNamespace(values=values);rt._adapter=object();rt._samples=samples
    def stop(*a,**k):raise RuntimeError("advanced-after-actual-adapter-budget")
    rt._build_execution_plan=stop
    if adequate:
        with pytest.raises(RuntimeError,match="advanced-after-actual-adapter-budget"):rt.preflight()
    else:
        with pytest.raises(ValueError,match="cumulative speech-audio"):rt.preflight()
    assert [s.sample_id for s in samples]==[row["sample_id"] for row in rows]

def test_huge_integer_duration_is_a_controlled_refusal():
    values=configured();values["items"][0]["audio_seconds"]=10**1000
    with pytest.raises(ValueError,match="duration"):derive_manual_architecture_audio_budget(values)
