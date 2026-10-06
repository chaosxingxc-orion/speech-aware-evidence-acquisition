"""Parent planning cannot bypass complete-population source custody."""
import copy
import json
import pytest
from test_abstract_population_sources import setup, pin
from test_system_search_parent_selection import config
from test_system_search_measurement import profile, timing
from speech_aware_evidence_acquisition.analysis import abstract_population_sources as sources
from speech_aware_evidence_acquisition.rails import system_search_parent_selection as subject
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_search_archive import SystemSearchArchive
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def prepared(setup, monkeypatch):
    s = setup
    def feedback(bindings, *, recipe_pin, **kwargs):
        tag = recipe_pin["relpath"].replace("-recipe.json", "")
        s.calls.append(("quality", tag))
        cohort = next(c for c in s.cfg["cohorts"] if c["cohort_id"] == tag)
        ids = cohort["sample_ids"]; members = cohort["control_ids"] + cohort["candidate_ids"]
        bound = {cid: {"bundle_id": content_hash("seed" if cid in cohort["control_ids"] else cid)} for cid in members}
        doc = {"measurement_profile": profile(), "feedback": {"groups": [{"sample_id": sid} for sid in ids]}, "summaries": {}}
        for i, cid in enumerate(members):
            doc["summaries"][cid] = dict(slu_f1=.8-i*.05, intent=.8, reliable_completion_rate=1.,
                model_calls=10, tool_calls=0, sample_timing=timing(ids, seconds=10+i), timing_session_sha256="e"*64)
        return doc, {}, {"member_bindings": bound}, {"measurement_profile": profile()}, cohort["candidate_ids"], cohort["control_ids"], {}
    monkeypatch.setattr(sources.learning, "_qualified_feedback", feedback)
    s.archive = SystemSearchArchive(s.data / "archive")
    s.request = {"schema": "saea-qualified-parent-selection-request-v1", "status": "ROOT_REGISTERED",
        "source_registration": s.pin, "cohort_id": "cohort-0", "selection_config": config(),
        "usage_counts": {content_hash(cid): 0 for cid in ["seed", *s.cfg["cohorts"][0]["candidate_ids"]]},
        "replicate_rule": "designated-control-then-registered-order"}
    return s


def run(s):
    return subject.prepare_qualified_parent_selection(s.archive,
        request_pin=pin(s.root, "selection-request.json", s.request), repo_root=s.root, data_root=s.data)


def test_all_cohorts_qualify_before_parent_selection_and_archive(prepared):
    s = prepared; result = run(s)
    assert result["selection"]["frontier_parent_ids"] == [content_hash("seed")]
    assert len(result["measurements"]) == 4
    assert result["control_ids"] == ["seed", "seed-aa"]
    assert result["learner_exported"] is False and result["runtime_admission"] is False
    first = next(i for i, event in enumerate(s.calls) if event[0] == "quality")
    assert [e for e in s.calls[:first] if e[0] == "qualify"] == [("qualify", "cohort-0"), ("qualify", "cohort-1")]
    assert len(list(s.archive.root.rglob("*.json"))) == 1
    with pytest.raises(PolicyError): run(s)


@pytest.mark.parametrize("fault", ["open_last", "unsigned_last", "missing_family", "bad_cohort", "draft"])
def test_partial_population_cannot_select_or_write(prepared, fault):
    s = prepared
    if fault == "open_last":
        f = next((s.data / "attempts/cohort-1-seed").glob("*.json")); f.write_text('{"state":"OPENED"}')
    elif fault == "unsigned_last": s.authorities.pop("cohort-1")
    elif fault == "missing_family":
        s.manifest["families"].pop(); s.request["source_registration"] = pin(s.root,"sources.json",s.manifest)
    elif fault == "bad_cohort": s.request["cohort_id"] = "foreign"
    else: s.request["status"] = "DRAFT"
    with pytest.raises((PolicyError, KeyError)): run(s)
    assert not list(s.archive.root.rglob("*.json"))
    assert not any(e[0] == "quality" for e in s.calls)


def test_selection_rechecks_source_before_any_archive_write(prepared, monkeypatch):
    s = prepared; original = subject.select_search_parents
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        (s.data / "cohort-1-frozen.json").write_text("{}")
        return result
    monkeypatch.setattr(subject, "select_search_parents", mutate)
    with pytest.raises(PolicyError): run(s)
    assert not list(s.archive.root.rglob("*.json"))


def test_duplicate_policy_keeps_designated_measurement_not_best_draw(prepared, monkeypatch):
    s = prepared; original = sources.learning._qualified_feedback
    def repeated(*args, **kwargs):
        result = original(*args, **kwargs)
        doc, _, reg, _, candidates, _, _ = result
        cid = candidates[-1]; reg["member_bindings"][cid]["bundle_id"] = content_hash("seed")
        doc["summaries"][cid]["slu_f1"] = 1.
        return result
    monkeypatch.setattr(sources.learning, "_qualified_feedback", repeated)
    s.request["usage_counts"].pop(content_hash("candidate-2"))
    result = run(s)
    assert len(result["duplicate_bundle_replicates"]) == 2
    assert result["measurements"][0]["slu_f1"] == .8
    assert result["duplicate_bundle_replicates"][0]["slu_f1"] == 1.



def test_feedback_drift_between_two_qualifications_refuses_selection(prepared, monkeypatch):
    s = prepared; original = sources.learning._qualified_feedback; count = 0
    def drifting(*args, **kwargs):
        nonlocal count
        result = original(*args, **kwargs); count += 1
        if count > len(s.cfg["cohorts"]): result[0]["summaries"]["seed"]["slu_f1"] = .1
        return result
    monkeypatch.setattr(sources.learning, "_qualified_feedback", drifting)
    with pytest.raises(PolicyError, match="source changed"): run(s)
    assert not list(s.archive.root.rglob("*.json"))


def test_request_drift_during_selection_refuses_archive(prepared, monkeypatch):
    s = prepared; original = subject.select_search_parents
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        (s.root / "selection-request.json").write_text("{}")
        return result
    monkeypatch.setattr(subject, "select_search_parents", mutate)
    with pytest.raises(PolicyError): run(s)
    assert not list(s.archive.root.rglob("*.json"))


def test_only_target_cohort_measurements_enter_frontier(prepared):
    result = run(prepared)
    ids = {r["candidate_id"] for r in result["measurements"]}
    assert ids == {"seed", "candidate-0", "candidate-1", "candidate-2"}
    assert result["duplicate_bundle_replicates"][0]["candidate_id"] == "seed-aa"
    assert "private_families" not in result
    assert result["source_registration"] == prepared.pin



def test_same_roster_and_session_do_not_merge_distinct_evaluation_cohorts(prepared):
    s = prepared; first = run(s)
    s.request["cohort_id"] = "cohort-1"
    s.request["usage_counts"] = {content_hash(cid): 0 for cid in ["seed", "candidate-3", "candidate-4"]}
    second = run(s)
    assert first["selection"]["cohort_id"] == second["selection"]["cohort_id"]
    assert first["selection"]["measurement_id"] != second["selection"]["measurement_id"]
    # Repeated identical inputs and a shared server are not one evaluation batch.
    mixed = [first["measurements"][1], second["measurements"][1]]
    with pytest.raises(PolicyError, match="one measured cohort"):
        subject.select_search_parents(mixed, profile=profile(), selection_config=config(),
            usage_counts={r["bundle_id"]: 0 for r in mixed})
