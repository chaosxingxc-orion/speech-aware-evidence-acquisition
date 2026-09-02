from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.a2t_executable_ground_prompt_fit import (
    GroundPromptFitError,
    build_ground_envelopes,
    compute_prompt_fit_bounds,
    measure_text_prompt_tokens,
    validate_ground_observation,
    validate_registered_contact_counts,
)


class _FakeTokenizerClient:
    def __init__(self, *, prompt: str) -> None:
        self.prompt = prompt
        self.requests: list[tuple[str, object]] = []

    def post_json(self, path: str, body: object) -> dict[str, object]:
        self.requests.append((path, body))
        if path == "/apply-template":
            return {"prompt": self.prompt}
        if path == "/tokenize":
            assert isinstance(body, dict)
            content = str(body["content"])
            return {"tokens": list(range(len(content.split())))}
        raise AssertionError(path)


def test_build_ground_envelopes_preserves_complete_handbook_and_state_suffix() -> None:
    handbook = "AUDIO2TOOL EXECUTABLE HANDBOOK\nReturn only JSON.\n"

    envelopes = build_ground_envelopes(handbook)

    assert [item.envelope_id for item in envelopes] == [
        "ground-direct",
        "ground-agent-observed",
    ]
    assert all(
        item.messages[0] == {"role": "system", "content": handbook}
        for item in envelopes
    )
    assert envelopes[0].observation_token_allowance == 0
    assert envelopes[1].observation_token_allowance == 1024
    direct_content = envelopes[0].messages[1]["content"]
    observed_content = envelopes[1].messages[1]["content"]
    assert [part["type"] for part in direct_content] == ["input_speech_features"]
    assert [part["type"] for part in observed_content] == [
        "input_speech_features",
        "text",
    ]
    assert observed_content[-1]["text"].startswith(
        "[agent state executable-ground-observation kind=english_self_transcript] A"
    )


@pytest.mark.parametrize(
    "handbook", ["", "   ", "non-English: caf\N{LATIN SMALL LETTER E WITH ACUTE}"]
)
def test_build_ground_envelopes_rejects_empty_or_non_ascii_handbook(
    handbook: str,
) -> None:
    with pytest.raises(GroundPromptFitError):
        build_ground_envelopes(handbook)


def test_compute_prompt_fit_bounds_adds_every_registered_reserve() -> None:
    report = compute_prompt_fit_bounds(
        {"ground-direct": 15_000, "ground-agent-observed": 15_020}
    )

    rows = {row["envelope_id"]: row for row in report["envelopes"]}
    assert rows["ground-direct"]["prompt_tokens_with_all_reserves"] == 15_457
    assert rows["ground-agent-observed"]["prompt_tokens_with_all_reserves"] == 16_501
    assert report["maximum_prompt_tokens_with_all_reserves"] == 16_501
    assert report["required_context_per_slot"] == 17_525
    assert report["context_margin_tokens"] == 15_243
    assert report["maximum_prompt_fits_one_slot"] is True


def test_compute_prompt_fit_bounds_rejects_missing_or_overflowing_envelope() -> None:
    with pytest.raises(GroundPromptFitError, match="exact envelope ids"):
        compute_prompt_fit_bounds({"ground-direct": 10})
    with pytest.raises(GroundPromptFitError, match="does not fit"):
        compute_prompt_fit_bounds(
            {"ground-direct": 31_300, "ground-agent-observed": 31_300}
        )


def test_measure_text_prompt_tokens_splits_around_one_media_marker() -> None:
    marker = "<MEDIA>"
    client = _FakeTokenizerClient(prompt=f"one two {marker} three four five")
    counts = {"POST /apply-template": 0, "POST /tokenize": 0}

    measured = measure_text_prompt_tokens(
        client,
        ({"role": "system", "content": "unused"},),
        media_marker=marker,
        request_counts=counts,
    )

    assert measured == 5
    assert counts == {"POST /apply-template": 1, "POST /tokenize": 2}
    assert [request[0] for request in client.requests] == [
        "/apply-template",
        "/tokenize",
        "/tokenize",
    ]


def test_measure_text_prompt_tokens_refuses_marker_drift() -> None:
    client = _FakeTokenizerClient(prompt="no marker")
    with pytest.raises(GroundPromptFitError, match="exactly one media marker"):
        measure_text_prompt_tokens(
            client,
            (),
            media_marker="<MEDIA>",
            request_counts={"POST /apply-template": 0, "POST /tokenize": 0},
        )


def test_validate_ground_observation_enforces_word_character_and_ascii_bounds() -> None:
    accepted = validate_ground_observation("Turn the kitchen lights off.")
    assert accepted.valid is True
    assert accepted.text == "Turn the kitchen lights off."

    assert validate_ground_observation("word " * 161).valid is False
    assert validate_ground_observation("a" * 1025).valid is False
    assert (
        validate_ground_observation("caf\N{LATIN SMALL LETTER E WITH ACUTE}").valid
        is False
    )


def test_validate_registered_contact_counts_accepts_only_the_frozen_surface() -> None:
    validate_registered_contact_counts(
        {"GET /props": 1, "POST /apply-template": 2, "POST /tokenize": 4}
    )
    validate_registered_contact_counts(
        {"GET /props": 1, "POST /apply-template": 2, "POST /tokenize": 3}
    )
    with pytest.raises(GroundPromptFitError):
        validate_registered_contact_counts(
            {"GET /props": 1, "POST /apply-template": 1, "POST /tokenize": 3}
        )
    with pytest.raises(GroundPromptFitError):
        validate_registered_contact_counts(
            {"GET /props": 1, "POST /apply-template": 2, "POST /tokenize": 5}
        )
