"""Local node preparation proofs use source-only fixtures and no service contacts."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.local_node_panel import (
    SELECTOR, SOURCE_RECEIPT, SOURCE_POPULATION, require_local_role_policy,
    require_local_node_basis, require_local_identities, local_node_documents,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.experiment_population import population_accounting
from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
from speech_aware_evidence_acquisition.rails.architecture_audio_budget import derive_manual_architecture_audio_budget

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("local_prepare", ROOT / "scripts/preparation/prepare_manual_audio_recovery.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)
RECEIPT = json.loads((ROOT / SOURCE_RECEIPT["relpath"]).read_bytes())
POLICY = json.loads((ROOT / RECEIPT["source_policy"]["relpath"]).read_bytes())
BASIS = {"schema": "saea-local-node-panel-basis-v1", "target_role": "solver",
         "proposal_custody": {"registration": {"relpath": "registration.json", "sha256": "a" * 64},
                             "validation": {"relpath": "validation.json", "sha256": "b" * 64}},
         "source_preparation_receipt": SOURCE_RECEIPT, "source_population": SOURCE_POPULATION}


def local_population(k=2):
    value = json.loads((ROOT / SOURCE_POPULATION["relpath"]).read_bytes())
    cohort = value["cohorts"][0]
    cohort["control_ids"] = ["control", "control-aa"]
    cohort["candidate_ids"] = [f"candidate-{i}" for i in range(k)]
    member = next(m for m in value["architecture"]["members"] if m["member_id"] == "review-off")
    value["architecture"]["members"] = [dict(deepcopy(member), member_id=label)
        for label in cohort["control_ids"] + cohort["candidate_ids"]]
    value["contact_limits"]["model_per_trajectory"] = member["model_per_trajectory"]
    return value


def text_fixture(tmp_path):
    source = deepcopy(POLICY)
    params = next(c["params"] for c in source["native_episode"]["consumption_module"]["components"]
                  if c["component_id"] == "knowledge-consumption-opportunity")
    for role in ("perception", "solver", "reviewer", "planner"):
        raw = (ROOT / "configs" / source["phase_material"][role]["instruction_template"]).read_bytes()
        relative = f"probes/{role}.txt"
        path = tmp_path / "configs" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        source["phase_material"][role]["instruction_template"] = relative
        params[role + "_template"] = relative
    return source


def candidate_policy(tmp_path, source):
    candidate = deepcopy(source)
    params = next(c["params"] for c in candidate["native_episode"]["consumption_module"]["components"]
                  if c["component_id"] == "knowledge-consumption-opportunity")
    for role in ("perception", "solver", "reviewer", "planner"):
        old = tmp_path / "configs" / source["phase_material"][role]["instruction_template"]
        relative = f"probes/relocated-{role}.txt"
        (tmp_path / "configs" / relative).write_bytes(old.read_bytes() + (b"\nSynthetic Solver instruction." if role == "solver" else b""))
        candidate["phase_material"][role]["instruction_template"] = relative
        params[role + "_template"] = relative
    return candidate


def test_only_solver_bytes_may_change_even_when_all_bundle_paths_move(tmp_path):
    source = text_fixture(tmp_path)
    candidate = candidate_policy(tmp_path, source)
    before = deepcopy((source, candidate))
    assert require_local_role_policy(source, candidate, repo_root=tmp_path, target_role="solver")["target_text_changed"]
    assert (source, candidate) == before
    with pytest.raises(PolicyError, match="control/A/A"):
        require_local_role_policy(source, candidate, repo_root=tmp_path, target_role="solver", control=True)


@pytest.mark.parametrize("fault", ["knowledge", "supply", "tool", "review", "schema", "perception-text"])
def test_non_solver_policy_drift_is_rejected(tmp_path, fault):
    source = text_fixture(tmp_path)
    candidate = candidate_policy(tmp_path, source)
    if fault == "knowledge":
        candidate["knowledge_stores"]["slot-contracts"]["release"]["sha256"] = "b" * 64
    elif fault == "supply":
        candidate["knowledge_stores"]["train-exemplars"]["phase_supply"]["solver"]["k"] += 1
    elif fault == "tool":
        candidate["phase_tools"]["solver"] = {"allowed_tools": ["synthetic-new-tool"]}
    elif fault == "review":
        candidate["native_episode"]["roles"]["reviewer"]["max_iterations"] = 1
    elif fault == "schema":
        candidate["phase_material"]["solver"]["response_format_id"] = "different-schema"
    else:
        (tmp_path / "configs" / candidate["phase_material"]["perception"]["instruction_template"]).write_text("Changed upstream.")
    with pytest.raises(PolicyError, match="non-target"):
        require_local_role_policy(source, candidate, repo_root=tmp_path, target_role="solver")


@pytest.mark.parametrize("k", [2, 3, 4, 5])
def test_members_and_budgets_come_from_configuration(k):
    population = local_population(k)
    assert require_local_node_basis(BASIS, population, repo_root=ROOT) == RECEIPT
    budget = population_accounting(population, "comparison")
    assert budget["K"] == k and budget["N"] == 100
    assert budget["family_trajectories"] == (k + 2) * 100
    assert budget["generation_contacts_cap"] == (k + 2) * 200


@pytest.mark.parametrize("fault", ["roster-order", "roster-size", "sampling", "geometry", "basis-pin", "roles"])
def test_original_basis_and_complete_roster_are_required(fault):
    population, basis = local_population(), deepcopy(BASIS)
    if fault == "roster-order":
        population["cohorts"][0]["sample_ids"].reverse()
    elif fault == "roster-size":
        population["cohorts"][0]["sample_ids"].pop()
    elif fault == "sampling":
        population["sampling"]["seed"] += 1
    elif fault == "geometry":
        population["execution"]["slot_count"] += 1
    elif fault == "basis-pin":
        basis["source_preparation_receipt"]["sha256"] = "b" * 64
    else:
        population["architecture"]["members"][0]["active_roles"] += ["reviewer", "planner"]
    with pytest.raises(PolicyError):
        require_local_node_basis(basis, population, repo_root=ROOT)


def identities():
    return [dict(member_id=label, experiment="local-" + label, cell_id="local-" + label,
                 run_id="LOCAL-" + label, attempt_id="attempt-" + label,
                 fit_run_id="LOCAL-" + label + "-FIT", fit_attempt_id="attempt-" + label + "-fit")
            for label in ("control", "control-aa", "candidate")]


@pytest.mark.parametrize("fault", ["run", "fit", "attempt", "member", "experiment", "source", "escape"])
def test_duplicate_or_spent_identity_is_rejected(fault):
    rows = identities()
    source_cell = {"run_id": "OLD", "attempt_id": "old-attempt"}
    source_fit = {"run_id": "OLD-FIT", "attempt_id": "old-fit"}
    if fault == "source":
        rows[0]["run_id"] = "OLD"
    elif fault == "escape":
        rows[0]["attempt_id"] = "../escaped"
    elif fault == "fit":
        rows[0]["fit_run_id"] = rows[0]["run_id"]
    else:
        key = {"run": "run_id", "attempt": "attempt_id", "member": "member_id", "experiment": "experiment"}[fault]
        rows[1][key] = rows[0][key]
        if fault == "experiment":
            rows[1]["cell_id"] = rows[0]["cell_id"]
    with pytest.raises(PolicyError):
        require_local_identities(rows, source_cell=source_cell, source_fit=source_fit)


def source_configs():
    cell, = load_campaign_cells(ROOT, RECEIPT["experiment"])
    c = cell.document
    ep = json.loads((ROOT / "configs/experiment" / (RECEIPT["experiment"] + ".json")).read_bytes())
    bp = json.loads((ROOT / "configs/baseline" / (c["baseline_fragment"] + ".json")).read_bytes())
    values = compose(ROOT, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], RECEIPT["experiment"]).values
    return ep, bp, values


def test_exact_audio_and_contact_budgets_replace_inherited_caps_without_mutation():
    ep, bp, values = source_configs()
    before = deepcopy((ep, bp))
    report = derive_manual_architecture_audio_budget(values)
    stage = {"N": 100, "population_budget": {"K": 3}, "member_generation_contacts_caps": {"candidate": 200},
             "member_fit_endpoints_caps": {"candidate": 800}}
    identity = identities()[-1]
    new_ep, new_bp = local_node_documents(ep, bp, POLICY, identity, policy_binding=RECEIPT["policy_binding"],
        population_pin=SOURCE_POPULATION, cohort_id="comparison", stage=stage, basis=BASIS, report=report)
    assert (ep, bp) == before
    assert new_ep["execution_plan"]["planned_model_calls"] == 200
    assert new_ep["execution_plan"]["planned_speech_audio_seconds"] == 588
    assert new_bp["native_contact_fit"]["contact_cap"] == 800
    assert new_bp["knowledge_stores"] == bp["knowledge_stores"]
    assert new_ep["populations"] == ep["populations"]
    assert new_ep["cells"][0]["readiness"]["state"] == "held"
    assert "architecture_extent" not in new_bp and "prepared_phase_supply" not in new_bp


@pytest.mark.parametrize("kind", ["capacity", "graph", "natural"])
def test_companion_configs_use_existing_graph4_and_retain_knowledge(kind):
    ep, bp, _ = source_configs()
    row = dict(experiment="local-proof", cell_id="local-proof", run_id="LOCAL-PROOF-FIT-V1",
               attempt_id="local-proof", fit_run_id="LOCAL-ACTUAL-FIT-V1", fit_attempt_id="local-actual-fit")
    graph_name = "slurp-speech-native-simple-consumption-n100-graph4-v1"
    view = json.loads((ROOT / "configs/dataset" / (graph_name + ".json")).read_bytes())
    original = deepcopy((ep, bp))
    pp, pb = prepare.local_companion_documents(ep, bp, row, kind=kind, graph_view=view,
                                               graph_dataset=graph_name, capacity_budget={"contact_cap": 321})
    assert (ep, bp) == original and pb["knowledge_stores"] == bp["knowledge_stores"]
    assert pp["family_budget"]["official_complete_scoring_jobs"] == 0
    if kind == "capacity":
        assert pp["population"]["count"] == 100 and pp["execution_plan"]["planned_model_calls"] == 321
        assert pp["cells"][0]["allowed_execution_stages"] == ["check", "prepare-supply", "prompt-fit"]
    else:
        assert pp["population"]["count"] == 4 and pp["execution_plan"]["planned_model_calls"] == 8
        assert pp["populations"][0]["ids"] == ep["populations"][0]["ids"][:4]
    assert (kind == "natural") == ("native_contact_fit" in pb)


def test_named_selector_is_added_without_removing_historical_selectors():
    from speech_aware_evidence_acquisition.analysis.system_architecture_read import SELECTORS
    assert SELECTORS == ("manual-architecture-n20-v1", "manual-architecture-fixed-roster-v1", SELECTOR, "local-reviewer-panel-v1")


@pytest.mark.parametrize("target_role", ["solver", "reviewer"])
def test_each_role_uses_its_exact_source_topology(target_role):
    from speech_aware_evidence_acquisition.rails.local_node_panel import REVIEWER_SOURCE_RECEIPT
    population, basis = local_population(), deepcopy(BASIS)
    basis["target_role"] = target_role
    if target_role == "reviewer":
        basis["source_preparation_receipt"] = REVIEWER_SOURCE_RECEIPT
        source = json.loads((ROOT / REVIEWER_SOURCE_RECEIPT["relpath"]).read_bytes())
        for member in population["architecture"]["members"]:
            member.update(active_roles=["perception", "solver", "reviewer", "planner"],
                          model_per_trajectory=13, execution_config=source["source_policy"])
        population["contact_limits"]["model_per_trajectory"] = 13
    receipt = require_local_node_basis(basis, population, repo_root=ROOT)
    assert receipt["member_id"] == ("seed" if target_role == "reviewer" else "review-off")


def test_reviewer_can_change_only_reviewer_text(tmp_path):
    source = text_fixture(tmp_path)
    candidate = candidate_policy(tmp_path, source)
    solver = tmp_path / "configs" / candidate["phase_material"]["solver"]["instruction_template"]
    solver.write_bytes((tmp_path / "configs" / source["phase_material"]["solver"]["instruction_template"]).read_bytes())
    reviewer = tmp_path / "configs" / candidate["phase_material"]["reviewer"]["instruction_template"]
    reviewer.write_bytes(reviewer.read_bytes() + b"\nSynthetic reviewer instruction.")
    assert require_local_role_policy(source, candidate, repo_root=tmp_path, target_role="reviewer")["target_text_changed"]
    with pytest.raises(PolicyError, match="non-target"):
        require_local_role_policy(source, candidate, repo_root=tmp_path, target_role="solver")


def map_world(tmp_path):
    from speech_aware_evidence_acquisition.rails.local_node_panel import MAP_SCHEMA
    from speech_aware_evidence_acquisition.rails.experiment_population import population_stage_spec
    old_cell, = load_campaign_cells(ROOT, RECEIPT["experiment"])
    paths = [SOURCE_RECEIPT["relpath"], SOURCE_POPULATION["relpath"], RECEIPT["source_policy"]["relpath"],
             f"configs/model/{old_cell.document['model_fragment']}.json",
             f"configs/dataset/{old_cell.document['dataset_fragment']}.json",
             f"configs/baseline/{old_cell.document['baseline_fragment']}.json",
             f"configs/experiment/{RECEIPT['experiment']}.json"]
    paths += ["configs/" + material["instruction_template"] for material in POLICY["phase_material"].values()]
    for relative in paths:
        p = tmp_path / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT / relative).read_bytes())
    population = local_population()
    pp = tmp_path / "configs/experiments/local-population.json"
    prepare.save(pp, population)
    population_pin = prepare.pin(pp, tmp_path)
    stage = population_stage_spec(population_pin, repo_root=tmp_path, cohort_id="comparison", allow_architecture=True)
    ep, bp, values = source_configs()
    report = derive_manual_architecture_audio_budget(values)
    rows = []
    for member in population["architecture"]["members"]:
        label = member["member_id"]
        row = dict(member_id=label, experiment="local-" + label, cell_id="local-" + label,
                   run_id="LOCAL-" + label, attempt_id="attempt-" + label,
                   fit_run_id="LOCAL-" + label + "-FIT", fit_attempt_id="attempt-" + label + "-fit")
        new_ep, new_bp = local_node_documents(ep, bp, POLICY, row, policy_binding=RECEIPT["policy_binding"],
            population_pin=population_pin, cohort_id="comparison", stage=stage, basis=BASIS, report=report)
        prepare.save(tmp_path / "configs/experiment" / (row["experiment"] + ".json"), new_ep)
        prepare.save(tmp_path / "configs/baseline" / (row["experiment"] + ".json"), new_bp)
        rows.append({**row, "planned_speech_audio_seconds": report["required_integer_audio_seconds"]})
    mapping = dict(schema=MAP_SCHEMA, experiment_population=population_pin, architecture_extent=None,
                   local_node_basis=BASIS, members=rows)
    return population, population_pin, mapping


def test_real_map_composition_accepts_held_identity_projection(tmp_path):
    from speech_aware_evidence_acquisition.rails.local_node_panel import mapped_local_node_cells
    population, population_pin, mapping = map_world(tmp_path)
    result = mapped_local_node_cells(mapping, population, population_pin, repo_root=tmp_path)
    assert [label for label, _, _ in result] == ["control", "control-aa", "candidate-0", "candidate-1"]
    assert all(config.values["execution_plan"]["planned_speech_audio_seconds"] == 588 for _, _, config in result)


@pytest.mark.parametrize("fault", ["decoding", "model", "order", "duplicate-fit"])
def test_real_map_rejects_extra_runtime_drift(tmp_path, fault):
    from speech_aware_evidence_acquisition.rails.local_node_panel import mapped_local_node_cells
    population, population_pin, mapping = map_world(tmp_path)
    if fault == "order":
        mapping["members"].reverse()
    elif fault == "duplicate-fit":
        mapping["members"][1]["fit_run_id"] = mapping["members"][0]["fit_run_id"]
    else:
        path = tmp_path / "configs/experiment/local-control.json"
        document = json.loads(path.read_bytes())
        if fault == "decoding":
            document["request_decoding_overrides"] = {"temperature": 0.4}
        else:
            document["cells"][0]["model_fragment"] = "different-model"
        path.write_text(json.dumps(document))
    with pytest.raises(PolicyError):
        mapped_local_node_cells(mapping, population, population_pin, repo_root=tmp_path)


def test_local_selector_requires_new_capacity_before_historical_proof(monkeypatch):
    from speech_aware_evidence_acquisition.rails import architecture_natural_registration as gate
    from speech_aware_evidence_acquisition.rails import local_node_panel as local
    from speech_aware_evidence_acquisition.rails import system_text_policy as policies
    _, _, values = source_configs()
    values = deepcopy(values)
    values.pop("architecture_extent")
    values["local_node_basis"] = BASIS
    cell, = load_campaign_cells(ROOT, RECEIPT["experiment"])
    plans = [dict(plan_role=role, architecture_proof=SELECTOR, local_node_basis=BASIS,
                  experiment_population=values["experiment_population"], population_cohort=values["population_cohort"],
                  capacity_prerequisite={"registration": "new", "qualification": "new"},
                  natural_prerequisite={"registration": "new", "qualification": "new"}) for role in ("generation", "fit")]
    monkeypatch.setattr(local, "require_local_node_basis", lambda *a, **k: RECEIPT)
    monkeypatch.setattr(policies, "verify_system_text_binding", lambda *a, **k: None)
    def fresh(*a, **k):
        raise RuntimeError("fresh-capacity-required")
    def historical(*a, **k):
        pytest.fail("Local node must not inherit historical fixed400 natural proof")
    monkeypatch.setattr(gate, "_qualified_capacity", fresh)
    monkeypatch.setattr(gate, "_fixed400_natural", historical)
    with pytest.raises(RuntimeError, match="fresh-capacity-required"):
        gate.require_architecture_n20_registration(values, cell.document, plans, repo_root=ROOT, data_root=ROOT)

def original_proposal_world(tmp_path, monkeypatch, k=2):
    from speech_aware_evidence_acquisition.rails import local_node_panel as local
    from speech_aware_evidence_acquisition.core.preparation import digest
    population, basis = local_population(k), deepcopy(BASIS)
    registration = tmp_path / "registration.json"
    prepare.save(registration, {"schema": "saea-local-solver-proposer-contact-plan-v1",
        "status": "ROOT_COUNTERSIGNED_AND_POSITIONS_RESERVED_BEFORE_CONTACT", "runtime_admission": False,
        "design_slots": ["original-" + candidate for candidate in population["cohorts"][0]["candidate_ids"]]})
    validation = {"schema": "saea-local-node-original-proposal-validation-v1",
        "status": "ROOT_VALIDATED_ORIGINAL_PROPOSALS", "target_role": "solver",
        "proposal_registration": prepare.pin(registration, tmp_path),
        "candidate_ids": deepcopy(population["cohorts"][0]["candidate_ids"]), "runtime_admission": False,
        "original_design_slot": {candidate: "original-" + candidate for candidate in population["cohorts"][0]["candidate_ids"]},
        "members": {m["member_id"]: {"execution_config": m["execution_config"],
                    "base_bundle_id": m["base_bundle_id"]}
                    for m in population["architecture"]["members"]
                    if m["member_id"] in population["cohorts"][0]["candidate_ids"]}}
    ids = population["cohorts"][0]["sample_ids"]
    output = {"facets": {}, "values": {"perception": {sid: [] for sid in ids}}}
    artifact = {"output": output, "output_sha256": digest(output)}
    receipt = dict(deepcopy(RECEIPT), output_sha256=digest(output))
    original_read = local._read_pin
    def source_supply_fixture(pin, root):
        if Path(root) == ROOT and pin == SOURCE_RECEIPT:
            return json.dumps(receipt).encode()
        if Path(root) == tmp_path and pin in (RECEIPT["prepared_phase_supply"], RECEIPT["source_prepared_phase_supply"]):
            return json.dumps(artifact).encode()
        return original_read(pin, root)
    monkeypatch.setattr(local, "_read_pin", source_supply_fixture)
    basis["proposal_custody"]["registration"] = prepare.pin(registration, tmp_path)
    return population, basis, validation


@pytest.mark.parametrize("fault", [None, "role", "candidate-order", "runtime", "policy", "bundle", "duplicate-slot", "registration", "missing-member", "raw-pin", "actor-schema", "actor-status", "actor-role", "actor-slots", "unregistered-slot", "slot-order", "actor-admission"])
@pytest.mark.parametrize("k", [2, 4])
def test_original_proposal_custody_is_independent_of_runtime_allocation(tmp_path, monkeypatch, fault, k):
    population, basis, validation = original_proposal_world(tmp_path, monkeypatch, k)
    ids = population["cohorts"][0]["candidate_ids"]
    if fault == "role":
        validation["target_role"] = "reviewer"
    elif fault == "candidate-order":
        validation["candidate_ids"].reverse()
    elif fault == "runtime":
        validation["runtime_admission"] = True
    elif fault == "policy":
        validation["members"][ids[0]]["execution_config"] = SOURCE_POPULATION
    elif fault == "bundle":
        validation["members"][ids[0]]["base_bundle_id"] = "changed"
    elif fault == "duplicate-slot":
        validation["original_design_slot"][ids[1]] = validation["original_design_slot"][ids[0]]
    elif fault == "registration":
        validation["proposal_registration"]["sha256"] = "c" * 64
    elif fault == "missing-member":
        validation["members"].pop(ids[0])
    if fault == "unregistered-slot":
        validation["original_design_slot"][ids[0]] = "unregistered-new-opportunity"
    elif fault == "slot-order":
        validation["original_design_slot"][ids[0]], validation["original_design_slot"][ids[1]] = (
            validation["original_design_slot"][ids[1]], validation["original_design_slot"][ids[0]])
    elif fault is not None and fault.startswith("actor-"):
        regpath = tmp_path / "registration.json"
        actor = json.loads(regpath.read_bytes())
        if fault == "actor-schema":
            actor["schema"] = "foreign-plan"
        elif fault == "actor-role":
            actor["schema"] = "saea-local-reviewer-proposer-contact-plan-v1"
        elif fault == "actor-status":
            actor["status"] = "DRAFT"
        elif fault == "actor-admission":
            actor["runtime_admission"] = True
        else:
            actor["design_slots"].pop()
        regpath.write_text(json.dumps(actor))
        basis["proposal_custody"]["registration"] = prepare.pin(regpath, tmp_path)
        validation["proposal_registration"] = deepcopy(basis["proposal_custody"]["registration"])
    path = tmp_path / "validation.json"
    prepare.save(path, validation)
    basis["proposal_custody"]["validation"] = prepare.pin(path, tmp_path)
    if fault == "raw-pin":
        path.write_text("{}")
    if fault is None:
        assert require_local_node_basis(basis, population, repo_root=ROOT, data_root=tmp_path)["member_id"] == "review-off"
        assert set(validation["members"]) == set(ids)
        assert not set(population["cohorts"][0]["control_ids"]).intersection(validation["members"])
    else:
        with pytest.raises(PolicyError):
            require_local_node_basis(basis, population, repo_root=ROOT, data_root=tmp_path)

def test_pure_capacity_budget_uses_explicit_carrier_and_experiment_profile():
    from speech_aware_evidence_acquisition.analysis.native_graph_capacity import native_graph_capacity_budget
    ep, bp, values = source_configs()
    expected = native_graph_capacity_budget(values, slot_value_count=5, intent_value_count=7,
                                            profile=ep["native_graph_capacity_profile"])
    actual = prepare.local_capacity_budget(ep, bp, slot_value_count=5, intent_value_count=7)
    assert actual == expected

@pytest.mark.parametrize("target_role,label", [("solver", "review-off"), ("reviewer", "seed")])
@pytest.mark.parametrize("obsolete_tokenizer_budget", [False, True])
def test_generated_natural_budget_passes_actual_existing_gate(tmp_path, target_role, label, obsolete_tokenizer_budget):
    from test_architecture_natural_registration import fixture, invoke
    from speech_aware_evidence_acquisition.rails.local_node_panel import REVIEWER_SOURCE_RECEIPT
    args = fixture(tmp_path, label)
    source_receipt = RECEIPT if target_role == "solver" else json.loads((ROOT / REVIEWER_SOURCE_RECEIPT["relpath"]).read_bytes())
    cell, = load_campaign_cells(ROOT, source_receipt["experiment"])
    ep = json.loads((ROOT / "configs/experiment" / (source_receipt["experiment"] + ".json")).read_bytes())
    bp = json.loads((ROOT / "configs/baseline" / (cell.document["baseline_fragment"] + ".json")).read_bytes())
    row = dict(experiment="local-proof", cell_id="local-proof", run_id="LOCAL-PROOF-V1",
               attempt_id="local-proof", fit_run_id="LOCAL-PROOF-FIT-V1", fit_attempt_id="local-proof-fit")
    graph_name = "slurp-speech-native-simple-consumption-n100-graph4-v1"
    view = json.loads((ROOT / "configs/dataset" / (graph_name + ".json")).read_bytes())
    pp, pb = prepare.local_companion_documents(ep, bp, row, kind="natural", graph_view=view,
                                               graph_dataset=graph_name, capacity_budget={})
    args["values"]["family_budget"] = pp["family_budget"]
    if obsolete_tokenizer_budget:
        args["values"]["family_budget"] = {"complete_system_trajectories": 0, "generation_calls_cap": 0,
                                           "official_complete_scoring_jobs": 0, "tokenizer_endpoint_cap": 0}
        with pytest.raises(PolicyError, match="natural family budget"):
            invoke(args)
    else:
        result = invoke(args)
        assert result["generation_cap"] == pp["execution_plan"]["planned_model_calls"]
        assert result["fit_cap"] == pb["native_contact_fit"]["contact_cap"]

@pytest.mark.parametrize("role", ["solver", "reviewer"])
@pytest.mark.parametrize("fault", [None, "cross-role", "pair-selector", "historical", "historical-pair-only"])
def test_local_read_selector_is_bound_to_each_pair_and_role(tmp_path, monkeypatch, role, fault):
    import hashlib
    from types import SimpleNamespace
    from test_system_architecture_read import scope_fixture, validate, manual
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    v = scope_fixture(tmp_path, monkeypatch)
    _, recipe, registration, *_ = v
    basis = {"schema": "saea-local-node-panel-basis-v1", "target_role": role}
    selector = "local-" + role + "-panel-v1"
    recipe.update(architecture_proof=selector, local_node_basis=basis)
    registration.update(architecture_proof=selector, local_node_basis=basis)
    for binding in registration["member_bindings"].values():
        for pin in binding["registered_plans"].values():
            path = tmp_path / pin["relpath"]
            plan = json.loads(path.read_bytes())
            plan.update(architecture_proof=selector, local_node_basis=basis)
            if fault == "pair-selector":
                plan["architecture_proof"] = "local-" + ("reviewer" if role == "solver" else "solver") + "-panel-v1"
            path.write_text(json.dumps(plan))
            pin["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    configured_basis = basis
    if fault == "cross-role":
        recipe["architecture_proof"] = registration["architecture_proof"] = (
            "local-" + ("reviewer" if role == "solver" else "solver") + "-panel-v1")
    elif fault in ("historical", "historical-pair-only"):
        recipe["architecture_proof"] = registration["architecture_proof"] = "manual-architecture-n20-v1"
        if fault == "historical-pair-only":
            recipe.pop("local_node_basis")
            registration.pop("local_node_basis")
            configured_basis = None
    def configured(root, model, data, label, experiment):
        values = {"label": label}
        if configured_basis is not None:
            values["local_node_basis"] = configured_basis
        return SimpleNamespace(values=values, config_hash=registration["member_bindings"][label]["config_hash"])
    monkeypatch.setattr(manual, "compose", configured)
    registration["registration_sha256"] = content_hash(
        {k: value for k, value in registration.items() if k != "registration_sha256"})
    if fault is None:
        assert validate(v, tmp_path)["labels"] == list(registration["member_bindings"])
    else:
        with pytest.raises(PolicyError, match="local node READ"):
            validate(v, tmp_path)
