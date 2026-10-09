"""Prospective stage contracts use copied source configuration and synthetic identities."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import architecture_natural_registration as joint
from speech_aware_evidence_acquisition.rails.local_node_panel import REVIEWER_SOURCE_RECEIPT, SOURCE_POPULATION, local_node_documents
from speech_aware_evidence_acquisition.rails.experiment_population import population_stage_spec
from speech_aware_evidence_acquisition.rails.architecture_audio_budget import derive_manual_architecture_audio_budget
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.core.config import compose, ConfigError
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("joint_prepare_test", ROOT / "scripts/preparation/prepare_manual_audio_recovery.py")
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def world(tmp_path, monkeypatch):
    root, data = tmp_path / "repo", tmp_path / "data"
    receipt = json.loads((ROOT / REVIEWER_SOURCE_RECEIPT["relpath"]).read_bytes())
    old_cell, = load_campaign_cells(ROOT, receipt["experiment"])
    c = old_cell.document
    policy = json.loads((ROOT / receipt["source_policy"]["relpath"]).read_bytes())
    paths = [f"configs/{kind}/{name}.json" for kind, name in (
        ("model", c["model_fragment"]), ("dataset", c["dataset_fragment"]),
        ("baseline", c["baseline_fragment"]), ("experiment", receipt["experiment"]))]
    paths.append(joint.JOINT_PROOF_ROSTER["relpath"])
    paths.append(receipt["source_policy"]["relpath"])
    paths.append("scripts/preparation/prepare_manual_audio_recovery.py")
    paths.extend("configs/" + material["instruction_template"] for material in policy["phase_material"].values())
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    population = json.loads((ROOT / SOURCE_POPULATION["relpath"]).read_bytes())
    cohort = population["cohorts"][0]
    labels = ["control", "control-aa", "solver-import", "reviewer-import", "joint-import"]
    cohort.update(control_ids=labels[:2], candidate_ids=labels[2:])
    seed_member = next(m for m in population["architecture"]["members"] if m["member_id"] == "seed")
    population["architecture"]["members"] = [dict(deepcopy(seed_member), member_id=label,
        execution_config=receipt["source_policy"]) for label in labels]
    # This fixture isolates identity/admission projection; pure import/raw custody are tested separately.
    population["contact_limits"]["model_per_trajectory"] = seed_member["model_per_trajectory"]
    population_pin_path = root / "configs/experiments/synthetic-joint.json"
    prepare.save(population_pin_path, population)
    population_pin = prepare.pin(population_pin_path, root)
    basis = {"relpath": "synthetic-basis.json", "sha256": "a" * 64}
    bound = dict(receipt=receipt, donor_receipts={}, cumulative_sources=[
        {"kind": "selection", "sha256": "b" * 64, "sample_ids": cohort["sample_ids"]}])
    monkeypatch.setattr(joint, "require_joint_role_basis", lambda *args, **kwargs: deepcopy(bound))
    ep = json.loads((root / "configs/experiment" / (receipt["experiment"] + ".json")).read_bytes())
    bp = json.loads((root / "configs/baseline" / (c["baseline_fragment"] + ".json")).read_bytes())
    config = compose(root, c["model_fragment"], c["dataset_fragment"], c["baseline_fragment"], receipt["experiment"])
    stage = population_stage_spec(population_pin, repo_root=root, cohort_id=cohort["cohort_id"], allow_architecture=True)
    report = derive_manual_architecture_audio_budget(config.values)
    rows = []
    for label in labels:
        row = dict(member_id=label, experiment="synthetic-" + label, cell_id="synthetic-" + label,
            run_id="SYNTHETIC-" + label, attempt_id="synthetic-" + label,
            fit_run_id="SYNTHETIC-" + label + "-FIT", fit_attempt_id="synthetic-" + label + "-fit")
        new_ep, new_bp = local_node_documents(ep, bp, policy, row, policy_binding=receipt["policy_binding"],
            population_pin=population_pin, cohort_id=cohort["cohort_id"], stage=stage, basis={}, report=report)
        new_bp.pop("local_node_basis"); new_bp["joint_role_basis"] = basis
        new_ep["stage3_measurement"].update(tuning_roster=ep["stage3_measurement"]["read_roster"],
            read_roster=ep["stage3_measurement"]["read_roster"], independent_validation=False,
            runtime_adoption=False, learner_export=False)
        prepare.save(root / "configs/experiment" / (row["experiment"] + ".json"), new_ep)
        prepare.save(root / "configs/baseline" / (row["experiment"] + ".json"), new_bp)
        rows.append(dict(row, planned_speech_audio_seconds=report["required_integer_audio_seconds"]))
    mapping = dict(schema=joint.JOINT_MAP_SCHEMA, experiment_population=population_pin,
        architecture_extent=None, joint_role_basis=basis, members=rows)
    map_path = root / "synthetic-generation-map.json"; prepare.save(map_path, mapping)
    return SimpleNamespace(root=root, data=data, population=population, population_pin=population_pin,
        basis=basis, bound=bound, mapping=mapping, map_path=map_path, receipt=receipt)


def cells(f):
    return joint._mapped_joint_cells(f.mapping, f.population, f.population_pin, repo_root=f.root, data_root=f.data)


def admission(f, members, stage="generation"):
    rows = []
    for label, cell, config in members:
        c, m = cell.document, config.values["stage3_measurement"]
        rows.append(dict(member_id=label, cell_id=c["cell_id"], run_id=c["run_id"], attempt_id=c["attempt_id"],
            config_hash=config.config_hash, tuning_roster=m["tuning_roster"], read_roster=m["read_roster"],
            intersection_sample_ids=config.values["populations"][0]["ids"]))
    disposition = dict(schema="saea-owner227-adaptive-joint-roster-reuse-v1", root_decision=joint.JOINT_SOURCE_DECISION,
        joint_role_basis=f.basis, scope="adaptive-development-discovery-only", stage=stage,
        claims_benefit=False, independent_validation=False, runtime_adoption=False, learner_export=False,
        members=rows, cumulative_sources=f.bound["cumulative_sources"])
    return dict(schema="saea-campaign-decision-v1", status="decided", owner_decisions=[227],
        learner_export=False, joint_role_basis=f.basis, adaptive_joint_roster_reuse=disposition)


def proof(f, monkeypatch, stage):
    generation = cells(f)
    view = json.loads((f.root / joint.JOINT_PROOF_ROSTER["relpath"]).read_bytes())
    monkeypatch.setattr(joint, "_joint_knowledge_counts", lambda *args: dict(slot_value_count=2, intent_value_count=2))
    rows = []
    for label, cell, config in generation:
        c = cell.document
        ep = json.loads((f.root / "configs/experiment" / (c["cell_id"] + ".json")).read_bytes())
        bp = json.loads((f.root / "configs/baseline" / (c["baseline_fragment"] + ".json")).read_bytes())
        name = "synthetic-" + stage + "-" + label
        row = dict(member_id=label, experiment=name, cell_id=name, run_id=name.upper() + "-FIT-V1", attempt_id=name)
        if stage == "natural": row.update(fit_run_id=name.upper() + "-ACTUAL-FIT", fit_attempt_id=name + "-actual-fit")
        budget = prepare.local_capacity_budget(ep, bp, slot_value_count=2, intent_value_count=2) if stage == "capacity" else {}
        pp, pb = prepare.local_companion_documents(ep, bp, {k:v for k,v in row.items() if k != "member_id"},
            kind=stage, graph_view=view, graph_dataset="slurp-speech-native-simple-consumption-n100-graph4-v1", capacity_budget=budget)
        prepare.save(f.root / "configs/experiment" / (name + ".json"), pp)
        prepare.save(f.root / "configs/baseline" / (name + ".json"), pb)
        row["config_hash"] = compose(f.root, pp["cells"][0]["model_fragment"], pp["cells"][0]["dataset_fragment"], name, name).config_hash
        rows.append(row)
    mapping = dict(schema=joint.JOINT_PROOF_MAP_SCHEMA, stage=stage, experiment_population=f.population_pin,
        joint_role_basis=f.basis, generation_identity_map=prepare.pin(f.map_path, f.root),
        proof_roster=deepcopy(joint.JOINT_PROOF_ROSTER), members=rows)
    path = f.root / (stage + "-map.json"); prepare.save(path, mapping)
    return mapping, path


@pytest.mark.parametrize("stage", ["generation", "capacity", "natural"])
def test_complete_fresh_stage_configuration_and_explicit_visible_overlap(tmp_path, monkeypatch, stage):
    f = world(tmp_path, monkeypatch)
    members = cells(f)
    if stage != "generation":
        _, path = proof(f, monkeypatch, stage)
        members = joint._mapped_joint_proof_cells(prepare.pin(path, f.root), f.population, f.population_pin,
            repo_root=f.root, data_root=f.data, stage=stage)
    decision = admission(f, members, stage)
    assert joint.require_joint_adaptive_disposition(decision, f.basis, f.population, members,
        repo_root=f.root, data_root=f.data, stage=stage) == decision["adaptive_joint_roster_reuse"]
    assert len(members) == 5


@pytest.mark.parametrize("fault", ["partial", "reorder", "held", "owner", "scope", "benefit", "independent", "adoption", "export", "ancestry", "confirmatory", "profile", "foreign-roster"])
def test_self_consistent_overlap_cannot_authorize_foreign_scope(tmp_path, monkeypatch, fault):
    f = world(tmp_path, monkeypatch); members = cells(f)
    if fault == "partial": members.pop()
    elif fault == "reorder": members.reverse()
    elif fault in {"confirmatory", "profile", "foreign-roster"}:
        values = members[-1][2].values
        if fault == "confirmatory": values["execution_plan"]["split_role"] = "confirmatory"
        elif fault == "profile": values["execution_plan"]["execution_profile"] = "paper-scale-confirmatory"
        else: values["populations"][0]["ids"] = values["populations"][0]["ids"][:-1]
    decision = admission(f, members)
    d = decision["adaptive_joint_roster_reuse"]
    if fault == "held": decision["status"] = "held"
    elif fault == "owner": decision["owner_decisions"] = [228]
    elif fault == "scope": d["scope"] = "independent-confirmatory"
    elif fault in {"benefit", "independent", "adoption", "export"}:
        key = dict(benefit="claims_benefit", independent="independent_validation", adoption="runtime_adoption", export="learner_export")[fault]
        d[key] = True
    elif fault == "ancestry": d["cumulative_sources"] = []
    with pytest.raises(PolicyError): joint.require_joint_adaptive_disposition(decision, f.basis, f.population,
        members, repo_root=f.root, data_root=f.data)


@pytest.mark.parametrize("fault", ["partial", "order", "parent", "roster-pin", "arbitrary-subset", "geometry", "spent", "duplicate"])
def test_complete_original_proof_refuses_repinned_partial_or_foreign_maps(tmp_path, monkeypatch, fault):
    f = world(tmp_path, monkeypatch); mapping, path = proof(f, monkeypatch, "natural")
    if fault == "partial": mapping["members"].pop()
    elif fault == "order": mapping["members"].reverse()
    elif fault == "parent": mapping["generation_identity_map"]["sha256"] = "f" * 64
    elif fault == "roster-pin": mapping["proof_roster"]["sha256"] = "f" * 64
    else:
        row = mapping["members"][-1]
        ep_path = f.root / "configs/experiment" / (row["experiment"] + ".json")
        ep = json.loads(ep_path.read_bytes())
        if fault == "arbitrary-subset": ep["populations"][0]["ids"][-1] = f.population["cohorts"][0]["sample_ids"][-1]
        elif fault == "geometry": ep["cells"][0]["model_fragment"] = "foreign-model"
        elif fault == "spent":
            row["run_id"] = f.receipt["run_id"]; ep["cells"][0]["run_id"] = row["run_id"]; ep["experiment_id"] = row["run_id"]
        else: row["attempt_id"] = mapping["members"][0]["attempt_id"]; ep["cells"][0]["attempt_id"] = row["attempt_id"]
        ep_path.write_text(json.dumps(ep))
        if fault != "geometry": row["config_hash"] = compose(f.root, ep["cells"][0]["model_fragment"], ep["cells"][0]["dataset_fragment"], row["experiment"], row["experiment"]).config_hash
    path.write_text(json.dumps(mapping))
    with pytest.raises((PolicyError, ValueError, FileNotFoundError, ConfigError)):
        joint._mapped_joint_proof_cells(prepare.pin(path, f.root), f.population, f.population_pin,
            repo_root=f.root, data_root=f.data, stage="natural")


@pytest.mark.parametrize("fault", [None, "unsigned", "partial", "foreign-parent", "wrong-member", "wrong-roster", "wrong-fit", "missing-basis"])
def test_completed_original_natural_registration_joins_same_full_parent(tmp_path, monkeypatch, fault):
    f = world(tmp_path, monkeypatch); mapping, path = proof(f, monkeypatch, "natural")
    mapped = joint._mapped_joint_proof_cells(prepare.pin(path, f.root), f.population, f.population_pin,
        repo_root=f.root, data_root=f.data, stage="natural")
    decision = admission(f, mapped, "natural")
    decision["joint_proof_identity_map"] = prepare.pin(path, f.root)
    decision["eligible_run_ids"] = [run for _, c, config in mapped
        for run in (c.document["run_id"], config.values["native_contact_fit"]["run_id"])]
    qualified = {"members": [dict(label=label, experiment=c.document["cell_id"], run_id=c.document["run_id"],
        attempt_id=c.document["attempt_id"], config_hash=config.config_hash,
        configured_sample_ids=config.values["populations"][0]["ids"],
        fit_run_id=config.values["native_contact_fit"]["run_id"]) for label, c, config in mapped]}
    next_decision = dict(joint_role_basis=f.basis, execution_identity_map=prepare.pin(f.map_path, f.root))
    if fault == "unsigned": decision["status"] = "held"
    elif fault == "partial": qualified["members"].pop()
    elif fault == "foreign-parent": next_decision["execution_identity_map"]["sha256"] = "f" * 64
    elif fault == "missing-basis": decision.pop("joint_role_basis")
    elif fault:
        key = {"wrong-member":"label", "wrong-roster":"configured_sample_ids", "wrong-fit":"fit_run_id"}[fault]
        qualified["members"][-1][key] = [] if key == "configured_sample_ids" else "foreign"
    args = (decision, qualified, next_decision, f.population, f.population_pin)
    kwargs = dict(repo_root=f.root, data_root=f.data)
    if fault:
        with pytest.raises(PolicyError): joint._require_joint_completed_natural(*args, **kwargs)
    else: joint._require_joint_completed_natural(*args, **kwargs)


@pytest.mark.parametrize("stage", ["capacity", "natural"])
@pytest.mark.parametrize("successor_map", [False, True])
def test_final_ready_proof_requires_fresh_raw_map_and_preserves_held_map(tmp_path, monkeypatch, stage, successor_map):
    f = world(tmp_path, monkeypatch); mapping, path = proof(f, monkeypatch, stage)
    original = path.read_bytes()
    for row in mapping["members"]:
        ep_path = f.root / "configs/experiment" / (row["experiment"] + ".json")
        ep = json.loads(ep_path.read_bytes())
        ep["cells"][0]["readiness"] = dict(state="ready", reason="Synthetic separately countersigned stage.", requirements=[])
        ep_path.write_text(json.dumps(ep))
        row["config_hash"] = compose(f.root, ep["cells"][0]["model_fragment"], ep["cells"][0]["dataset_fragment"],
            row["experiment"], row["experiment"]).config_hash
    if successor_map:
        final = f.root / (stage + "-final-map.json"); prepare.save(final, mapping)
        mapped = joint._mapped_joint_proof_cells(prepare.pin(final, f.root), f.population, f.population_pin,
            repo_root=f.root, data_root=f.data, stage=stage)
        decision = admission(f, mapped, stage)
        joint.require_joint_adaptive_disposition(decision, f.basis, f.population, mapped,
            repo_root=f.root, data_root=f.data, stage=stage)
    else:
        with pytest.raises(PolicyError, match="composed identity"):
            joint._mapped_joint_proof_cells(prepare.pin(path, f.root), f.population, f.population_pin,
                repo_root=f.root, data_root=f.data, stage=stage)
    assert path.read_bytes() == original


@pytest.mark.parametrize("stage", ["generation", "capacity", "natural"])
@pytest.mark.parametrize("authorized", [False, True])
def test_flight_entry_retains_overlap_until_canonical_stage_authentication(tmp_path, monkeypatch, stage, authorized):
    spec = importlib.util.spec_from_file_location("joint_gate_test", ROOT / "scripts/checks/flight_registration_check.py")
    gate = importlib.util.module_from_spec(spec)
    import sys
    monkeypatch.setitem(sys.modules, spec.name, gate)
    spec.loader.exec_module(gate)
    root = tmp_path / "repo"
    package = root / "docs/readiness/synthetic-package"
    package.mkdir(parents=True)
    for index in range(1 if stage == "capacity" else 2):
        (package / (str(index) + "-plan-registered-v1.json")).write_text(json.dumps({"run_id":"SYNTHETIC"}))
    report = gate.CellReport("synthetic", "synthetic", "SYNTHETIC", "ready", True,
        run_ids={"generation":"SYNTHETIC"}, findings=[
            gate.Finding("tuning-read-overlap", "Original exact intersection", "SYNTHETIC"),
            gate.Finding("tuning-read-overlap", "Foreign cell intersection", "FOREIGN"),
            gate.Finding("another-blocker", "Unchanged blocker", "SYNTHETIC")])
    values = {"joint_role_basis":{"relpath":"basis.json","sha256":"a"*64}}
    from speech_aware_evidence_acquisition.core import config as core_config
    from speech_aware_evidence_acquisition.rails import experiment_population as population_module
    from speech_aware_evidence_acquisition.rails import architecture_audio_budget as audio_module
    monkeypatch.setattr(core_config, "compose", lambda *args: SimpleNamespace(values=values))
    monkeypatch.setattr(audio_module, "require_manual_architecture_audio_budget", lambda *args: None)
    calls = []
    def validate(*args, **kwargs):
        calls.append(stage)
        if not authorized: raise PolicyError("Synthetic complete canonical admission refusal")
    target = population_module if stage == "capacity" else joint
    name = "require_architecture_capacity_registration" if stage == "capacity" else (
        "require_architecture_n20_registration" if stage == "generation" else "require_architecture_natural_registration")
    monkeypatch.setattr(target, name, validate)
    stages = ["check", "prepare-supply", "prompt-fit"] if stage == "capacity" else ["check", "prepare-supply", "worker"]
    if stage == "generation": stages.append("campaign")
    cell = dict(allowed_execution_stages=stages, model_fragment="synthetic", dataset_fragment="synthetic", baseline_fragment="synthetic")
    baseline = dict(experiment_population={}, architecture_member="control")
    gate._check_registered_supply_binding(report, baseline, SimpleNamespace(repo_root=root), "synthetic-package", {},
        cell=cell, fragment={}, data_root=tmp_path / "data")
    assert calls
    first, foreign, blocker = report.findings[:3]
    assert first.kind == ("authorized-adaptive-joint-roster-overlap" if authorized else "tuning-read-overlap")
    assert first.severity == ("advisory" if authorized else None)
    assert "Original exact intersection" in first.message
    assert foreign.kind == "tuning-read-overlap" and foreign.severity is None
    assert blocker.kind == "another-blocker" and blocker.severity is None
