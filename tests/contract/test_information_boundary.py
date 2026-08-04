"""Contract 3: gold/reference/test-annotation/future-turn fields fail closed at the boundary."""

import pytest

from speech_aware_evidence_acquisition.contracts import (
    BoundaryViolation,
    assert_information_boundary,
)


CLEAN_REQUEST = {
    "request_id": "SAEA-E-000-smoke",
    "speech_ref": "earnings21-original/dev/0001",
    "visible_fields": ["speech_ref", "task_instruction"],
    "task_instruction": "transcribe the segment",
    "history": [{"turn": 1, "role": "user", "content": "..."}],
}


def test_clean_runtime_request_passes():
    assert_information_boundary(CLEAN_REQUEST)


@pytest.mark.parametrize(
    "forbidden",
    [
        "gold",
        "gold_answer",
        "gold_transcript",
        "reference_transcript",
        "test_annotation",
        "test_label",
        "answer_key",
        "future_turns",
    ],
)
def test_forbidden_top_level_field_is_rejected(forbidden):
    payload = dict(CLEAN_REQUEST)
    payload[forbidden] = "leak"
    with pytest.raises(BoundaryViolation):
        assert_information_boundary(payload)


def test_forbidden_field_is_rejected_at_any_nesting_depth():
    payload = dict(CLEAN_REQUEST)
    payload["context"] = {"documents": [{"meta": {"Reference_Transcript": "leak"}}]}
    with pytest.raises(BoundaryViolation):
        assert_information_boundary(payload)


def test_non_mapping_top_level_payload_fails_closed():
    with pytest.raises(BoundaryViolation):
        assert_information_boundary(["not", "a", "mapping"])


def test_unserializable_value_fails_closed():
    payload = dict(CLEAN_REQUEST)
    payload["blob"] = object()
    with pytest.raises(BoundaryViolation):
        assert_information_boundary(payload)
