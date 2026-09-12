"""Unit coverage of the durable attempt store itself (R0 repair T4, invariant I6).

See tests/unit/test_frozen_core_adapter.py and tests/contract/test_attempt_accounting.py
for the behaviors this store exists to enforce, exercised through FrozenCoreAdapter and
the real gate respectively.
"""

import json
import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.attempts import (
    ATTEMPT_SCHEMA,
    CONTACT_KIND_SPEECH,
    CONTACT_KIND_TEXT_ENCODER,
    STATE_ABORTED,
    STATE_FINALIZED,
    STATE_OPENED,
    STATE_RESERVED,
    AttemptError,
    AttemptHandle,
    AttemptStore,
    validate_id,
)


@pytest.mark.parametrize(
    "value",
    ["run-1", "RUN_1", "a", "a.b-c_d", "9start-with-digit"],
)
def test_validate_id_accepts_well_formed_ids(value):
    assert validate_id(value, "label") == value


@pytest.mark.parametrize(
    "value",
    ["", "   ", None, 7, True, "has space", "has/slash", "has\\backslash", "../escape", ".dot-start", "-dash-start"],
)
def test_validate_id_rejects_malformed_ids(value):
    with pytest.raises(AttemptError):
        validate_id(value, "label")


def test_open_attempt_writes_a_schema_versioned_opened_document(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original",
        reserved_calls=5,
        reserved_audio_seconds=600.0,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    assert document["schema"] == ATTEMPT_SCHEMA
    assert document["state"] == STATE_OPENED
    assert document["reserved"] == {"calls": 5, "audio_seconds": 600.0}
    assert document["actual"] == {"calls": 0, "audio_seconds": 0.0}
    assert "contact_kind" not in document
    assert handle.path.read_bytes() == json.dumps(
        document, ensure_ascii=False, sort_keys=True, indent=2
    ).encode("utf-8")
    assert handle.state() == STATE_OPENED
    assert handle.actual_totals() == (0, 0.0)


def test_open_text_encoder_attempt_persists_kind_and_exact_zero_audio(tmp_path):
    store = AttemptStore(tmp_path / "attempts")

    handle = store.open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=152,
        reserved_audio_seconds=0,
        contact_kind=CONTACT_KIND_TEXT_ENCODER,
    )

    document = json.loads(handle.path.read_text(encoding="utf-8"))
    assert document["contact_kind"] == CONTACT_KIND_TEXT_ENCODER
    assert document["reserved"]["audio_seconds"] == 0.0


def test_default_speech_attempt_still_refuses_zero_reserved_audio(tmp_path):
    store = AttemptStore(tmp_path / "attempts")

    with pytest.raises(AttemptError, match="finite positive"):
        store.open_attempt(
            "run-1",
            "attempt-1",
            carrier_lock_key="audio2tool",
            reserved_calls=1,
            reserved_audio_seconds=0,
        )


@pytest.mark.parametrize("audio_seconds", [1, -1, 0.5])
def test_text_encoder_attempt_refuses_nonzero_reserved_audio(
    tmp_path, audio_seconds
):
    store = AttemptStore(tmp_path / "attempts")

    with pytest.raises(AttemptError, match="exactly zero"):
        store.open_attempt(
            "run-1",
            "attempt-1",
            carrier_lock_key="audio2tool",
            reserved_calls=1,
            reserved_audio_seconds=audio_seconds,
            contact_kind=CONTACT_KIND_TEXT_ENCODER,
        )


def test_open_attempt_refuses_unknown_contact_kind(tmp_path):
    store = AttemptStore(tmp_path / "attempts")

    with pytest.raises(AttemptError, match="contact_kind"):
        store.open_attempt(
            "run-1",
            "attempt-1",
            carrier_lock_key="audio2tool",
            reserved_calls=1,
            reserved_audio_seconds=1,
            contact_kind="unknown",
        )


def test_open_attempt_second_call_same_run_and_attempt_id_is_refused(tmp_path):
    """Campaign probe P4 at the store's own atomic-creation boundary."""

    store = AttemptStore(tmp_path / "attempts")
    store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original",
        reserved_calls=5,
        reserved_audio_seconds=600.0,
    )
    with pytest.raises(AttemptError, match="already reserved or opened"):
        store.open_attempt(
            "run-1", "attempt-1",
            carrier_lock_key="earnings21-original",
            reserved_calls=5,
            reserved_audio_seconds=600.0,
        )


def test_open_attempt_different_attempt_id_same_run_succeeds(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle2 = store.open_attempt(
        "run-1", "attempt-2",
        carrier_lock_key="earnings21-original", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    assert handle2.attempt_id == "attempt-2"


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(reserved_calls=0, reserved_audio_seconds=1.0),
        dict(reserved_calls=-1, reserved_audio_seconds=1.0),
        dict(reserved_calls=1.5, reserved_audio_seconds=1.0),
        dict(reserved_calls=1, reserved_audio_seconds=0.0),
        dict(reserved_calls=1, reserved_audio_seconds=float("nan")),
        dict(reserved_calls=1, reserved_audio_seconds=float("inf")),
    ],
)
def test_open_attempt_rejects_non_positive_or_non_finite_reservations(tmp_path, kwargs):
    store = AttemptStore(tmp_path / "attempts")
    with pytest.raises(AttemptError):
        store.open_attempt(
            "run-1", "attempt-1", carrier_lock_key="earnings21-original", **kwargs
        )


def test_open_attempt_rejects_blank_carrier_lock_key(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    with pytest.raises(AttemptError, match="carrier_lock_key"):
        store.open_attempt(
            "run-1", "attempt-1", carrier_lock_key="", reserved_calls=1, reserved_audio_seconds=1.0
        )


def test_record_usage_accumulates_and_persists(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    assert handle.record_usage(calls=1, audio_seconds=100.0) == (1, 100.0)
    assert handle.record_usage(calls=1, audio_seconds=50.5) == (2, 150.5)
    assert handle.actual_totals() == (2, 150.5)
    # A fresh handle over the same file reads back exactly what was persisted --
    # the file, not any in-process field, is the source of truth.
    from speech_aware_evidence_acquisition.core.attempts import AttemptHandle

    reread = AttemptHandle(path=handle.path, run_id="run-1", attempt_id="attempt-1")
    assert reread.actual_totals() == (2, 150.5)


def test_text_encoder_usage_accumulates_calls_with_exact_zero_audio(tmp_path):
    handle = AttemptStore(tmp_path / "attempts").open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=152,
        reserved_audio_seconds=0,
        contact_kind=CONTACT_KIND_TEXT_ENCODER,
    )

    assert handle.record_usage(calls=1, audio_seconds=0) == (1, 0.0)
    assert handle.record_usage(calls=2, audio_seconds=0.0) == (3, 0.0)
    assert handle.actual_totals() == (3, 0.0)


def test_text_encoder_usage_refuses_positive_audio(tmp_path):
    handle = AttemptStore(tmp_path / "attempts").open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=1,
        reserved_audio_seconds=0,
        contact_kind=CONTACT_KIND_TEXT_ENCODER,
    )

    with pytest.raises(AttemptError, match="exactly zero"):
        handle.record_usage(calls=1, audio_seconds=0.25)


def test_record_usage_accepts_explicit_persisted_speech_kind(tmp_path):
    handle = AttemptStore(tmp_path / "attempts").open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=1,
        reserved_audio_seconds=1,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    document["contact_kind"] = CONTACT_KIND_SPEECH
    handle.path.write_text(json.dumps(document), encoding="utf-8")

    assert handle.record_usage(calls=1, audio_seconds=0.5) == (1, 0.5)


def test_record_usage_refuses_a_malformed_persisted_contact_kind(tmp_path):
    handle = AttemptStore(tmp_path / "attempts").open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=1,
        reserved_audio_seconds=1,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    document["contact_kind"] = "unknown"
    handle.path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(AttemptError, match="persisted contact_kind"):
        handle.record_usage(calls=1, audio_seconds=0.5)


@pytest.mark.parametrize("section", ["reserved", "actual"])
def test_text_encoder_usage_refuses_nonzero_persisted_audio_state(
    tmp_path, section
):
    handle = AttemptStore(tmp_path / "attempts").open_attempt(
        "run-1",
        "attempt-1",
        carrier_lock_key="audio2tool",
        reserved_calls=1,
        reserved_audio_seconds=0,
        contact_kind=CONTACT_KIND_TEXT_ENCODER,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    document[section]["audio_seconds"] = 0.25
    handle.path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(AttemptError, match=f"persisted text-encoder {section}"):
        handle.record_usage(calls=1, audio_seconds=0)


def test_record_usage_refuses_when_not_opened(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    document["state"] = "FINALIZED"
    handle.path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(AttemptError, match="not OPENED"):
        handle.record_usage(calls=1, audio_seconds=1.0)


@pytest.mark.parametrize(
    "kwargs",
    [dict(calls=0, audio_seconds=1.0), dict(calls=-1, audio_seconds=1.0), dict(calls=1, audio_seconds=0.0)],
)
def test_record_usage_rejects_non_positive_values(tmp_path, kwargs):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1",
        carrier_lock_key="earnings21-original", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    with pytest.raises(AttemptError):
        handle.record_usage(**kwargs)


def test_prior_actual_usage_returns_zero_when_run_dir_missing(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    assert store.prior_actual_usage("never-opened") == (0, 0.0)


def test_prior_actual_usage_sums_across_multiple_attempts_for_the_same_run(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    h1 = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h1.record_usage(calls=2, audio_seconds=40.0)
    h2 = store.open_attempt(
        "run-1", "attempt-2", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h2.record_usage(calls=3, audio_seconds=60.0)
    assert store.prior_actual_usage("run-1") == (5, 100.0)


def test_prior_actual_usage_excludes_the_named_attempt_id(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    h1 = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h1.record_usage(calls=2, audio_seconds=40.0)
    h2 = store.open_attempt(
        "run-1", "attempt-2", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h2.record_usage(calls=3, audio_seconds=60.0)
    assert store.prior_actual_usage("run-1", exclude_attempt_id="attempt-2") == (2, 40.0)


def test_all_actual_usage_sums_across_multiple_runs(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    ).record_usage(calls=1, audio_seconds=10.0)
    store.open_attempt(
        "run-2", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    ).record_usage(calls=4, audio_seconds=40.0)
    assert store.all_actual_usage() == (5, 50.0, 0.0)


def test_all_actual_usage_returns_zero_when_store_root_missing(tmp_path):
    store = AttemptStore(tmp_path / "does-not-exist")
    assert store.all_actual_usage() == (0, 0.0, 0.0)


def _write_attempt_file(store: AttemptStore, run_id: str, attempt_id: str, actual: dict) -> None:
    """Directly write an attempt file (bypassing open_attempt/record_usage's
    own validation) so a malformed/tampered ``actual`` block can be tested
    at the READ side, in _sum_actual_for_run itself."""

    run_dir = store.attempts_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    document = {
        "schema": ATTEMPT_SCHEMA,
        "run_id": run_id,
        "attempt_id": attempt_id,
        "carrier_lock_key": "c",
        "state": STATE_OPENED,
        "reserved": {"calls": 5, "audio_seconds": 500.0},
        "actual": actual,
    }
    (run_dir / f"{attempt_id}.json").write_text(json.dumps(document), encoding="utf-8")


# ---------------------------------------------------------------------------
# MINOR 1 (external-threat-model review round 3): a JSON-valid attempt file
# whose actual.calls/audio_seconds/gpu_seconds is non-numeric must never leak
# a bare ValueError past this module's own documented AttemptError contract
# (and therefore past every real caller's `except AttemptError` wrapper); a
# negative or non-finite persisted value must never silently deflate the
# summed actual-usage total this store reports.
# ---------------------------------------------------------------------------


def test_prior_actual_usage_wraps_a_non_numeric_calls_field_as_attempt_error(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(store, "run-1", "attempt-1", {"calls": "lots", "audio_seconds": 10.0})
    with pytest.raises(AttemptError):
        store.prior_actual_usage("run-1")


def test_all_actual_usage_wraps_a_non_numeric_gpu_seconds_field_as_attempt_error(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(
        store, "run-1", "attempt-1",
        {"calls": 1, "audio_seconds": 10.0, "gpu_seconds": "a lot"},
    )
    with pytest.raises(AttemptError):
        store.all_actual_usage()


def test_prior_actual_usage_refuses_a_negative_persisted_calls_value(tmp_path):
    """A corrupted/hand-tampered attempt file with a NEGATIVE calls value
    must never silently deflate the summed actual-usage total this store
    reports."""

    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(store, "run-1", "attempt-1", {"calls": -100, "audio_seconds": 10.0})
    with pytest.raises(AttemptError, match="non-negative"):
        store.prior_actual_usage("run-1")


def test_all_actual_usage_refuses_a_negative_persisted_audio_seconds_value(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(store, "run-1", "attempt-1", {"calls": 1, "audio_seconds": -5.0})
    with pytest.raises(AttemptError, match="non-negative"):
        store.all_actual_usage()


def test_prior_actual_usage_refuses_a_non_finite_persisted_value(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(store, "run-1", "attempt-1", {"calls": 1, "audio_seconds": float("nan")})
    with pytest.raises(AttemptError, match="finite"):
        store.prior_actual_usage("run-1")


def test_prior_actual_usage_still_sums_legitimate_values_after_the_fix(tmp_path):
    """Regression: ordinary, well-formed attempt files (including an older
    file missing gpu_seconds entirely) still sum correctly."""

    store = AttemptStore(tmp_path / "attempts")
    _write_attempt_file(store, "run-1", "attempt-1", {"calls": 3, "audio_seconds": 30.0})
    assert store.prior_actual_usage("run-1") == (3, 30.0)


# ---------------------------------------------------------------------------
# fix-wave2 Minor: gpu hours had no derived counterpart -- record_gpu_seconds
# is the write path core.driver.run_experiment feeds a whole-run measured
# total back through; all_actual_usage's 3rd element is that durable per-run
# GPU-seconds figure, summed across runs.
# ---------------------------------------------------------------------------


def test_record_gpu_seconds_accumulates_and_persists(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    assert handle.record_gpu_seconds(12.5) == 12.5
    assert handle.record_gpu_seconds(2.5) == 15.0
    assert handle.actual_gpu_seconds() == 15.0


def test_record_gpu_seconds_allows_zero(tmp_path):
    """Unlike record_usage's calls/audio_seconds (strictly positive per
    request), a genuinely idle GPU for an entire run legitimately measures
    0.0 gpu_seconds -- that must not be refused as a non-positive value."""

    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    assert handle.record_gpu_seconds(0.0) == 0.0


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_record_gpu_seconds_rejects_negative_or_non_finite(tmp_path, bad):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    with pytest.raises(AttemptError):
        handle.record_gpu_seconds(bad)


def test_record_gpu_seconds_refuses_when_not_opened(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_finalized()
    with pytest.raises(AttemptError, match="not OPENED"):
        handle.record_gpu_seconds(1.0)


def test_actual_gpu_seconds_defaults_to_zero_for_an_attempt_file_predating_the_field(tmp_path):
    """An attempt file written before gpu_seconds existed (no key in
    'actual') must read back as 0.0, never raise."""

    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    assert "gpu_seconds" not in document["actual"]
    assert handle.actual_gpu_seconds() == 0.0


def test_all_actual_usage_includes_recorded_gpu_seconds(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    h1 = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h1.record_usage(calls=1, audio_seconds=10.0)
    h1.record_gpu_seconds(3.0)
    h2 = store.open_attempt(
        "run-2", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0
    )
    h2.record_usage(calls=4, audio_seconds=40.0)
    h2.record_gpu_seconds(7.5)
    assert store.all_actual_usage() == (5, 50.0, 10.5)


# ---------------------------------------------------------------------------
# R0 repair T6 carried minor (from the T4 review): open_attempt's
# create+write must be atomic, not O_EXCL-create-then-write-separately -- a
# concurrent reader could otherwise observe an empty file mid-write and raise
# JSONDecodeError/AttemptError.
# ---------------------------------------------------------------------------


def test_open_attempt_stages_full_content_before_the_final_path_ever_exists(tmp_path, monkeypatch):
    """Deterministic proof of atomicity: whatever function makes ``path``
    visible in the directory (``os.link`` in the current implementation) is
    called with a source file that ALREADY carries the full, final RESERVED
    document -- and at the moment it is called, ``path`` does not exist yet.
    A concurrent reader therefore only ever sees "file not found" or a fully
    populated, valid document -- never a 0-byte or truncated one."""

    observed: list[bytes] = []
    real_link = os.link

    def _spy_link(src, dst):
        assert not os.path.exists(dst), "the final path must not exist before the atomic step"
        observed.append(open(src, "rb").read())
        return real_link(src, dst)

    monkeypatch.setattr(os, "link", _spy_link)
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=5, reserved_audio_seconds=500.0,
    )
    assert len(observed) == 1
    staged = json.loads(observed[0].decode("utf-8"))
    # Staged content is RESERVED (mark_opened() only runs AFTER the atomic
    # publish); the final file on disk is OPENED.
    assert staged["state"] == STATE_RESERVED
    assert staged["schema"] == ATTEMPT_SCHEMA
    assert handle.state() == STATE_OPENED


def test_open_attempt_leaves_no_temp_file_behind_on_success_or_collision(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    with pytest.raises(AttemptError):
        store.open_attempt(
            "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
        )
    run_dir = tmp_path / "attempts" / "run-1"
    names = sorted(entry.name for entry in run_dir.iterdir())
    assert names == ["attempt-1.json"], f"stray temp file(s) left behind: {names}"


# ---------------------------------------------------------------------------
# mark_finalized / mark_aborted (R0 repair T6, invariant I7): the terminal
# transitions core.bundle.finalize_bundle relies on.
# ---------------------------------------------------------------------------


def test_mark_finalized_transitions_opened_to_finalized(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_finalized()
    assert handle.state() == STATE_FINALIZED


def test_mark_finalized_refuses_when_not_opened(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_finalized()
    with pytest.raises(AttemptError, match="not OPENED"):
        handle.mark_finalized()


def test_mark_aborted_transitions_opened_to_aborted_and_records_reason(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_aborted("transport exploded")
    assert handle.state() == STATE_ABORTED
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    assert document["failure_reason"] == "transport exploded"


def test_mark_aborted_refuses_a_blank_reason(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    with pytest.raises(AttemptError, match="reason"):
        handle.mark_aborted("")


def test_mark_aborted_refuses_from_a_terminal_state(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_finalized()
    with pytest.raises(AttemptError, match="RESERVED/OPENED"):
        handle.mark_aborted("too late")


def test_store_abort_if_opened_marks_an_opened_attempt(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    assert store.abort_if_opened("run-1", "attempt-1", reason="boom") is True
    assert handle.state() == STATE_ABORTED


def test_store_abort_if_opened_is_a_noop_when_never_opened(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    assert store.abort_if_opened("run-1", "never-opened", reason="boom") is False


def test_store_abort_if_opened_is_a_noop_on_an_already_terminal_attempt(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-1", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    handle.mark_finalized()
    assert store.abort_if_opened("run-1", "attempt-1", reason="too late") is False
    assert handle.state() == STATE_FINALIZED


def test_store_handle_returns_a_handle_without_requiring_the_file_to_exist(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.handle("run-1", "attempt-1")
    assert handle.path == tmp_path / "attempts" / "run-1" / "attempt-1.json"
    assert not handle.path.exists()


def _record_usage_worker(path: str, run_id: str, attempt_id: str) -> None:
    handle = AttemptHandle(path=Path(path), run_id=run_id, attempt_id=attempt_id)
    handle.record_usage(calls=1, audio_seconds=1.0)


def test_cross_process_usage_updates_are_serialized(tmp_path):
    import multiprocessing
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-process", "attempt-1", carrier_lock_key="c", reserved_calls=20, reserved_audio_seconds=20.0,
    )
    context = multiprocessing.get_context("fork")
    with context.Pool(2) as pool:
        pool.starmap(
            _record_usage_worker,
            [(str(handle.path), "run-process", "attempt-1")] * 10,
        )
    assert handle.actual_totals() == (10, 10.0)


def test_concurrent_terminal_mutations_leave_one_terminal_state(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-race", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )

    def finalize():
        try:
            handle.mark_finalized()
            return "finalized"
        except AttemptError:
            return "refused"

    def abort():
        try:
            handle.mark_aborted("race")
            return "aborted"
        except AttemptError:
            return "refused"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda fn: fn(), (finalize, abort)))
    assert sorted(results).count("refused") == 1
    assert handle.state() in {STATE_FINALIZED, STATE_ABORTED}
    with pytest.raises(AttemptError, match="not OPENED"):
        handle.record_usage(calls=1, audio_seconds=1.0)


def test_finalize_with_receipt_is_exactly_idempotent(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-receipt", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    digest = "a" * 64
    handle.finalize_with_receipt("runs/run-manifest.json", digest, "run-manifest")
    handle.finalize_with_receipt("runs/run-manifest.json", digest, "run-manifest")
    document = json.loads(handle.path.read_text(encoding="utf-8"))
    assert document["state"] == STATE_FINALIZED
    assert document["finalization"] == {
        "path": "runs/run-manifest.json",
        "sha256": digest,
        "kind": "run-manifest",
    }
    with pytest.raises(AttemptError, match="not OPENED"):
        handle.finalize_with_receipt("runs/other.json", "b" * 64, "run-manifest")


@pytest.mark.parametrize(
    ("path", "sha256", "kind"),
    [("", "a" * 64, "receipt"), ("receipt", "A" * 64, "receipt"), ("receipt", "a" * 63, "receipt"), ("receipt", "a" * 64, "")],
)
def test_finalize_with_receipt_validates_binding(tmp_path, path, sha256, kind):
    store = AttemptStore(tmp_path / "attempts")
    handle = store.open_attempt(
        "run-receipt", "attempt-1", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    with pytest.raises(AttemptError, match="finalization"):
        handle.finalize_with_receipt(path, sha256, kind)


def test_finalize_with_receipt_refuses_aborted_and_legacy_finalized(tmp_path):
    store = AttemptStore(tmp_path / "attempts")
    aborted = store.open_attempt(
        "run-receipt", "attempt-aborted", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    aborted.mark_aborted("failure")
    with pytest.raises(AttemptError, match="not OPENED"):
        aborted.finalize_with_receipt("receipt", "a" * 64, "kind")

    legacy = store.open_attempt(
        "run-receipt", "attempt-legacy", carrier_lock_key="c", reserved_calls=1, reserved_audio_seconds=1.0,
    )
    legacy.mark_finalized()
    with pytest.raises(AttemptError, match="not OPENED"):
        legacy.finalize_with_receipt("receipt", "a" * 64, "kind")
