import hashlib
import json
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.core.flight.receipts import (
    FlightReceiptError,
    FlightReceipts,
    persist_flight_receipts,
    read_flight_receipts,
    write_flight_receipts,
)


def _receipts(*, through: str = "score", run_id: str = "run-a") -> FlightReceipts:
    receipts = FlightReceipts(run_id, "attempt-a")
    payloads = {
        "preflight": {"sample_count": 1},
        "preprocess": {"packet_count": 1},
        "serve": {"session_id": "session-a"},
        "run_phases": {
            "phase_supply": {
                "candidate_selections": {
                    "sample-a:perception": {
                        "selected_candidate_ids": ["playMusic", "setVolume"],
                    }
                }
            }
        },
        "seal": {"manifest_sha256": "a" * 64},
        "score": {"result": {"completed": 1, "failed": 0}},
    }
    for stage, payload in payloads.items():
        receipts.record(stage, payload)
        if stage == through:
            break
    return receipts


def test_atomic_writer_recovers_exact_candidate_audit_and_complete_score(tmp_path):
    path = tmp_path / "run-a" / "attempt-a" / "flight-receipts.json"
    receipts = _receipts(through="seal")

    seal_sha = write_flight_receipts(path, receipts)
    assert write_flight_receipts(path, receipts) == seal_sha

    receipts.record("score", {"result": {"completed": 1, "failed": 0}})
    score_sha = write_flight_receipts(path, receipts)
    del receipts

    recovered = json.loads(
        subprocess.check_output(
            [
                sys.executable,
                "-c",
                (
                    "import json,sys; "
                    "from speech_aware_evidence_acquisition.core.flight.receipts "
                    "import read_flight_receipts; "
                    "print(json.dumps(read_flight_receipts(sys.argv[1])))"
                ),
                str(path),
            ],
            text=True,
        )
    )
    assert score_sha != seal_sha
    assert recovered["stages"]["run_phases"]["phase_supply"][
        "candidate_selections"
    ]["sample-a:perception"]["selected_candidate_ids"] == [
        "playMusic",
        "setVolume",
    ]
    assert recovered["stages"]["score"]["result"] == {
        "completed": 1,
        "failed": 0,
    }


def test_writer_rejects_rollback_or_changed_prior_stage(tmp_path):
    path = tmp_path / "flight-receipts.json"
    write_flight_receipts(path, _receipts())

    with pytest.raises(FlightReceiptError, match="rollback"):
        write_flight_receipts(path, _receipts(through="seal"))

    changed = _receipts(through="seal")
    changed.record("score", {"result": {"completed": 0, "failed": 1}})
    with pytest.raises(FlightReceiptError, match="change recorded stage"):
        write_flight_receipts(path, changed)


def test_writer_rejects_wrong_identity_or_invalid_existing_hash(tmp_path):
    path = tmp_path / "flight-receipts.json"
    write_flight_receipts(path, _receipts(through="seal"))

    with pytest.raises(FlightReceiptError, match="identity"):
        write_flight_receipts(path, _receipts(through="seal", run_id="run-b"))

    document = json.loads(path.read_text(encoding="utf-8"))
    document["stages"]["seal"]["manifest_sha256"] = "b" * 64
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(FlightReceiptError, match="stage hash"):
        read_flight_receipts(path)


def test_shared_persistence_uses_governed_identity_path_and_skips_empty_ledger(
    tmp_path,
):
    empty = FlightReceipts("run-a", "attempt-a")
    assert (
        persist_flight_receipts(
            tmp_path, run_id="run-a", attempt_id="attempt-a", receipts=empty
        )
        is None
    )
    assert not (tmp_path / "runs").exists()

    receipts = _receipts(through="seal")
    reference = persist_flight_receipts(
        tmp_path, run_id="run-a", attempt_id="attempt-a", receipts=receipts
    )
    path = tmp_path / "runs/run-a/attempt-a/flight-receipts.json"
    assert reference == {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    assert read_flight_receipts(path) == receipts.as_json()


@pytest.mark.parametrize(
    "run_id, attempt_id",
    [("run-b", "attempt-a"), ("run-a", "attempt-b"), ("../run-a", "attempt-a")],
)
def test_shared_persistence_rejects_live_identity_mismatch_or_escaped_path(
    tmp_path, run_id, attempt_id
):
    with pytest.raises(FlightReceiptError, match="identity|escapes"):
        persist_flight_receipts(
            tmp_path,
            run_id=run_id,
            attempt_id=attempt_id,
            receipts=_receipts(through="seal"),
        )


def test_shared_persistence_rejects_matching_identity_that_escapes_runs_root(
    tmp_path,
):
    receipts = FlightReceipts("../run-a", "attempt-a")
    receipts.record("preflight", {"sample_count": 1})
    with pytest.raises(FlightReceiptError, match="escapes"):
        persist_flight_receipts(
            tmp_path,
            run_id="../run-a",
            attempt_id="attempt-a",
            receipts=receipts,
        )
