"""Materialize complete population source pins without reading task quality."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from test_abstract_population_sources import setup, pin
from speech_aware_evidence_acquisition.analysis import abstract_population_registration as subject
from speech_aware_evidence_acquisition.analysis import abstract_population_sources as sources
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError


@pytest.fixture
def planned(setup):
    s = setup
    families = []
    for f in s.manifest["families"]:
        backend = pin(s.data, f["cohort_id"] + "-backend.json", {}, True)
        families.append({
            "cohort_id": f["cohort_id"], "recipe": f["recipe"],
            "read_id": s.authorities[f["cohort_id"]]["read_run_id"],
            "frozen_check": f["frozen_check"],
            "expected_saved_family": f["saved_family"]["path"],
            "expected_source_specifications": backend["path"],
        })
    s.plan = {"schema": "saea-abstract-population-source-plan-v1",
              "status": "ROOT_PLAN_REGISTERED_NOT_EXPORTED", "at_utc": "2026-10-05T00:00:00Z",
              "scope": "Projection only", "projection_config": s.manifest["projection_config"],
              "families": families, "runtime_admission": False,
              "source_complete_required": True, "policy_update_before_all_sources_complete": False}
    s.plan_pin = pin(s.root, "plan.json", s.plan)
    return s


def run(s):
    return subject.prepare_population_source_registration(
        plan_pin=s.plan_pin, repo_root=s.root, data_root=s.data)


def test_complete_registration_preparation_reads_no_quality_and_writes_nothing(planned):
    s = planned
    before = sorted(str(p) for p in s.root.rglob("*"))
    out = run(s)
    assert out["source_registration"] == s.manifest
    assert set(out["source_specifications"]) == {c["cohort_id"] for c in s.cfg["cohorts"]}
    assert out["learner_exported"] is False and out["runtime_admission"] is False
    assert out["model_contacts"] == out["scorer_contacts"] == 0
    assert sorted(str(p) for p in s.root.rglob("*")) == before
    assert not any(x[0] == "quality" for x in s.calls)
    assert sum(x[0] == "qualify" for x in s.calls) == len(s.cfg["cohorts"])


@pytest.mark.parametrize("fault", ["missing_saved", "missing_backend", "escape", "missing_cohort",
    "wrong_order", "wrong_read", "unsigned", "opened", "wrong_roster", "runtime", "early_update",
    "draft", "changed_frozen", "extra_field"])
def test_incomplete_or_ambiguous_plan_refuses_without_quality(planned, fault):
    s = planned; last = s.plan["families"][-1]; cid = last["cohort_id"]
    if fault.startswith("missing_") and fault != "missing_cohort":
        key = "expected_saved_family" if fault == "missing_saved" else "expected_source_specifications"
        from pathlib import Path
        Path(last[key]).unlink()
    elif fault == "escape": last["expected_saved_family"] = str(s.root / "outside.json")
    elif fault == "missing_cohort": s.plan["families"].pop()
    elif fault == "wrong_order": s.plan["families"].reverse()
    elif fault == "wrong_read": last["read_id"] = "another-READ"
    elif fault == "unsigned": s.authorities.pop(cid)
    elif fault == "opened":
        next((s.data / "attempts" / (cid + "-seed")).glob("*.json")).write_text('{"state":"OPENED"}')
    elif fault == "wrong_roster":
        rp = s.root / last["recipe"]["relpath"]; doc = json.loads(rp.read_text())
        doc["sample_ids"].reverse(); last["recipe"] = pin(s.root, rp.name, doc)
    elif fault == "runtime": s.plan["runtime_admission"] = True
    elif fault == "early_update": s.plan["policy_update_before_all_sources_complete"] = True
    elif fault == "draft": s.plan["status"] = "DRAFT"
    elif fault == "changed_frozen": (s.data / (cid + "-frozen.json")).write_text("{}")
    else: last["unknown"] = True
    s.plan_pin = pin(s.root, "plan.json", s.plan)
    with pytest.raises((PolicyError, KeyError, FileNotFoundError)):
        run(s)
    assert not any(x[0] == "quality" for x in s.calls)
    assert not any(x[0] == "qualify" for x in s.calls)


@pytest.mark.parametrize("fault", ["wait", "source_change", "authority_change", "metadata_change", "plan_change"])
def test_change_during_qualification_never_returns_registration(planned, monkeypatch, fault):
    s = planned; original = sources._reader(s.root)
    job = pin(s.data, "job.json", {"status": "succeeded"}, True)
    def qualify(**kwargs):
        q = original.qualify_registered_context_family(**kwargs)
        q["job_metadata_pins"] = [job]
        if kwargs["frozen_check"]["commit"] == s.cfg["cohorts"][-1]["cohort_id"]:
            if fault == "wait": q["status"] = "WAIT"
            elif fault == "source_change":
                (s.data / (s.cfg["cohorts"][0]["cohort_id"] + "-backend.json")).write_text('{"changed":true}')
            elif fault == "authority_change":
                s.authorities[s.cfg["cohorts"][0]["cohort_id"]]["ledger_row_sha256"] = "changed"
            elif fault == "plan_change": (s.root / "plan.json").write_text("{}")
            else: (s.data / "job.json").write_text('{"status":"failed"}')
        return q
    monkeypatch.setattr(sources, "_reader", lambda root: SimpleNamespace(
        CLI=original.CLI, qualify_registered_context_family=qualify))
    with pytest.raises(PolicyError):
        run(s)
    assert not any(x[0] == "quality" for x in s.calls)

