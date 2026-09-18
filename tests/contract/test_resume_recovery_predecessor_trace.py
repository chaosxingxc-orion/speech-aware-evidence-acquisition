"""E10: the replay reads the REAL aborted attempt it was built for.

The B4b replicate attempt
(``SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2``) died at
2,922 of ~5,400 contacts on 2026-09-17 when the resident server was killed
externally -- code and request bytes unchanged, which is exactly the
infrastructure failure a resume-recovery applies to. Its attempt directory
holds only the trace: no ``outputs.jsonl`` exists, because canonical rows are
written at seal.

This test is read-only and contact-free. It opens ONE aborted attempt's trace
under ``SPEECHRL_DATA_DIR``, reports ids, counts and hashes, and asserts
nothing about, prints nothing of, and writes nothing into that directory.
Skipped wherever that data root is absent (CI, any clean checkout).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.flight.resume import (
    read_predecessor_attempt,
)

RUN_ID = "SAEA-SLURP-NATIVE-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-REPLICATE-V2"
ATTEMPT_ID = (
    "attempt-slurp-native-slot-store-v2-anchor-train-fold-a-replicate-generation-v2"
)
PROGRAM_ID = "phase-native-candidates-review-revise-v1"

#: Measured from the bytes on disk on 2026-09-18 (202,733,292 bytes).
TRACE_SHA256 = "ad7a78c77c26b8c7255e31fa897678b23609c9578933425b679594831e17c897"

#: What the aborted attempt actually reached: 584 rows had requests; 580 of
#: them emitted a terminal episode receipt with every response present; 4 lost
#: their last response when the server died. (A request-count read alone
#: suggests 577/7 -- three of the seven rows with fewer than five requests
#: nevertheless finished their episode, which is why completeness is decided
#: by the terminal receipt, never by counting contacts.)
COMPLETE_ROWS = 580
INCOMPLETE_ROWS = 4
STARTED_ROWS = 584
CONTACTS = 2922


def _attempt_dir() -> Path | None:
    data_root = os.environ.get("SPEECHRL_DATA_DIR")
    if not data_root:
        return None
    attempt_dir = Path(data_root) / "runs" / RUN_ID / ATTEMPT_ID
    return attempt_dir if (attempt_dir / f"{RUN_ID}.trace.jsonl").is_file() else None


@pytest.mark.skipif(
    _attempt_dir() is None,
    reason="the aborted B4b replicate attempt is not present under SPEECHRL_DATA_DIR",
)
def test_replay_reports_the_aborted_b4b_replicate_attempt():
    attempt_dir = _attempt_dir()
    assert attempt_dir is not None  # narrowed by the skip above
    scan = read_predecessor_attempt(
        run_id=RUN_ID,
        attempt_id=ATTEMPT_ID,
        attempt_dir=attempt_dir,
        expected_trace_sha256=TRACE_SHA256,
        program_id=PROGRAM_ID,
    )
    assert scan.trace_sha256 == TRACE_SHA256
    assert scan.contact_count() == CONTACTS
    assert len(scan.started_sample_ids) == STARTED_ROWS
    assert len(scan.complete_sample_ids) == COMPLETE_ROWS
    assert len(scan.incomplete_sample_ids) == INCOMPLETE_ROWS
    # Every incomplete row is incomplete for the recorded reason, and the two
    # sets partition the started rows -- no row is both, none is neither.
    assert set(scan.complete_sample_ids).isdisjoint(scan.incomplete_sample_ids)
    assert set(scan.complete_sample_ids) | set(scan.incomplete_sample_ids) == set(
        scan.started_sample_ids
    )
    for sample_id, reason in scan.incomplete.items():
        assert sample_id.startswith("slurp:train:")
        assert "terminal receipt" in reason

    # The replay hands back real RequestTiming records for the kept rows, and
    # one result per kept sample -- what the seal stage renders its row from.
    summaries, timings = scan.replay(scan.complete_sample_ids, controller_policy_id=PROGRAM_ID)
    assert len(summaries) == 1
    assert len(summaries[0].results) == COMPLETE_ROWS
    assert {timing.sample_id for timing in timings} == set(scan.complete_sample_ids)
    assert all(
        len(timing.request_sha256) == 64 and len(timing.response_text_sha256) == 64
        for timing in timings
    )

    block = scan.manifest_block(scan.complete_sample_ids, flown=500, partial=4)
    assert block["counts"] == {"kept": COMPLETE_ROWS, "flown": 500, "partial": 4}
    assert block["trace_sha256"] == TRACE_SHA256
