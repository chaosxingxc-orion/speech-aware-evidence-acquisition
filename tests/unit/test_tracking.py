"""MLflow linkage (stubbed) and the umbrella ledger row renderer."""

import sys
import types

import pytest

from speech_aware_evidence_acquisition.core.tracking import (
    LEDGER_COLUMNS,
    MlflowUnavailable,
    ledger_row,
)


def test_ledger_columns_match_the_umbrella_table_exactly():
    assert len(LEDGER_COLUMNS) == 21
    assert LEDGER_COLUMNS[0] == "experiment_id"
    assert LEDGER_COLUMNS[-1] == "decision"
    assert "split identity hash" in LEDGER_COLUMNS


def test_ledger_row_renders_and_validates():
    cells = {column: f"v{i}" for i, column in enumerate(LEDGER_COLUMNS)}
    row = ledger_row(cells)
    assert row.startswith("| v0 |") and row.endswith("| v20 |")
    with pytest.raises(ValueError, match="exactly"):
        ledger_row({"experiment_id": "x"})
    bad = dict(cells)
    bad["decision"] = "a|b"
    with pytest.raises(ValueError, match="pipe"):
        ledger_row(bad)


def test_ledger_row_refuses_newline_in_cell():
    cells = {column: f"v{i}" for i, column in enumerate(LEDGER_COLUMNS)}
    bad_newline = dict(cells)
    bad_newline["deviations"] = "line one\nline two"
    with pytest.raises(ValueError, match="newline"):
        ledger_row(bad_newline)
    bad_cr = dict(cells)
    bad_cr["deviations"] = "line one\rline two"
    with pytest.raises(ValueError, match="newline"):
        ledger_row(bad_cr)


def test_log_run_requires_mlflow(monkeypatch):
    # sys.modules["mlflow"] = None makes `import mlflow` raise ImportError even
    # when mlflow IS installed in this environment.
    monkeypatch.setitem(sys.modules, "mlflow", None)
    from speech_aware_evidence_acquisition.core import tracking

    with pytest.raises(MlflowUnavailable, match="tracking"):
        tracking._require_mlflow()


class _ActiveRunStub:
    """A real class, not types.SimpleNamespace: Python resolves the `with`
    statement's __enter__/__exit__ on the type, not the instance dict, so a
    SimpleNamespace carrying those as instance attributes can never satisfy
    the context manager protocol."""

    def __enter__(self):
        return types.SimpleNamespace(info=types.SimpleNamespace(run_id="mlrun-1"))

    def __exit__(self, *exc_info):
        return False


def test_log_run_with_stub_mlflow(tmp_path, monkeypatch):
    calls = {"params": {}, "metrics": {}, "artifacts": []}
    stub = types.SimpleNamespace(
        set_tracking_uri=lambda uri: calls.setdefault("uri", uri),
        set_experiment=lambda name: calls.setdefault("experiment", name),
        start_run=lambda run_name: _ActiveRunStub(),
        log_params=lambda params: calls["params"].update(params),
        log_metrics=lambda metrics: calls["metrics"].update(metrics),
        log_artifact=lambda path: calls["artifacts"].append(path),
    )
    monkeypatch.setitem(sys.modules, "mlflow", stub)

    from speech_aware_evidence_acquisition.contracts import ExecutionPlan
    from speech_aware_evidence_acquisition.core.base import RunResult
    from speech_aware_evidence_acquisition.core.config import ComposedConfig
    from speech_aware_evidence_acquisition.core.tracking import log_run

    outputs = tmp_path / "SAEA-E-000-x.outputs.jsonl"
    outputs.write_text("{}\n", encoding="utf-8")
    (tmp_path / "SAEA-E-000-x.trace-manifest.json").write_text("{}", encoding="utf-8")
    result = RunResult(
        run_id="SAEA-E-000-x", arm="bare-core", outputs_path=outputs,
        trace_manifest_hash="c" * 64,
        cost={"calls_used": 2, "audio_seconds_used": 20.0,
              "latency_seconds_total": 1.0, "prompt_tokens_total": 5,
              "completion_tokens_total": 4},
    )
    composed = ComposedConfig(
        values={"arm": "bare-core"}, config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )
    plan = ExecutionPlan(
        run_id="SAEA-E-000-x", execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings22-original", split_role="dev",
        split_identity_hash="a" * 64, planned_model_calls=5, planned_gpu_hours=1.0,
        planned_speech_audio_seconds=100, protocol_hash="b" * 64,
    )
    run_id = log_run(result, composed, plan, "b" * 64, tracking_uri=str(tmp_path / "mlruns"))
    assert run_id == "mlrun-1"
    assert calls["params"]["arm"] == "bare-core"
    assert calls["metrics"]["calls_used"] == 2
    assert len(calls["artifacts"]) == 2
