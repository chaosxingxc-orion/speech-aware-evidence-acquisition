"""Six-system reports use the shared complete-family statistics and READ boundary."""

import importlib.util
import json
from pathlib import Path
import pytest
from speech_aware_evidence_acquisition.rails.system_text_policy import (
    PolicyError,
    canonical,
)
from speech_aware_evidence_acquisition.rails.system_text_feedback import (
    CompleteSystemFeedback,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from test_system_text_pilot_read import fixture as pilot_fixture
from test_system_search_measurement import profile, timing


def fixture(tmp_path):
    d, recipe, reg, _, auth, roster, supplement = pilot_fixture(tmp_path)
    names = dict(
        zip(
            [
                "L-parent",
                "L-parent-aa",
                "L-candidate-1",
                "L-candidate-2",
                "B-candidate-1",
                "B-candidate-2",
            ],
            ["seed", "seed-aa", "a", "b", "c", "d"],
        )
    )
    reg["member_bindings"] = {
        names[c]: b for c, b in reg["member_bindings"].items() if c in names
    }
    reg["expected_members"] = {
        c: b["run_id"] for c, b in reg["member_bindings"].items()
    }
    for c, b in reg["member_bindings"].items():
        b["bundle_id"] = content_hash("seed" if c == "seed-aa" else c)
    recipe["family_id"] = reg["family_id"] = d["family_id"] = "context-initial4-n20"
    reg["registration_sha256"] = content_hash(reg)
    d["registration_sha256"] = reg["registration_sha256"]
    d["schema"] = "saea-context-learning-feedback-v1"
    recipe["expected_members"] = reg["expected_members"]
    d["summaries"] = {names[c]: v for c, v in d["summaries"].items() if c in names}
    d["feedback"]["sources"] = [
        {**s, "candidate_id": names[s["candidate_id"]]}
        for s in d["feedback"]["sources"]
        if s["candidate_id"] in names
    ]
    for g in d["feedback"]["groups"]:
        g["members"] = [
            {**m, "candidate_id": names[m["candidate_id"]]}
            for m in g["members"]
            if m["candidate_id"] in names
        ]
    p = profile()
    d["measurement_profile"] = recipe["measurement_profile"] = reg[
        "measurement_profile"
    ] = p
    for i, (cid, s) in enumerate(d["summaries"].items()):
        s["sample_timing"] = timing(recipe["sample_ids"], seconds=10 + i)
        s["timing_session_sha256"] = "a" * 64
    protocol = {
        "candidate_members": ["a", "b", "c", "d"],
        "control_members": ["seed", "seed-aa"],
    }
    return d, recipe, reg, protocol, roster, supplement


def test_context_report_all_candidates_controls_paired_cost_and_history(tmp_path):
    from speech_aware_evidence_acquisition.analysis.system_context_read import analyze

    d, r, g, p, roster, s = fixture(tmp_path)
    report = analyze(
        CompleteSystemFeedback(canonical(d)),
        recipe=r,
        registration=g,
        protocol=p,
        roster=roster,
        supplement=s,
    )
    assert len(report["branches"]["context"]["comparisons"]) == 9
    assert set(report["official_summaries"]) == {"seed", "seed-aa", "a", "b", "c", "d"}
    assert report["sample_count"] == 20 and report["cluster_count"] == 10
    assert len(report["per_stratum"]) == 2
    assert len(report["measured_rows"]) == 6
    assert all(x["candidate_id"] != "seed-aa" for x in report["measured_frontier"])
    assert report["automatic_expansion"] is False
    assert report["optimizer_feedback_allowed"] is False
    assert report["branches"]["context"]["comparisons"]["a-minus-parent"][
        "whole_answer_exact_changes"
    ]["counts"]
    assert report["contacts_added"] == {"model": 0, "scorer": 0}


@pytest.mark.parametrize(
    "fault", ["source", "summary", "read", "row", "profile", "cohort"]
)
def test_context_report_rejects_mixed_or_partial_evidence(tmp_path, fault):
    from speech_aware_evidence_acquisition.analysis.system_context_read import analyze

    d, r, g, p, roster, s = fixture(tmp_path)
    if fault == "source":
        d["feedback"]["sources"][0]["config_hash"] = "f" * 64
    elif fault == "summary":
        d["summaries"].pop("a")
    elif fault == "read":
        d["read_authority"]["read_run_id"] = "other"
    elif fault == "row":
        d["feedback"]["groups"][0]["members"].pop()
    elif fault == "profile":
        d["measurement_profile"] = {}
    elif fault == "cohort":
        d["feedback"]["groups"].reverse()
    with pytest.raises(PolicyError):
        analyze(
            CompleteSystemFeedback(canonical(d)),
            recipe=r,
            registration=g,
            protocol=p,
            roster=roster,
            supplement=s,
        )


def cli_module():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "context_read_cli", root / "scripts/analysis/system_text_pilot_read.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_context_documents_and_unsigned_cli_fail_before_sources(tmp_path, monkeypatch):
    from test_system_context_learning import setup, pin

    setup(tmp_path, monkeypatch)
    # Read only the synthetic prospective files; no trajectory source is accessed.
    recipe = json.loads((tmp_path / "recipe.json").read_text())
    rp = pin(tmp_path, "recipe.json", recipe)
    sp = pin(
        tmp_path,
        "supplement.json",
        {
            "schema": "saea-context-learning-analysis-supplement-v1",
            "recipe": rp,
            "registration": recipe["context_learning_registration"],
        },
    )
    cli = cli_module()
    loaded = cli.load_documents(rp, sp, tmp_path)
    assert loaded[2]["schema"] == "saea-context-learning-protocol-v1"

    def refuse(*a, **kw):
        raise PolicyError("READ unsigned")

    monkeypatch.setattr(cli.CLI, "require_read_registration", refuse)
    monkeypatch.setattr(
        cli, "source_bindings", lambda *a: pytest.fail("source opened before READ")
    )
    with pytest.raises(PolicyError, match="unsigned"):
        cli.run(
            recipe_pin=rp,
            supplement_pin=sp,
            repo_root=tmp_path,
            data_root=tmp_path / "data",
            output=tmp_path / "data/analysis/new",
        )
    assert not (tmp_path / "data/analysis/new").exists()


@pytest.mark.parametrize(
    "fault", [None, "missing", "failed", "seal", "scope", "learning"]
)
def test_context_cli_saved_score_join_and_complete_rejections(
    tmp_path, monkeypatch, fault
):
    from types import SimpleNamespace
    from test_system_text_pilot_read import cli_fixture

    store = {}

    def factory(path):
        d, recipe, reg, protocol, roster, supplement = fixture(path)
        store.update(
            recipe=recipe, registration=reg, protocol=protocol, supplement=supplement
        )
        return d, recipe, reg, protocol, d["read_authority"], roster, supplement

    cli, repo, data, rp, sp, calls, d = cli_fixture(tmp_path, monkeypatch, factory)
    recipe, reg, protocol, supplement = (
        store[k] for k in ("recipe", "registration", "protocol", "supplement")
    )
    recipe["context_learning_registration"] = {
        "relpath": "registration.json",
        "sha256": "a" * 64,
    }
    monkeypatch.setattr(
        cli, "load_documents", lambda *a: (recipe, reg, protocol, supplement)
    )

    def scope(*a, **kw):
        if fault == "scope":
            raise PolicyError("wrong scope")

    monkeypatch.setattr(cli.context_learning, "_validate_scope", scope)

    def qualified(*a, **kw):
        assert (
            len(calls["verify"]) == len(calls["reuse"]) == len(calls["artifacts"]) == 6
        )
        return (d,)

    monkeypatch.setattr(cli.context_learning, "_qualified_feedback", qualified)
    b = reg["member_bindings"]["d"]
    job_dir = data / "runs" / b["run_id"] / b["attempt_id"]
    if fault == "missing":
        (job_dir / "score-jobs.jsonl").unlink()
    if fault == "failed":
        path = job_dir / "score-batch/batch-summary.json"
        doc = json.loads(path.read_text())
        doc["failed"] = 1
        path.write_text(json.dumps(doc))
    if fault == "seal":
        monkeypatch.setattr(
            cli, "verify_bundle", lambda *a: SimpleNamespace(attempt_state="OPENED")
        )
    kwargs = dict(
        recipe_pin=rp,
        supplement_pin=sp,
        repo_root=repo,
        data_root=data,
        output=data / "analysis/context",
    )
    if fault == "learning":
        kwargs.update(
            learning_amendment_pin={}, reference_family_path=data / "old.json"
        )
    if fault:
        with pytest.raises((PolicyError, FileNotFoundError)):
            cli.run(**kwargs)
        assert not calls["reuse"] and not calls["artifacts"]
    else:
        report = cli.run(**kwargs)
        assert len(report["measured_rows"]) == 6
        saved = json.loads((data / "analysis/context/family.json").read_text())
        assert len(saved["bindings"]) == 6
        assert not (data / "analysis/context/learning-feedback.json").exists()


@pytest.mark.parametrize("fault", ["code", "registration", "mixed"])
def test_context_pinned_documents_refuse_changed_sources(tmp_path, monkeypatch, fault):
    from test_system_context_learning import setup, pin

    setup(tmp_path, monkeypatch)
    recipe = json.loads((tmp_path / "recipe.json").read_text())
    if fault == "mixed":
        recipe["pilot_registration"] = {}
    rp = pin(tmp_path, "recipe.json", recipe)
    cp = pin(tmp_path, "reader.py", {"code": "original"})
    supplement = {
        "schema": "saea-context-learning-analysis-supplement-v1",
        "recipe": rp,
        "registration": recipe["context_learning_registration"],
        "source_code": {"reader": cp},
    }
    if fault == "code":
        (tmp_path / "reader.py").write_text("changed")
    if fault == "registration":
        supplement["registration"] = {}
    sp = pin(tmp_path, "supplement.json", supplement)
    with pytest.raises(PolicyError):
        cli_module().load_documents(rp, sp, tmp_path)
