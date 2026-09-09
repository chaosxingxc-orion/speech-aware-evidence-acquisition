"""Synthetic process/file tests for the single generation lease."""
import json
import os
import subprocess
import sys

import pytest

from speech_aware_evidence_acquisition.core.flight.lease import (
    GenerationLease, GenerationLeaseError, WorkerExecutionPolicy,
)


def acquire(root, **kwargs):
    return GenerationLease.acquire(
        root, owner="coordinator", run_id="run", attempt_id="attempt",
        session_id="resident", study_head="a" * 40, **kwargs,
    )


def test_live_lease_excludes_other_process_and_preserves_metadata(tmp_path):
    with acquire(tmp_path) as lease:
        policy = WorkerExecutionPolicy(expected_session_id="resident", lease_token=lease.token)
        policy.assert_lease(tmp_path, run_id="run", attempt_id="attempt")
        code = (
            "from pathlib import Path; "
            "from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease; "
            f"GenerationLease.acquire(Path({str(tmp_path)!r}), owner='other', run_id='run', "
            "attempt_id='other', session_id='resident', study_head='b'*40)"
        )
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        assert result.returncode != 0
        assert "already held" in result.stderr
        doc = json.loads((tmp_path / "locks/flight.lock").read_text())
        assert doc["token"] == lease.token
        assert doc["study_head"] == "a" * 40
    assert not (tmp_path / "locks/flight.lock").exists()
    with acquire(tmp_path):
        pass


@pytest.mark.parametrize("field,value", [
    ("lease_token", "wrong"), ("expected_session_id", "other"),
])
def test_wrong_worker_capability_is_refused(tmp_path, field, value):
    with acquire(tmp_path) as lease:
        fields = {"expected_session_id": "resident", "lease_token": lease.token}
        fields[field] = value
        with pytest.raises(GenerationLeaseError):
            WorkerExecutionPolicy(**fields).assert_lease(tmp_path, run_id="run", attempt_id="attempt")


def test_wrong_attempt_and_unheld_metadata_are_refused(tmp_path):
    with acquire(tmp_path) as lease:
        policy = WorkerExecutionPolicy(expected_session_id="resident", lease_token=lease.token)
        with pytest.raises(GenerationLeaseError, match="attempt"):
            policy.assert_lease(tmp_path, run_id="run", attempt_id="other")
        doc = (tmp_path / "locks/flight.lock").read_text()
    (tmp_path / "locks/flight.lock").write_text(doc)
    with pytest.raises(GenerationLeaseError, match="not held"):
        policy.assert_lease(tmp_path, run_id="run", attempt_id="attempt")


def test_release_never_removes_another_owners_metadata(tmp_path):
    lease = acquire(tmp_path)
    path = tmp_path / "locks/flight.lock"
    doc = json.loads(path.read_text())
    doc["token"] = "replaced"
    path.write_text(json.dumps(doc))
    with pytest.raises(GenerationLeaseError, match="ownership"):
        lease.release()
    assert json.loads(path.read_text())["token"] == "replaced"


def test_live_legacy_lock_blocks_new_lease(tmp_path):
    path = tmp_path / "locks/flight.lock"
    path.parent.mkdir()
    path.write_text(json.dumps({"pid": os.getpid(), "run_ids": ["legacy"]}))
    with pytest.raises(GenerationLeaseError, match="legacy"):
        acquire(tmp_path)


@pytest.mark.parametrize("pid", [999999999, os.getpid()])
def test_unreconciled_dead_owner_or_reused_pid_never_clears_metadata(tmp_path, pid):
    path = tmp_path / "locks/flight.lock"
    path.parent.mkdir()
    original = json.dumps({"pid": pid, "run_ids": ["unfinished"], "contact_state": "unknown"})
    path.write_text(original)
    with pytest.raises(GenerationLeaseError, match="unreconciled"):
        acquire(tmp_path)
    assert path.read_text() == original


def test_unreadable_lease_requires_reconciliation(tmp_path):
    path = tmp_path / "locks/flight.lock"
    path.parent.mkdir()
    path.write_text("broken")
    with pytest.raises(GenerationLeaseError, match="unreadable"):
        acquire(tmp_path)
    assert path.read_text() == "broken"


def test_worker_policy_requires_explicit_identity_and_attach_only():
    for kwargs in [
        {"expected_session_id": "", "lease_token": "x"},
        {"expected_session_id": "s", "lease_token": ""},
        {"expected_session_id": "s", "lease_token": "x", "require_resident": False},
    ]:
        with pytest.raises(GenerationLeaseError):
            WorkerExecutionPolicy(**kwargs)
