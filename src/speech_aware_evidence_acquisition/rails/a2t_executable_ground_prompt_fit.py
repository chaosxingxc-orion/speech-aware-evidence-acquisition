"""Exact prompt envelopes and bounds for the Audio2Tool executable ground.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_ground_envelopes`` is catalog id
``saea-tool-a2t-ground-prompt-envelopes-v1`` on the ``USE`` axis, scope
``carrier:audio2tool``, wrapped as
a passthrough by ``rails/tool_wrappers/a2t_renderers.py``; the manifest pins
the sha256 of that entry point's own source, so editing its body without
re-pinning fails the catalog check. Nothing here was rebuilt or re-signed for that --
the reuse map's verdict was "Register, do not rebuild" -- and
``tests/unit/test_a2t_renderer_tools.py`` asserts the wrapped output is the
direct output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, MutableMapping, Sequence

from ..analysis import training_free_a2t_self_transcript_cascade as selftx
from ..core.model.transport import (
    _ordered_speech_feature_content,
    _speech_history_texts,
)

PROMPT_ORDER = "speech-query-prefix-v2"
DIRECT_ENVELOPE_ID = "ground-direct"
OBSERVED_ENVELOPE_ID = "ground-agent-observed"
OBSERVATION_WORD_LIMIT = 160
OBSERVATION_CHARACTER_LIMIT = 1_024
OBSERVATION_TOKEN_ALLOWANCE = 1_024
SPEECH_FEATURE_TOKEN_RESERVE = 455
SPECIAL_TOKEN_RESERVE = 2
COMPLETION_TOKEN_ALLOWANCE = 1_024
CONTEXT_TOKENS = 65_536
SLOT_COUNT = 2
CONTEXT_TOKENS_PER_SLOT = CONTEXT_TOKENS // SLOT_COUNT


class GroundPromptFitError(RuntimeError):
    """The executable-ground capacity check refused an invalid input or fit."""


@dataclass(frozen=True)
class GroundPromptEnvelope:
    """One exact message shape and its separately accounted observation reserve."""

    envelope_id: str
    messages: tuple[dict[str, object], ...]
    observation_token_allowance: int


def _query_feature_part() -> dict[str, object]:
    return {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": "audit/a2t-executable-ground-prompt-fit/query",
            "sha256": "0" * 64,
            "role": "query",
        },
    }


def _observation_state_text() -> str:
    state = {
        "turn": 1,
        "role": "agent_state",
        "state_id": "executable-ground-observation",
        "state_kind": "english_self_transcript",
        "content": "A",
        "content_sha256": (
            "559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd"
        ),
        "source_query_state_sha256": "0" * 64,
        "source_response_sha256": "0" * 64,
        "producer_policy_id": "saea-a2t-executable-ground-observation-v1",
        "cited_value_ids": [],
    }
    return _speech_history_texts([state])[0]


def build_ground_envelopes(handbook_text: str) -> tuple[GroundPromptEnvelope, ...]:
    """Render the two preregistered direct and one-state transport envelopes."""

    if not isinstance(handbook_text, str) or not handbook_text.strip():
        raise GroundPromptFitError("handbook must be non-empty text")
    if not handbook_text.isascii():
        raise GroundPromptFitError("handbook must be ASCII English")
    feature_parts = [_query_feature_part()]
    direct_content = _ordered_speech_feature_content(
        prompt_order=PROMPT_ORDER,
        evidence_texts=[],
        feature_parts=feature_parts,
        state_texts=[],
    )
    observed_content = _ordered_speech_feature_content(
        prompt_order=PROMPT_ORDER,
        evidence_texts=[],
        feature_parts=feature_parts,
        state_texts=[_observation_state_text()],
    )
    return (
        GroundPromptEnvelope(
            envelope_id=DIRECT_ENVELOPE_ID,
            messages=(
                {"role": "system", "content": handbook_text},
                {"role": "user", "content": direct_content},
            ),
            observation_token_allowance=0,
        ),
        GroundPromptEnvelope(
            envelope_id=OBSERVED_ENVELOPE_ID,
            messages=(
                {"role": "system", "content": handbook_text},
                {"role": "user", "content": observed_content},
            ),
            observation_token_allowance=OBSERVATION_TOKEN_ALLOWANCE,
        ),
    )


def measure_text_prompt_tokens(
    client: object,
    messages: Sequence[Mapping[str, object]],
    *,
    media_marker: str,
    request_counts: MutableMapping[str, int],
) -> int:
    """Measure only rendered text, excluding the opaque speech marker."""

    if not isinstance(media_marker, str) or not media_marker:
        raise GroundPromptFitError("media marker must be non-empty text")
    post_json = getattr(client, "post_json", None)
    if not callable(post_json):
        raise GroundPromptFitError("tokenizer client must expose post_json")
    rendered = post_json("/apply-template", {"messages": list(messages)})
    request_counts["POST /apply-template"] += 1
    prompt = rendered.get("prompt") if isinstance(rendered, Mapping) else None
    if not isinstance(prompt, str):
        raise GroundPromptFitError("apply-template returned no prompt text")
    if prompt.count(media_marker) != 1:
        raise GroundPromptFitError(
            "rendered prompt must contain exactly one media marker"
        )
    total = 0
    for segment in prompt.split(media_marker):
        if not segment:
            continue
        response = post_json(
            "/tokenize",
            {"content": segment, "add_special": False, "parse_special": True},
        )
        request_counts["POST /tokenize"] += 1
        tokens = response.get("tokens") if isinstance(response, Mapping) else None
        if not isinstance(tokens, list):
            raise GroundPromptFitError("tokenize returned no token list")
        total += len(tokens)
    if total <= 0:
        raise GroundPromptFitError("rendered text prompt must contain tokens")
    return total


def compute_prompt_fit_bounds(
    text_prompt_tokens: Mapping[str, int],
) -> dict[str, object]:
    """Apply every frozen reserve and refuse a non-positive context margin."""

    expected = {DIRECT_ENVELOPE_ID, OBSERVED_ENVELOPE_ID}
    if set(text_prompt_tokens) != expected:
        raise GroundPromptFitError("text-token map must carry the exact envelope ids")
    rows: list[dict[str, object]] = []
    for envelope_id in (DIRECT_ENVELOPE_ID, OBSERVED_ENVELOPE_ID):
        text_tokens = text_prompt_tokens[envelope_id]
        if (
            isinstance(text_tokens, bool)
            or not isinstance(text_tokens, int)
            or text_tokens <= 0
        ):
            raise GroundPromptFitError(
                "text prompt token counts must be positive integers"
            )
        observation_allowance = (
            OBSERVATION_TOKEN_ALLOWANCE if envelope_id == OBSERVED_ENVELOPE_ID else 0
        )
        prompt_with_reserves = (
            text_tokens
            + SPEECH_FEATURE_TOKEN_RESERVE
            + SPECIAL_TOKEN_RESERVE
            + observation_allowance
        )
        rows.append(
            {
                "envelope_id": envelope_id,
                "text_prompt_tokens": text_tokens,
                "speech_feature_token_reserve": SPEECH_FEATURE_TOKEN_RESERVE,
                "special_token_reserve": SPECIAL_TOKEN_RESERVE,
                "observation_token_allowance": observation_allowance,
                "prompt_tokens_with_all_reserves": prompt_with_reserves,
            }
        )
    worst = max(
        rows,
        key=lambda row: (
            int(row["prompt_tokens_with_all_reserves"]),
            str(row["envelope_id"]),
        ),
    )
    maximum_prompt = int(worst["prompt_tokens_with_all_reserves"])
    required = maximum_prompt + COMPLETION_TOKEN_ALLOWANCE
    margin = CONTEXT_TOKENS_PER_SLOT - required
    if margin <= 0:
        raise GroundPromptFitError(
            "complete executable-ground prompt does not fit one serving slot"
        )
    return {
        "envelopes": rows,
        "worst_envelope_id": worst["envelope_id"],
        "maximum_text_prompt_tokens": max(text_prompt_tokens.values()),
        "maximum_prompt_tokens_with_all_reserves": maximum_prompt,
        "completion_token_allowance": COMPLETION_TOKEN_ALLOWANCE,
        "required_context_per_slot": required,
        "context_tokens": CONTEXT_TOKENS,
        "slot_count": SLOT_COUNT,
        "context_tokens_per_slot": CONTEXT_TOKENS_PER_SLOT,
        "context_margin_tokens": margin,
        "maximum_prompt_fits_one_slot": True,
    }


def validate_ground_observation(response_text: object) -> selftx.TranscriptParse:
    """Apply the inherited transcript gate plus the frozen character ceiling."""

    parsed = selftx.validate_self_transcript(response_text)
    if not parsed.valid:
        return parsed
    if parsed.word_count > OBSERVATION_WORD_LIMIT:
        return selftx.TranscriptParse(
            False,
            "observation exceeds the frozen word limit",
            "",
            0,
            False,
        )
    if len(parsed.text) > OBSERVATION_CHARACTER_LIMIT:
        return selftx.TranscriptParse(
            False,
            "observation exceeds the frozen character limit",
            "",
            0,
            False,
        )
    return parsed


def validate_registered_contact_counts(request_counts: Mapping[str, int]) -> None:
    """Refuse any tokenizer surface outside the preregistered request budget."""

    expected = {"GET /props", "POST /apply-template", "POST /tokenize"}
    if set(request_counts) != expected:
        raise GroundPromptFitError("tokenizer request-count keys drifted")
    if request_counts["GET /props"] != 1 or request_counts["POST /apply-template"] != 2:
        raise GroundPromptFitError("props or apply-template request count drifted")
    if not 2 <= request_counts["POST /tokenize"] <= 4:
        raise GroundPromptFitError("tokenize request count exceeds its frozen surface")


__all__ = [
    "COMPLETION_TOKEN_ALLOWANCE",
    "CONTEXT_TOKENS",
    "CONTEXT_TOKENS_PER_SLOT",
    "DIRECT_ENVELOPE_ID",
    "GroundPromptEnvelope",
    "GroundPromptFitError",
    "OBSERVATION_CHARACTER_LIMIT",
    "OBSERVATION_TOKEN_ALLOWANCE",
    "OBSERVATION_WORD_LIMIT",
    "OBSERVED_ENVELOPE_ID",
    "PROMPT_ORDER",
    "SLOT_COUNT",
    "SPECIAL_TOKEN_RESERVE",
    "SPEECH_FEATURE_TOKEN_RESERVE",
    "build_ground_envelopes",
    "compute_prompt_fit_bounds",
    "measure_text_prompt_tokens",
    "validate_ground_observation",
    "validate_registered_contact_counts",
]
