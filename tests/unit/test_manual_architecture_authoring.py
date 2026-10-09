"""Root-only package authoring preserves source bytes and never dispatches."""

import copy
import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.rails import (
    architecture_natural_registration as pair_api,
)
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from test_system_text_policy_binding import bound  # noqa: F401

SOURCE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "manual_author", SOURCE / "scripts/analysis/author_manual_architecture_package.py"
)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


def fixture(tmp_path, monkeypatch, *, candidates=2, rows=5):
    repo, data = tmp_path / "repo", tmp_path / "data"
    repo.mkdir()
    data.mkdir()
    ids = [f"slurp:train:{i:06d}" for i in range(rows)]
    labels = ["seed", "seed-aa"] + ["candidate-" + str(i) for i in range(candidates)]

    def rp(path, value, base=repo):
        helper.write_new(base / path, value)
        return helper.raw_pin(base / path, base)

    population = rp("population.json", {"fixture": "synthetic architecture metadata"})
    stage = {
        "control_members": labels[:2],
        "candidate_members": labels[2:],
        "sample_ids": ids,
        "N": rows,
        "architecture_members": [],
        "member_generation_contacts_caps": {},
        "member_fit_endpoints_caps": {},
    }
    for i, label in enumerate(labels):
        cap = 13 if i < 2 else i
        identity = {
            "member_id": label,
            "base_bundle_id": "bundle",
            "model_per_trajectory": cap,
            "active_roles": ["perception", "solver"]
            + (["reviewer", "planner"] if i < 2 else []),
            "execution_config": rp(
                "policy-" + label + ".json", {"policy": "controls" if i < 2 else label}
            ),
        }
        stage["architecture_members"].append(identity)
        stage["member_generation_contacts_caps"][label] = rows * cap
        stage["member_fit_endpoints_caps"][label] = rows * cap * 4
    stage["population_budget"] = {
        "family_trajectories": len(labels) * rows,
        "generation_contacts_cap": sum(
            stage["member_generation_contacts_caps"].values()
        ),
        "fit_endpoints_cap": sum(stage["member_fit_endpoints_caps"].values()),
        "N": rows,
        "K": candidates,
    }
    monkeypatch.setattr(
        helper, "population_stage_spec", lambda *a, **k: copy.deepcopy(stage)
    )
    roster = [
        {"sample_id": sid, "utterance_id": sid + "-utterance", "stratum": "fixture"}
        for sid in ids
    ]
    owner = rp("owner.json", {"decision_id": 227, "status": "approved"})
    roster_pin = rp("roster.json", {"items": roster})
    strata_pin = rp("strata.json", {"items": roster})
    template = rp(
        "template.json",
        {
            "schema": "saea-system-text-analysis-recipe-v1",
            "experiment_population": population,
            "population_cohort": "comparison",
            "sample_ids": ids,
            "population_budget": stage["population_budget"],
            "analysis_roster": roster_pin,
            "resampling": {
                "bootstrap_draws": 10,
                "confidence": 0.95,
                "seed": 1,
                "unit": "paired utterance; keep all recording variants together",
            },
            "endpoint": "Official SLU-F1",
            "scientific_claims": "Form evidence; no stable benefit.",
        },
    )
    for rel in (
        "scripts/analysis/system_text_pilot_read.py",
        "src/speech_aware_evidence_acquisition/analysis/system_architecture_read.py",
    ):
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((SOURCE / rel).read_bytes())
    rp("configs/model/model.json", {})
    rp("configs/dataset/dataset.json", {})
    receipts = {}
    originals = {}
    eligible = []
    checks = []
    warm = []
    for identity in stage["architecture_members"]:
        label = identity["member_id"]
        run = "RUN-" + label
        attempt = "attempt-" + label
        supply = rp(
            "prepared/" + run + "/phase.json",
            {"schema": "synthetic prepared metadata", "output_sha256": "c" * 64},
            data,
        )
        fit = {
            "run_id": run + "-FIT",
            "attempt_id": attempt + "-FIT",
            "contact_cap": stage["member_fit_endpoints_caps"][label],
        }
        baseline = {
            "native_contact_fit": fit,
            "prepared_phase_supply": supply,
            "system_search_measurement": {
                "schema": "saea-system-search-measurement-v2",
                "latency_scope": "sample-admission-to-settled-workflow-v1",
                "schedule": "sequential-trajectory",
                "slot_count": 4,
                "queue_depth": 4,
                "minimum_reliable_completion_rate": 1.0,
            },
            "serving_slots": 4,
            "serving_slot_tokens": 24576,
            "decoding_params": {"max_tokens": 1024},
            "server_args": ["-np", "4", "-c", "98304"],
            "native_episode": {},
        }
        rp("configs/baseline/" + label + ".json", baseline)
        cell = {
            "cell_id": label,
            "run_id": run,
            "attempt_id": attempt,
            "model_fragment": "model",
            "dataset_fragment": "dataset",
            "baseline_fragment": label,
            "allowed_execution_stages": [
                "check",
                "prepare-supply",
                "worker",
                "campaign",
            ],
            "readiness": {"state": "held", "reason": "original held metadata"},
            "system_text_policy_binding": {"bundle_id": "bundle"},
        }
        rp(
            "configs/experiment/" + label + ".json",
            {"cells": [cell], "populations": [{"ids": ids}]},
        )
        composed = helper.compose(repo, "model", "dataset", label, label)
        receipt = {
            "member_id": label,
            "experiment": label,
            "run_id": run,
            "attempt_id": attempt,
            "config_hash": composed.config_hash,
            "configured_sample_ids": ids,
            "runtime_sample_ids": ids[::-1],
            "prepared_phase_supply": supply,
            "prepared_source_commit": "b" * 40,
            "source_policy": identity["execution_config"],
            "output_sha256": "c" * 64,
            "contacts": 0,
            "output_equal": True,
            "warm_verified": True,
            "runtime_admission": False,
        }
        receipts[label] = rp("receipts/" + label + ".json", receipt)
        originals[label] = (repo / receipts[label]["relpath"]).read_bytes()
        eligible.extend([run, fit["run_id"]])
    capacity = {
        k: rp("coordination/capacity-" + k + ".json", {"kind": k}, data)
        for k in ("registration", "qualification")
    }
    natural = {
        k: rp("coordination/natural-" + k + ".json", {"kind": k}, data)
        for k in ("registration", "qualification")
    }
    decision = {
        "schema": "saea-campaign-decision-v1",
        "status": "decided",
        "decision_id": "fixture-decision",
        "owner_decisions": [227],
        "learner_export": False,
        "eligible_run_ids": eligible,
        "experiment_population": population,
        "capacity_prerequisite": capacity,
        "natural_prerequisite": natural,
        "source_preparation_commit": "b" * 40,
        "resource_policy": {
            "start_gib": 4,
            "floor_gib": 4,
            "wait_seconds": 600,
            "stable_samples": 3,
            "process_memory_diagnostics": True,
        },
    }
    decision_pin = rp("coordination/decision.json", decision, data)
    values = {
        "schema": "saea-manual-architecture-authoring-input-v1",
        "architecture_proof": helper.reader.SELECTOR,
        "package_relpath": "docs/readiness/fresh-authoring",
        "family_id": "manual-fixture",
        "read_run_id": "READ-FIXTURE",
        "ready_reason": "Final approved prospective metadata.",
        "registered_at_utc": "2026-10-07T00:00:00Z",
        "queue_owner": "root-fixture",
        "experiment_population": population,
        "population_cohort": "comparison",
        "preparation_receipts": receipts,
        "decision_receipt": decision_pin,
        "capacity_prerequisite": capacity,
        "natural_prerequisite": natural,
        "analysis_template": template,
        "stratum_metadata": strata_pin,
        "owner_decision": owner,
        "process_memory_diagnostics": True,
        "process_guard": {
            "start_gib": 4,
            "floor_gib": 4,
            "wait_seconds": 600,
            "stable_samples": 3,
        },
        "runtime_root": str(tmp_path / "runtime"),
        "datasets_lock_path": str(tmp_path / "lock.json"),
    }

    def runtime(repo_root, data_root, *, experiment, **kwargs):
        (cell,) = helper.load_campaign_cells(repo_root, experiment)
        c = cell.document
        assert c["readiness"]["state"] == "ready"
        composed = helper.compose(
            repo_root,
            c["model_fragment"],
            c["dataset_fragment"],
            c["baseline_fragment"],
            experiment,
        )
        plan = ExecutionPlan(
            run_id=c["run_id"],
            attempt_id=c["attempt_id"],
            carrier_lock_key="slurp",
            split_identity_hash="d" * 64,
            protocol_hash=composed.config_hash,
            execution_profile="bounded-discovery-probe",
            split_role="discovery",
            planned_model_calls=stage["member_generation_contacts_caps"][experiment],
            planned_gpu_hours=0.1,
            planned_speech_audio_seconds=rows,
        ).validate()
        warm.append(experiment)
        return SimpleNamespace(
            _composed=composed,
            preparation_context=lambda: {
                "sample_ids": ids[::-1],
                "values": composed.values,
                "execution_plan": plan,
            },
            verify_prepared_artifacts=lambda: (
                {"kind": "phase-supply", "verified": True},
            ),
        )

    monkeypatch.setattr(helper, "build_flight_runtime", runtime)
    monkeypatch.setattr(helper, "require_prepared_graph_artifacts", lambda rt: None)

    def validate_pair(composed, cell, plans, *, repo_root, data_root):
        label = cell["cell_id"]
        for p in plans:
            receipt = json.loads(helper._read_pin(p["preparation_receipt"], repo_root))
            assert receipt["config_hash"] == p["composed_config_hash"]
            assert (
                receipt["execution_plan"]["protocol_hash"]
                == p["execution_plan"]["protocol_hash"]
            )
            assert (
                receipt["prepared_source_commit"]
                == decision["source_preparation_commit"]
            )
            assert cell["readiness"]["reason"] == values["ready_reason"]
        checks.append(label)
        return {
            "member_id": label,
            "runtime_sample_ids": ids[::-1],
            "sample_ids": ids,
            "generation_cap": stage["member_generation_contacts_caps"][label],
            "fit_cap": stage["member_fit_endpoints_caps"][label],
        }

    monkeypatch.setattr(
        pair_api, "require_architecture_n20_registration", validate_pair, raising=False
    )
    return repo, data, values, stage, originals, checks, warm


@pytest.mark.parametrize("additional", [False, True])
@pytest.mark.parametrize("candidates,rows", [(1, 3), (3, 7)])
def test_dynamic_full_package_preserves_originals_and_final_hashes(
    tmp_path, monkeypatch, candidates, rows, additional
):
    repo, data, s, stage, originals, checks, warm = fixture(
        tmp_path, monkeypatch, candidates=candidates, rows=rows
    )
    block = None
    if additional:
        block = {
            "schema": "saea-additional-pooled-contrasts-v1",
            "comparison_group": "architecture", "metric": "slu_f1",
            "contrasts": [{"id": "candidate-minus-control",
                           "coefficients": {stage["candidate_members"][0]: 1, "seed": -1}}],
        }
        # Copy only synthetic source dependencies.
        template_path = repo / s["analysis_template"]["relpath"]
        template = json.loads(template_path.read_text())
        template["additional_paired_contrasts"] = block
        template_path.write_bytes(helper.serialized(template))
        s["analysis_template"] = helper.raw_pin(template_path, repo)
        for name in ("system_text_update", "paired", "bootstrap", "null_calibration"):
            rel = "src/speech_aware_evidence_acquisition/analysis/" + name + ".py"
            target = repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SOURCE / rel).read_bytes())
    result = helper.author(s, repo_root=repo, data_root=data)
    package = repo / result["package"]
    labels = stage["control_members"] + stage["candidate_members"]
    assert (
        checks == warm == labels
        and result["population_budget"] == stage["population_budget"]
    )
    for label in labels:
        assert (
            repo / s["preparation_receipts"][label]["relpath"]
        ).read_bytes() == originals[label]
        prior = json.loads(originals[label])
        receipt = json.loads(
            (package / (label + "-preparation-receipt-final-v1.json")).read_text()
        )
        generation = json.loads(
            (package / (label + "-generation-plan-registered-v1.json")).read_text()
        )
        assert receipt["config_hash"] != prior["config_hash"]
        assert receipt["config_hash"] == generation["composed_config_hash"]
        assert (
            receipt["output_sha256"] == prior["output_sha256"]
            and receipt["runtime_sample_ids"] == prior["runtime_sample_ids"]
        )
        assert generation["status"].startswith("PROSPECTIVE UNSIGNED")
        assert (repo / receipt["original_experiment"]["relpath"]).read_bytes() != (
            repo / receipt["final_experiment"]["relpath"]
        ).read_bytes()
    queue = json.loads((package / "queue-v1.json").read_text())
    assert len(queue) == len(labels) and all(
        q["kind"] == "cell" and q["campaign_plan"] is None for q in queue
    )
    assert all(
        q["expected_rows"] == rows and q["smoke_experiment"] is None for q in queue
    )
    assert all(q["process_start_gib"] == q["process_floor_gib"] == 4 for q in queue)
    assert len(
        helper.load_campaign_plan(repo, package / "campaign-plan-v1.json")
    ) == len(labels)
    read = json.loads((package / "root-read-draft-v1.json").read_text())
    assert read["status"].startswith("DRAFT") and not read["read_authorized"]
    assert (
        not (repo / "docs/exposure-ledger.md").exists()
        and not (data / "attempts").exists()
    )
    # Worker intent is preregistered but cannot execute a scientific reader yet.
    intent_path = package / "manual-architecture-analysis-intent-v1.json"
    intent = json.loads(intent_path.read_text())
    from speech_aware_evidence_acquisition.rails.reward_links import RewardProjection, SLURP_NATIVE_FIELDS
    projection = RewardProjection.from_json(intent["supplement_definition"]["projection"])
    assert projection.scorer == "slurp-slu-official-train"
    assert projection.aggregate_fields == ("port_micro.slu_f1", "port_micro.intent_accuracy")
    assert projection.per_sample_fields == SLURP_NATIVE_FIELDS
    if additional:
        assert intent["additional_paired_contrasts"] == intent["analysis_definition"]["additional_paired_contrasts"] == block
        assert set(intent["supplement_definition"]["source_code"]) == {
            "reader", "analyzer", "system_text_update", "paired", "bootstrap", "null_calibration"}
    else:
        assert "additional_paired_contrasts" not in intent
        assert "additional_paired_contrasts" not in intent["analysis_definition"]
        assert set(intent["supplement_definition"]["source_code"]) == {"reader", "analyzer"}
    assert "source_commit" not in intent
    assert (
        intent["measurement_profile"]
        == intent["analysis_definition"]["measurement_profile"]
    )
    assert all(
        json.loads(
            (package / (label + "-generation-plan-registered-v1.json")).read_text()
        )["measurement_profile"]
        == intent["measurement_profile"]
        for label in labels
    )
    assert all("source_commit" not in m for m in intent["member_bindings"].values())
    assert not (package / "manual-architecture-registration-v1.json").exists()
    worker = tmp_path / "immutable-worker"
    shutil.copytree(repo, worker)
    monkeypatch.setattr(helper, "_frozen_identity", lambda root: "a" * 40)
    launch = {
        "schema": "saea-root-frozen-launch-binding-v1",
        "status": "decided",
        "owner_decisions": [227],
        "worker_commit": "a" * 40,
        "worker_root": str(worker),
        "admission_sha256": s["decision_receipt"]["sha256"],
        "queue_sha256": helper.raw_pin(package / "queue-v1.json", repo)["sha256"],
    }
    launch_path = data / "coordination/frozen-launch.json"
    helper.write_new(launch_path, launch)
    resolution = {
        "schema": "saea-manual-architecture-analysis-resolution-input-v1",
        "analysis_intent": helper.raw_pin(intent_path, repo),
        "frozen_launch_binding": helper.raw_pin(launch_path, data),
        "package_relpath": "docs/readiness/resolved-analysis",
    }
    frozen_bytes = {
        p.relative_to(worker): p.read_bytes() for p in worker.rglob("*") if p.is_file()
    }
    result = helper.resolve_analysis(
        resolution, repo_root=repo, data_root=data, frozen_worker_root=worker
    )
    resolved = repo / result["package"]
    assert all((worker / p).read_bytes() == raw for p, raw in frozen_bytes.items())
    spec = importlib.util.spec_from_file_location(
        "authored_reader", SOURCE / "scripts/analysis/system_text_pilot_read.py"
    )
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    docs = cli.load_documents(
        helper.raw_pin(resolved / "analysis-recipe-v1.json", repo),
        helper.raw_pin(resolved / "analysis-supplement-v1.json", repo),
        repo,
    )
    assert docs[0]["expected_members"] == docs[1]["expected_members"]
    assert docs[1]["measurement_profile"] == docs[0]["measurement_profile"]
    assert RewardProjection.from_json(docs[3]["projection"]) == projection
    if additional:
        assert docs[0]["additional_paired_contrasts"] == docs[1]["additional_paired_contrasts"] == block
    assert docs[1]["source_commit"] == "a" * 40
    assert all(
        m["source_commit"] == "a" * 40 for m in docs[1]["member_bindings"].values()
    )
    expected_definition = intent["analysis_definition"]
    assert {
        k: v for k, v in docs[0].items() if k != "manual_architecture_registration"
    } == expected_definition
    assert json.loads((resolved / "root-read-draft-v1.json").read_text())[
        "status"
    ].startswith("DRAFT")


@pytest.mark.parametrize(
    "fault",
    [
        "partial",
        "receipt-pin",
        "config-reason",
        "source-commit",
        "eligible",
        "policy",
        "roster",
        "existing-package",
    ],
)
def test_invalid_source_refuses_before_ready_or_package_mutation(
    tmp_path, monkeypatch, fault
):
    repo, data, s, stage, originals, _, _ = fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    if fault == "partial":
        s["preparation_receipts"].pop("seed-aa")
    elif fault == "receipt-pin":
        (repo / s["preparation_receipts"]["seed"]["relpath"]).write_text("{}")
    elif fault == "config-reason":
        p = repo / "configs/experiment/seed.json"
        d = json.loads(p.read_text())
        d["cells"][0]["readiness"]["reason"] = "wording drift"
        p.write_bytes(helper.serialized(d))
        before[p] = p.read_bytes()
    elif fault == "source-commit":
        p = data / s["decision_receipt"]["relpath"]
        d = json.loads(p.read_text())
        d["source_preparation_commit"] = "c" * 40
        p.write_bytes(helper.serialized(d))
        s["decision_receipt"] = helper.raw_pin(p, data)
    elif fault == "eligible":
        p = data / s["decision_receipt"]["relpath"]
        d = json.loads(p.read_text())
        d["eligible_run_ids"].reverse()
        p.write_bytes(helper.serialized(d))
        s["decision_receipt"] = helper.raw_pin(p, data)
    elif fault == "policy":
        stage["architecture_members"][0]["execution_config"] = {}
    elif fault == "roster":
        (repo / "roster.json").write_text("{}")
    else:
        (repo / s["package_relpath"]).mkdir(parents=True)
    with pytest.raises(PolicyError):
        helper.author(s, repo_root=repo, data_root=data)
    assert all(p.read_bytes() == raw for p, raw in before.items())
    package = repo / s["package_relpath"]
    assert not package.exists() or not list(package.iterdir())


def test_warm_contact_refusal_preserves_failure_without_silent_retry(
    tmp_path, monkeypatch
):
    import socket

    repo, data, s, _, originals, _, _ = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        helper,
        "build_flight_runtime",
        lambda *a, **k: socket.create_connection(("127.0.0.1", 1)),
    )
    with pytest.raises(RuntimeError, match="refuses"):
        helper.author(s, repo_root=repo, data_root=data)
    package = repo / s["package_relpath"]
    assert (package / "seed-original-experiment-v1.json").exists()
    assert not (package / "seed-preparation-receipt-final-v1.json").exists()
    assert all(
        (repo / s["preparation_receipts"][label]["relpath"]).read_bytes() == raw
        for label, raw in originals.items()
    )
    with pytest.raises(PolicyError, match="fresh readiness"):
        helper.author(s, repo_root=repo, data_root=data)
    assert not (data / "attempts").exists()


def test_root_opt_in_authors_plan_status_only_and_never_read_or_exposure(
    tmp_path, monkeypatch
):
    repo, data, s, _, _, _, _ = fixture(tmp_path, monkeypatch)
    helper.author(s, repo_root=repo, data_root=data, root_countersign_plans=True)
    package = repo / s["package_relpath"]
    assert json.loads(
        (package / "seed-generation-plan-registered-v1.json").read_text()
    )["status"].startswith("ROOT COUNTERSIGNED BEFORE CONTACT")
    assert json.loads((package / "root-read-draft-v1.json").read_text())[
        "status"
    ].startswith("DRAFT")
    assert not (repo / "docs/exposure-ledger.md").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "projection",
        "missing-profile",
        "profile-mismatch",
        "same-worker",
        "commit",
        "decision",
        "queue",
        "intent",
        "dependency",
        "configuration",
    ],
)
def test_postfreeze_resolution_refuses_wrong_source_before_any_write(
    tmp_path, monkeypatch, fault
):
    repo, data, inputs, _, _, _, _ = fixture(tmp_path, monkeypatch)
    helper.author(inputs, repo_root=repo, data_root=data)
    package = repo / inputs["package_relpath"]
    if fault in {"projection", "missing-profile", "profile-mismatch"}:
        intent_path = package / "manual-architecture-analysis-intent-v1.json"
        invalid = json.loads(intent_path.read_text())
        if fault == "projection":
            invalid["supplement_definition"]["projection"] = {"scorer": "slurp-slu-official-train"}
        elif fault == "missing-profile":
            invalid.pop("measurement_profile")
        else:
            invalid["measurement_profile"]["queue_depth"] = 8
        intent_path.write_bytes(helper.serialized(invalid))
    worker = tmp_path / "immutable-worker"
    shutil.copytree(repo, worker)
    intent = helper.raw_pin(
        package / "manual-architecture-analysis-intent-v1.json", repo
    )
    launch = {
        "schema": "saea-root-frozen-launch-binding-v1",
        "status": "decided",
        "owner_decisions": [227],
        "worker_commit": "a" * 40,
        "worker_root": str(worker),
        "admission_sha256": inputs["decision_receipt"]["sha256"],
        "queue_sha256": helper.raw_pin(package / "queue-v1.json", repo)["sha256"],
    }
    if fault == "commit":
        launch["worker_commit"] = "c" * 40
    if fault == "decision":
        launch["admission_sha256"] = "c" * 64
    if fault == "queue":
        launch["queue_sha256"] = "c" * 64
    if fault == "intent":
        (worker / intent["relpath"]).write_text("{}")
    if fault == "dependency":
        (repo / "roster.json").write_text("{}")
    if fault == "configuration":
        p = worker / "configs/experiment/seed.json"
        value = json.loads(p.read_text())
        value["cells"][0]["readiness"]["reason"] = "drift"
        p.write_bytes(helper.serialized(value))
    path = data / "coordination/frozen-launch.json"
    helper.write_new(path, launch)
    spec = {
        "schema": "saea-manual-architecture-analysis-resolution-input-v1",
        "analysis_intent": intent,
        "frozen_launch_binding": helper.raw_pin(path, data),
        "package_relpath": "docs/readiness/resolved-analysis",
    }
    monkeypatch.setattr(helper, "_frozen_identity", lambda root: "a" * 40)
    from speech_aware_evidence_acquisition.rails.reward_links import RewardLinkError
    with pytest.raises((PolicyError, RewardLinkError)):
        helper.resolve_analysis(
            spec,
            repo_root=repo,
            data_root=data,
            frozen_worker_root=repo if fault == "same-worker" else worker,
        )
    assert not (repo / spec["package_relpath"]).exists()


def test_frozen_identity_requires_clean_git_head(tmp_path):
    import subprocess

    repo = tmp_path / "git-worker"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(repo), *args], text=True
        ).strip()

    git("init", "-q")
    p = repo / "tracked.json"
    p.write_text("{}")
    git("add", "tracked.json")
    git(
        "-c",
        "user.name=Synthetic test",
        "-c",
        "user.email=synthetic@example.invalid",
        "commit",
        "-qm",
        "Synthetic fixture",
    )
    assert helper._frozen_identity(repo) == git("rev-parse", "HEAD")
    p.write_text("changed")
    with pytest.raises(PolicyError, match="changed tracked"):
        helper._frozen_identity(repo)


def test_existing_preflight_accepts_manual_intent_and_draft_read(
    tmp_path, monkeypatch, bound  # noqa: F811
):
    authored_root = tmp_path / "authored"
    authored_root.mkdir()
    repo, data, inputs, _, _, _, _ = fixture(authored_root, monkeypatch)
    helper.author(inputs, repo_root=repo, data_root=data)
    package = repo / inputs["package_relpath"]
    recipe = json.loads((package / "analysis-recipe-intent-v1.json").read_text())
    module_spec = importlib.util.spec_from_file_location(
        "registration_checker", SOURCE / "scripts/checks/flight_registration_check.py"
    )
    checker = importlib.util.module_from_spec(module_spec)
    import sys

    monkeypatch.setitem(sys.modules, module_spec.name, checker)
    module_spec.loader.exec_module(checker)
    report = SimpleNamespace(
        run_id="RUN-seed",
        experiment="seed",
        findings=[],
        read_run_id=inputs["read_run_id"],
    )
    # Reuse the established compiled-policy fixture, not an early return or a
    # mocked policy verifier. The actual checker composes a policy-bound cell.
    compiled, binding, policy_repo, policy_data, _, _ = bound
    shutil.copytree(policy_repo / "configs", repo / "configs", dirs_exist_ok=True)
    shutil.copytree(policy_repo / "docs", repo / "docs", dirs_exist_ok=True)
    shutil.copytree(policy_data / "search", data / "search")
    baseline_path = repo / "configs/baseline/seed.json"
    metadata = json.loads(baseline_path.read_text())
    baseline = {
        **compiled,
        **{k: v for k, v in metadata.items() if k != "native_episode"},
    }
    baseline_path.write_bytes(helper.serialized(baseline))
    cell_path = repo / "configs/experiment/seed.json"
    fragment = json.loads(cell_path.read_text())
    cell = fragment["cells"][0]
    cell["system_text_policy_binding"] = binding
    cell_path.write_bytes(helper.serialized(fragment))
    checker._check_system_text_binding(report, cell, baseline, recipe, repo, data)
    checker._check_context_read_scope(
        report, recipe, [{"root countersignature": "DRAFT"}]
    )
    assert not report.findings
    assert checker.read_run_id_of(recipe) == inputs["read_run_id"]
    assert recipe["measurement_profile"] == baseline["system_search_measurement"]
    for invalid in (
        {k: v for k, v in recipe.items() if k != "measurement_profile"},
        {
            **recipe,
            "measurement_profile": {**recipe["measurement_profile"], "queue_depth": 8},
        },
    ):
        refused = SimpleNamespace(run_id="RUN-seed", experiment="seed", findings=[])
        checker._check_system_text_binding(refused, cell, baseline, invalid, repo, data)
        assert len(refused.findings) == 1
        assert "registered measurement profile differs" in refused.findings[0].message


@pytest.mark.parametrize("enabled", [True, False])
def test_process_memory_diagnostics_is_explicitly_forwarded(
    tmp_path, monkeypatch, enabled
):
    repo, data, inputs, _, _, _, _ = fixture(tmp_path, monkeypatch)
    inputs["process_memory_diagnostics"] = enabled
    decision_path = data / inputs["decision_receipt"]["relpath"]
    decision = json.loads(decision_path.read_text())
    decision["resource_policy"]["process_memory_diagnostics"] = enabled
    decision_path.write_bytes(helper.serialized(decision))
    inputs["decision_receipt"] = helper.raw_pin(decision_path, data)
    helper.author(inputs, repo_root=repo, data_root=data)
    queue = json.loads((repo / inputs["package_relpath"] / "queue-v1.json").read_text())
    assert all(row["process_memory_diagnostics"] is enabled for row in queue)


@pytest.mark.parametrize("value", [None, 1, "true"])
def test_invalid_process_memory_diagnostics_refuses_before_mutation(
    tmp_path, monkeypatch, value
):
    repo, data, inputs, _, _, _, _ = fixture(tmp_path, monkeypatch)
    inputs["process_memory_diagnostics"] = value
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    with pytest.raises(PolicyError, match="explicit boolean"):
        helper.author(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("fault", ["floor", "diagnostics"])
def test_decided_resource_policy_mismatch_refuses_before_mutation(
    tmp_path, monkeypatch, fault
):
    repo, data, inputs, _, _, _, _ = fixture(tmp_path, monkeypatch)
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    if fault == "floor":
        inputs["process_guard"]["floor_gib"] = 1
    else:
        inputs["process_memory_diagnostics"] = False
    with pytest.raises(PolicyError, match="decided resource policy"):
        helper.author(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


def test_mismatched_family_measurement_profile_refuses_before_mutation(
    tmp_path, monkeypatch
):
    repo, data, inputs, _, _, _, _ = fixture(tmp_path, monkeypatch)
    path = repo / "configs/baseline/seed-aa.json"
    value = json.loads(path.read_text())
    value["system_search_measurement"]["queue_depth"] = 8
    path.write_bytes(helper.serialized(value))
    receipt_path = repo / inputs["preparation_receipts"]["seed-aa"]["relpath"]
    receipt = json.loads(receipt_path.read_text())
    receipt["config_hash"] = helper.compose(
        repo, "model", "dataset", "seed-aa", "seed-aa"
    ).config_hash
    receipt_path.write_bytes(helper.serialized(receipt))
    inputs["preparation_receipts"]["seed-aa"] = helper.raw_pin(receipt_path, repo)
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    with pytest.raises(PolicyError, match="family measurement profiles differ"):
        helper.author(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists()
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("case", ["selector-without-extent", "root-extent", "spec-extent"])
def test_fixed_roster_metadata_refuses_before_write(tmp_path, monkeypatch, case):
    repo, data, inputs, stage, originals, checks, warm = fixture(tmp_path, monkeypatch)
    if case == "selector-without-extent":
        inputs["architecture_proof"] = helper.reader.FIXED_ROSTER_SELECTOR
    elif case == "root-extent":
        path = data / inputs["decision_receipt"]["relpath"]
        decision = json.loads(path.read_bytes())
        decision["architecture_extent"] = {"count": 100}
        path.write_text(json.dumps(decision), encoding="utf-8")
        inputs["decision_receipt"] = helper.raw_pin(path, data)
    else:
        inputs["architecture_extent"] = {"count": 100}
    with pytest.raises(PolicyError):
        helper.validate_inputs(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists()
    assert not warm and not checks
    for label, raw in originals.items():
        assert (repo / inputs["preparation_receipts"][label]["relpath"]).read_bytes() == raw



def test_optional_map_propagates_exactly_without_changing_unsigned_authority(tmp_path, monkeypatch):
    repo, data, inputs, stage, _, _, _ = fixture(tmp_path, monkeypatch)
    map_path = repo / "identity-map.json"
    helper.write_new(map_path, {"schema": "synthetic map projection seam"})
    map_pin = helper.raw_pin(map_path, repo)
    inputs["execution_identity_map"] = map_pin
    decision_path = data / inputs["decision_receipt"]["relpath"]
    decision = json.loads(decision_path.read_bytes())
    decision["execution_identity_map"] = map_pin
    decision_path.write_bytes(helper.serialized(decision))
    inputs["decision_receipt"] = helper.raw_pin(decision_path, data)
    def mapped(pin, population, pop_pin, extent, *, repo_root):
        assert pin == map_pin
        rows = []
        for label in stage["control_members"] + stage["candidate_members"]:
            c, = helper.load_campaign_cells(repo_root, label)
            d = c.document
            config = helper.compose(repo_root, d["model_fragment"], d["dataset_fragment"], d["baseline_fragment"], label)
            rows.append((label, c, config))
        return rows
    monkeypatch.setattr(pair_api, "_mapped_execution_cells", mapped)
    helper.author(inputs, repo_root=repo, data_root=data)
    package = repo / inputs["package_relpath"]
    for label in stage["control_members"] + stage["candidate_members"]:
        for role in ("generation", "fit"):
            plan = json.loads((package / (label + "-" + role + "-plan-registered-v1.json")).read_bytes())
            assert plan["execution_identity_map"] == map_pin
            assert plan["status"].startswith("PROSPECTIVE UNSIGNED")
    intent = json.loads((package / "manual-architecture-analysis-intent-v1.json").read_bytes())
    assert intent["execution_identity_map"] == intent["analysis_definition"]["execution_identity_map"] == map_pin
    assert not json.loads((package / "root-read-draft-v1.json").read_bytes())["read_authorized"]


def test_root_map_mismatch_refuses_before_authoring_writes(tmp_path, monkeypatch):
    repo, data, inputs, _, _, checks, warm = fixture(tmp_path, monkeypatch)
    inputs["execution_identity_map"] = {"relpath": "missing.json", "sha256": "f" * 64}
    before = {p: p.read_bytes() for p in (repo / "configs/experiment").glob("*.json")}
    with pytest.raises(PolicyError, match="identity maps differ"):
        helper.author(inputs, repo_root=repo, data_root=data)
    assert not (repo / inputs["package_relpath"]).exists() and not warm and not checks
    assert all(p.read_bytes() == raw for p, raw in before.items())


@pytest.mark.parametrize("bad", [None, {}, {"schema": "unknown"}])
def test_additional_contrast_template_refuses_before_authoring_writes(tmp_path, monkeypatch, bad):
    repo, data, s, _, _, checks, warm = fixture(tmp_path, monkeypatch)
    path = repo / s["analysis_template"]["relpath"]
    template = json.loads(path.read_text())
    template["additional_paired_contrasts"] = bad
    path.write_bytes(helper.serialized(template))
    s["analysis_template"] = helper.raw_pin(path, repo)
    with pytest.raises(PolicyError):
        helper.author(s, repo_root=repo, data_root=data)
    assert checks == warm == []
    assert not (repo / s["package_relpath"]).exists()
