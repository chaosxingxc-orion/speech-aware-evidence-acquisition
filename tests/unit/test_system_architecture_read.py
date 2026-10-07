"""Manual architecture reads remain complete, source-bound and root-only."""

import copy
import json
from types import SimpleNamespace
from pathlib import Path

import pytest
from test_system_text_context_read import fixture as context_fixture
from speech_aware_evidence_acquisition.analysis import (
    system_architecture_read as manual,
)
from speech_aware_evidence_acquisition.rails import (
    architecture_natural_registration as pairs,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)


def fixture(tmp_path):
    d, r, g, o, a, roster, supplement = context_fixture(tmp_path)
    renames = dict(
        zip(g["expected_members"], ["seed", "seed-aa", "review-off", "solver-lookup"])
    )
    for key in ("member_bindings", "expected_members"):
        g[key] = {renames[k]: v for k, v in g[key].items()}
    r["expected_members"] = g["expected_members"]
    labels = list(g["expected_members"])
    d["summaries"] = {renames[k]: v for k, v in d["summaries"].items()}
    for source in d["feedback"]["sources"]:
        source["candidate_id"] = renames[source["candidate_id"]]
    for group in d["feedback"]["groups"]:
        for member in group["members"]:
            member["candidate_id"] = renames[member["candidate_id"]]
    budget = {"family_trajectories": len(labels) * len(r["sample_ids"])}
    binding = {"relpath": "population.json", "sha256": "a" * 64}
    r.update(
        architecture_proof=manual.SELECTOR,
        family_id="manual-comparison",
        learner_export=False,
        experiment_population=binding,
        population_cohort="comparison",
        population_budget=budget,
        score_jobs=len(labels),
        comparison_groups={"architecture": [labels[0], labels[1], labels[2:]]},
        run_ids={"read": "MANUAL-READ"},
        capacity_prerequisite={"registration": "C4"},
        natural_prerequisite={"qualification": "NATURAL"},
        runtime_sample_ids={},
    )
    identities = []
    for i, (label, b) in enumerate(g["member_bindings"].items()):
        runtime = list(reversed(r["sample_ids"]))
        b.update(
            experiment="experiment-" + label,
            source_commit="f" * 40,
            runtime_sample_ids=runtime,
            registered_plans={},
        )
        r["runtime_sample_ids"][label] = runtime
        for role in ("generation", "fit"):
            path = tmp_path / (label + "-" + role + ".json")
            path.write_text(
                json.dumps(
                    {
                        "capacity_prerequisite": r["capacity_prerequisite"],
                        "natural_prerequisite": r["natural_prerequisite"],
                    }
                )
            )
            import hashlib

            b["registered_plans"][role] = {
                "relpath": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        identities.append(
            {
                "member_id": label,
                "model_per_trajectory": 13 if i < 2 else i,
                "execution_config": {"sha256": "pinned-policy" if i < 2 else label},
                "active_roles": ["perception", "solver"]
                + (["reviewer", "planner"] if i < 2 else []),
                "base_bundle_id": b["bundle_id"],
            }
        )
    g.update(
        schema=manual.REGISTRATION,
        architecture_proof=manual.SELECTOR,
        family_id=r["family_id"],
        learner_export=False,
        experiment_population=binding,
        population_cohort="comparison",
        sample_ids=r["sample_ids"],
        population_budget=budget,
        rows_per_member=len(r["sample_ids"]),
        official_score_jobs_cap=len(labels),
        ordered_member_labels=labels,
        read_id="MANUAL-READ",
        source_commit="f" * 40,
    )
    g["registration_sha256"] = content_hash(
        {k: v for k, v in g.items() if k != "registration_sha256"}
    )
    a["read_run_id"] = "MANUAL-READ"
    d.update(
        schema=manual.SCHEMA,
        family_id=r["family_id"],
        read_authority=a,
        registration_sha256=g["registration_sha256"],
    )
    stage = {
        "architecture_members": identities,
        "control_members": labels[:2],
        "candidate_members": labels[2:],
        "sample_ids": r["sample_ids"],
        "N": len(r["sample_ids"]),
        "population_budget": budget,
        "member_generation_contacts_caps": dict.fromkeys(labels, 260),
        "member_fit_endpoints_caps": dict.fromkeys(labels, 1040),
    }
    return (
        d,
        r,
        g,
        {"decision_id": 227, "status": "approved"},
        a,
        roster,
        supplement,
        stage,
    )


def scope_fixture(tmp_path, monkeypatch):
    values = fixture(tmp_path)
    d, r, g, o, a, roster, supplement, stage = values
    monkeypatch.setattr(
        manual, "population_stage_spec", lambda *a, **k: copy.deepcopy(stage)
    )

    def cells(root, experiment):
        label = experiment.removeprefix("experiment-")
        b = g["member_bindings"][label]
        return (
            SimpleNamespace(
                document={
                    "model_fragment": "model",
                    "dataset_fragment": "data",
                    "baseline_fragment": label,
                    "run_id": b["run_id"],
                    "attempt_id": b["attempt_id"],
                }
            ),
        )

    monkeypatch.setattr(manual, "load_campaign_cells", cells)
    monkeypatch.setattr(
        manual,
        "compose",
        lambda root, model, data, label, experiment: SimpleNamespace(
            values={"label": label},
            config_hash=g["member_bindings"][label]["config_hash"],
        ),
    )

    def check(values, *args, **kwargs):
        label = values["label"]
        return {
            "member_id": label,
            "sample_ids": r["sample_ids"],
            "runtime_sample_ids": list(reversed(r["sample_ids"])),
            "generation_cap": 260,
            "fit_cap": 1040,
        }

    monkeypatch.setattr(
        pairs, "require_architecture_n20_registration", check, raising=False
    )
    return values


def validate(v, tmp_path):
    _, r, g, o, a, *_ = v
    return manual.validate_registration(
        r, g, o, a, repo_root=tmp_path, data_root=tmp_path / "data"
    )


def test_configured_family_keeps_five_contrasts_strata_and_no_learner(
    tmp_path, monkeypatch
):
    v = scope_fixture(tmp_path, monkeypatch)
    scope = validate(v, tmp_path)
    d, r, g, _, _, roster, s, _ = v
    evidence = manual.CompleteArchitectureEvidence(canonical(d))
    report = manual.analyze(
        evidence, recipe=r, registration=g, roster=roster, supplement=s, scope=scope
    )
    assert set(report["branches"]) == {"architecture"}
    assert len(report["branches"]["architecture"]["comparisons"]) == 5
    assert (
        report["sample_count"] == len(r["sample_ids"])
        and len(report["per_stratum"]) == 2
    )
    assert scope["review_applicability"]["review-off"]["review_loop"] == "off"
    assert scope["runtime_sample_ids"]["seed"] != r["sample_ids"]
    assert (
        not report["claims_feedback_learning_advantage"]
        and not report["learner_export"]
    )
    assert not hasattr(evidence, "learning_projection")


@pytest.mark.parametrize(
    "fault",
    [
        "selector",
        "mixed",
        "learner",
        "owner",
        "hash",
        "partial",
        "duplicate-run",
        "order",
        "roster",
        "budget",
        "rows",
        "comparators",
        "read",
        "config",
        "bundle",
        "runtime",
        "source",
        "plan-pin",
    ],
)
def test_refuse_registration_drift_before_source_read(tmp_path, monkeypatch, fault):
    v = scope_fixture(tmp_path, monkeypatch)
    _, r, g, o, a, *_ = v
    b = g["member_bindings"]["seed"]
    if fault == "selector":
        r["architecture_proof"] = "natural-four-row-v1"
    elif fault == "mixed":
        r["pilot_registration"] = {}
    elif fault == "learner":
        r["learner_export"] = True
    elif fault == "owner":
        o["status"] = "pending"
    elif fault == "partial":
        g["member_bindings"].pop("seed-aa")
    elif fault == "duplicate-run":
        g["expected_members"]["seed-aa"] = g["expected_members"]["seed"]
    elif fault == "order":
        g["ordered_member_labels"].reverse()
    elif fault == "roster":
        r["sample_ids"] = r["sample_ids"][::-1]
    elif fault == "budget":
        r["population_budget"] = {}
    elif fault == "rows":
        r["required_rows_per_member"] -= 1
    elif fault == "comparators":
        r["comparison_groups"]["architecture"][0] = "solver-lookup"
    elif fault == "read":
        a["read_run_id"] = "OTHER"
    elif fault == "config":
        monkeypatch.setattr(
            manual,
            "compose",
            lambda *a: SimpleNamespace(values={"label": "seed"}, config_hash="WRONG"),
        )
    elif fault == "bundle":
        b["bundle_id"] = "WRONG"
    elif fault == "runtime":
        b["runtime_sample_ids"] = r["sample_ids"]
    elif fault == "source":
        b["source_commit"] = "b" * 40
    elif fault == "plan-pin":
        (tmp_path / b["registered_plans"]["fit"]["relpath"]).write_text("{}")
    if fault != "hash":
        g["registration_sha256"] = content_hash(
            {k: v for k, v in g.items() if k != "registration_sha256"}
        )
    else:
        g["registration_sha256"] = "WRONG"
    with pytest.raises(PolicyError):
        validate(v, tmp_path)


@pytest.mark.parametrize(
    "fault",
    [
        "duplicate-source",
        "missing-source",
        "wrong-config",
        "partial-summary",
        "duplicate-row",
    ],
)
def test_analysis_refuses_incomplete_or_mismatched_saved_evidence(
    tmp_path, monkeypatch, fault
):
    v = scope_fixture(tmp_path, monkeypatch)
    scope = validate(v, tmp_path)
    d, r, g, _, _, roster, s, _ = v
    if fault == "duplicate-source":
        d["feedback"]["sources"][-1] = copy.deepcopy(d["feedback"]["sources"][0])
    elif fault == "missing-source":
        d["feedback"]["sources"].pop()
    elif fault == "wrong-config":
        d["feedback"]["sources"][0]["config_hash"] = "WRONG"
    elif fault == "partial-summary":
        d["summaries"].pop("seed")
    else:
        d["feedback"]["groups"][-1] = copy.deepcopy(d["feedback"]["groups"][0])
    with pytest.raises(PolicyError):
        manual.analyze(
            manual.CompleteArchitectureEvidence(canonical(d)),
            recipe=r,
            registration=g,
            roster=roster,
            supplement=s,
            scope=scope,
        )


def cli_fixture(tmp_path, monkeypatch):
    from test_system_text_pilot_read import cli_fixture as shared_fixture

    prepared = {}

    def make(path):
        v = fixture(path)
        d, r, g, o, a, roster, s, stage = v
        scope = {
            "labels": list(g["expected_members"]),
            "stage": stage,
            "source_commit": g["source_commit"],
            "runtime_sample_ids": r["runtime_sample_ids"],
            "review_applicability": {
                m["member_id"]: {
                    "schema": "saea-review-applicability-v1",
                    "config_sha256": g["member_bindings"][m["member_id"]][
                        "config_hash"
                    ],
                    "review_loop": "on" if "reviewer" in m["active_roles"] else "off",
                }
                for m in stage["architecture_members"]
            },
        }
        prepared.update(scope=scope, recipe=r, registration=g)
        return d, r, g, o, a, roster, s

    cli, repo, data, rpin, spin, calls, d = shared_fixture(
        tmp_path, monkeypatch, fixture_factory=make
    )
    import hashlib

    def rp(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        return {
            "relpath": path.relative_to(repo).as_posix(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    r = json.loads((repo / "recipe.json").read_text())
    r["manual_architecture_registration"] = r.pop("pilot_registration")
    rpin = rp(repo / "recipe.json", r)
    supplement = json.loads((repo / "supplement.json").read_text())
    supplement.update(
        schema="saea-manual-architecture-analysis-supplement-v1",
        recipe=rpin,
        registration=r["manual_architecture_registration"],
        source_code={},
    )
    for key, source in (
        ("reader", Path(cli.__file__)),
        ("analyzer", Path(manual.__file__)),
    ):
        rel = (
            "scripts/analysis/system_text_pilot_read.py"
            if key == "reader"
            else "src/speech_aware_evidence_acquisition/analysis/system_architecture_read.py"
        )
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        supplement["source_code"][key] = {
            "relpath": rel,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        }
    spin = rp(repo / "supplement.json", supplement)
    monkeypatch.setattr(
        manual, "validate_registration", lambda *a, **k: prepared["scope"]
    )
    monkeypatch.setattr(
        manual,
        "read_evidence",
        lambda *a, **k: manual.CompleteArchitectureEvidence(canonical(d)),
    )
    prior_verify = cli.verify_bundle

    def verify(path):
        bundle = prior_verify(path)
        member = next(
            b
            for b in prepared["registration"]["member_bindings"].values()
            if b["run_id"] == bundle.manifest["run_id"]
        )
        bundle.manifest["study_commit"] = member["source_commit"]
        bundle.outputs_rows = [
            {"sample_id": sid} for sid in member["runtime_sample_ids"]
        ]
        return bundle

    monkeypatch.setattr(cli, "verify_bundle", verify)
    return cli, repo, data, rpin, spin, calls, prepared


def test_manual_cli_uses_complete_source_path_and_never_exports(tmp_path, monkeypatch):
    cli, repo, data, rpin, spin, calls, p = cli_fixture(tmp_path, monkeypatch)
    report = cli.run(
        recipe_pin=rpin,
        supplement_pin=spin,
        repo_root=repo,
        data_root=data,
        output=data / "analysis/manual",
    )
    assert len(calls["reuse"]) == len(p["scope"]["labels"])
    assert report["process_diagnostics_status"].startswith("UNAVAILABLE")
    assert not (data / "analysis/manual/learning-feedback.json").exists()
    assert "architecture" in report["branches"] and "B" not in report["branches"]


@pytest.mark.parametrize(
    "fault", ["root-read", "learning", "source", "runtime", "duplicate-score"]
)
def test_manual_cli_refuses_before_derivatives(tmp_path, monkeypatch, fault):
    cli, repo, data, rpin, spin, calls, p = cli_fixture(tmp_path, monkeypatch)
    kwargs = {}
    if fault == "root-read":

        def refuse(*a, **k):
            raise PolicyError("root READ absent")

        monkeypatch.setattr(cli.CLI, "require_read_registration", refuse)
    elif fault == "learning":
        kwargs.update(
            learning_amendment_pin={}, reference_family_path=tmp_path / "reference"
        )
    elif fault in {"source", "runtime"}:
        prior = cli.verify_bundle

        def verify(path):
            bundle = prior(path)
            if fault == "source":
                bundle.manifest["study_commit"] = "WRONG"
            else:
                bundle.outputs_rows[0]["sample_id"] = "WRONG"
            return bundle

        monkeypatch.setattr(cli, "verify_bundle", verify)
    else:
        directory = next(next((data / "runs").iterdir()).iterdir())
        path = directory / "score-jobs.jsonl"
        path.write_text(path.read_text() + "\n" + path.read_text())
    output = data / "analysis/manual"
    with pytest.raises(PolicyError):
        cli.run(
            recipe_pin=rpin,
            supplement_pin=spin,
            repo_root=repo,
            data_root=data,
            output=output,
            **kwargs,
        )
    assert not calls["reuse"] and not output.exists()


def process_fixture(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.analysis.slurp_process_metrics import (
        BOOL_FIELDS,
        aggregate_process_metrics,
    )

    v = scope_fixture(tmp_path, monkeypatch)
    scope = validate(v, tmp_path)
    d, r, g, _, a, roster, s, _ = v
    business = manual.analyze(
        manual.CompleteArchitectureEvidence(canonical(d)),
        recipe=r,
        registration=g,
        roster=roster,
        supplement=s,
        scope=scope,
    )
    sources = {
        label: {
            "manifest": {"path": "manifest-" + label, "sha256": "a" * 64},
            "score_result": {"path": "score-" + label, "sha256": "b" * 64},
            "attempt_id": g["member_bindings"][label]["attempt_id"],
        }
        for label in scope["labels"]
    }
    process = {
        "read_id": r["run_ids"]["read"],
        "read_authority": a,
        "source_bindings": copy.deepcopy(sources),
        "members": {},
    }
    timing = {}
    for label in scope["labels"]:
        binding = scope["review_applicability"][label]
        enabled = binding["review_loop"] == "on"
        rows = [
            dict.fromkeys(BOOL_FIELDS, None)
            | {
                "sample_id": sid,
                "scenario": roster[sid]["stratum"],
                "review_applicable": enabled,
                "revised": False,
            }
            for sid in scope["runtime_sample_ids"][label]
        ]
        report = aggregate_process_metrics(rows)
        report.update(
            rows=rows,
            review_applicability=binding,
            role_counts={"reviewer_contacts": 0},
            recall_status="unavailable-until-actual-source-projection",
            delivery_stages={},
            source={
                "config_hash": binding["config_sha256"],
                "run_id": r["expected_members"][label],
                "attempt_id": sources[label]["attempt_id"],
                "official_score_result_sha256": "b" * 64,
                "ordered_sample_ids_sha256": content_hash(
                    scope["runtime_sample_ids"][label]
                ),
            },
        )
        process["members"][label] = report
        timing[label] = {"completed_samples": len(r["sample_ids"]), "failed_samples": 0}
    return dict(
        recipe=r,
        business=business,
        process=process,
        timing=timing,
        scope=scope,
        score_sources=sources,
    )


def test_disabled_reviewer_metrics_are_inapplicable_without_fake_missingness(
    tmp_path, monkeypatch
):
    values = process_fixture(tmp_path, monkeypatch)
    report = manual.combine_process(**values)
    for label in ("review-off", "solver-lookup"):
        metric = report["process"][label]["metrics"]["review_valid"]
        assert metric["applicability"] == "not-applicable-by-design"
        assert metric["unknown"] == metric["denominator"] == 0
        assert metric["excluded_by_design"] == len(values["recipe"]["sample_ids"])
    assert not report["learner_exported"] and not report["adoption_decided"]


@pytest.mark.parametrize(
    "fault",
    [
        "read",
        "score",
        "config",
        "runtime",
        "applicability",
        "metric",
        "partial",
        "timing",
    ],
)
def test_process_combination_refuses_source_or_applicability_drift(
    tmp_path, monkeypatch, fault
):
    values = process_fixture(tmp_path, monkeypatch)
    p = values["process"]
    off = p["members"]["review-off"]
    if fault == "read":
        p["read_authority"] = {}
    elif fault == "score":
        off["source"]["official_score_result_sha256"] = "WRONG"
    elif fault == "config":
        off["source"]["config_hash"] = "WRONG"
    elif fault == "runtime":
        off["rows"].reverse()
    elif fault == "applicability":
        off["review_applicability"] = {
            **off["review_applicability"],
            "review_loop": "on",
        }
    elif fault == "metric":
        off["metrics"]["review_valid"]["unknown"] = 1
    elif fault == "partial":
        p["members"].pop("seed-aa")
    else:
        values["timing"]["seed"]["completed_samples"] -= 1
    with pytest.raises((PolicyError, ValueError)):
        manual.combine_process(**values)


def test_actual_pinned_population_derives_full_family_bounds():
    repo = Path(__file__).resolve().parents[2]
    draft = json.loads(
        (
            repo
            / "docs/readiness/2026-10-07-slurp-simple-consumption-n20-preparation-v3/analysis-recipe-draft-v1.json"
        ).read_text()
    )
    stage = manual.population_stage_spec(
        draft["experiment_population"],
        repo_root=repo,
        cohort_id=draft["population_cohort"],
        allow_architecture=True,
    )
    members = stage["architecture_members"]
    assert [m["member_id"] for m in members] == stage["control_members"] + stage[
        "candidate_members"
    ]
    assert stage["population_budget"]["family_trajectories"] == len(members) * len(
        stage["sample_ids"]
    )
    assert (
        sum(stage["member_generation_contacts_caps"].values())
        == stage["population_budget"]["generation_contacts_cap"]
    )
    assert (
        sum(stage["member_fit_endpoints_caps"].values())
        == stage["population_budget"]["fit_endpoints_cap"]
    )
    assert draft["comparison_groups"] == {
        "architecture": [*stage["control_members"], stage["candidate_members"]]
    }


def test_manual_process_pin_drift_refuses_before_any_source_derivative(
    tmp_path, monkeypatch
):
    import hashlib

    cli, repo, data, rpin, spin, calls, _ = cli_fixture(tmp_path, monkeypatch)
    path = repo / "supplement.json"
    supplement = json.loads(path.read_text())
    supplement["process_diagnostics"] = {"relpath": "wrong.json", "sha256": "a" * 64}
    path.write_text(json.dumps(supplement))
    spin["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    output = data / "analysis/manual"
    with pytest.raises(PolicyError, match="process binding"):
        cli.run(
            recipe_pin=rpin,
            supplement_pin=spin,
            repo_root=repo,
            data_root=data,
            output=output,
        )
    assert not calls["verify"] and not calls["reuse"] and not output.exists()


def test_manual_legacy_selector_cannot_downgrade_configured_extent(tmp_path, monkeypatch):
    values = scope_fixture(tmp_path, monkeypatch)
    registration = values[2]
    monkeypatch.setattr(manual, "compose", lambda root, model, data, label, experiment:
        SimpleNamespace(values={"label": label, "architecture_extent": {"count": 100}},
                        config_hash=registration["member_bindings"][label]["config_hash"]))
    with pytest.raises(PolicyError, match="configured extent"):
        validate(values, tmp_path)
