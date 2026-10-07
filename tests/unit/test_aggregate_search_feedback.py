"""Source-qualified aggregate history survives a smaller next search population."""
import json
from copy import deepcopy
import pytest
from test_abstract_population_projection import setup, with_archive
from test_partitioned_context_learning import ready, prepare
from test_partitioned_context_continuation import continuation, run
from test_abstract_population_sources import pin
from speech_aware_evidence_acquisition.analysis import aggregate_search_feedback as subject
from speech_aware_evidence_acquisition.analysis.abstract_process_feedback import project_process_feedback, compact_process_feedback
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def sources(continuation,monkeypatch):
    s=continuation
    s.reg.update(schema="saea-partitioned-context-continuation-registration-v2",learner_profile="aggregate-template-records-v1")
    s.regpin=pin(s.root,"continuation.json",s.reg);s.parent=run(s)
    s.history["private_custody"]["parent_input_sha256"]=s.parent["input_sha256"]
    s.hreceipt["output"]=pin(s.data,"search-history.json",s.history,True)
    bindings={c["cohort_id"]:{m["member_id"]:m for m in c["members"]} for c in s.process_reg["cohorts"]}
    compact=compact_process_feedback(project_process_feedback(s.process,config=s.cfg,bindings=bindings))
    s.root_process={"schema":"saea-complete-root-process-feedback-v1","source_registration":s.process_reg["source_registration"],
        "process_feedback":compact,"runtime_admission":False,"learner_exported":False,
        "contacts_added":{"model":0,"official_scorer":0},"private_source_pins":[pin(s.data,"bound-process-source.json",s.process,True)],
        "plan":pin(s.root,"process-plan.json",{"scope":"Complete numeric source preparation."},True)}
    process_pin=pin(s.data,"complete-process.json",s.root_process)
    s.receipt={"schema":"saea-complete-trial-process-preparation-receipt-v1","status":"COMPLETE_ROOT_PROCESS_FEEDBACK_PREPARED",
        "process_feedback":process_pin,"runtime_admission":False,"learner_exported":False}
    s.request={"schema":"saea-aggregate-search-feedback-registration-v1","status":"ROOT_REGISTERED",
        "parent_input_sha256":s.parent["input_sha256"],"source_registration":s.process_reg["source_registration"],
        "history_completion":pin(s.root,"search-history-complete.json",s.hreceipt),
        "process_completion":pin(s.root,"search-process-complete.json",s.receipt),"max_feedback_bytes":2000000}
    monkeypatch.setattr(subject,"read_registered_population_sources",lambda **kw:s.joined)
    return s


def prepare_feedback(s):
    return subject.prepare_aggregate_search_feedback(s.archive,registration_pin=pin(s.root,"search-feedback.json",s.request),repo_root=s.root,data_root=s.data)


def outputs(s):return list((s.archive.root/"context-learning/search-feedback").glob("*.json"))


def test_all_historical_positions_preserved_and_no_new_allocation(sources):
    s=sources;result=prepare_feedback(s)
    evidence=result["aggregate_feedback"]
    assert len(evidence["records"])==15
    assert evidence["observed_populations"]==[{"iteration":i,"candidate_records":5} for i in [2,3,4]]
    assert len({r["record_id"] for r in evidence["records"]})==15
    assert evidence["records"][-1]["process"]["model_transitions"]
    assert len(evidence["comparators"])==12
    assert not result["learner_exported"] and not result["proposal_allocation_granted"]
    assert "PRIVATE_" not in json.dumps(evidence) and "slurp:train:" not in json.dumps(evidence)
    assert "slurp:train:PRIVATE_HISTORY" in result["private_custody"]["feedback_sample_ids"]
    assert not (s.archive.root/"context-learning/search-updates").exists()
    with pytest.raises(PolicyError):prepare_feedback(s)


@pytest.mark.parametrize("fault",["missing-read","open-source","history-hash","process-hash","missing-member","wrong-source","plan-hash","source-hash","unreviewed","budget","registration-extra"])
def test_refuse_before_partial_export(sources,monkeypatch,fault):
    s=sources
    if fault in {"missing-read","open-source"}:
        def fail(**kw):raise PolicyError("source qualification refused")
        monkeypatch.setattr(subject,"read_registered_population_sources",fail)
    elif fault=="history-hash":(s.data/"search-history.json").write_text("{}")
    elif fault=="process-hash":(s.data/"complete-process.json").write_text("{}")
    elif fault=="missing-member":
        s.root_process["process_feedback"]["cohorts"]["cohort-0"]["members"].pop("candidate-0")
    elif fault=="wrong-source":s.root_process["source_registration"]={"relpath":"other","sha256":"a"*64}
    elif fault=="plan-hash":(s.root/"process-plan.json").write_text("{}")
    elif fault=="source-hash":(s.data/"bound-process-source.json").write_text("{}")
    elif fault=="unreviewed":s.receipt["status"]="IN_PROGRESS"
    elif fault=="budget":s.request["max_feedback_bytes"]=1
    else:s.request["raw_cases"]=[]
    if fault in {"missing-member","wrong-source"}:
        s.receipt["process_feedback"]=pin(s.data,"complete-process.json",s.root_process)
    if fault in {"missing-member","wrong-source","unreviewed"}:
        s.request["process_completion"]=pin(s.root,"search-process-complete.json",s.receipt)
    with pytest.raises((PolicyError,KeyError)):prepare_feedback(s)
    assert not outputs(s)


def test_source_authority_change_during_assembly_refuses_write(sources,monkeypatch):
    s=sources;calls=[]
    def read(**kw):
        calls.append(1)
        if len(calls)>1:raise PolicyError("READ withdrawn")
        return s.joined
    monkeypatch.setattr(subject,"read_registered_population_sources",read)
    with pytest.raises(PolicyError):prepare_feedback(s)
    assert len(calls)==2 and not outputs(s)


def test_registration_mutation_during_assembly_refuses_write(sources,monkeypatch):
    s=sources;original=subject._round
    def mutate(*args,**kwargs):
        original(*args,**kwargs);(s.root/"search-feedback.json").write_text("{}")
    monkeypatch.setattr(subject,"_round",mutate)
    with pytest.raises(PolicyError):prepare_feedback(s)
    assert not outputs(s)


def test_real_process_pin_cell_annotation_is_verified_without_actor_export(sources):
    s = sources
    s.root_process["private_source_pins"][0]["cell_id"] = "attempt-private-process-member"
    s.receipt["process_feedback"] = pin(s.data, "complete-process.json", s.root_process)
    s.request["process_completion"] = pin(s.root, "search-process-complete.json", s.receipt)
    result = prepare_feedback(s)
    assert len(result["aggregate_feedback"]["records"]) == 15
    assert "attempt-private-process-member" not in json.dumps(result["aggregate_feedback"])


@pytest.mark.parametrize("fault", ["empty-cell", "numeric-cell", "extra-field", "changed-file", "outside-root"])
def test_annotated_private_pin_does_not_weaken_identity_checks(tmp_path, fault):
    root, data = tmp_path / "repo", tmp_path / "data"
    root.mkdir(); data.mkdir()
    value = pin(data, "source.json", {"receipt": "fixed"}, True)
    value["cell_id"] = "attempt-private-process-member"
    if fault == "empty-cell": value["cell_id"] = ""
    elif fault == "numeric-cell": value["cell_id"] = 7
    elif fault == "extra-field": value["unchecked"] = "field"
    elif fault == "changed-file": (data / "source.json").write_text("{}")
    else: value = {**pin(tmp_path, "outside.json", {}, True), "cell_id": value["cell_id"]}
    with pytest.raises(PolicyError):
        subject._verify_private_pin(value, root, data)
