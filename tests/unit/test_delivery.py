"""Terminal delivery contracts shared by live execution and replay."""

from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.delivery import (
    deliver_terminal_response,
    normalize_terminal_response,
)
from speech_aware_evidence_acquisition.core.repair_alignment import accept_free_refresh
from speech_aware_evidence_acquisition.reproduction.obs_loop import (
    request_slice_with_retry,
)


@pytest.mark.parametrize(
    "text, saturated, skipped, expected",
    [
        ("  alpha beta\n", False, False, "alpha beta"),
        ("runaway", True, False, ""),
        (None, False, True, ""),
        ("   ", False, False, ""),
    ],
)
def test_terminal_input(text, saturated, skipped, expected):
    assert (
        normalize_terminal_response(text, saturated=saturated, skipped=skipped)
        == expected
    )


def test_success_requires_actual_text():
    with pytest.raises(ValueError, match="text"):
        normalize_terminal_response(None)


@pytest.mark.parametrize("saturated, skipped", [(True, False), (False, True)])
def test_quarantined_response_delivers_predecessor(saturated, skipped):
    result = deliver_terminal_response(
        "original draft",
        "raw runaway",
        rule=accept_free_refresh,
        saturated=saturated,
        skipped=skipped,
    )
    assert result.text == "original draft"
    assert result.refusal_reason == "empty_response"


def test_successful_retry_uses_terminal_request_and_stripped_text():
    seen = []

    def request(payload):
        seen.append(payload)
        if len(seen) == 1:
            raise TimeoutError("synthetic failure")
        return SimpleNamespace(text=" final words \n", usage={"completion_tokens": 2})

    rid, response, retry_of, saturated, skipped = request_slice_with_retry(
        request, lambda rid: rid, "actual", 1, 10
    )
    assert (rid, retry_of, seen) == ("actual-r1", "actual", ["actual", "actual-r1"])
    assert (
        deliver_terminal_response(
            "draft",
            response.text,
            rule=accept_free_refresh,
            saturated=saturated,
            skipped=skipped,
        ).text
        == "final words"
    )


def test_exhausted_retry_has_no_fabricated_response():
    def request(payload):
        raise TimeoutError("synthetic failure")

    rid, response, retry_of, saturated, skipped = request_slice_with_retry(
        request, lambda rid: rid, "actual", 1, 10
    )
    assert (rid, response, retry_of, saturated, skipped) == (
        "actual-r1",
        None,
        "actual",
        False,
        True,
    )
    assert (
        deliver_terminal_response(
            "draft", None, rule=accept_free_refresh, skipped=skipped
        ).text
        == "draft"
    )


def test_terminal_flags_must_be_explicit_booleans():
    with pytest.raises(ValueError, match="booleans"):
        normalize_terminal_response("text", skipped="false")


@pytest.mark.parametrize(
    "usage,cap,expected",
    [
        (None, 10, False),
        ({}, 10, False),
        ({"completion_tokens": True}, 10, False),
        ({"completion_tokens": 10}, None, False),
        ({"completion_tokens": 10}, True, False),
        ({"completion_tokens": 10}, {}, False),
        ({"completion_tokens": 10}, 10, True),
        ({"completion_tokens": 9}, 10, False),
    ],
)
def test_saturation_rule_matches_live_missing_and_malformed_usage(usage, cap, expected):
    from speech_aware_evidence_acquisition.core.delivery import (
        terminal_response_saturated,
    )

    assert terminal_response_saturated(usage, cap) is expected
