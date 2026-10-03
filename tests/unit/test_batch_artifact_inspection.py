"""Exercise scoreless artifact acceptance through the unattended driver's CLI."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from test_bundle import bundled_repo, _finalized_artifact_bundle  # noqa: F401

SCRIPT = Path(__file__).parents[2] / "scripts/flights/batch/batch_inspect.py"


def inspect(world, kind=None, mode="arm"):
    args = [sys.executable, str(SCRIPT), str(world["data"]), world["run"], world["attempt"],
            mode, str(world["rows"]), "1", "1", world["commit"]]
    if kind is not None:
        args += ["--result-kind", kind]
    if os.environ.get("SAEA_INSPECT_COVERAGE") == "1":
        args[1:1] = ["-m", "coverage", "run", "--parallel-mode", "--branch"]
    result = subprocess.run(args, capture_output=True, text=True)
    return result


@pytest.fixture
def task_world(tmp_path):
    data = tmp_path / "data"
    run, attempt = "fixture-run", "fixture-attempt"
    run_dir = data / "runs" / run / attempt
    run_dir.mkdir(parents=True)
    att_path = data / "attempts" / run / (attempt + ".json")
    att_path.parent.mkdir(parents=True)
    att_path.write_text(json.dumps({"state": "FINALIZED", "actual": {"calls": 1}}))
    manifest_path = run_dir / "fixture.run-manifest.json"
    manifest = {"status": "COMPLETED", "study_commit": "a"*40, "study_repo_dirt": [],
                "exposure_run_id": run, "plan": {"attempt_id": attempt},
                "scorers": ["slurp-slu-official-train"], "scores": {"sha256": "b"*64}}
    manifest_path.write_text(json.dumps(manifest))
    (run_dir / "fixture.outputs.jsonl").write_text(json.dumps({"sample_id": "s1", "text": "PRIVATE_ANSWER"}) + "\n")
    (run_dir / "score-jobs.jsonl").write_text(json.dumps({"job_id": attempt}) + "\n")
    return {"data": data, "run": run, "attempt": attempt, "rows": 1, "commit": "a"*40,
            "manifest": manifest, "manifest_path": manifest_path, "run_dir": run_dir, "attempt_path": att_path}


@pytest.fixture
def artifact_world(synthetic_world, bundled_repo, tmp_path, monkeypatch):  # noqa: F811
    run, attempt = "SAEA-E-000-artifact", "attempt-artifact"
    destination = synthetic_world.data_root / "runs" / run / attempt
    path, plan = _finalized_artifact_bundle(synthetic_world, bundled_repo, tmp_path, monkeypatch,
                                           run_dir_name=str(destination))
    manifest = json.loads(path.read_text())
    return {"data": synthetic_world.data_root, "run": run, "attempt": attempt,
            "rows": len(manifest["split"]["ids"]), "commit": manifest["study_commit"],
            "manifest": manifest, "manifest_path": path, "run_dir": path.parent,
            "attempt_path": synthetic_world.data_root / "attempts" / run / (attempt + ".json"),
            "plan": plan}


@pytest.mark.parametrize("mode", ["smoke", "arm"])
def test_finalized_artifact_passes_without_a_scoring_job(artifact_world, mode):
    w = artifact_world
    before = {p: p.read_bytes() for p in w["run_dir"].iterdir() if p.is_file()}
    result = inspect(w, "artifact", mode)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["pass"] and report["score_jobs"] == report["expected_score_jobs"] == 0
    assert report["result_kind"] == "artifact" and report["bundle_verified"]
    assert "token tags" not in result.stdout
    assert {p: p.read_bytes() for p in before} == before
    assert not (w["run_dir"] / "score-jobs.jsonl").exists()


@pytest.mark.parametrize("kind", [None, "task-answer"])
def test_legacy_task_still_requires_exactly_one_score_job(task_world, kind):
    w = task_world
    result = inspect(w, kind)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PRIVATE_ANSWER" not in result.stdout
    (w["run_dir"] / "score-jobs.jsonl").unlink()
    result = inspect(w, kind)
    assert result.returncode == 2
    assert "score jobs 0 (expected 1)" in result.stdout


def test_artifact_cannot_be_implicitly_treated_as_task_answer(artifact_world):
    result = inspect(artifact_world)
    assert result.returncode == 2 and "result kind" in result.stdout


def test_task_cannot_bypass_scoring_by_requesting_artifact_inspection(task_world):
    (task_world["run_dir"] / "score-jobs.jsonl").unlink()
    result = inspect(task_world, "artifact")
    assert result.returncode == 2 and "result kind" in result.stdout


@pytest.mark.parametrize("mutation", [
    "score-job", "scorers", "score-binding", "unfinalized", "aborted", "raw-output",
    "wrong-run", "wrong-attempt", "ambiguous-manifest", "dirty", "wrong-commit",
])
def test_invalid_artifact_refuses_without_score_replay(artifact_world, mutation):
    w = artifact_world
    m = w["manifest"]
    if mutation == "score-job":
        (w["run_dir"] / "score-jobs.jsonl").write_text("{}\n")
    elif mutation == "scorers":
        m["scorers"] = ["cost"]
    elif mutation == "score-binding":
        m["scores"] = {"path": "forbidden", "sha256": "f"*64}
    elif mutation in {"unfinalized", "aborted"}:
        attempt = json.loads(w["attempt_path"].read_text())
        attempt["state"] = "OPENED" if mutation == "unfinalized" else "ABORTED"
        w["attempt_path"].write_text(json.dumps(attempt))
    elif mutation == "raw-output":
        outputs = Path(m["outputs"]["path"])
        outputs.write_text(outputs.read_text().replace("token tags", "PRIVATE_TAMPERED"))
    elif mutation == "wrong-run":
        m["exposure_run_id"] = "another-run"
    elif mutation == "wrong-attempt":
        m["plan"]["attempt_id"] = "another-attempt"
    elif mutation == "ambiguous-manifest":
        (w["run_dir"] / "extra.run-manifest.json").write_text(json.dumps(m))
    elif mutation == "dirty":
        m["study_repo_dirt"] = ["src/changed.py"]
    elif mutation == "wrong-commit":
        m["study_commit"] = "f"*40
    w["manifest_path"].write_text(json.dumps(m))
    result = inspect(w, "artifact")
    assert result.returncode == 2, result.stdout + result.stderr
    assert not json.loads(result.stdout)["pass"]
    assert "PRIVATE_TAMPERED" not in result.stdout
    assert len(list(w["run_dir"].glob("*scores*"))) == 0


def test_invalid_mode_and_result_kind_are_cli_errors(task_world):
    assert inspect(task_world, "unknown").returncode == 2
    assert inspect(task_world, "task-answer", mode="unknown").returncode == 2


def test_historical_task_smoke_can_remain_opened_and_unscored(task_world):
    w = task_world
    w["attempt_path"].write_text(json.dumps({"state": "OPENED"}))
    (w["run_dir"] / "score-jobs.jsonl").unlink()
    result = inspect(w, mode="smoke")
    assert result.returncode == 0 and json.loads(result.stdout)["expected_score_jobs"] is None


@pytest.mark.parametrize("mutation", ["missing-attempt", "missing-manifest", "missing-rows", "over-budget", "tool-cost", "tool-schema"])
def test_legacy_structural_failures_still_stop(task_world, mutation):
    w = task_world
    if mutation == "missing-attempt":
        w["attempt_path"].unlink()
    elif mutation == "missing-manifest":
        w["manifest_path"].unlink()
    elif mutation == "missing-rows":
        (w["run_dir"] / "fixture.outputs.jsonl").unlink()
    elif mutation == "over-budget":
        row = {"sample_id": "s1", "native_episode_receipt": {
            "contact_count": 2, "terminal_disposition": {"reason": "finite_completion"},
            "finite_completion": {"used": True}, "dispositions": {"react_exhaustion": ["one"]}}}
        (w["run_dir"] / "fixture.outputs.jsonl").write_text(json.dumps(row) + "\n")
    elif mutation == "tool-cost":
        (w["run_dir"] / "fixture.generation-manifest.json").write_text(json.dumps({"cost": {"tool_calls": 1}}))
    else:
        events = [{"channel": "EVENT", "payload": {}},
                  {"channel": "MODEL_REQUEST", "payload": {"payload": {"tool_schemas": [{"name": "unexpected"}]}}}]
        (w["run_dir"] / "fixture.trace.jsonl").write_text("".join(json.dumps(e)+"\n" for e in events))
    result = inspect(w)
    assert result.returncode == (3 if mutation.startswith("missing-") and mutation != "missing-rows" else 2)
    assert "PRIVATE_ANSWER" not in result.stdout


def test_artifact_metadata_uses_verified_outputs_not_first_glob_match(artifact_world):
    w = artifact_world
    outputs = Path(w["manifest"]["outputs"]["path"])
    original = outputs.read_bytes()
    outputs.unlink()
    (w["run_dir"] / "unrelated.outputs.jsonl").write_text(json.dumps({"sample_id": "foreign"}) + "\n")
    outputs.write_bytes(original)
    result = inspect(w, "artifact")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["rows"] == w["rows"]
    assert report["sha256_outputs"] == w["manifest"]["outputs"]["sha256"]
    w["rows"] = 1
    assert inspect(w, "artifact").returncode == 2


@pytest.fixture
def worker_world(synthetic_world, bundled_repo, tmp_path):  # noqa: F811
    from test_bundle import _run_completed
    from speech_aware_evidence_acquisition.core.flight.scoring import seal_scoring_inputs
    from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts, write_flight_receipts

    run, attempt = "SAEA-E-000-worker", "attempt-worker"
    directory = synthetic_world.data_root / "runs" / run / attempt
    path, _, _, _ = _run_completed(synthetic_world, bundled_repo, tmp_path,
        run_id=run, attempt_id=attempt, run_dir_name=str(directory))
    manifest = json.loads(path.read_text())
    seal = seal_scoring_inputs(path, run_id=run, attempt_id=attempt, ledger_cells={})
    seal["manifest_path"] = str(path)
    receipts = FlightReceipts(run, attempt)
    for stage in ("preflight", "preprocess", "serve", "run_phases"):
        receipts.record(stage, {})
    receipts.record("seal", seal)
    write_flight_receipts(directory / "flight-receipts.json", receipts)
    return {"data": synthetic_world.data_root, "run": run, "attempt": attempt,
            "rows": len(manifest["split"]["ids"]), "commit": manifest["study_commit"],
            "manifest": manifest, "manifest_path": path, "run_dir": directory,
            "attempt_path": synthetic_world.data_root / "attempts" / run / (attempt + ".json")}


def test_generation_worker_passes_real_bundle_and_never_scores(worker_world):
    w = worker_world
    before = {p: p.read_bytes() for p in w["run_dir"].rglob("*") if p.is_file()}
    result = inspect(w, mode="worker")
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["bundle_verified"] and report["attempt_state"] == "OPENED"
    assert report["score_jobs"] == report["expected_score_jobs"] == 1
    assert "token tags" not in result.stdout
    assert {p: p.read_bytes() for p in before} == before
    assert not list(w["run_dir"].glob("*.scores.json"))
    assert inspect(w, mode="arm").returncode == 2


@pytest.mark.parametrize("mutation", ["generation", "receipt", "score-spec", "score-file",
    "score-stage", "missing-receipt", "raw-output", "finalized", "aborted",
    "wrong-commit", "dirty", "wrong-run", "wrong-attempt", "ambiguous-manifest"])
def test_generation_worker_refuses_broken_custody(worker_world, mutation):
    w = worker_world
    directory, m = w["run_dir"], w["manifest"]
    if mutation in {"generation", "receipt", "score-spec"}:
        name = {"generation": w["run"] + ".generation-manifest.json",
                "receipt": "flight-receipts.json", "score-spec": "score-jobs.jsonl"}[mutation]
        (directory / name).write_text("{}\n")
    elif mutation == "score-file":
        (directory / "unexpected.scores.json").write_text("{}")
    elif mutation == "score-stage":
        from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts, read_flight_receipts, write_flight_receipts
        doc = read_flight_receipts(directory / "flight-receipts.json")
        receipt = FlightReceipts(w["run"], w["attempt"], doc["stages"])
        receipt.record("score", {"synthetic": True})
        write_flight_receipts(directory / "flight-receipts.json", receipt)
    elif mutation == "missing-receipt":
        (directory / "flight-receipts.json").unlink()
    elif mutation == "raw-output":
        Path(m["outputs"]["path"]).write_text("{}\n")
    elif mutation in {"finalized", "aborted"}:
        doc = json.loads(w["attempt_path"].read_text())
        doc["state"] = mutation.upper()
        w["attempt_path"].write_text(json.dumps(doc))
    else:
        if mutation == "wrong-commit":
            m["study_commit"] = "f" * 40
        elif mutation == "dirty":
            m["study_repo_dirt"] = ["modified.py"]
        elif mutation == "wrong-run":
            m["exposure_run_id"] = "another"
        elif mutation == "wrong-attempt":
            m["plan"]["attempt_id"] = "another"
        elif mutation == "ambiguous-manifest":
            (directory / "extra.run-manifest.json").write_text(json.dumps(m))
        w["manifest_path"].write_text(json.dumps(m))
    result = inspect(w, mode="worker")
    assert result.returncode == 2, result.stdout + result.stderr
    assert "token tags" not in result.stdout
