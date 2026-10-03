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


def schedule_inputs():
    doc = inputs()
    doc["schema"] = "saea-node-panel-schedule-read-inputs-v1"
    for key, filename in (("recipe", "analysis-recipe-v1.json"), ("registration", "registration-v1.json")):
        name = "docs/readiness/2026-10-03-node-panel-schedule-n20-entry-v1/" + filename
        doc[key] = {"relpath": name, "sha256": hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
    return doc


@pytest.mark.parametrize("schedule", [False, True])
def test_unsigned_real_read_refuses_before_results_or_output(tmp_path, monkeypatch, schedule):
    cli = load_cli()
    doc = schedule_inputs() if schedule else inputs()
    repo = tmp_path / "repo"
    for key in ("recipe", "registration"):
        path = repo / doc[key]["relpath"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / doc[key]["relpath"]).read_bytes())
    gate = cli.CLI.registration_gate()
    run_id = json.loads((ROOT / doc["recipe"]["relpath"]).read_text())["run_ids"]["read"]
    columns = [gate.RUN_COLUMN, "execution profile", "split role", "calls",
               gate.ARTIFACTS_COLUMN, gate.NOTES_COLUMN]
    values = [run_id, "model-free-check", "discovery", "0", doc["recipe"]["relpath"], "DRAFT UNSIGNED"]
    (repo / gate.EXPOSURE_LEDGER).write_text(
        "| " + " | ".join(columns) + " |\n| " + " | ".join(["---"] * len(columns))
        + " |\n| " + " | ".join(values) + " |\n")
    monkeypatch.setattr(cli, "preflight_members", lambda *a, **k: pytest.fail("source opened before READ"))
    with pytest.raises(PolicyError, match="countersigned"):
        cli.run(doc, repo_root=repo, data_root=tmp_path, output=tmp_path / "analysis/read",
                server_log_pin={"relpath": "MUST-NOT-OPEN.log", "sha256": "a" * 64})
    assert not (tmp_path / "analysis/read").exists()


@pytest.mark.parametrize("target", ["optimizer/run", "analysis", "existing"])
def test_output_cannot_overwrite_or_export_to_optimizer(tmp_path, target):
    cli = load_cli()
    output = tmp_path / ("analysis/existing" if target == "existing" else target)
    if target == "existing":
        output.mkdir(parents=True)
    with pytest.raises(PolicyError, match="fresh"):
        cli.run(inputs(), repo_root=ROOT, data_root=tmp_path, output=output)


@pytest.mark.parametrize("changed_artifact", [None, "archive", "flight", "server"])
@pytest.mark.parametrize("with_server", [False, True])
@pytest.mark.parametrize("schedule", [False, True])
def test_complete_orchestration_rechecks_authority_and_metadata_without_contacts(tmp_path, monkeypatch, changed_artifact, schedule, with_server):
    if changed_artifact == "server" and not with_server:
        return
    cli = load_cli()
    doc = schedule_inputs() if schedule else inputs()
    frozen = tmp_path / "frozen"
    doc["frozen_worker"]["path"] = str(frozen)
    original_read_pin, frozen_checks = cli._read_pin, []
    def read_pin(pin, root):
        if Path(root) == frozen:
            frozen_checks.append(pin)
            return b""
        return original_read_pin(pin, root)
    monkeypatch.setattr(cli, "_read_pin", read_pin)
    reg = json.loads((ROOT / doc["registration"]["relpath"]).read_text())
    admission_path = ROOT / Path(doc["registration"]["relpath"]).parent / "root-admission-v1.json"
    admission = json.loads(admission_path.read_text())
    path = tmp_path / reg["admission"]["relpath"]
    path.parent.mkdir(parents=True)
    path.write_bytes(admission_path.read_bytes())
    assert admission["status"] == "decided"
    seen = []
    server_path = tmp_path / "finite-server.log"
    server_path.write_bytes(b"synthetic numeric server log")
    server_pin = {"relpath": server_path.name, "sha256": hashlib.sha256(server_path.read_bytes()).hexdigest()}
    wire_archive = tmp_path / "analysis/prepared-wire.json"
    wire_archive.parent.mkdir(parents=True)
    wire_archive.write_text("{}")
    wire_pin = {"relpath": "analysis/prepared-wire.json", "sha256": hashlib.sha256(wire_archive.read_bytes()).hexdigest()}
    flight_receipt = tmp_path / "flight.json"
    flight_receipt.write_text("{}")
    flight_pin = {"relpath": "flight.json", "sha256": hashlib.sha256(flight_receipt.read_bytes()).hexdigest()}
    authority = {"read_run_id": reg["read_id"], "ledger_row_sha256": "a" * 64}
    def gate(*a, **k):
        seen.append("authority")
        return authority
    def preflight(*a, **k):
        seen.append("preflight")
        assert len(k["sample_ids"]) == 20
        return [{"metadata_pins": []} for _ in range(16 if schedule else 8)]
    def numeric(*a, **k):
        seen.append("numeric")
        row = {"source_bindings": {"flight_receipts": flight_pin}, "experiment_stage_timing": {
            "generation_wall_seconds": 120, "score_stage_seconds": 60,
            "score_batch_seconds": 55, "official_finalize_worker_seconds": 54}, "context_execution": {
            "wire_requests": {"artifact": wire_pin}}}
        if not schedule:
            return {"synthetic-member": row}
        result = {}
        for member in reg["members"]:
            result[member["run_id"]] = copy.deepcopy(row)
            if member["schedule"] == "panel":
                result[member["run_id"]]["context_execution"]["node_panel_timing"] = {"label": member["label"]}
        return result
    def analysis(*a, **k):
        seen.append("analysis")
        assert k["bootstrap_draws"] == 10000 and k["seed"] == 20261003
        assert len(k["roster"]) == 20
        if changed_artifact == "archive":
            wire_archive.write_text('{"changed":true}')
        elif changed_artifact == "flight":
            flight_receipt.write_text('{"changed":true}')
        elif changed_artifact == "server":
            server_path.write_text("changed")
        return {"members": {}, "comparisons": [], "interpretation": "Synthetic complete orchestration only."}
    monkeypatch.setattr(cli.CLI, "require_read_registration", gate)
    monkeypatch.setattr(cli, "preflight_members", preflight)
    monkeypatch.setattr(cli, "read_numeric_members", numeric)
    monkeypatch.setattr(cli, "describe_configurations", analysis)
    if with_server:
        def assemble(numeric_rows, member_rows):
            seen.append("server-contacts")
            assert member_rows == reg["members"]
            return ["synthetic-contact"]
        def slot_history(contacts, raw, *, expected_sha256):
            seen.append("slot-history")
            assert contacts == ["synthetic-contact"] and raw == server_path.read_bytes()
            assert expected_sha256 == server_pin["sha256"]
            return {"contacts": [], "summary": [], "server_assignment_verified": True}
        monkeypatch.setattr(cli, "contacts_from_numeric_members", assemble)
        monkeypatch.setattr(cli, "audit_slot_history", slot_history)
    if schedule:
        def combine(rows):
            assert [r["label"] for r in rows] == [m["label"] for m in reg["members"] if m["schedule"] == "panel"]
            return {"jobs": 160, "barriers_verified": True}
        monkeypatch.setattr(cli, "combine_node_panel_timings", combine)
    out = tmp_path / "analysis/read"
    if changed_artifact:
        with pytest.raises(PolicyError, match="hash mismatch"):
            cli.run(doc, repo_root=ROOT, data_root=tmp_path, output=out,
                    server_log_pin=server_pin if with_server else None)
        assert not out.exists()
        return
    report = cli.run(doc, repo_root=ROOT, data_root=tmp_path, output=out,
                    server_log_pin=server_pin if with_server else None)
    expected = ["authority", "preflight", "numeric"]
    if with_server:
        expected += ["server-contacts", "slot-history"]
        assert report["server_slot_history"]["server_assignment_verified"]
        assert report["server_slot_history"]["server_log"] == server_pin
        assert "Actual slot predecessor" in (out / "README.md").read_text()
    assert seen == expected + ["analysis", "authority", "preflight"]
    assert report["read_authority"] == authority
    assert report["experiment_stage_timing"][reg["members"][0]["run_id"] if schedule else "synthetic-member"]["generation_wall_seconds"] == 120
    rendered = (out / "README.md").read_text()
    assert "Experiment turnaround" in rendered and "120.000" in rendered
    assert "not additive" in rendered and "sample latency" in rendered
    assert frozen_checks == json.loads((ROOT / doc["recipe"]["relpath"]).read_text())["source_checks"]
    if schedule:
        assert report["whole_node_panel_timing"]["jobs"] == 160
    assert (out / "report.json").exists() and (out / "README.md").exists()


def test_render_uses_original_exporter_field_names_and_preserves_missing_values():
    cli = load_cli()
    from test_context_configuration import fixture, describe
    members, pairs, roster = fixture()
    report = describe(members, pairs, roster)
    report["experiment_stage_timing"] = {"unmeasured": {key: None for key in (
        "generation_wall_seconds", "score_stage_seconds", "score_batch_seconds", "official_finalize_worker_seconds")}}
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


@pytest.mark.parametrize("fault", ["wrong-schema", "wrong-read", "missing-owner", "budget", "decision", "undecided", "unadmitted", "missing-timing"])
def test_schedule_gate_rejects_misregistration_before_any_scientific_output(tmp_path, monkeypatch, fault):
    cli = load_cli()
    doc = schedule_inputs()
    recipe_doc = json.loads((ROOT / doc["recipe"]["relpath"]).read_text())
    reg = json.loads((ROOT / doc["registration"]["relpath"]).read_text())
    adm = json.loads((ROOT / Path(doc["registration"]["relpath"]).parent / "root-admission-v1.json").read_text())
    if fault == "wrong-schema":
        reg["schema"] = "saea-context-matrix-n20-registration-v1"
    elif fault == "wrong-read":
        reg["read_id"] = "foreign"
    elif fault == "missing-owner":
        reg["members"].pop()
    elif fault == "budget":
        reg["generation_contact_cap"] += 1
    elif fault == "decision":
        adm["decision_id"] = "foreign"
    elif fault == "undecided":
        adm["status"] = "pending"
    elif fault == "unadmitted":
        adm["eligible_run_ids"] = []
    monkeypatch.setattr(cli, "_document", lambda pin, root: recipe_doc if pin == doc["recipe"] else reg)
    monkeypatch.setattr(cli.CLI, "require_read_registration", lambda *a, **k: {"read_run_id": recipe_doc["run_ids"]["read"]})
    monkeypatch.setattr(cli, "_pinned_json", lambda *a: (adm, "hash"))
    monkeypatch.setattr(cli, "preflight_members", lambda *a, **k: pytest.fail("unqualified family opened"))
    if fault == "missing-timing":
        # No real score/source is read: fail on incomplete synthetic numeric family.
        monkeypatch.setattr(cli, "_read_pin", lambda *a: b"{}")
        original_document = cli._document
        roster = {"items": [{"sample_id": str(i), "utterance_id": str(i), "stratum": "s"} for i in range(20)]}
        monkeypatch.setattr(cli, "_document", lambda pin, root: roster if pin in [doc["roster"], doc["strata"]] else original_document(pin, root))
        monkeypatch.setattr(cli, "preflight_members", lambda *a, **k: [])
        monkeypatch.setattr(cli, "read_numeric_members", lambda *a, **k: {})
    with pytest.raises(PolicyError):
        cli.run(doc, repo_root=ROOT, data_root=tmp_path, output=tmp_path / "analysis/read")
    assert not (tmp_path / "analysis/read").exists()


@pytest.mark.parametrize("option", ["--server-log", "--server-log-sha256"])
def test_cli_refuses_an_unpinned_server_log(tmp_path, monkeypatch, option):
    cli = load_cli()
    monkeypatch.setattr(sys, "argv", ["reader", "--inputs", "unread", "--data-root", str(tmp_path),
        "--output", str(tmp_path / "analysis/result"), option, "only-one-half"])
    with pytest.raises(SystemExit):
        cli.main()


def test_slot_history_render_retains_original_means_and_missingness():
    cli = load_cli()
    row = {"schedule": "panel", "layout": "legacy", "role_id": "solver",
           "successor_kind": "same-node-same-context-different-sample", "contacts": 3,
           "measurements": {k: {"mean_observed": v} for k, v in (
               ("reused_input_tokens", 2500), ("evaluated_input_tokens", None),
               ("prefill_ms", 17.5), ("generation_ms", 40))}}
    rendered = cli.render({"members": {}, "interpretation": "Synthetic rendering only.",
                           "server_slot_history": {"summary": [row]}})
    assert "3 | 2500.000 | unavailable | 17.500 | 40.000" in rendered


@pytest.mark.parametrize("outside", [False, True])
def test_cli_pins_the_preserved_log_under_the_data_root(tmp_path, monkeypatch, capsys, outside):
    cli = load_cli()
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps(inputs()))
    log = tmp_path.parent / "outside.log" if outside else tmp_path / "finite.log"
    monkeypatch.setattr(sys, "argv", ["reader", "--inputs", str(path), "--data-root", str(tmp_path),
        "--output", str(tmp_path / "analysis/result"), "--server-log", str(log),
        "--server-log-sha256", "a" * 64])
    seen = []
    def run(doc, **kwargs):
        seen.append(kwargs["server_log_pin"])
        return {"content_sha256": "b" * 64}
    monkeypatch.setattr(cli, "run", run)
    if outside:
        with pytest.raises(PolicyError, match="escaped"):
            cli.main()
        assert not seen
    else:
        cli.main()
        assert seen == [{"relpath": "finite.log", "sha256": "a" * 64}]
        assert json.loads(capsys.readouterr().out)["scorer_contacts_added"] == 0
