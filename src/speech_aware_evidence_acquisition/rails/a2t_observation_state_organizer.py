"""Organize sealed ASCII OBS into task-blind structured dialogue state.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``organize_sealed_observation`` is catalog id
``saea-tool-a2t-observation-state-organizer-v1`` on the ``ORG`` axis, scope
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
import hashlib
import re
from typing import Mapping, Sequence

from .a2t_structured_dialogue_state import (
    ObservationTurnSpan,
    StateValue,
    StructuredDialogueStateArtifact,
    StructuredDialogueStateError,
    build_structured_dialogue_state,
    extract_role_labeled_g3_turns,
)

MAX_ACTION_CLAUSES = 8
ObservationStateOrganizerError = StructuredDialogueStateError

_ROLE_PREFIX = re.compile(r"(?m)^(?:User|Assistant):")
_PRIMARY_BREAK = re.compile(
    r"[;.!?]+|,(?=\s*(?:actually|instead|no|not)\b)", re.IGNORECASE
)
_COORDINATION_BREAK = re.compile(
    r"\s+(?:and\s+|(?=then\s+)|(?=also\s+))", re.IGNORECASE
)
_CORRECTION_MARKER = re.compile(
    r"\b(?:actually|instead)\b|^\s*(?:no\s*,|not\b)", re.IGNORECASE
)
_EXPLICIT_NEGATION = re.compile(
    r"\bnot\s+(?P<old>[^,;.]+?)\s+(?:but|rather\s+than)\s+"
    r"(?P<new>[^,;.]+)",
    re.IGNORECASE,
)
_REQUEST_PREFIX = re.compile(
    r"^(?:please\b|kindly\b|(?:could|would|can|will)\s+you\b|"
    r"i\s+(?:want|need)(?:\s+you)?\s+to\b|let[' ]s\b)",
    re.IGNORECASE,
)
_NARRATIVE_PREFIX = re.compile(
    r"^(?:i|we|he|she|they|it|this|that|these|those|the|a|an|there|here|"
    r"my|our|your|his|her|their|its|someone|something|thanks|thank|"
    r"why|what|when|where|who|how)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class _Clause:
    """One exact source clause and its task-blind structural metadata."""

    source_turn: int
    surface: str
    normalized: str
    action_like: bool
    correction: bool
    superseded_values: tuple[StateValue, ...]


def _normalize_english_span(text: str) -> str:
    """Apply only ASCII-safe case and whitespace normalization."""

    return re.sub(r"\s+", " ", text).strip().lower()


def _trimmed_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return None if start == end else (start, end)


def _split_at_pattern(
    text: str, start: int, end: int, pattern: re.Pattern[str]
) -> tuple[tuple[int, int], ...]:
    spans: list[tuple[int, int]] = []
    cursor = start
    for match in pattern.finditer(text, start, end):
        trimmed = _trimmed_span(text, cursor, match.start())
        if trimmed is not None:
            spans.append(trimmed)
        cursor = match.end()
    trimmed = _trimmed_span(text, cursor, end)
    if trimmed is not None:
        spans.append(trimmed)
    return tuple(spans)


def _classification_text(surface: str) -> str:
    text = surface.strip()
    text = re.sub(
        r"^(?:(?:actually|instead|then|also)\b\s*[,;:]?\s*)+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^no\s*,\s*", "", text, flags=re.IGNORECASE)
    return text


def _looks_action_like(surface: str) -> bool:
    text = _classification_text(surface)
    if not text or re.match(r"^not\b", text, flags=re.IGNORECASE):
        return False
    if _REQUEST_PREFIX.search(text):
        return True
    if _NARRATIVE_PREFIX.search(text):
        return False
    return re.match(r"^[\"']?[A-Za-z]+\b", text) is not None


def _has_correction(surface: str) -> bool:
    return bool(_CORRECTION_MARKER.search(surface) or _EXPLICIT_NEGATION.search(surface))


def _clause_spans(turn_surface: str) -> tuple[tuple[int, int], ...]:
    primary = _split_at_pattern(
        turn_surface, 0, len(turn_surface), _PRIMARY_BREAK
    )
    clauses: list[tuple[int, int]] = []
    for start, end in primary:
        surface = turn_surface[start:end]
        if _looks_action_like(surface) or _has_correction(surface):
            clauses.extend(
                _split_at_pattern(turn_surface, start, end, _COORDINATION_BREAK)
            )
        else:
            clauses.append((start, end))
    return tuple(clauses)


def _explicit_superseded_values(
    surface: str, *, source_turn: int
) -> tuple[StateValue, ...]:
    values: list[StateValue] = []
    for match in _EXPLICIT_NEGATION.finditer(surface):
        old_surface = match.group("old")
        values.append(
            StateValue(
                surface=old_surface,
                normalized=_normalize_english_span(old_surface),
                source_turn=source_turn,
            )
        )
    return tuple(values)


def _turn_spans(observation: str) -> tuple[ObservationTurnSpan, ...]:
    if _ROLE_PREFIX.search(observation):
        extracted = extract_role_labeled_g3_turns(observation)
        return tuple(
            ObservationTurnSpan(
                role=turn.role,
                start=turn.start,
                end=turn.end,
                normalized=_normalize_english_span(
                    observation[turn.start : turn.end]
                ),
            )
            for turn in extracted
        )
    return (
        ObservationTurnSpan(
            role="user",
            start=0,
            end=len(observation),
            normalized=_normalize_english_span(observation),
        ),
    )


def _clauses_for_user_turns(
    observation: str, turns: Sequence[ObservationTurnSpan]
) -> tuple[_Clause, ...]:
    clauses: list[_Clause] = []
    for source_turn, turn in enumerate(turns):
        if turn.role != "user":
            continue
        turn_surface = observation[turn.start : turn.end]
        for start, end in _clause_spans(turn_surface):
            surface = turn_surface[start:end]
            clauses.append(
                _Clause(
                    source_turn=source_turn,
                    surface=surface,
                    normalized=_normalize_english_span(surface),
                    action_like=_looks_action_like(surface),
                    correction=_has_correction(surface),
                    superseded_values=_explicit_superseded_values(
                        surface, source_turn=source_turn
                    ),
                )
            )
    return tuple(clauses)


def _value(clause: _Clause) -> StateValue:
    return StateValue(
        surface=clause.surface,
        normalized=clause.normalized,
        source_turn=clause.source_turn,
    )


def _canonical_values(values: Sequence[StateValue]) -> tuple[StateValue, ...]:
    unique = {
        (value.source_turn, value.normalized, value.surface): value for value in values
    }
    return tuple(unique[key] for key in sorted(unique))


def organize_sealed_observation(
    sealed_observation_text: str,
) -> StructuredDialogueStateArtifact:
    """Build one deterministic task-blind state from sealed ASCII OBS."""

    turns = _turn_spans(sealed_observation_text)
    clauses = _clauses_for_user_turns(sealed_observation_text, turns)
    action_count = sum(clause.action_like for clause in clauses)
    flat_overflow = False
    if action_count > MAX_ACTION_CLAUSES:
        if _ROLE_PREFIX.search(sealed_observation_text):
            raise ObservationStateOrganizerError(
                f"sealed OBS contains {action_count} action clauses; at most "
                f"{MAX_ACTION_CLAUSES} action clauses are allowed"
            )
        flat_overflow = True
        clauses = (
            _Clause(
                source_turn=0,
                surface=sealed_observation_text,
                normalized=_normalize_english_span(sealed_observation_text),
                action_like=True,
                correction=False,
                superseded_values=(),
            ),
        )

    active: list[StateValue] = []
    superseded: list[StateValue] = []
    superseded_values: list[StateValue] = []
    for clause in clauses:
        if clause.correction:
            superseded.extend(active)
            active.clear()
        superseded_values.extend(clause.superseded_values)
        if clause.action_like:
            active.append(_value(clause))

    active_values = _canonical_values(active)
    active_normalized = {value.normalized for value in active_values}
    superseded_values_actions = _canonical_values(
        value for value in superseded if value.normalized not in active_normalized
    )
    explicit_values = _canonical_values(superseded_values)
    final_turn_index = len(turns) - 1
    final_turn = turns[final_turn_index]
    final_surface = sealed_observation_text[final_turn.start : final_turn.end]
    current_request = (
        _value(clauses[0])
        if flat_overflow
        else StateValue(
            surface=final_surface,
            normalized=final_turn.normalized,
            source_turn=final_turn_index,
        )
    )
    return build_structured_dialogue_state(
        sealed_observation_text,
        turns=turns,
        current_request=current_request,
        active_actions=active_values,
        superseded_actions=superseded_values_actions,
        superseded_values=explicit_values,
    )


def _hash_lines(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("ascii")).hexdigest()


def build_external_state_receipt(
    observations: Mapping[str, str],
) -> dict[str, object]:
    """Build a source-free receipt for exactly sixteen externally held OBS states."""

    if not isinstance(observations, Mapping) or len(observations) != 16:
        raise ObservationStateOrganizerError(
            "external state receipt requires exactly 16 observations"
        )
    records: list[dict[str, object]] = []
    observation_hashes: list[str] = []
    state_hashes: list[str] = []
    for identity, observation in observations.items():
        if not isinstance(identity, str) or not identity or not identity.isascii():
            raise ObservationStateOrganizerError(
                "external observation identities must be non-empty ASCII text"
            )
        if not isinstance(observation, str):
            raise ObservationStateOrganizerError(
                "external observations must be sealed text"
            )
        artifact = organize_sealed_observation(observation)
        identity_hash = hashlib.sha256(identity.encode("ascii")).hexdigest()
        observation_hash = hashlib.sha256(observation.encode("ascii")).hexdigest()
        observation_hashes.append(observation_hash)
        state_hashes.append(artifact.sha256)
        records.append(
            {
                "external_identity_sha256": identity_hash,
                "observation_sha256": observation_hash,
                "state_sha256": artifact.sha256,
                "state_utf8_bytes": len(artifact.json_text.encode("utf-8")),
            }
        )
    records.sort(key=lambda record: str(record["external_identity_sha256"]))
    return {
        "schema": "saea-a2t-external-observation-state-receipt-v1",
        "execution_profile": "model-free-check",
        "observation_count": len(records),
        "state_count": len(records),
        "observation_set_sha256": _hash_lines(observation_hashes),
        "state_set_sha256": _hash_lines(state_hashes),
        "states": records,
        "source_observations_rendered": 0,
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "tokenizer": 0,
            "scorer": 0,
        },
    }


__all__ = [
    "MAX_ACTION_CLAUSES",
    "ObservationStateOrganizerError",
    "StructuredDialogueStateError",
    "build_external_state_receipt",
    "organize_sealed_observation",
]
