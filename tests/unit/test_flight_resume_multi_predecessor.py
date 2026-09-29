"""E10d (2026-09-29): multi-predecessor, seal-only resume completion.

These tests exercise the model-free merge/classification logic in
``core.flight.resume`` directly, over small SYNTHETIC ``PredecessorAttempt``
objects built by hand (no episode harness, no server, no trace files) --
the merge itself does not care how a predecessor's COMPLETE rows were
produced, only that each sample id is claimed by exactly one predecessor.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.core.flight.resume import (
    MergedPredecessors,
    PredecessorAttempt,
    ReplayedEpisodeResult,
    ReplayedPhaseSummary,
    ResumeDeclaration,
    ResumeRecoveryError,
    resume_declarations_from_document,
)


def _result(sample_id: str) -> ReplayedEpisodeResult:
    return ReplayedEpisodeResult(
        sample_id=sample_id,
        final_response_text=f"answer-{sample_id}",
        contacts=(),
        native_episode_receipt={"schema": "test", "sample_id": sample_id},
    )


def _predecessor(
    attempt_id: str, sample_ids, *, incomplete=None, run_id="SAEA-TEST-RUN",
) -> PredecessorAttempt:
    incomplete = dict(incomplete or {})
    complete = {sample_id: _result(sample_id) for sample_id in sample_ids}
    order = tuple(sample_ids) + tuple(incomplete)
    contacts = {sample_id: () for sample_id in order}
    from pathlib import Path

    return PredecessorAttempt(
        run_id=run_id,
        attempt_id=attempt_id,
        trace_path=Path(f"/fake/{attempt_id}.trace.jsonl"),
        trace_sha256="a" * 64 if attempt_id == "attempt-a" else "b" * 64,
        contacts=contacts,
        complete=complete,
        incomplete=incomplete,
        record_count=len(order),
        _sample_order=order,
    )


# ---------------------------------------------------------------------------
# resume_declarations_from_document
# ---------------------------------------------------------------------------


def test_single_mapping_normalises_to_a_one_item_tuple():
    declarations = resume_declarations_from_document(
        {"attempt_id": "a", "trace_sha256": "0" * 64}
    )
    assert declarations == (ResumeDeclaration(attempt_id="a", trace_sha256="0" * 64),)


def test_a_list_of_mappings_normalises_in_declared_order():
    declarations = resume_declarations_from_document([
        {"attempt_id": "a", "trace_sha256": "0" * 64},
        {"attempt_id": "b", "trace_sha256": "1" * 64},
    ])
    assert [d.attempt_id for d in declarations] == ["a", "b"]


def test_an_empty_list_is_refused():
    with pytest.raises(ResumeRecoveryError, match="at least one predecessor"):
        resume_declarations_from_document([])


def test_a_duplicate_attempt_id_in_the_list_is_refused():
    with pytest.raises(ResumeRecoveryError, match="names the same predecessor"):
        resume_declarations_from_document([
            {"attempt_id": "a", "trace_sha256": "0" * 64},
            {"attempt_id": "a", "trace_sha256": "1" * 64},
        ])


def test_a_malformed_item_inside_the_list_still_refuses():
    with pytest.raises(ResumeRecoveryError):
        resume_declarations_from_document([
            {"attempt_id": "a", "trace_sha256": "0" * 64},
            {"attempt_id": "b"},
        ])


@pytest.mark.parametrize("document", (None, 1, "attempt-a", ("attempt-a",)))
def test_a_document_that_is_neither_shape_is_refused(document):
    with pytest.raises(ResumeRecoveryError):
        resume_declarations_from_document(document)


# ---------------------------------------------------------------------------
# MergedPredecessors: classification and conflict refusal.
# ---------------------------------------------------------------------------


def test_disjoint_predecessors_merge_into_the_union():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1", "s2")),
        _predecessor("attempt-b", ("s3",)),
    ))
    assert merged.complete_sample_ids == ("s1", "s2", "s3")
    assert merged.origin("s1").attempt_id == "attempt-a"
    assert merged.origin("s3").attempt_id == "attempt-b"


def test_overlapping_predecessors_are_refused_naming_both_attempts():
    with pytest.raises(ResumeRecoveryError, match="attempt-a.*attempt-b|attempt-b.*attempt-a"):
        MergedPredecessors((
            _predecessor("attempt-a", ("s1", "s2")),
            _predecessor("attempt-b", ("s2", "s3")),
        ))


def test_a_single_predecessor_merges_trivially():
    merged = MergedPredecessors((_predecessor("attempt-a", ("s1",)),))
    assert merged.complete_sample_ids == ("s1",)


def test_a_merge_with_no_predecessors_is_refused():
    with pytest.raises(ResumeRecoveryError, match="at least one predecessor"):
        MergedPredecessors(())


def test_incomplete_reasons_merge_across_predecessors():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1",), incomplete={"s2": "reason-a"}),
        _predecessor("attempt-b", ("s3",), incomplete={"s4": "reason-b"}),
    ))
    assert merged.incomplete == {"s2": "reason-a", "s4": "reason-b"}


def test_incomplete_tie_break_keeps_the_first_declared_reason():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1",), incomplete={"s2": "reason-a"}),
        _predecessor("attempt-b", (), incomplete={"s2": "reason-b"}),
    ))
    assert merged.incomplete["s2"] == "reason-a"


def test_origin_refuses_a_sample_kept_by_nobody():
    merged = MergedPredecessors((_predecessor("attempt-a", ("s1",)),))
    with pytest.raises(ResumeRecoveryError, match="not COMPLETE in any"):
        merged.origin("s9")


# ---------------------------------------------------------------------------
# MergedPredecessors.replay: one merged ReplayedPhaseSummary, never one per
# predecessor (FlightRuntime._rows_from_phase_summaries requires every
# summary it is handed to describe the same whole roster).
# ---------------------------------------------------------------------------


def test_replay_merges_every_predecessors_rows_into_one_summary():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1", "s2")),
        _predecessor("attempt-b", ("s3",)),
    ))
    summaries, timings = merged.replay(("s1", "s2", "s3"), controller_policy_id="prog")
    assert len(summaries) == 1
    (summary,) = summaries
    assert isinstance(summary, ReplayedPhaseSummary)
    assert summary.controller_policy_id == "prog"
    assert {result.sample_id for result in summary.results} == {"s1", "s2", "s3"}
    assert timings == ()


def test_replay_can_be_asked_for_a_subset_of_the_union():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1", "s2")),
        _predecessor("attempt-b", ("s3",)),
    ))
    (summary,), _timings = merged.replay(("s3",))
    assert [result.sample_id for result in summary.results] == ["s3"]


def test_replay_refuses_a_sample_no_predecessor_completed():
    merged = MergedPredecessors((_predecessor("attempt-a", ("s1",)),))
    with pytest.raises(ResumeRecoveryError, match="not COMPLETE in any"):
        merged.replay(("s9",))


# ---------------------------------------------------------------------------
# MergedPredecessors.manifest_blocks: one block per predecessor that kept
# something, sharing the resuming attempt's own flown/partial totals.
# ---------------------------------------------------------------------------


def test_manifest_blocks_names_every_predecessor_that_kept_a_row():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1", "s2")),
        _predecessor("attempt-b", ("s3",)),
    ))
    blocks = merged.manifest_blocks(("s1", "s2", "s3"), flown=1, partial=0)
    assert len(blocks) == 2
    by_attempt = {block["attempt_id"]: block for block in blocks}
    assert by_attempt["attempt-a"]["kept_sample_ids"] == ["s1", "s2"]
    assert by_attempt["attempt-b"]["kept_sample_ids"] == ["s3"]
    for block in blocks:
        assert block["counts"]["flown"] == 1
        assert block["counts"]["partial"] == 0
        assert block["counts"]["kept"] == len(block["kept_sample_ids"])


def test_manifest_blocks_omits_a_predecessor_that_kept_nothing_of_this_resume():
    merged = MergedPredecessors((
        _predecessor("attempt-a", ("s1",)),
        _predecessor("attempt-b", ("s2",)),
    ))
    blocks = merged.manifest_blocks(("s1",), flown=0, partial=0)
    assert len(blocks) == 1
    assert blocks[0]["attempt_id"] == "attempt-a"
