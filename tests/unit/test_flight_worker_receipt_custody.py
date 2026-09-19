import json

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignCell,
    CampaignError,
)
from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease
from speech_aware_evidence_acquisition.core.flight.receipts import (
    FLIGHT_STAGES,
    FlightReceipts,
    read_flight_receipts,
)


RUN_ID = "SAEA-WORKER-RECEIPT-TEST"
ATTEMPT_ID = "attempt-worker-receipt-test"


class Runtime:
    def __init__(self, *, failure_stage=None):
        self.run_id = RUN_ID
        self.attempt_id = ATTEMPT_ID
        self.receipts = FlightReceipts(RUN_ID, ATTEMPT_ID)
        self.calls = []
        self.failure_stage = failure_stage

    def _record(self, stage):
        self.calls.append(stage)
        self.receipts.record(stage, {"evidence": stage})
        if self.failure_stage == stage:
            raise RuntimeError(f"{stage} failed after genuine receipt")

    def verify_prepared_artifacts(self):
        # E16: nothing pinned, so the launch guard has nothing to refuse.
        return ()

    def preflight(self, *, enforce_prepared_artifacts=True):
        self._record("preflight")

    def preprocess(self):
        self._record("preprocess")

    def serve(self):
        self._record("serve")

    def run_phases(self):
        self._record("run_phases")

    def seal(self):
        self._record("seal")
        return {
            "manifest_path": "complete-manifest.json",
            "status": "COMPLETED",
            "flight_receipt": {"historical": "retained"},
        }

    def score(self, **kwargs):
        pytest.fail("generation-only worker must not score")

    def stop_serving(self):
        pytest.fail("generation-only worker must not stop the root-owned service")


def _cell(*, readiness="ready"):
    return CampaignCell.from_document(
        {
            "cell_id": "worker-cell",
            "model_fragment": "m",
            "dataset_fragment": "d",
            "baseline_fragment": "b",
            "run_id": RUN_ID,
            "attempt_id": ATTEMPT_ID,
            "allowed_execution_stages": ["worker"],
            "readiness": {"state": readiness, "reason": "test readiness"},
        }
    )


def _args(repo, data, token):
    return [
        "worker",
        "--repo-root",
        str(repo),
        "--data-root",
        str(data),
        "--runtime-root",
        str(data / "runtime"),
        "--lock-path",
        str(data / "datasets.lock.json"),
        "--experiment",
        "worker-proof",
        "--cell",
        "worker-cell",
        "--expected-session-id",
        "serving-test",
        "--lease-token-file",
        str(token),
    ]


def _run_under_lease(cli, *, repo, data, runtime):
    token = data / "locks/flight.lock"
    with GenerationLease.acquire(
        data,
        owner="root",
        run_id=RUN_ID,
        attempt_id=ATTEMPT_ID,
        session_id="serving-test",
        study_head="a" * 40,
    ):
        return cli.main(_args(repo, data, token))


def _patch_cli(monkeypatch, cli, repo, runtime, *, readiness="ready"):
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *args: (_cell(readiness=readiness),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *args, **kwargs: runtime)


def test_worker_persists_exact_sealed_receipts_and_returns_reference(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    runtime = Runtime()
    _patch_cli(monkeypatch, cli, repo, runtime)

    assert _run_under_lease(cli, repo=repo, data=data, runtime=runtime) == 0

    output = json.loads(capsys.readouterr().out)
    receipt_path = (
        data / "runs" / RUN_ID / ATTEMPT_ID / "flight-receipts.json"
    ).resolve()
    assert output["manifest_path"] == "complete-manifest.json"
    assert output["status"] == "COMPLETED"
    assert output["flight_receipt"] == {"historical": "retained"}
    reference = output["flight_receipts"][RUN_ID]
    assert reference["path"] == str(receipt_path)
    assert reference["sha256"]
    persisted = read_flight_receipts(receipt_path)
    assert tuple(
        stage for stage in FLIGHT_STAGES if stage in persisted["stages"]
    ) == FLIGHT_STAGES[:-1]
    assert runtime.calls == list(FLIGHT_STAGES[:-1])


@pytest.mark.parametrize("failure_stage", ["run_phases", "seal"])
def test_worker_preserves_genuine_partial_receipts_on_generation_or_seal_failure(
    tmp_path, monkeypatch, failure_stage
):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    runtime = Runtime(failure_stage=failure_stage)
    _patch_cli(monkeypatch, cli, repo, runtime)

    with pytest.raises(RuntimeError, match=f"{failure_stage} failed"):
        _run_under_lease(cli, repo=repo, data=data, runtime=runtime)

    persisted = read_flight_receipts(
        data / "runs" / RUN_ID / ATTEMPT_ID / "flight-receipts.json"
    )
    expected = FLIGHT_STAGES[: FLIGHT_STAGES.index(failure_stage) + 1]
    assert tuple(
        stage for stage in FLIGHT_STAGES if stage in persisted["stages"]
    ) == expected


def test_worker_receipt_failure_is_note_on_original_generation_error(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    runtime = Runtime(failure_stage="run_phases")
    _patch_cli(monkeypatch, cli, repo, runtime)

    def fail_persistence(*args, **kwargs):
        raise OSError("receipt storage unavailable")

    monkeypatch.setattr(cli, "persist_flight_receipts", fail_persistence)
    with pytest.raises(RuntimeError, match="run_phases failed") as raised:
        _run_under_lease(cli, repo=repo, data=data, runtime=runtime)

    assert any(
        "receipt storage unavailable" in note for note in raised.value.__notes__
    )


def test_held_worker_creates_no_receipt_or_runtime_stage(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo = tmp_path / "repo"
    data = tmp_path / "data"
    runtime = Runtime()
    _patch_cli(monkeypatch, cli, repo, runtime, readiness="held")

    with pytest.raises(CampaignError, match="test readiness"):
        _run_under_lease(cli, repo=repo, data=data, runtime=runtime)

    assert runtime.calls == []
    assert not (data / "runs").exists()
