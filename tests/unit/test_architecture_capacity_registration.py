"""Register manual capacity metadata without authorizing generation or contacts."""

from copy import deepcopy
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.rails.experiment_population import (
    require_architecture_capacity_registration,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_system_context_learning import pin

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "docs/readiness/2026-10-07-slurp-simple-consumption-capacity-entry-v2"


def actual(label):
    plan = json.loads(
        (PACKAGE / (label + "-capacity-fit-plan-registered-v1.json")).read_bytes()
    )
    (cell,) = load_campaign_cells(REPO, plan["experiment"])
    d = cell.document
    config = compose(
        REPO,
        d["model_fragment"],
        d["dataset_fragment"],
        d["baseline_fragment"],
        plan["experiment"],
    )
    return deepcopy(config.values), deepcopy(d), plan


@pytest.mark.parametrize(
    "label,cap,contacts,profile",
    [
        ("seed", 299, 13, "legacy-four-path-v1"),
        ("seed-aa", 299, 13, "legacy-four-path-v1"),
        ("review-off", 157, 2, "review-off-v1"),
        ("solver-lookup", 241, 3, "review-off-v1"),
    ],
)
def test_exact_pinned_registered_capacity(label, cap, contacts, profile):
    values, cell, plan = actual(label)
    before = deepcopy((values, cell, plan))
    result = require_architecture_capacity_registration(
        values, cell, plan, repo_root=REPO
    )
    assert result["contact_cap"] == cap and result["model_per_trajectory"] == contacts
    assert result["member_id"] == label and result["rehearsal_profile"] == profile
    assert result["runtime_admission"] is False
    assert (values, cell, plan) == before


@pytest.mark.parametrize(
    "fault",
    [
        "missing_member",
        "foreign_member",
        "missing_profile",
        "wrong_profile",
        "learning",
        "semantic_proposals",
        "generation_budget",
        "score_budget",
        "trajectory_budget",
        "bad_cap",
        "bool_cap",
        "worker_stage",
        "missing_stage",
        "policy_change",
        "missing_roles",
        "changed_sampling",
        "foreign_run",
        "foreign_attempt",
        "foreign_cell",
        "foreign_bundle",
        "foreign_plan_pin",
        "foreign_plan_hash",
        "wrong_plan_cap",
        "bool_plan_cap",
        "score_jobs",
        "feedback",
        "missing_plan",
        "foreign_plan_schema",
        "unregistered_plan",
    ],
)
def test_fail_closed_manual_capacity(fault):
    values, cell, plan = actual("solver-lookup")
    if fault == "missing_member":
        values.pop("architecture_member")
    elif fault == "foreign_member":
        values["architecture_member"] = "foreign"
    elif fault == "missing_profile":
        values.pop("native_graph_capacity_profile")
    elif fault == "wrong_profile":
        values["native_graph_capacity_profile"] = "legacy-four-path-v1"
    elif fault == "learning":
        values["system_context_learning"] = {"enabled": True}
    elif fault == "semantic_proposals":
        values["system_search_learning"] = {}
    elif fault == "generation_budget":
        values["family_budget"]["generation_calls_cap"] = 1
    elif fault == "score_budget":
        values["family_budget"]["official_complete_scoring_jobs"] = 1
    elif fault == "trajectory_budget":
        values["family_budget"]["complete_system_trajectories"] = 1
    elif fault == "bad_cap":
        values["family_budget"]["tokenizer_endpoint_cap"] = 1
    elif fault == "bool_cap":
        values["family_budget"]["tokenizer_endpoint_cap"] = True
    elif fault == "worker_stage":
        cell["allowed_execution_stages"].append("worker")
    elif fault == "missing_stage":
        cell.pop("allowed_execution_stages")
    elif fault == "policy_change":
        values["native_episode"]["roles"]["solver"]["max_iterations"] = 3
    elif fault == "missing_roles":
        values["native_episode"].pop("roles")
    elif fault == "changed_sampling":
        values["decoding_params"]["temperature"] = 1
    elif fault == "foreign_run":
        plan["execution_plan"]["run_id"] = "foreign"
    elif fault == "foreign_attempt":
        plan["execution_plan"]["attempt_id"] = "foreign"
    elif fault == "foreign_cell":
        plan["cell"] = "foreign"
    elif fault == "foreign_bundle":
        plan["policy_binding"]["bundle_id"] = "b" * 64
    elif fault == "foreign_plan_pin":
        plan["experiment_population"]["sha256"] = "b" * 64
    elif fault == "foreign_plan_hash":
        plan["composed_config_hash"] = "b" * 64
    elif fault == "wrong_plan_cap":
        plan["execution_plan"]["planned_model_calls"] = 1
    elif fault == "bool_plan_cap":
        plan["execution_plan"]["planned_model_calls"] = True
    elif fault == "score_jobs":
        plan["official_score_jobs"] = 1
    elif fault == "feedback":
        plan["scientific_feedback"] = True
    elif fault == "missing_plan":
        plan = None
    elif fault == "foreign_plan_schema":
        plan["schema"] = "learning"
    else:
        plan.pop("status")
    with pytest.raises((PolicyError, KeyError, TypeError, ValueError)):
        require_architecture_capacity_registration(values, cell, plan, repo_root=REPO)


@pytest.mark.parametrize("label", ["seed", "seed-aa", "review-off", "solver-lookup"])
def test_shared_registration_gate_accepts_only_exact_manual_capacity(label):
    from test_flight_registration_check import gate

    values, cell, plan = actual(label)
    report = gate.CellReport(
        experiment=plan["experiment"],
        cell_id=cell["cell_id"],
        run_id=cell["run_id"],
        state="ready",
        named=True,
    )
    report.run_ids = {"generation": cell["run_id"]}
    index = gate.PackageIndex(REPO)
    package = PACKAGE.relative_to(REPO / gate.READINESS).as_posix()
    fragment = json.loads(
        (REPO / "configs/experiment" / (plan["experiment"] + ".json")).read_bytes()
    )
    baseline = json.loads(
        (REPO / "configs/baseline" / (cell["baseline_fragment"] + ".json")).read_bytes()
    )
    gate._check_registered_supply_binding(
        report, baseline, index, package, {}, cell=cell, fragment=fragment
    )
    assert not report.findings
    cell["allowed_execution_stages"].append("worker")
    gate._check_registered_supply_binding(
        report, baseline, index, package, {}, cell=cell, fragment=fragment
    )
    assert any(f.kind == "population-config-binding" for f in report.findings)


@pytest.mark.parametrize(
    "fault", ["roles", "contacts", "changed_policy_bytes", "learning_population"]
)
def test_pinned_population_role_and_contact_identity(tmp_path, fault):
    values, cell, plan = actual("seed")
    population = json.loads(
        (REPO / values["experiment_population"]["relpath"]).read_bytes()
    )
    for member in population["architecture"]["members"]:
        source = REPO / member["execution_config"]["relpath"]
        target = tmp_path / member["execution_config"]["relpath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    member = population["architecture"]["members"][0]
    if fault == "roles":
        member["active_roles"] = ["perception", "solver"]
    elif fault == "contacts":
        member["model_per_trajectory"] = 12
    elif fault == "changed_policy_bytes":
        (tmp_path / member["execution_config"]["relpath"]).write_text("{}")
    else:
        population["proposer"] = {"model": "foreign", "semantic_batches": 1}
    values["experiment_population"] = pin(tmp_path, "population.json", population)
    plan["experiment_population"] = deepcopy(values["experiment_population"])
    plan["composed_config_hash"] = content_hash(values)
    with pytest.raises((PolicyError, ValueError)):
        require_architecture_capacity_registration(
            values, cell, plan, repo_root=tmp_path
        )
