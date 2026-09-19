"""E16 (2026-09-19): prepared-artifact identity is verified BEFORE an attempt opens.

A prepared artifact is evidence only for the implementation that produced it:
``core.preparation.artifact_inputs`` binds the composed config, the split
identity and ``sources`` -- and ``sources["implementation"]`` carries the
SHA-256 of ``core/flight/runtime.py`` and the rails modules. The two four-row
smokes of 2026-09-19 (B8b, B4a v2) passed ``core.flight.cli check`` and then
died in ``FlightRuntime.run_phases`` with ``prepared artifact identity
mismatch``, each leaving an OPENED attempt behind, because ``check`` never
loaded the artifact at all.

These tests pin the closure: the identity is recomputed exactly as the dispatch
will, ``check`` reports it, the worker/campaign launch refuses on it before any
reservation, and the refusal names which input moved. Nothing here contacts a
model, a server, a lease-bearing service or ``SPEECHRL_DATA_DIR``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight import cli as flight_cli
from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell
from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease
from speech_aware_evidence_acquisition.core.preparation import (
    PreparationError,
    canonical_bytes,
    first_input_difference,
)
from speech_aware_evidence_acquisition.rails import phase_supply

from test_flight_runtime import _make_runtime
from test_prepared_phase_supply import setup_runtime


RUN_ID = "SAEA-E16-PREPARED-ARTIFACT"
ATTEMPT_ID = "attempt-e16-prepared-artifact"


# ---------------------------------------------------------------------------
# The diff-naming helper.
# ---------------------------------------------------------------------------


def _inputs(*, config: str = "a" * 64, runtime: str = "b" * 64) -> dict[str, object]:
    return {
        "config_sha256": config,
        "split_identity_hash": "d" * 64,
        "sources": {
            "snapshot": "c" * 64,
            "implementation": {
                "runtime": runtime,
                "speech_aware_evidence_acquisition.rails.kb_policy": "e" * 64,
            },
        },
    }


def test_identical_inputs_have_no_difference():
    assert first_input_difference(_inputs(), _inputs()) is None


def test_a_moved_implementation_file_is_named_by_its_key_path():
    assert (
        first_input_difference(_inputs(), _inputs(runtime="f" * 64))
        == "sources.implementation.runtime"
    )


def test_a_config_edit_is_named_config_sha256():
    assert (
        first_input_difference(_inputs(), _inputs(config="9" * 64))
        == "config_sha256"
    )


def test_config_wins_over_implementation_when_both_moved():
    """Sorted key order, so one stale artifact always names one stable key."""

    assert (
        first_input_difference(_inputs(), _inputs(config="9" * 64, runtime="f" * 64))
        == "config_sha256"
    )


def test_a_key_present_on_only_one_side_is_named_and_attributed():
    expected = _inputs()
    actual = _inputs()
    del actual["sources"]["implementation"]["runtime"]
    difference = first_input_difference(expected, actual)
    assert difference.startswith("sources.implementation.runtime")
    assert "absent from the prepared artifact" in difference


# ---------------------------------------------------------------------------
# FlightRuntime.verify_prepared_artifacts, against a real prepared artifact.
# ---------------------------------------------------------------------------


def _prepare_pinned_artifact(tmp_path, monkeypatch):
    runtime, _binding, _program = setup_runtime(tmp_path)
    monkeypatch.setattr(
        phase_supply, "build_bootstrap_selection", lambda *a, **k: ({}, {"s1": ("v1",)})
    )
    receipt = runtime.prepare_phase_supply(tmp_path / "seed.json")
    runtime._composed.values["prepared_phase_supply"] = {
        "relpath": "seed.json",
        "sha256": receipt["sha256"],
    }
    return runtime, tmp_path / "seed.json"


def test_a_fresh_artifact_verifies(tmp_path, monkeypatch):
    runtime, path = _prepare_pinned_artifact(tmp_path, monkeypatch)

    reports = runtime.verify_prepared_artifacts()

    assert [report["key"] for report in reports] == ["prepared_phase_supply"]
    assert reports[0]["identity_ok"] is True
    assert reports[0]["relpath"] == "seed.json"
    assert reports[0]["reason"] is None and reports[0]["difference"] is None
    assert reports[0]["sha256"] == runtime._composed.values[
        "prepared_phase_supply"
    ]["sha256"]
    assert path.is_file()


def test_a_changed_implementation_source_fails_closed_and_is_named(
    tmp_path, monkeypatch
):
    """Exactly the 2026-09-19 defect: the E14/E15 merges moved runtime.py."""

    runtime, path = _prepare_pinned_artifact(tmp_path, monkeypatch)
    document = json.loads(path.read_bytes())
    assert "runtime" in document["inputs"]["sources"]["implementation"]
    document["inputs"]["sources"]["implementation"]["runtime"] = "0" * 64
    raw = canonical_bytes(document)
    path.write_bytes(raw)
    import hashlib

    runtime._composed.values["prepared_phase_supply"]["sha256"] = hashlib.sha256(
        raw
    ).hexdigest()

    reports = runtime.verify_prepared_artifacts()

    assert len(reports) == 1
    assert reports[0]["identity_ok"] is False
    assert reports[0]["difference"] == "sources.implementation.runtime"
    assert "identity mismatch" in reports[0]["reason"]
    assert "sources.implementation.runtime" in reports[0]["reason"]


def test_a_pin_whose_file_hash_moved_fails_closed(tmp_path, monkeypatch):
    runtime, _path = _prepare_pinned_artifact(tmp_path, monkeypatch)
    runtime._composed.values["prepared_phase_supply"]["sha256"] = "1" * 64

    reports = runtime.verify_prepared_artifacts()

    assert reports[0]["identity_ok"] is False
    assert "not the pinned" in reports[0]["reason"]


def test_an_absent_artifact_fails_closed(tmp_path, monkeypatch):
    runtime, path = _prepare_pinned_artifact(tmp_path, monkeypatch)
    path.unlink()

    reports = runtime.verify_prepared_artifacts()

    assert reports[0]["identity_ok"] is False
    assert "absent on disk" in reports[0]["reason"]


def test_a_cell_pinning_nothing_verifies_nothing(tmp_path, monkeypatch):
    runtime, _binding, _program = setup_runtime(tmp_path)

    assert runtime.verify_prepared_artifacts() == ()


def test_the_verdict_is_memoized(tmp_path, monkeypatch):
    runtime, _path = _prepare_pinned_artifact(tmp_path, monkeypatch)
    first = runtime.verify_prepared_artifacts()

    def refuse(*args, **kwargs):
        raise AssertionError("the memoized verdict must not be recomputed")

    runtime._prepared_phase_program_binding = refuse
    assert runtime.verify_prepared_artifacts() is first


def test_prepare_phase_supply_names_the_difference_on_a_warm_mismatch(
    tmp_path, monkeypatch
):
    """``core.flight.repin`` verifies a pin by re-running this producer."""

    runtime, path = _prepare_pinned_artifact(tmp_path, monkeypatch)
    document = json.loads(path.read_bytes())
    document["inputs"]["sources"]["implementation"]["runtime"] = "0" * 64
    path.write_bytes(canonical_bytes(document))

    with pytest.raises(PreparationError, match="sources.implementation.runtime"):
        runtime.prepare_phase_supply(path)


# ---------------------------------------------------------------------------
# preflight(): the receipt fields, and the refusal that precedes every attempt.
# ---------------------------------------------------------------------------


def _stale_report():
    return {
        "key": "prepared_phase_supply",
        "relpath": "prepared/SAEA-X/phase-supply-v2.json",
        "sha256": "2" * 64,
        "identity_ok": False,
        "reason": (
            "prepared artifact identity mismatch; first differing identity key: "
            "sources.implementation.runtime"
        ),
        "difference": "sources.implementation.runtime",
    }


def test_preflight_records_the_prepared_artifact_verdict(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)

    receipt = runtime.preflight()

    assert receipt["prepared_artifacts"] == []
    assert receipt["prepared_artifacts_ok"] is True


def test_preflight_refuses_a_stale_artifact_and_opens_no_attempt(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.verify_prepared_artifacts = lambda: (_stale_report(),)

    with pytest.raises(PreparationError) as raised:
        runtime.preflight()

    assert "refusing to open an attempt" in str(raised.value)
    assert "sources.implementation.runtime" in str(raised.value)
    assert "prepared/SAEA-X/phase-supply-v2.json" in str(raised.value)
    assert not (tmp_path / "data" / "attempts").exists()
    assert not runtime.receipts.has("preflight")


def test_check_mode_preflight_reports_instead_of_refusing(tmp_path):
    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.verify_prepared_artifacts = lambda: (_stale_report(),)

    receipt = runtime.preflight(enforce_prepared_artifacts=False)

    assert receipt["prepared_artifacts_ok"] is False
    assert receipt["prepared_artifacts"] == [_stale_report()]
    assert not (tmp_path / "data" / "attempts").exists()


# ---------------------------------------------------------------------------
# core.flight.cli: check reports and exits non-zero; worker refuses first.
# ---------------------------------------------------------------------------


def test_blockers_are_empty_for_a_current_package():
    assert flight_cli.prepared_artifact_blockers(
        {"prepared_artifacts": [], "prepared_artifacts_ok": True}
    ) == []
    assert flight_cli.prepared_artifact_blockers({}) == []


def test_blockers_name_the_artifact_and_the_cause():
    blockers = flight_cli.prepared_artifact_blockers(
        {"prepared_artifacts": [_stale_report()], "prepared_artifacts_ok": False}
    )

    assert len(blockers) == 1
    assert "prepared_phase_supply" in blockers[0]
    assert "prepared/SAEA-X/phase-supply-v2.json" in blockers[0]
    assert "sources.implementation.runtime" in blockers[0]


class _Runtime:
    """A launch double: the only real work it does is open an attempt file.

    ``preflight`` writes the attempt record that
    ``core.model.adapter.FrozenCoreAdapter`` writes for real, so a test can
    assert the E16 guard ran BEFORE anything could reserve the one-time
    ``(run_id, attempt_id)`` key.
    """

    def __init__(self, data_root: Path, reports=()):
        self.run_id = RUN_ID
        self.attempt_id = ATTEMPT_ID
        self._data_root = Path(data_root)
        self._reports = tuple(reports)
        self.calls: list[str] = []

    def verify_prepared_artifacts(self):
        self.calls.append("verify")
        return self._reports

    def _open_attempt(self):
        path = self._data_root / "attempts" / self.run_id / f"{self.attempt_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"state": "OPENED"}), encoding="utf-8")

    def preflight(self, *, enforce_prepared_artifacts=True):
        self.calls.append("preflight")
        self._open_attempt()
        return {
            "run_id": self.run_id,
            "prepared_artifacts": [dict(report) for report in self._reports],
            "prepared_artifacts_ok": all(
                report["identity_ok"] for report in self._reports
            ),
        }

    def preprocess(self):
        self.calls.append("preprocess")

    def serve(self):
        self.calls.append("serve")

    def run_phases(self):
        self.calls.append("run_phases")

    def seal(self):
        self.calls.append("seal")
        return {"manifest_path": "complete-manifest.json", "status": "COMPLETED"}

    @property
    def receipts(self):
        return SimpleNamespace(as_json=lambda: {"stages": list(self.calls)}, stages={})


def _cell():
    return CampaignCell.from_document(
        {
            "cell_id": "e16-cell",
            "model_fragment": "m",
            "dataset_fragment": "d",
            "baseline_fragment": "b",
            "run_id": RUN_ID,
            "attempt_id": ATTEMPT_ID,
            "allowed_execution_stages": ["worker", "check"],
            "readiness": {"state": "ready"},
        }
    )


def _patch_cli(monkeypatch, repo, runtime):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(
        flight_cli, "__file__", str(repo / "src/package/core/flight/cli.py")
    )
    monkeypatch.setattr(flight_cli, "load_campaign_cells", lambda *args: (_cell(),))
    monkeypatch.setattr(
        flight_cli, "build_flight_runtime", lambda *args, **kwargs: runtime
    )
    monkeypatch.setattr(
        flight_cli, "persist_flight_receipts", lambda *args, **kwargs: None
    )


def _worker_argv(repo, data, token):
    return [
        "worker",
        "--repo-root", str(repo),
        "--data-root", str(data),
        "--runtime-root", str(data / "runtime"),
        "--lock-path", str(data / "datasets.lock.json"),
        "--experiment", "e16-experiment",
        "--cell", "e16-cell",
        "--expected-session-id", "serving-test",
        "--lease-token-file", str(token),
    ]


def _check_argv(repo, data):
    return [
        "check",
        "--repo-root", str(repo),
        "--data-root", str(data),
        "--runtime-root", str(data / "runtime"),
        "--lock-path", str(data / "datasets.lock.json"),
        "--experiment", "e16-experiment",
        "--cell", "e16-cell",
    ]


def _under_lease(data, call):
    with GenerationLease.acquire(
        data,
        owner="root",
        run_id=RUN_ID,
        attempt_id=ATTEMPT_ID,
        session_id="serving-test",
        study_head="a" * 40,
    ):
        return call()


def test_worker_refuses_a_stale_artifact_before_any_attempt_is_opened(
    tmp_path, monkeypatch
):
    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = _Runtime(data, reports=(_stale_report(),))
    _patch_cli(monkeypatch, repo, runtime)
    token = data / "locks/flight.lock"

    with pytest.raises(PreparationError) as raised:
        _under_lease(data, lambda: flight_cli.main(_worker_argv(repo, data, token)))

    assert "refusing to launch" in str(raised.value)
    assert f"{RUN_ID}/{ATTEMPT_ID}" in str(raised.value)
    assert "sources.implementation.runtime" in str(raised.value)
    assert runtime.calls == ["verify"]
    assert not (data / "attempts").exists()


def test_worker_proceeds_when_every_prepared_artifact_verifies(
    tmp_path, monkeypatch, capsys
):
    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = _Runtime(data)
    _patch_cli(monkeypatch, repo, runtime)
    token = data / "locks/flight.lock"

    exit_code = _under_lease(
        data, lambda: flight_cli.main(_worker_argv(repo, data, token))
    )

    assert exit_code == 0
    assert runtime.calls[0] == "verify"
    assert runtime.calls[1:] == ["preflight", "preprocess", "serve", "run_phases", "seal"]
    assert (data / "attempts" / RUN_ID / f"{ATTEMPT_ID}.json").is_file()
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETED"


def test_check_reports_the_stale_artifact_and_exits_non_zero(
    tmp_path, monkeypatch, capsys
):
    repo, data = tmp_path / "repo", tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    runtime = _Runtime(data, reports=(_stale_report(),))
    _patch_cli(monkeypatch, repo, runtime)

    exit_code = flight_cli.main(_check_argv(repo, data))

    assert exit_code == 1
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["preflight"]["prepared_artifacts_ok"] is False
    assert receipt["preflight"]["prepared_artifacts"] == [_stale_report()]
    assert receipt["generation_authorized"] is False
    # The registration's own readiness is reported verbatim, never overwritten.
    assert receipt["scientific_readiness"]["state"] == "ready"
    assert len(receipt["blockers"]) == 1
    assert "sources.implementation.runtime" in receipt["blockers"][0]


def test_check_exits_zero_when_every_prepared_artifact_verifies(
    tmp_path, monkeypatch, capsys
):
    repo, data = tmp_path / "repo", tmp_path / "data"
    data.mkdir(parents=True, exist_ok=True)
    runtime = _Runtime(data)
    _patch_cli(monkeypatch, repo, runtime)

    exit_code = flight_cli.main(_check_argv(repo, data))

    assert exit_code == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["preflight"]["prepared_artifacts_ok"] is True
    assert "blockers" not in receipt
