import importlib.util
import json
from pathlib import Path

import pytest


SOURCE = Path(__file__).parents[2] / "scripts" / "watch_attempt.py"
SPEC = importlib.util.spec_from_file_location("watch_attempt", SOURCE)
watch_attempt = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(watch_attempt)

RUN_ID = "SYNTHETIC-RUN-V1"
ATTEMPT_ID = "synthetic-attempt-v1"


def _path(tmp_path):
    return watch_attempt.authoritative_attempt_path(tmp_path, RUN_ID, ATTEMPT_ID)


def _write_attempt(path, *, state="OPENED", calls=0, audio_seconds=0.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "saea-attempt-v1",
                "run_id": RUN_ID,
                "attempt_id": ATTEMPT_ID,
                "carrier_lock_key": "synthetic-carrier",
                "state": state,
                "reserved": {"calls": 12, "audio_seconds": 12.0},
                "actual": {"calls": calls, "audio_seconds": audio_seconds},
            }
        )
    )


def test_attempt_path_is_derived_and_rejects_non_plain_ids(tmp_path):
    assert _path(tmp_path) == (
        tmp_path / "attempts" / RUN_ID / f"{ATTEMPT_ID}.json"
    )
    with pytest.raises(ValueError, match="run_id must match"):
        watch_attempt.authoritative_attempt_path(tmp_path, "../escape", ATTEMPT_ID)


def test_missing_ledger_waits_once_and_remains_silent(tmp_path):
    attempt, status = watch_attempt.read_attempt(_path(tmp_path), RUN_ID, ATTEMPT_ID)
    assert attempt is None
    assert status == "waiting"
    events = watch_attempt.Events()
    assert events.update(None, None, True, False, None, True, 0) == [
        "waiting-for-attempt-ledger"
    ]
    assert events.update(None, None, True, False, None, True, 1) == []


@pytest.mark.parametrize(
    "document,error",
    [
        (
            {"run_id": RUN_ID, "attempt_id": ATTEMPT_ID},
            "attempt schema must be saea-attempt-v1",
        ),
        (
            {
                "schema": "saea-attempt-v1",
                "run_id": "WRONG-RUN",
                "attempt_id": ATTEMPT_ID,
                "state": "OPENED",
                "actual": {"calls": 0, "audio_seconds": 0.0},
            },
            "attempt identity mismatch",
        ),
    ],
)
def test_malformed_schema_or_identity_is_terminal_observer_error(
    tmp_path, document, error
):
    path = _path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(document))
    attempt, status = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    assert attempt is None
    assert error in status
    assert watch_attempt.Events().update(
        None, None, True, False, status, False, 0
    ) == ["observer-error"]


@pytest.mark.parametrize(
    ("calls", "audio_seconds"),
    [(True, 0.0), (-1, 0.0), (1.5, 0.0), (0, -1.0), (0, float("inf"))],
)
def test_invalid_actual_counts_are_rejected(tmp_path, calls, audio_seconds):
    path = _path(tmp_path)
    _write_attempt(path, calls=calls, audio_seconds=audio_seconds)
    attempt, status = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    assert attempt is None
    assert status.startswith("invalid-attempt-metadata:")


def test_first_progress_then_unchanged_is_silent(tmp_path):
    path = _path(tmp_path)
    _write_attempt(path, calls=1, audio_seconds=1.0)
    attempt, status = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    assert status is None
    events = watch_attempt.Events()
    assert events.update(attempt, None, True, False, None, False, 10) == [
        "phase-change",
        "first-progress",
    ]
    assert events.update(attempt, None, True, False, None, False, 11) == []


def test_stall_is_one_shot_and_progress_resumes(tmp_path):
    path = _path(tmp_path)
    _write_attempt(path, calls=1, audio_seconds=1.0)
    attempt, _ = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    events = watch_attempt.Events()
    events.update(attempt, None, True, False, None, False, 0)
    assert events.update(attempt, None, True, False, None, False, 600) == [
        "unchanged-calls-over-600s"
    ]
    assert events.update(attempt, None, True, False, None, False, 601) == []
    _write_attempt(path, calls=2, audio_seconds=2.0)
    resumed, _ = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    assert events.update(resumed, None, True, False, None, False, 602) == [
        "resumed-progress"
    ]


def test_aborted_is_terminal_while_campaign_pid_is_live(tmp_path):
    path = _path(tmp_path)
    _write_attempt(path, state="ABORTED", calls=2, audio_seconds=2.0)
    attempt, status = watch_attempt.read_attempt(path, RUN_ID, ATTEMPT_ID)
    assert status is None
    assert watch_attempt.Events().update(
        attempt, None, True, False, None, False, 0
    ) == ["attempt-terminal", "first-progress"]


def test_pid_reuse_is_terminal_identity_loss():
    assert watch_attempt.Events().update(
        None, None, False, True, None, False, 0
    ) == ["pid-identity-loss"]
