"""Resolve the exact engineering family without masquerading as L/B feedback."""
import copy
import json
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.system_search_stage import recipe_family_identity
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError

ROOT = Path(__file__).resolve().parents[2]
RECIPE = "docs/readiness/2026-10-03-context-matrix-n20-entry-v1/analysis-recipe-v1.json"


def recipe():
    return json.loads((ROOT / RECIPE).read_text())


def test_exact_registered_context_family_is_not_learning_branch_aliases():
    family, members = recipe_family_identity(recipe())
    assert family == "context-matrix-n20"
    assert len(members) == 8
    assert members["before-speech-role-aa"] == "SAEA-SLURP-CONTEXT-MATRIX-N20-BEFORE-SPEECH-ROLE-AA-V1"
    assert not any(name.startswith(("L-", "B-")) for name in members)


@pytest.mark.parametrize("fault", ["other_read", "missing", "duplicate", "extra", "alias", "learning", "swap", "stage"])
def test_matrix_read_cannot_authorize_another_family(fault):
    doc = recipe()
    if fault == "other_read":
        doc["run_ids"]["read"] = "SAEA-OTHER-READ-V1"
    elif fault == "missing":
        doc["comparisons"].pop()
    elif fault == "duplicate":
        doc["comparisons"][1] = copy.deepcopy(doc["comparisons"][0])
    elif fault == "extra":
        doc["complete_family"].append("extra")
    elif fault == "alias":
        doc["family_id"] = "update-2"
    elif fault == "learning":
        doc["optimizer_export"] = True
    elif fault == "swap":
        doc["comparisons"][0]["primary"], doc["comparisons"][0]["aa"] = (
            doc["comparisons"][0]["aa"], doc["comparisons"][0]["primary"])
    elif fault == "stage":
        doc["stage"] = "update-2"
    with pytest.raises(PolicyError):
        recipe_family_identity(doc)


def load_cli():
    path = ROOT / "scripts/analysis/context_matrix_read.py"
    spec = importlib.util.spec_from_file_location("_context_matrix_test_cli", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inputs():
    def pin(name):
        return {"relpath": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
    return {"schema": "saea-context-matrix-read-inputs-v1", "recipe": pin(RECIPE),
            "registration": pin("docs/readiness/2026-10-03-context-matrix-n20-entry-v1/registration-v1.json"),
            "roster": pin("docs/receipts/rosters/slurp-system-text-pilot20-owner220-analysis-v1.json"),
            "strata": pin("docs/receipts/rosters/slurp-evo-fold-a-v2.json"),
            "frozen_worker": {"path": "/home/chao/saea-worktrees/codex-context-matrix-n20-v1",
                              "commit": "d8456cefecafc8a7da681e06bfc06f141e994972"}}


def test_unsigned_real_read_refuses_before_results_or_output(tmp_path, monkeypatch):
    cli = load_cli()
    doc = inputs()
    repo = tmp_path / "repo"
    for key in ("recipe", "registration"):
        path = repo / doc[key]["relpath"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / doc[key]["relpath"]).read_bytes())
    gate = cli.CLI.registration_gate()
    run_id = recipe()["run_ids"]["read"]
    columns = [gate.RUN_COLUMN, "execution profile", "split role", "calls",
               gate.ARTIFACTS_COLUMN, gate.NOTES_COLUMN]
    values = [run_id, "model-free-check", "discovery", "0", RECIPE, "DRAFT UNSIGNED"]
    (repo / gate.EXPOSURE_LEDGER).write_text(
        "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns))
        + " |\n| " + " | ".join(values) + " |\n")
    monkeypatch.setattr(cli, "preflight_members", lambda *a, **k: pytest.fail("source opened before READ"))
    with pytest.raises(PolicyError, match="countersigned"):
        cli.run(doc, repo_root=repo, data_root=tmp_path, output=tmp_path / "analysis/read")
    assert not (tmp_path / "analysis/read").exists()


@pytest.mark.parametrize("target", ["optimizer/run", "analysis", "existing"])
def test_output_cannot_overwrite_or_export_to_optimizer(tmp_path, target):
    cli = load_cli()
    output = tmp_path / ("analysis/existing" if target == "existing" else target)
    if target == "existing":
        output.mkdir(parents=True)
    with pytest.raises(PolicyError, match="fresh"):
        cli.run(inputs(), repo_root=ROOT, data_root=tmp_path, output=output)


def test_complete_orchestration_rechecks_authority_and_metadata_without_contacts(tmp_path, monkeypatch):
    cli = load_cli()
    doc = inputs()
    doc["frozen_worker"]["path"] = str(ROOT)
    reg = json.loads((ROOT / doc["registration"]["relpath"]).read_text())
    admission = json.loads(
        (ROOT / "docs/readiness/2026-10-03-context-matrix-n20-entry-v1/root-admission-v1.json").read_text())
    path = tmp_path / reg["admission"]["relpath"]
    path.parent.mkdir(parents=True)
    path.write_bytes((ROOT / "docs/readiness/2026-10-03-context-matrix-n20-entry-v1/root-admission-v1.json").read_bytes())
    assert admission["status"] == "decided"
    seen = []
    authority = {"read_run_id": reg["read_id"], "ledger_row_sha256": "a" * 64}
    def gate(*a, **k):
        seen.append("authority")
        return authority
    def preflight(*a, **k):
        seen.append("preflight")
        assert len(k["sample_ids"]) == 20
        return [{"metadata_pins": []} for _ in range(8)]
    def numeric(*a, **k):
        seen.append("numeric")
        return {}
    def analysis(*a, **k):
        seen.append("analysis")
        assert k["bootstrap_draws"] == 10000 and k["seed"] == 20261003
        assert len(k["roster"]) == 20
        return {"members": {}, "comparisons": [], "interpretation": "Synthetic complete orchestration only."}
    monkeypatch.setattr(cli.CLI, "require_read_registration", gate)
    monkeypatch.setattr(cli, "preflight_members", preflight)
    monkeypatch.setattr(cli, "read_numeric_members", numeric)
    monkeypatch.setattr(cli, "describe_configurations", analysis)
    out = tmp_path / "analysis/read"
    report = cli.run(doc, repo_root=ROOT, data_root=tmp_path, output=out)
    assert seen == ["authority", "preflight", "numeric", "analysis", "authority", "preflight"]
    assert report["read_authority"] == authority
    assert (out / "report.json").exists() and (out / "README.md").exists()


def test_render_uses_original_exporter_field_names_and_preserves_missing_values():
    cli = load_cli()
    from test_context_configuration import fixture, describe
    members, pairs, roster = fixture()
    report = describe(members, pairs, roster)
    for row in report["members"].values():
        row["node_timing"] = {"by_role": {"solver": {"contacts": 4, "reused_input_fraction": None,
            "metrics": {key: {"mean_observed": value} for key, value in [
                ("client_transport_ms", 5000.0), ("prefill_ms", None), ("generation_ms", 1200.0)]}}}}
    text = cli.render(report)
    assert "5000.000 | unavailable | 1200.000 | unavailable" in text
    assert "90.000%" in text and "11.000 | 20.000 | 8.000" in text


def test_cli_main_preserves_exact_supplied_input_identity(tmp_path, monkeypatch, capsys):
    cli = load_cli()
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(inputs()))
    monkeypatch.setattr(sys, "argv", ["reader", "--inputs", str(path), "--data-root", str(tmp_path),
                                     "--output", str(tmp_path / "analysis/result")])
    monkeypatch.setattr(cli, "run", lambda doc, **kwargs: {"content_sha256": "a" * 64})
    cli.main()
    result = json.loads(capsys.readouterr().out)
    assert result["inputs_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0
