"""Contact-free tests for the root-owned worker lease handoff."""
import io
import json
import stat

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell
from speech_aware_evidence_acquisition.core.flight.lease import GenerationLease, GenerationLeaseError
from speech_aware_evidence_acquisition.core.flight.lease_cli import LeaseHandoffError, handoff_worker_lease


def cell(*, ready=True, dependency=False, stage="worker"):
    readiness = {"state": "ready" if ready else "held", "reason": "test hold"}
    if dependency:
        readiness["depends_on"] = [{"run_id": "prior", "required_state": "scored"}]
    return CampaignCell.from_document({
        "cell_id": "worker-cell", "model_fragment": "model", "dataset_fragment": "dataset",
        "baseline_fragment": "baseline", "run_id": "run", "attempt_id": "attempt",
        "allowed_execution_stages": [stage], "readiness": readiness,
    })


class Runtime:
    def session_required_identity(self):
        return {"host": "127.0.0.1", "port": 8080}


class Lease:
    token = "secret-token"
    def __init__(self):
        self.released = False
        self.preserved = False
    def release(self):
        self.released = True
    def __exit__(self, *args):
        self.preserved = True


def run(
    tmp_path, *, stdin="release\n", lease=None, selected=None,
    token="coordination/worker.token", stage="worker", resident=None,
):
    lease = lease or Lease()
    out = io.StringIO()
    result = handoff_worker_lease(
        repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
        lock_path=tmp_path / "lock", experiment="experiment", cell=selected or cell(),
        owner="root", expected_session_id="session", token_output=token,
        stage=stage,
        input_stream=io.StringIO(stdin), output_stream=out,
        runtime_factory=lambda *args, **kwargs: Runtime(), lease_factory=lambda *args, **kwargs: lease,
        resident_finder=lambda _: resident if resident is not None else (tmp_path / "session", {
            "session_id": "session", "identity": {"host": "127.0.0.1", "port": 8080},
        }), study_head_factory=lambda _: "a" * 40,
    )
    return result, lease, out.getvalue()


@pytest.mark.parametrize("stage", ["prepare-window-features", "prompt-fit"])
def test_preparation_stage_issues_and_releases_custody(tmp_path, stage):
    result, lease, output = run(
        tmp_path,
        selected=cell(stage=stage),
        stage=stage,
        token="coordination/prep.token",
    )
    assert result == 0 and lease.released
    assert not (tmp_path / "coordination/prep.token").exists()
    assert f"{stage}-lease-ready" in output
    assert "secret-token" not in output

    result, lease, _ = run(
        tmp_path,
        stdin="",
        selected=cell(stage=stage),
        stage=stage,
        token="coordination/prep-preserved.token",
    )
    assert result == 2 and lease.preserved
    token = json.loads(
        (tmp_path / "coordination/prep-preserved.token").read_text()
    )
    assert token["stage"] == stage


@pytest.mark.parametrize(
    ("selected", "stage", "message"),
    [
        (cell(stage="worker"), "prepare-window-features", "does not permit"),
        (cell(stage="worker"), "prompt-fit", "does not permit"),
        (cell(stage="prompt-fit", ready=False), "prompt-fit", "readiness"),
        (cell(stage="prepare-window-features", ready=False), "prepare-window-features", "readiness"),
    ],
)
def test_prepare_stage_requires_exact_declared_mode_and_ready_state(
    tmp_path, selected, stage, message
):
    with pytest.raises(LeaseHandoffError, match=message):
        run(tmp_path, selected=selected, stage=stage, token="coordination/no.token")
    assert not (tmp_path / "coordination/no.token").exists()


@pytest.mark.parametrize("stage", ["prepare-window-features", "prompt-fit"])
def test_prepare_stage_refuses_stale_resident_identity_before_lease(tmp_path, stage):
    stale = (
        tmp_path / "session",
        {"session_id": "session", "identity": {"host": "127.0.0.1", "port": 9999}},
    )
    with pytest.raises(LeaseHandoffError, match="identity mismatch"):
        run(
            tmp_path,
            selected=cell(stage=stage),
            stage=stage,
            token="coordination/no.token",
            resident=stale,
        )
    assert not (tmp_path / "coordination/no.token").exists()


def test_release_clears_secret_and_reports_only_public_identity(tmp_path):
    result, lease, output = run(tmp_path)
    token_path = tmp_path / "coordination/worker.token"
    assert result == 0 and lease.released and not token_path.exists()
    assert "secret-token" not in output
    assert '"run_id": "run"' in output


@pytest.mark.parametrize("stdin", ["", "stop\n", " release\n", "release now\n"])
def test_eof_or_wrong_input_preserves_lease_and_token(tmp_path, stdin):
    result, lease, _ = run(tmp_path, stdin=stdin)
    assert result == 2 and not lease.released and lease.preserved
    token_path = tmp_path / "coordination/worker.token"
    assert token_path.is_file()
    assert stat.S_IMODE(token_path.stat().st_mode) == 0o600


def test_readiness_dependency_and_resident_refusals_issue_no_token(tmp_path):
    with pytest.raises(LeaseHandoffError, match="readiness"):
        run(tmp_path, selected=cell(ready=False))
    with pytest.raises(LeaseHandoffError, match="dependencies"):
        run(tmp_path, selected=cell(dependency=True))
    with pytest.raises(LeaseHandoffError, match="resident session"):
        handoff_worker_lease(
            repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
            lock_path=tmp_path / "lock", experiment="experiment", cell=cell(), owner="root",
            expected_session_id="session", token_output="coordination/no.token",
            runtime_factory=lambda *args, **kwargs: Runtime(), lease_factory=lambda *args, **kwargs: Lease(),
            resident_finder=lambda _: None, study_head_factory=lambda _: "a" * 40,
        )
    assert not (tmp_path / "coordination/no.token").exists()


def test_token_path_is_confined_and_never_overwritten(tmp_path):
    with pytest.raises(LeaseHandoffError, match="confined"):
        run(tmp_path, token="../escape.token")
    token_path = tmp_path / "coordination/worker.token"
    token_path.parent.mkdir()
    token_path.write_text("existing")
    with pytest.raises(LeaseHandoffError, match="overwrite"):
        run(tmp_path)
    assert token_path.read_text() == "existing"


def test_real_generation_lease_rejects_a_second_owner(tmp_path):
    first = GenerationLease.acquire(
        tmp_path, owner="root", run_id="run", attempt_id="attempt", session_id="session", study_head="a" * 40,
    )
    try:
        with pytest.raises(GenerationLeaseError, match="already held"):
            GenerationLease.acquire(
                tmp_path, owner="other", run_id="run2", attempt_id="attempt2", session_id="session2", study_head="b" * 40,
            )
    finally:
        first.release()
