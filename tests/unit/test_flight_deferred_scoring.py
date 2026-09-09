"""Worker generation seals once; the complete official finalizer runs after custody."""
import hashlib
from pathlib import Path

from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease, WorkerExecutionPolicy
from test_flight_runtime import _serving_world, _serving_runtime, _write_serving_session, _SERVING_RUN_ID


def test_worker_seals_without_scoring_then_finalizes_one_complete_manifest(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    calls = []
    def forbidden_inline_finalizer(*args, **kwargs):
        raise AssertionError("sealing must not score")
    def background_finalizer(jobs, **kwargs):
        assert not (data / "locks/flight.lock").exists()
        assert len(jobs) == 1
        assert jobs[0].ledger_cells.is_file()
        assert kwargs["operation"] == "finalize"
        assert kwargs["include_per_sample"] is True
        calls.append(jobs[0].manifest)
        jobs[0].manifest.write_text('{"fake": "finalized score binding"}')
        return {"job_count": 1, "failed": 0, "succeeded": 1}
    with GenerationLease.acquire(
        data, owner="root", run_id=_SERVING_RUN_ID, attempt_id="attempt-serving",
        session_id="serving-test", study_head="a" * 40,
    ) as lease:
        runtime, starter, _ = _serving_runtime(
            tmp_path, repo,
            execution_policy=WorkerExecutionPolicy("serving-test", lease.token),
            bundle_finalizer=forbidden_inline_finalizer, score_batch=background_finalizer,
        )
        runtime.preflight()
        runtime.preprocess()
        runtime.serve()
        runtime.run_phases()
        seal = runtime.seal()
        assert calls == []
        frozen = Path(seal["generation_manifest_path"])
        source = frozen.read_bytes()
        assert hashlib.sha256(source).hexdigest() == seal["generation_manifest_sha256"]
        assert seal["finalize"]["status"] == "deferred-to-score-worker"
    score = runtime.score(include_per_sample=True)
    assert len(calls) == 1 and starter.calls == 0
    assert frozen.read_bytes() == source
    assert score["source_generation_manifest_sha256"] == seal["generation_manifest_sha256"]
    assert score["finalized_manifest_sha256"] == hashlib.sha256(calls[0].read_bytes()).hexdigest()


def test_changed_generation_seal_or_job_table_refuses_before_scoring(tmp_path):
    import pytest
    from speech_aware_evidence_acquisition.core.flight.scoring import (
        DeferredScoringError, load_sealed_score_jobs, seal_scoring_inputs,
    )
    manifest = tmp_path / "one.run-manifest.json"
    manifest.write_text('{"synthetic": true}')
    receipt = seal_scoring_inputs(manifest, run_id="one", attempt_id="a", ledger_cells={})
    receipt["manifest_path"] = str(manifest)
    assert len(load_sealed_score_jobs(receipt)) == 1
    manifest.write_text('{"synthetic": false}')
    with pytest.raises(DeferredScoringError, match="manifest changed"):
        load_sealed_score_jobs(receipt)
    Path(receipt["score_jobs_path"]).write_text("changed")
    with pytest.raises(DeferredScoringError, match="score_jobs"):
        load_sealed_score_jobs(receipt)


def test_batch_finalizer_carries_per_sample_and_explicit_worktree_context(tmp_path, monkeypatch):
    import json
    import subprocess
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.scoring_batch import (
        ScoreJob, ScoringContext, run_score_batch,
    )
    manifest = tmp_path / "one.run-manifest.json"
    manifest.write_text("{}")
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{}")
    calls = []
    def run(arguments, **kwargs):
        calls.append((arguments, kwargs))
        return SimpleNamespace(returncode=0, stderr="", stdout=json.dumps({
            "verified": True, "manifest": str(manifest),
            "scores": str(tmp_path / "one.scores.json"), "attempt_state": "FINALIZED",
        }))
    monkeypatch.setattr(subprocess, "run", run)
    context = ScoringContext(
        repo_root=tmp_path / "repo", data_root=tmp_path / "data", lock_path=tmp_path / "lock.json",
    )
    result = run_score_batch(
        [ScoreJob("one", manifest, ledger_cells=ledger)],
        output_dir=tmp_path / "batch", max_workers=1, operation="finalize",
        include_per_sample=True, context=context,
    )
    assert result["succeeded"] == 1 and len(calls) == 1
    arguments, kwargs = calls[0]
    assert arguments[4] == "finalize"
    assert "--include-per-sample" in arguments
    assert arguments[arguments.index("--lock-path") + 1] == str(context.lock_path)
    assert arguments[arguments.index("--data-root") + 1] == str(context.data_root)
    assert kwargs["cwd"] == context.repo_root
    assert kwargs["env"]["PYTHONPATH"].split(":")[0] == str(context.repo_root / "src")


def test_finalize_cli_returns_saved_per_sample_scores_without_another_scorer(tmp_path, monkeypatch, capsys):
    import json
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.driver import cli
    from speech_aware_evidence_acquisition.data import lock as lock_module
    scores = {"synthetic-scorer": {"aggregate": {"count": 1}, "per_sample": [{"sample_id": "one"}]}}
    scores_path = tmp_path / "scores.json"
    scores_path.write_text(json.dumps(scores))
    seen = []
    def finalize(*args, **kwargs):
        seen.append((args, kwargs))
        return SimpleNamespace(
            scores_path=scores_path, ledger_markdown_path="ledger.md",
            ledger_json_path="ledger.json", mlflow_run_id=None, attempt_state="FINALIZED",
        )
    monkeypatch.setattr(cli, "__file__", str(tmp_path / "repo/src/package/core/driver/cli.py"))
    monkeypatch.setattr(cli, "finalize_bundle", finalize)
    monkeypatch.setattr(lock_module, "load_lock", lambda path: {})
    code = cli.main([
        "finalize", "--manifest", str(tmp_path / "one.run-manifest.json"),
        "--include-per-sample", "--lock-path", str(tmp_path / "lock.json"),
        "--data-root", str(tmp_path / "data"), "--repo-root", str(tmp_path / "repo"),
    ])
    assert code == 0 and len(seen) == 1
    assert seen[0][1]["repo_root"] == tmp_path / "repo"
    assert json.loads(capsys.readouterr().out)["score_details"] == scores
