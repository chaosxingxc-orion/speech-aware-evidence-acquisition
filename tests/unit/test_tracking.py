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


def _fake_manifest(**overrides):
    manifest = {
        "run_id": "SAEA-E-000-track",
        "created_at": "2026-08-05T12:00:00+00:00",
        "study_commit": "a" * 40,
        "config": {"config_hash": "b" * 64, "fragments": {}},
        "protocol_hash": "c" * 64,
        "plan": {
            "split_role": "discovery",
            "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "earnings21-original",
        },
        "split": {"identity_hash": "d" * 64},
        "outputs": {"path": "outputs.jsonl", "sha256": "e" * 64},
        "raw_trace": {"path": "trace.jsonl", "sha256": "f" * 64},
        "trace_manifest": {"path": "trace-manifest.json", "sha256": "0" * 64},
        "scores": None,
        "session_receipt": None,
        "cost": {"calls_used": 3, "audio_seconds_used": 30.0},
    }
    manifest.update(overrides)
    return manifest


def _fake_bundle(manifest_path, **overrides):
    from speech_aware_evidence_acquisition.core.bundle import VerifiedBundle

    return VerifiedBundle(
        manifest_path=manifest_path,
        manifest=_fake_manifest(**overrides),
        outputs_path=None,
        outputs_rows=(),
        trace_records={},
        split_ids=frozenset(),
        attempt_state="OPENED",
    )


def test_bundle_ledger_cells_derives_only_the_machine_checkable_columns(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import bundle_ledger_cells

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    derived = bundle_ledger_cells(bundle)
    assert derived["study commit"] == "a" * 40
    assert derived["config hash"] == "b" * 64
    assert derived["protocol hash"] == "c" * 64
    assert derived["split role"] == "discovery"
    assert derived["split identity hash"] == "d" * 64
    # IMPORTANT fix (round-2 external-threat-model review): `consumed` means
    # CONFIRMATORY exposure was read, never "this bundle finalized" -- a
    # dev/discovery split_role (the only kind Stage-2 can ever produce) must
    # derive "no", not a hard-coded "yes".
    assert derived["consumed"] == "no"
    assert derived["date"] == "2026-08-05"
    assert "outputs=" + "e" * 64 in derived["artifact hashes"]
    assert "raw_trace=" + "f" * 64 in derived["artifact hashes"]
    # A human-judgment column must never appear here.
    assert "decision" not in derived
    assert "experiment_id" not in derived


def test_ledger_row_for_bundle_merges_human_and_derived_cells(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import ledger_row_for_bundle

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    human = {
        "experiment_id": "SAEA-E-000", "speech task/carrier": "earnings21 discovery",
        "changed axes": "none", "shared code revision": "n/a", "model rev": "n/a",
        "dataset rev": "n/a", "MLflow run": "n/a", "effectiveness": "n/a",
        "reasonableness": "n/a", "efficiency": "n/a", "deviations": "none", "decision": "test",
    }
    row, merged = ledger_row_for_bundle(bundle, human)
    assert set(merged) == set(LEDGER_COLUMNS)
    assert merged["study commit"] == "a" * 40
    assert merged["experiment_id"] == "SAEA-E-000"
    assert row.count("|") == len(LEDGER_COLUMNS) + 1


def test_ledger_row_for_bundle_refuses_a_contradicting_hand_supplied_cell(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import ledger_row_for_bundle

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    with pytest.raises(ValueError, match="contradict"):
        ledger_row_for_bundle(bundle, {"protocol hash": "0" * 64})


# ---------------------------------------------------------------------------
# IMPORTANT fix (round-2 external-threat-model review): `consumed` is derived
# from the bundle's own verified split_role, never a hard-coded literal.
# Probes: a dev bundle -> consumed=no; hand-supplying yes for a dev bundle
# (the only kind Stage-2 can ever produce -- confirmatory is refused by
# contracts.ExecutionPlan.validate before a bundle can even verify) ->
# refused, so the study exposure ledger and the umbrella index row can never
# contradict each other by construction.
# ---------------------------------------------------------------------------


def test_bundle_ledger_cells_consumed_is_no_for_a_dev_split(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import bundle_ledger_cells

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json", plan={
        "split_role": "dev", "execution_profile": "bounded-discovery-probe",
        "carrier_lock_key": "earnings21-original",
    })
    assert bundle_ledger_cells(bundle)["consumed"] == "no"


def test_ledger_row_for_bundle_refuses_a_hand_supplied_yes_consumed_for_a_dev_bundle(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import ledger_row_for_bundle

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    with pytest.raises(ValueError, match="contradict"):
        ledger_row_for_bundle(bundle, {"consumed": "yes"})


def test_ledger_row_for_bundle_accepts_a_matching_hand_supplied_cell(tmp_path):
    from speech_aware_evidence_acquisition.core.tracking import ledger_row_for_bundle

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    human = {
        "experiment_id": "SAEA-E-000", "speech task/carrier": "earnings21 discovery",
        "changed axes": "none", "shared code revision": "n/a", "model rev": "n/a",
        "dataset rev": "n/a", "MLflow run": "n/a", "effectiveness": "n/a",
        "reasonableness": "n/a", "efficiency": "n/a", "deviations": "none", "decision": "test",
    }
    # Supplying the SAME value the bundle would have derived is not a
    # contradiction -- only a DIFFERING value refuses.
    row, merged = ledger_row_for_bundle(bundle, {**human, "protocol hash": "c" * 64})
    assert merged["protocol hash"] == "c" * 64


def test_log_bundle_requires_mlflow(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "mlflow", None)
    from speech_aware_evidence_acquisition.core.tracking import log_bundle

    bundle = _fake_bundle(tmp_path / "run" / "x.run-manifest.json")
    with pytest.raises(MlflowUnavailable, match="tracking"):
        log_bundle(bundle, tracking_uri=str(tmp_path / "mlruns"))


def test_log_bundle_with_stub_mlflow_uploads_every_manifest_artifact(tmp_path, monkeypatch):
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

    from speech_aware_evidence_acquisition.core.tracking import log_bundle

    manifest_path = tmp_path / "run" / "SAEA-E-000-track.run-manifest.json"
    scores = {
        "outputs": {"path": "outputs.jsonl", "sha256": "e" * 64},
        "raw_trace": {"path": "trace.jsonl", "sha256": "f" * 64},
        "trace_manifest": {"path": "trace-manifest.json", "sha256": "0" * 64},
        "scores": {"path": "scores.json", "sha256": "1" * 64},
    }
    bundle = _fake_bundle(manifest_path, **scores)
    run_id = log_bundle(bundle, tracking_uri=str(tmp_path / "mlruns"))
    assert run_id == "mlrun-1"
    assert calls["params"]["config_hash"] == "b" * 64
    assert calls["metrics"]["calls_used"] == 3
    # outputs, raw trace, trace manifest, scores, and the manifest itself.
    assert len(calls["artifacts"]) == 5
    assert str(manifest_path) in calls["artifacts"]


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
