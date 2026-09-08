"""Strict, task-blind dialogue state derived from sealed Audio2Tool OBS.

WAVE R7 (owner Decision 12-F, 2026-09-08): this module is registered, unchanged,
in the SYSTEM-invoked tool catalog. ``build_structured_dialogue_state`` is catalog id
``saea-tool-a2t-structured-dialogue-state-v1`` on the ``ORG`` axis, scope
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
import json
import re
from typing import Mapping, Sequence

MAX_STATE_UTF8_BYTES = 8192

_TOP_LEVEL_FIELDS = frozenset(
    {
        "turns",
        "current_request",
        "active_actions",
        "superseded_actions",
        "superseded_values",
        "irrelevant_context",
    }
)
_TURN_FIELDS = frozenset({"role", "source_turn", "surface", "normalized"})
_VALUE_FIELDS = frozenset({"source_turn", "surface", "normalized"})
_ROLES = frozenset({"user", "assistant"})
_IDENTITY_PATTERN = re.compile(
    r"(?i)(?:\btier[0-9]+_[a-z0-9_]+:[0-9]{3,}\b|"
    r"\baudio2tool:[^\s]+|\bsample[_ -]?id\b)"
)
_ROLE_LINE = re.compile(r"(?m)^(User|Assistant):[ \t]+([^\r\n]+)$")


class StructuredDialogueStateError(RuntimeError):
    """The state is malformed, unsafe, noncanonical, or over budget."""


@dataclass(frozen=True)
class ObservationTurnSpan:
    """Explicit role and byte-preserving character span in a sealed OBS."""

    role: str
    start: int
    end: int
    normalized: str


@dataclass(frozen=True)
class StateValue:
    """One explicit surface/normalized span bound to its source turn."""

    surface: str
    normalized: str
    source_turn: int


@dataclass(frozen=True)
class StructuredDialogueStateArtifact:
    """Canonical JSON state and its SHA-256 identity."""

    json_text: str
    sha256: str

    @property
    def document(self) -> dict[str, object]:
        """Return a fresh decoded copy of the validated canonical state."""

        document = json.loads(self.json_text)
        if not isinstance(document, dict):  # pragma: no cover - constructor invariant
            raise StructuredDialogueStateError("canonical state is not a JSON object")
        return document


def _ascii_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StructuredDialogueStateError(f"{field} must be non-empty ASCII English")
    if not value.isascii():
        raise StructuredDialogueStateError(f"{field} must be ASCII English")
    if _IDENTITY_PATTERN.search(value):
        raise StructuredDialogueStateError(
            f"{field} contains a forbidden sample or tier identity"
        )
    return value


def _source_turn(value: object, *, field: str, turn_count: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < turn_count
    ):
        raise StructuredDialogueStateError(
            f"{field}.source_turn must identify an existing chronological turn"
        )
    return value


def _validate_role_sequence(roles: Sequence[str]) -> None:
    if not roles or roles[0] != "user":
        raise StructuredDialogueStateError("dialogue roles must begin with user")
    if roles[-1] != "user":
        raise StructuredDialogueStateError("dialogue roles must end with user")
    if any(role not in _ROLES for role in roles):
        raise StructuredDialogueStateError("dialogue role must be user or assistant")
    if any(left == right for left, right in zip(roles, roles[1:], strict=False)):
        raise StructuredDialogueStateError(
            "dialogue roles must alternate in chronological order"
        )


def extract_role_labeled_g3_turns(
    sealed_observation_text: str,
    *,
    normalized_turns: Sequence[str] | None = None,
) -> tuple[ObservationTurnSpan, ...]:
    """Extract exact turn spans from the sealed G3 role-labeled OBS format."""

    observation = _ascii_text(
        sealed_observation_text, field="sealed_observation_text"
    )
    matches = tuple(_ROLE_LINE.finditer(observation))
    if not matches:
        raise StructuredDialogueStateError(
            "sealed G3 OBS contains no exact role-labeled turns"
        )
    consumed_lines = "\n".join(match.group(0) for match in matches)
    if consumed_lines != observation:
        raise StructuredDialogueStateError(
            "sealed G3 OBS contains text outside exact role-labeled turns"
        )
    surfaces = tuple(match.group(2) for match in matches)
    normalized = surfaces if normalized_turns is None else tuple(normalized_turns)
    if len(normalized) != len(matches):
        raise StructuredDialogueStateError(
            "normalized_turns must align one-to-one with sealed G3 turns"
        )
    spans = tuple(
        ObservationTurnSpan(
            role=match.group(1).lower(),
            start=match.start(2),
            end=match.end(2),
            normalized=_ascii_text(
                normalized[index], field=f"turns[{index}].normalized"
            ),
        )
        for index, match in enumerate(matches)
    )
    _validate_role_sequence(tuple(span.role for span in spans))
    return spans


def _validate_spans_cover_observation(
    observation: str, turns: Sequence[ObservationTurnSpan]
) -> None:
    mask = [False] * len(observation)
    prior_end = -1
    for index, turn in enumerate(turns):
        if (
            not isinstance(turn, ObservationTurnSpan)
            or isinstance(turn.start, bool)
            or isinstance(turn.end, bool)
            or not isinstance(turn.start, int)
            or not isinstance(turn.end, int)
            or not 0 <= turn.start < turn.end <= len(observation)
            or turn.start < prior_end
        ):
            raise StructuredDialogueStateError(
                f"turn span {index} is invalid, overlapping, or nonchronological"
            )
        prior_end = turn.end
        for position in range(turn.start, turn.end):
            mask[position] = True
    remainder = "".join(
        character for index, character in enumerate(observation) if not mask[index]
    )
    remainder = re.sub(r"(?i)(?:user|assistant)\s*:", "", remainder)
    if remainder.strip():
        raise StructuredDialogueStateError(
            "turn spans do not preserve all sealed OBS content"
        )


def _turn_document(
    sealed_observation_text: str,
    turns: Sequence[ObservationTurnSpan],
) -> list[dict[str, object]]:
    observation = _ascii_text(
        sealed_observation_text, field="sealed_observation_text"
    )
    if not turns:
        raise StructuredDialogueStateError("dialogue must contain at least one turn")
    _validate_spans_cover_observation(observation, turns)
    roles = tuple(turn.role for turn in turns)
    _validate_role_sequence(roles)
    documents: list[dict[str, object]] = []
    for source_turn, turn in enumerate(turns):
        surface = _ascii_text(
            observation[turn.start : turn.end],
            field=f"turns[{source_turn}].surface",
        )
        normalized = _ascii_text(
            turn.normalized, field=f"turns[{source_turn}].normalized"
        )
        documents.append(
            {
                "role": turn.role,
                "source_turn": source_turn,
                "surface": surface,
                "normalized": normalized,
            }
        )
    return documents


def _state_value_document(value: StateValue, *, field: str) -> dict[str, object]:
    if not isinstance(value, StateValue):
        raise StructuredDialogueStateError(f"{field} must use explicit StateValue metadata")
    return {
        "surface": value.surface,
        "normalized": value.normalized,
        "source_turn": value.source_turn,
    }


def build_structured_dialogue_state(
    sealed_observation_text: str,
    *,
    turns: Sequence[ObservationTurnSpan],
    current_request: StateValue,
    active_actions: Sequence[StateValue] = (),
    superseded_actions: Sequence[StateValue] = (),
    superseded_values: Sequence[StateValue] = (),
    irrelevant_context: Sequence[StateValue] = (),
) -> StructuredDialogueStateArtifact:
    """Build state from sealed OBS bytes and explicit, task-blind metadata only."""

    document = {
        "turns": _turn_document(sealed_observation_text, turns),
        "current_request": _state_value_document(
            current_request, field="current_request"
        ),
        "active_actions": [
            _state_value_document(value, field="active_actions")
            for value in active_actions
        ],
        "superseded_actions": [
            _state_value_document(value, field="superseded_actions")
            for value in superseded_actions
        ],
        "superseded_values": [
            _state_value_document(value, field="superseded_values")
            for value in superseded_values
        ],
        "irrelevant_context": [
            _state_value_document(value, field="irrelevant_context")
            for value in irrelevant_context
        ],
    }
    return render_structured_dialogue_state(document)


def _require_exact_fields(
    value: object, expected: frozenset[str], *, context: str
) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise StructuredDialogueStateError(
            f"{context} must contain exact {context.split()[-1]} fields {sorted(expected)!r}"
        )
    return value


def _validate_turns(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list) or not value:
        raise StructuredDialogueStateError("turns must be a non-empty JSON array")
    turn_count = len(value)
    turns: list[Mapping[str, object]] = []
    roles: list[str] = []
    for index, raw in enumerate(value):
        turn = _require_exact_fields(raw, _TURN_FIELDS, context="exact turn")
        role = turn.get("role")
        if role not in _ROLES:
            raise StructuredDialogueStateError("dialogue role must be user or assistant")
        if turn.get("source_turn") != index:
            raise StructuredDialogueStateError(
                "turn source_turn values must be chronological zero-based indices"
            )
        _ascii_text(turn.get("surface"), field=f"turns[{index}].surface")
        _ascii_text(turn.get("normalized"), field=f"turns[{index}].normalized")
        roles.append(str(role))
        turns.append(turn)
    _validate_role_sequence(roles)
    if turn_count != len(turns):  # pragma: no cover - loop invariant
        raise StructuredDialogueStateError("turn validation failed")
    return tuple(turns)


def _validate_value(
    raw: object,
    *,
    field: str,
    turns: Sequence[Mapping[str, object]],
    require_user_turn: bool,
) -> Mapping[str, object]:
    value = _require_exact_fields(raw, _VALUE_FIELDS, context="exact value")
    source_turn = _source_turn(
        value.get("source_turn"), field=field, turn_count=len(turns)
    )
    surface = _ascii_text(value.get("surface"), field=f"{field}.surface")
    normalized = _ascii_text(
        value.get("normalized"), field=f"{field}.normalized"
    )
    turn = turns[source_turn]
    if require_user_turn and turn.get("role") != "user":
        raise StructuredDialogueStateError(f"{field} must originate in a user turn")
    if surface not in str(turn["surface"]) or normalized not in str(turn["normalized"]):
        raise StructuredDialogueStateError(
            f"{field} surface or normalized value is not present in its source turn"
        )
    return value


def _validate_value_list(
    raw: object,
    *,
    field: str,
    turns: Sequence[Mapping[str, object]],
    require_user_turn: bool,
) -> tuple[Mapping[str, object], ...]:
    if not isinstance(raw, list):
        raise StructuredDialogueStateError(f"{field} must be a JSON array")
    values = tuple(
        _validate_value(
            value,
            field=f"{field}[{index}]",
            turns=turns,
            require_user_turn=require_user_turn,
        )
        for index, value in enumerate(raw)
    )
    order = tuple(
        (int(value["source_turn"]), str(value["normalized"]), str(value["surface"]))
        for value in values
    )
    if order != tuple(sorted(order)) or len(order) != len(set(order)):
        raise StructuredDialogueStateError(
            f"{field} must be unique and chronological without fallback sorting"
        )
    return values


def _validate_document(document: object) -> Mapping[str, object]:
    state = _require_exact_fields(
        document, _TOP_LEVEL_FIELDS, context="exact top-level"
    )
    turns = _validate_turns(state["turns"])
    current = _validate_value(
        state["current_request"],
        field="current_request",
        turns=turns,
        require_user_turn=True,
    )
    if current.get("source_turn") != len(turns) - 1:
        raise StructuredDialogueStateError(
            "current_request must originate in the final chronological user turn"
        )
    active = _validate_value_list(
        state["active_actions"],
        field="active_actions",
        turns=turns,
        require_user_turn=True,
    )
    superseded = _validate_value_list(
        state["superseded_actions"],
        field="superseded_actions",
        turns=turns,
        require_user_turn=True,
    )
    _validate_value_list(
        state["superseded_values"],
        field="superseded_values",
        turns=turns,
        require_user_turn=True,
    )
    _validate_value_list(
        state["irrelevant_context"],
        field="irrelevant_context",
        turns=turns,
        require_user_turn=False,
    )
    active_normalized = {str(value["normalized"]) for value in active}
    superseded_normalized = {str(value["normalized"]) for value in superseded}
    if active_normalized & superseded_normalized:
        raise StructuredDialogueStateError(
            "active_actions and superseded_actions must be mutually exclusive"
        )
    return state


def render_structured_dialogue_state(
    document: Mapping[str, object],
) -> StructuredDialogueStateArtifact:
    """Validate and canonically render one exact state; never repair it."""

    state = _validate_document(document)
    json_text = json.dumps(
        state,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    rendered = json_text.encode("utf-8")
    if len(rendered) > MAX_STATE_UTF8_BYTES:
        raise StructuredDialogueStateError(
            f"structured dialogue state exceeds the {MAX_STATE_UTF8_BYTES:,}-byte cap"
        )
    return StructuredDialogueStateArtifact(
        json_text=json_text,
        sha256=hashlib.sha256(rendered).hexdigest(),
    )


def parse_structured_dialogue_state(json_text: str) -> StructuredDialogueStateArtifact:
    """Accept only already canonical valid state JSON; never repair or fall back."""

    if not isinstance(json_text, str):
        raise StructuredDialogueStateError("structured dialogue state must be JSON text")
    if len(json_text.encode("utf-8")) > MAX_STATE_UTF8_BYTES:
        raise StructuredDialogueStateError(
            f"structured dialogue state exceeds the {MAX_STATE_UTF8_BYTES:,}-byte cap"
        )
    try:
        document = json.loads(json_text)
    except (json.JSONDecodeError, UnicodeError) as error:
        raise StructuredDialogueStateError(f"malformed JSON state: {error}") from error
    artifact = render_structured_dialogue_state(document)
    if artifact.json_text != json_text:
        raise StructuredDialogueStateError(
            "structured dialogue state JSON is not canonical; repair is forbidden"
        )
    return artifact


__all__ = [
    "MAX_STATE_UTF8_BYTES",
    "ObservationTurnSpan",
    "StateValue",
    "StructuredDialogueStateArtifact",
    "StructuredDialogueStateError",
    "build_structured_dialogue_state",
    "extract_role_labeled_g3_turns",
    "parse_structured_dialogue_state",
    "render_structured_dialogue_state",
]
