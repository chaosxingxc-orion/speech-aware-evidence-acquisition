"""Natural four-row admission metadata, using only synthetic capacity evidence."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_context_structural_entry import (
    qualify_architecture_capacity_family,
)
from test_architecture_capacity_family import example

ROOT = Path(__file__).resolve().parents[2]
LABELS = ("seed", "seed-aa", "review-off", "solver-lookup")


def write(root, rel, document):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(document, sort_keys=True).encode()
    path.write_bytes(raw)
    return {"relpath": rel, "sha256": hashlib.sha256(raw).hexdigest()}


def prepared(label, kind):
    stem = f"slurp-native-stage3-simple-consumption-{label}-engineering-{kind}-v2"
    (cell,) = load_campaign_cells(ROOT, stem)
    c = cell.document
    return c, compose(
        ROOT, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], stem
    )


def fixture(tmp_path, label="solver-lookup"):
    args = example()
    rel = "configs/experiments/slurp-simple-consumption-architecture-n20-v2.json"
    raw = (ROOT / rel).read_bytes()
    population = json.loads(raw)
    pin = {"relpath": rel, "sha256": hashlib.sha256(raw).hexdigest()}
    args.update(population=population, population_pin=pin)
    reg = args["registration"]
    reg.update(experiment_population=pin, new_receipt_root=str(tmp_path / "capacity"))
    for member, identity in zip(
        reg["members"], population["architecture"]["members"], strict=True
    ):
        name = member["label"]
        _, graph = prepared(name, "graph")
        member.update(
            execution_config=identity["execution_config"],
            execution_identity_sha256=content_hash(identity),
            experiment_population=pin,
            graph=f"slurp-native-stage3-simple-consumption-{name}-engineering-graph-v2",
            graph_config_hash=graph.config_hash,
        )
        args["graph_config_hashes"][name] = graph.config_hash
        args["receipts"][name]["inputs"]["graph_config_hash"] = graph.config_hash
        args["policy_config_bytes"][name] = (
            ROOT / identity["execution_config"]["relpath"]
        ).read_bytes()
    source = args["source_check"]
    source.update(experiment_population=pin, passed=True, commit=reg["worker_commit"])
    source_pin = write(tmp_path, "capacity/frozen-check.json", source)
    reg["source_check_sha256"] = content_hash(source)
    reg["frozen_preflight_receipts"] = [
        {"path": str(tmp_path / source_pin["relpath"]), "sha256": source_pin["sha256"]}
    ]
    args["original_registration"] = deepcopy(reg)
    documents = {
        "registration-v1.json": reg,
        "capacity-finished.json": args["finished"],
        "capacity-task-exit.json": args["windows_exit"],
        "frozen-check.json": source,
    }
    for name in LABELS:
        documents[f"{name}/request-fit-v1.json"] = args["receipts"][name]
        documents[f"{name}-capacity-finished.json"] = args["member_terminals"][name]
    evidence = []
    for name, document in documents.items():
        p = write(tmp_path, "capacity/" + name, document)
        evidence.append({"path": str(tmp_path / p["relpath"]), "sha256": p["sha256"]})
    qualified = {
        "schema": "saea-simple-consumption-capacity-root-qualification-v1",
        "runtime_admission": False,
        "result": qualify_architecture_capacity_family(**args),
        "evidence": evidence,
    }
    prerequisite = {
        "registration": write(tmp_path, "capacity/registration-v1.json", reg),
        "qualification": write(
            tmp_path, "capacity/capacity-qualified-v1.json", qualified
        ),
    }
    cell, config = prepared(label, "smoke-4")
    values = deepcopy(config.values)
    base = json.loads(
        (
            ROOT
            / "docs/readiness/2026-10-07-slurp-simple-consumption-engineering-v2"
            / f"{label}-structural-bases-v2.json"
        ).read_bytes()
    )[1]
    plans = []
    for role in ("generation", "fit"):
        execution = deepcopy(base["execution_plan"])
        if role == "fit":
            spec = values["native_contact_fit"]
            execution.update(
                run_id=spec["run_id"],
                attempt_id=spec["attempt_id"],
                planned_model_calls=spec["contact_cap"],
            )
        plans.append(
            {
                "schema": f"saea-registered-{role}-plan-v1",
                "plan_role": role,
                "architecture_proof": "natural-four-row-v1",
                "status": "ROOT COUNTERSIGNED BEFORE CONTACT",
                "cell": cell["cell_id"],
                "experiment": base["experiment"],
                "composed_config_hash": config.config_hash,
                "experiment_population": deepcopy(pin),
                "population_cohort": "comparison",
                "architecture_member": label,
                "sample_ids": deepcopy(values["populations"][0]["ids"]),
                "execution_plan": execution,
                "policy_binding": deepcopy(cell["system_text_policy_binding"]),
                "prepared_phase_supply": deepcopy(values["prepared_phase_supply"]),
                "official_score_jobs": 0,
                "scientific_feedback": False,
                "learner_export": False,
                "capacity_prerequisite": deepcopy(prerequisite),
            }
        )
    return dict(
        values=values,
        cell=deepcopy(cell),
        registered_plans=plans,
        repo_root=ROOT,
        data_root=tmp_path,
    )


def invoke(args):
    from speech_aware_evidence_acquisition.rails.architecture_natural_registration import (
        require_architecture_natural_registration,
    )

    return require_architecture_natural_registration(**args)


@pytest.mark.parametrize(
    "label,generation,fit",
    [
        ("seed", 52, 208),
        ("seed-aa", 52, 208),
        ("review-off", 8, 32),
        ("solver-lookup", 12, 48),
    ],
)
def test_complete_original_capacity_binds_both_natural_plans(
    tmp_path, label, generation, fit
):
    args = fixture(tmp_path, label)
    before = deepcopy(args)
    result = invoke(args)
    assert (
        result["member_id"] == label
        and result["generation_cap"] == generation
        and result["fit_cap"] == fit
    )
    assert result["runtime_admission"] is False and result["read_authorized"] is False
    assert args == before


@pytest.mark.parametrize(
    "fault",
    [
        "missing_fit",
        "duplicate_plan",
        "unmarked_fit",
        "wrong_schema",
        "unsigned",
        "foreign_cell",
        "foreign_run",
        "foreign_attempt",
        "wrong_fit_cap",
        "wrong_generation_cap",
        "bool_cap",
        "wrong_profile",
        "foreign_member",
        "changed_roles",
        "changed_policy",
        "foreign_bundle",
        "changed_sampling",
        "missing_stage",
        "score_stage",
        "wrong_rows",
        "reordered_roster",
        "foreign_roster",
        "missing_supply",
        "changed_supply",
        "score_jobs",
        "feedback",
        "learner",
        "learning",
        "wrong_config",
        "missing_prerequisite",
        "different_prerequisite",
        "missing_data_root",
        "wrong_split",
        "wrong_protocol",
        "fit_generation_identity",
        "extra_trajectory",
        "family_cap",
        "geometry",
    ],
)
def test_refuse_malformed_crossbound_or_overbroad_natural_registration(tmp_path, fault):
    a = fixture(tmp_path)
    v, c, plans = a["values"], a["cell"], a["registered_plans"]
    g, f = plans
    if fault == "missing_fit":
        plans.pop()
    elif fault == "duplicate_plan":
        plans.append(deepcopy(g))
    elif fault == "unmarked_fit":
        f.pop("architecture_proof")
    elif fault == "wrong_schema":
        g["schema"] = "foreign"
    elif fault == "unsigned":
        g["status"] = "DRAFT"
    elif fault == "foreign_cell":
        g["cell"] = "foreign"
    elif fault == "foreign_run":
        g["execution_plan"]["run_id"] = "foreign"
    elif fault == "foreign_attempt":
        f["execution_plan"]["attempt_id"] = "foreign"
    elif fault == "wrong_fit_cap":
        f["execution_plan"]["planned_model_calls"] -= 1
    elif fault == "wrong_generation_cap":
        g["execution_plan"]["planned_model_calls"] += 1
    elif fault == "bool_cap":
        f["execution_plan"]["planned_model_calls"] = True
    elif fault == "wrong_profile":
        v["native_graph_capacity_profile"] = "legacy-four-path-v1"
    elif fault == "foreign_member":
        v["architecture_member"] = "seed"
    elif fault == "changed_roles":
        v["native_episode"]["roles"]["reviewer"]["max_iterations"] = 1
    elif fault == "changed_policy":
        v["phase_tools"]["solver"]["max_calls_per_sample"] = 2
    elif fault == "foreign_bundle":
        g["policy_binding"]["bundle_id"] = "b" * 64
    elif fault == "changed_sampling":
        v["decoding_params"]["temperature"] = 1
    elif fault == "missing_stage":
        c.pop("allowed_execution_stages")
    elif fault == "score_stage":
        c["allowed_execution_stages"].append("score")
    elif fault == "wrong_rows":
        v["population"]["count"] = 20
    elif fault == "reordered_roster":
        v["populations"][0]["ids"].reverse()
    elif fault == "foreign_roster":
        v["populations"][0]["ids"][0] = "foreign"
    elif fault == "missing_supply":
        g.pop("prepared_phase_supply")
    elif fault == "changed_supply":
        f["prepared_phase_supply"]["sha256"] = "b" * 64
    elif fault == "score_jobs":
        f["official_score_jobs"] = 1
    elif fault == "feedback":
        f["scientific_feedback"] = True
    elif fault == "learner":
        g["learner_export"] = True
    elif fault == "learning":
        v["system_context_learning"] = {}
    elif fault == "wrong_config":
        g["composed_config_hash"] = "b" * 64
    elif fault == "missing_prerequisite":
        g.pop("capacity_prerequisite")
    elif fault == "different_prerequisite":
        f["capacity_prerequisite"]["registration"]["sha256"] = "b" * 64
    elif fault == "missing_data_root":
        a["data_root"] = None
    elif fault == "wrong_split":
        f["execution_plan"]["split_identity_hash"] = "b" * 64
    elif fault == "wrong_protocol":
        f["execution_plan"]["protocol_hash"] = "b" * 64
    elif fault == "fit_generation_identity":
        v["native_contact_fit"]["run_id"] = c["run_id"]
    elif fault == "extra_trajectory":
        v["family_budget"]["complete_system_trajectories"] = 20
    elif fault == "family_cap":
        v["family_budget"]["actual_request_fit_endpoint_cap"] = 49
    else:
        v["system_search_measurement"]["slot_count"] = 2
    with pytest.raises((ValueError, KeyError, TypeError)):
        invoke(a)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_member",
        "wrong_worker",
        "failed_exit",
        "failed_lease",
        "changed_source",
        "wrong_graph",
        "wrong_result",
        "typed_result",
        "missing_evidence",
        "duplicate_evidence",
        "foreign_evidence",
        "qualification_schema",
        "qualification_admission",
        "changed_bytes",
        "wrong_pin",
        "missing_file",
    ],
)
def test_capacity_prerequisite_reverifies_original_source_evidence(tmp_path, fault):
    args = fixture(tmp_path)
    qpath = tmp_path / "capacity/capacity-qualified-v1.json"
    q = json.loads(qpath.read_bytes())
    name = "seed/request-fit-v1.json"
    path = tmp_path / "capacity" / name
    if fault == "wrong_result":
        q["result"]["tokenizer_endpoints"] += 1
    elif fault == "typed_result":
        q["result"]["generation_contacts"] = False
    elif fault == "missing_evidence":
        q["evidence"].pop()
    elif fault == "duplicate_evidence":
        q["evidence"].append(deepcopy(q["evidence"][0]))
    elif fault == "foreign_evidence":
        q["evidence"][0]["path"] = str(tmp_path.parent / "foreign.json")
    elif fault == "qualification_schema":
        q["schema"] = "partial"
    elif fault == "qualification_admission":
        q["runtime_admission"] = True
    elif fault == "changed_bytes":
        path.write_text("{}")
    elif fault == "wrong_pin":
        args["registered_plans"][0]["capacity_prerequisite"]["qualification"][
            "sha256"
        ] = "b" * 64
    elif fault == "missing_file":
        path.unlink()
    else:
        if fault == "missing_member":
            name = "registration-v1.json"
        elif fault == "failed_exit":
            name = "capacity-task-exit.json"
        elif fault == "failed_lease":
            name = "seed-capacity-finished.json"
        elif fault == "changed_source":
            name = "frozen-check.json"
        path = tmp_path / "capacity" / name
        d = json.loads(path.read_bytes())
        if fault == "missing_member":
            d["members"].pop()
        elif fault == "failed_exit":
            d["exit_code"] = 1
        elif fault == "failed_lease":
            d["members"][0]["lease_exit_code"] = 1
        elif fault == "changed_source":
            d["source_commit"] = "b" * 40
        elif fault == "wrong_worker":
            d["inputs"]["source_commit"] = "b" * 40
        else:
            d["inputs"]["graph_config_hash"] = "b" * 64
        p = write(tmp_path, "capacity/" + name, d)
        for pin in q["evidence"]:
            if pin["path"] == str(path):
                pin["sha256"] = p["sha256"]
        if fault == "missing_member":
            for plan in args["registered_plans"]:
                plan["capacity_prerequisite"]["registration"] = p
    new_pin = write(tmp_path, "capacity/capacity-qualified-v1.json", q)
    if fault != "wrong_pin":
        for plan in args["registered_plans"]:
            plan["capacity_prerequisite"]["qualification"] = new_pin
    with pytest.raises((ValueError, KeyError, TypeError, OSError)):
        invoke(args)


@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("complete", [True, False])
def test_shared_gate_requires_the_natural_generation_fit_pair(
    tmp_path, monkeypatch, label, complete
):
    from test_flight_registration_check import gate

    args = fixture(tmp_path, label)
    cell, values = args["cell"], args["values"]
    directory = tmp_path / "packages" / "natural"
    monkeypatch.setattr(gate, "READINESS", directory.parent)
    for plan in args["registered_plans"][: 2 if complete else 1]:
        write(directory, plan["plan_role"] + "-plan-registered-v1.json", plan)
    report = gate.CellReport(
        experiment=cell["cell_id"],
        cell_id=cell["cell_id"],
        run_id=cell["run_id"],
        state="held",
        named=True,
    )
    report.run_ids = {
        "generation": cell["run_id"],
        "native_contact_fit": values["native_contact_fit"]["run_id"],
    }
    baseline = json.loads(
        (ROOT / "configs/baseline" / (cell["baseline_fragment"] + ".json")).read_bytes()
    )
    fragment = json.loads(
        (ROOT / "configs/experiment" / (cell["cell_id"] + ".json")).read_bytes()
    )
    gate._check_registered_supply_binding(
        report,
        baseline,
        gate.PackageIndex(ROOT),
        "natural",
        {},
        cell=cell,
        fragment=fragment,
        data_root=tmp_path,
    )
    assert bool(report.findings) is not complete
    if not complete:
        assert any(f.kind == "population-config-binding" for f in report.findings)


def test_plan_pair_order_is_not_a_generation_order_override(tmp_path):
    args = fixture(tmp_path)
    args["registered_plans"].reverse()
    assert invoke(args)["member_id"] == "solver-lookup"


@pytest.mark.parametrize("field", ["run_id", "attempt_id"])
def test_optional_top_level_identity_cannot_disagree_with_execution_plan(
    tmp_path, field
):
    args = fixture(tmp_path)
    args["registered_plans"][0][field] = "foreign"
    with pytest.raises(ValueError):
        invoke(args)


@pytest.mark.parametrize("fault", ["hash", "roster"])
def test_other_capacity_member_graph_is_independently_bound(
    tmp_path, monkeypatch, fault
):
    from speech_aware_evidence_acquisition.rails import (
        architecture_natural_registration as binding,
    )

    args = fixture(tmp_path, "solver-lookup")
    original = binding.compose

    def changed(*parts):
        config = original(*parts)
        if (
            parts[-1]
            == "slurp-native-stage3-simple-consumption-seed-engineering-graph-v2"
        ):
            if fault == "hash":
                return replace(config, config_hash="b" * 64)
            values = deepcopy(config.values)
            values["populations"][0]["ids"].reverse()
            return replace(config, values=values)
        return config

    monkeypatch.setattr(binding, "compose", changed)
    with pytest.raises(ValueError):
        invoke(args)
