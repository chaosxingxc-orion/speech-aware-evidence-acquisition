"""Fail-closed arithmetic repricing of a frozen executable-ground prompt fit."""

from __future__ import annotations

from copy import deepcopy
from typing import Mapping


class PromptFitInheritanceError(RuntimeError):
    """A source or serving-geometry invariant drifted."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise PromptFitInheritanceError(f"{label} must be a mapping")
    return value


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PromptFitInheritanceError(f"{label} must be a positive integer")
    return value


def reprice_prompt_fit(
    prompt_fit: Mapping[str, object],
    preprocessing: Mapping[str, object],
) -> dict[str, object]:
    """Replace only the speech reserve with the complete-packet maximum."""

    if preprocessing.get("count") != 104 or preprocessing.get("packets_promoted") != 104:
        raise PromptFitInheritanceError("preprocessing must bind exactly 104 packets")
    feature_tokens = _mapping(
        preprocessing.get("speech_feature_tokens"), "speech_feature_tokens"
    )
    distribution = _mapping(feature_tokens.get("distribution"), "distribution")
    packets = feature_tokens.get("packets")
    if not isinstance(packets, list) or len(packets) != 104:
        raise PromptFitInheritanceError("packet token inventory must contain exactly 104 rows")
    packet_ids: set[str] = set()
    measured: list[int] = []
    for entry_value in packets:
        entry = _mapping(entry_value, "packet token row")
        packet_id = entry.get("packet_id")
        if not isinstance(packet_id, str) or not packet_id or packet_id in packet_ids:
            raise PromptFitInheritanceError("packet ids must be unique non-empty strings")
        packet_ids.add(packet_id)
        measured.append(_positive_int(entry.get("n_tokens"), "packet n_tokens"))
    new_reserve = max(measured)
    if distribution.get("count") != len(measured) or distribution.get("max") != new_reserve:
        raise PromptFitInheritanceError("packet distribution disagrees with complete inventory")
    if new_reserve != 468:
        raise PromptFitInheritanceError("fresh packet maximum must equal registered 468")

    bounds = _mapping(prompt_fit.get("bounds"), "prompt-fit bounds")
    completion = _positive_int(
        bounds.get("completion_token_allowance"), "completion allowance"
    )
    context = _positive_int(bounds.get("context_tokens"), "context tokens")
    slots = _positive_int(bounds.get("slot_count"), "slot count")
    per_slot = _positive_int(
        bounds.get("context_tokens_per_slot"), "context tokens per slot"
    )
    if context != 65_536 or slots != 2 or per_slot != 32_768 or context // slots != per_slot:
        raise PromptFitInheritanceError("serving slot geometry drifted")
    if completion != 1_024:
        raise PromptFitInheritanceError("completion allowance drifted")

    source_envelopes = bounds.get("envelopes")
    if not isinstance(source_envelopes, list) or len(source_envelopes) != 2:
        raise PromptFitInheritanceError("source must contain exactly two prompt envelopes")
    by_id: dict[str, Mapping[str, object]] = {}
    for row_value in source_envelopes:
        row = _mapping(row_value, "prompt envelope")
        envelope_id = row.get("envelope_id")
        if not isinstance(envelope_id, str) or envelope_id in by_id:
            raise PromptFitInheritanceError("prompt envelope ids must be unique strings")
        by_id[envelope_id] = row
    order = ("ground-direct", "ground-agent-observed")
    if set(by_id) != set(order):
        raise PromptFitInheritanceError("prompt envelope ids drifted")

    old_reserve = 455
    rows: list[dict[str, object]] = []
    for envelope_id in order:
        source = by_id[envelope_id]
        text_tokens = _positive_int(source.get("text_prompt_tokens"), "text prompt tokens")
        source_reserve = _positive_int(
            source.get("speech_feature_token_reserve"), "source speech reserve"
        )
        special = _positive_int(source.get("special_token_reserve"), "special reserve")
        observation_value = source.get("observation_token_allowance")
        if (
            isinstance(observation_value, bool)
            or not isinstance(observation_value, int)
            or observation_value < 0
        ):
            raise PromptFitInheritanceError("observation allowance must be non-negative")
        if source_reserve != old_reserve:
            raise PromptFitInheritanceError("source speech reserve drifted")
        old_prompt = text_tokens + source_reserve + special + observation_value
        if source.get("prompt_tokens_with_all_reserves") != old_prompt:
            raise PromptFitInheritanceError("source envelope arithmetic drifted")
        rows.append(
            {
                "envelope_id": envelope_id,
                "observation_token_allowance": observation_value,
                "prompt_tokens_with_all_reserves": (
                    text_tokens + new_reserve + special + observation_value
                ),
                "special_token_reserve": special,
                "speech_feature_token_reserve": new_reserve,
                "text_prompt_tokens": text_tokens,
            }
        )
    maximum_prompt = max(int(row["prompt_tokens_with_all_reserves"]) for row in rows)
    required = maximum_prompt + completion
    margin = per_slot - required
    if margin <= 0:
        raise PromptFitInheritanceError("repriced prompt does not fit one serving slot")
    return {
        "old_speech_feature_token_reserve": old_reserve,
        "new_speech_feature_token_reserve": new_reserve,
        "speech_reserve_delta": new_reserve - old_reserve,
        "envelopes": rows,
        "maximum_prompt_tokens_with_all_reserves": maximum_prompt,
        "completion_token_allowance": completion,
        "required_context_per_slot": required,
        "context_tokens": context,
        "slot_count": slots,
        "context_tokens_per_slot": per_slot,
        "context_margin_tokens": margin,
        "maximum_prompt_fits_one_slot": True,
        "message_sha256": deepcopy(prompt_fit.get("message_sha256")),
        "runtime_verification": deepcopy(prompt_fit.get("runtime_verification")),
        "handbook": deepcopy(prompt_fit.get("handbook")),
    }
