"""Configured proposal plans preserve qualified parent custody without admission."""
import json
import hashlib
import pytest
from test_abstract_population_sources import setup, pin
from test_qualified_parent_selection import prepared, run as select
from test_experiment_population_config import config as population_config
from speech_aware_evidence_acquisition.rails import system_search_parent_selection as subject
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


def external_pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def proposed(prepared):
    s = prepared
    s.selected = select(s)
    s.selection_path = next((s.archive.root / "context-learning/qualified-parent-selection").glob("*.json"))
    s.proposal = {"schema": "saea-qualified-parent-proposal-config-v1", "status": "ROOT_REGISTERED",
        "experiment_population": pin(s.root, "target-population.json", population_config((2,), n=3)),
        "selection_record": external_pin(s.selection_path),
        "modes": {"candidate-0": "local", "candidate-1": "explore"}}
    return s


def run(s):
    return subject.prepare_qualified_parent_proposal_plan(s.archive,
        configuration_pin=pin(s.root, "proposal-config.json", s.proposal),
        repo_root=s.root, data_root=s.data)


def plans(s):
    return list((s.archive.root / "context-learning/qualified-parent-proposals").glob("*.json"))


def test_config_to_source_qualified_plan_roundtrip(proposed):
    s = proposed; result = run(s)
    assert result["selection_record"] == s.proposal["selection_record"]
    assert result["experiment_population"] == s.proposal["experiment_population"]
    assert result["plan"]["population_budget"]["candidate_trajectories"] == 6
    assert result["plan"]["slots"][0]["parent_bundle_ids"] == s.selected["selection"]["frontier_parent_ids"]
    assert result["plan"]["slots"][1]["parent_bundle_ids"] == s.selected["selection"]["exploration_parent_ids"]
    assert result["proposal_allocation_granted"] is False
    assert result["runtime_admission"] is False and result["learner_exported"] is False
    assert len(plans(s)) == 1
    before = plans(s)[0].read_bytes()
    with pytest.raises(PolicyError): run(s)
    assert plans(s)[0].read_bytes() == before


@pytest.mark.parametrize("fault", ["changed_selection", "changed_request", "missing_read", "open_attempt",
                                  "wrong_schema", "draft", "missing_slot", "target_drift", "foreign_record", "copied_record", "record_schema", "record_digest"])
def test_invalid_source_or_configuration_never_writes_plan(proposed, fault):
    s = proposed
    if fault == "changed_selection":
        value = json.loads(s.selection_path.read_text())
        value["selection"]["frontier_parent_ids"] = ["f" * 64]
        value["record_sha256"] = content_hash({k: v for k, v in value.items() if k != "record_sha256"})
        s.selection_path.write_text(json.dumps(value)); s.proposal["selection_record"] = external_pin(s.selection_path)
    elif fault == "changed_request": (s.root / "selection-request.json").write_text("{}")
    elif fault == "missing_read": s.authorities.pop("cohort-1")
    elif fault == "open_attempt": next((s.data / "attempts/cohort-1-seed").glob("*.json")).write_text('{"state":"OPENED"}')
    elif fault == "wrong_schema": s.proposal["schema"] = "unregistered"
    elif fault == "draft": s.proposal["status"] = "DRAFT"
    elif fault == "missing_slot": s.proposal["modes"].pop("candidate-1")
    elif fault == "target_drift": (s.root / "target-population.json").write_text("{}")
    elif fault in {"record_schema", "record_digest"}:
        value = json.loads(s.selection_path.read_text())
        value["schema" if fault == "record_schema" else "record_sha256"] = "invalid"
        s.selection_path.write_text(json.dumps(value)); s.proposal["selection_record"] = external_pin(s.selection_path)
    else:
        path = (s.data if fault == "copied_record" else s.root) / "foreign.json"; path.write_bytes(s.selection_path.read_bytes())
        s.proposal["selection_record"] = external_pin(path)
    with pytest.raises((PolicyError, KeyError)): run(s)
    assert not plans(s)


@pytest.mark.parametrize("target", ["configuration", "selection", "population"])
def test_mutation_during_planning_refuses_archive(proposed, monkeypatch, target):
    s = proposed; original = subject.plan_parent_proposals
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        path = {"configuration": s.root / "proposal-config.json", "selection": s.selection_path,
                "population": s.root / "target-population.json"}[target]
        path.write_text("{}")
        return result
    monkeypatch.setattr(subject, "plan_parent_proposals", mutate)
    with pytest.raises(PolicyError): run(s)
    assert not plans(s)


def test_source_authority_change_after_parent_recheck_refuses_plan(proposed, monkeypatch):
    s = proposed; original = subject.plan_parent_proposals
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        s.authorities.pop("cohort-1")
        return result
    monkeypatch.setattr(subject, "plan_parent_proposals", mutate)
    with pytest.raises((PolicyError, KeyError)): run(s)
    assert not plans(s)
