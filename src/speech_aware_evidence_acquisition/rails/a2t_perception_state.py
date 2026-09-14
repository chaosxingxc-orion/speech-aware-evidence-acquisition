"""Pure, bounded native Audio2Tool Perception-state parsing."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Sequence


_PERCEPTION_STATE_KEYS = {"actions", "global_constraints"}
_PERCEPTION_ACTION_KEYS = {
    "action_id",
    "candidate_tools",
    "evidence",
    "uncertain_arguments",
}
_ACTION_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", flags=re.ASCII)
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*", flags=re.ASCII)


class Audio2ToolPerceptionStateError(ValueError):
    """Reject malformed or unbound native Audio2Tool Perception state."""


@dataclass(frozen=True)
class Audio2ToolPerceptionAction:
    """One ordered action occurrence proposed by Perception."""

    action_id: str
    candidate_tools: tuple[str, ...]
    evidence: str
    uncertain_arguments: tuple[str, ...]


@dataclass(frozen=True)
class Audio2ToolPerceptionState:
    """A non-authoritative, immutable Perception state."""

    actions: tuple[Audio2ToolPerceptionAction, ...]
    global_constraints: tuple[str, ...]
    unique_tool_names: tuple[str, ...]


def _strict_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Audio2ToolPerceptionStateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value):
    raise Audio2ToolPerceptionStateError(f"invalid non-finite JSON constant: {value}")


def _positive_bound(name, value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise Audio2ToolPerceptionStateError(f"{name} must be a positive integer")


def _text_list(value, *, name):
    if not isinstance(value, list):
        raise Audio2ToolPerceptionStateError(f"{name} must be an ordered list")
    if any(not isinstance(item, str) for item in value):
        raise Audio2ToolPerceptionStateError(f"{name} must contain text")
    return tuple(value)


def parse_audio2tool_perception_state(
    text: str,
    *,
    legal_tool_names: Sequence[str],
    max_actions: int,
    max_candidates_per_action: int,
) -> Audio2ToolPerceptionState:
    """Parse a bounded candidate state without granting answer authority."""
    _positive_bound("max_actions", max_actions)
    _positive_bound("max_candidates_per_action", max_candidates_per_action)
    if isinstance(legal_tool_names, (str, bytes)) or not isinstance(
        legal_tool_names, Sequence
    ):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names must be an ordered authoritative inventory"
        )
    legal = tuple(legal_tool_names)
    if not legal:
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names must be a non-empty authoritative inventory"
        )
    if any(
        not isinstance(name, str) or _TOOL_NAME.fullmatch(name) is None
        for name in legal
    ):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names contains a non-canonical tool name"
        )
    if len(set(legal)) != len(legal):
        raise Audio2ToolPerceptionStateError(
            "legal_tool_names contains duplicate tool names"
        )
    legal_set = frozenset(legal)

    if not isinstance(text, str) or not text.strip() or '```' in text:
        raise Audio2ToolPerceptionStateError(
            "Perception state must be one unfenced JSON object"
        )
    try:
        document = json.loads(
            text,
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
    except Audio2ToolPerceptionStateError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        raise Audio2ToolPerceptionStateError(
            "Perception state must be valid JSON"
        ) from exc
    if not isinstance(document, dict):
        raise Audio2ToolPerceptionStateError("Perception state must be a JSON object")
    if set(document) != _PERCEPTION_STATE_KEYS:
        raise Audio2ToolPerceptionStateError(
            "Perception state must contain exactly actions and global_constraints"
        )

    raw_actions = document["actions"]
    if not isinstance(raw_actions, list):
        raise Audio2ToolPerceptionStateError("actions must be an ordered list")
    if len(raw_actions) > max_actions:
        raise Audio2ToolPerceptionStateError("actions exceeds max_actions")

    action_ids = set()
    actions = []
    unique_tool_names = []
    seen_tool_names = set()
    for position, raw_action in enumerate(raw_actions):
        if not isinstance(raw_action, dict):
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}] must be a JSON object"
            )
        if set(raw_action) != _PERCEPTION_ACTION_KEYS:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}] must contain exactly action_id, "
                "candidate_tools, evidence, and uncertain_arguments"
            )
        action_id = raw_action["action_id"]
        if not isinstance(action_id, str) or _ACTION_ID.fullmatch(action_id) is None:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].action_id must be a canonical occurrence ID"
            )
        if action_id in action_ids:
            raise Audio2ToolPerceptionStateError(f"duplicate action_id: {action_id}")
        action_ids.add(action_id)

        raw_candidates = raw_action["candidate_tools"]
        if not isinstance(raw_candidates, list) or not raw_candidates:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].candidate_tools must be a non-empty ordered list"
            )
        if len(raw_candidates) > max_candidates_per_action:
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].candidate_tools exceeds max_candidates_per_action"
            )
        candidates = []
        for candidate in raw_candidates:
            if (
                not isinstance(candidate, str)
                or _TOOL_NAME.fullmatch(candidate) is None
            ):
                raise Audio2ToolPerceptionStateError(
                    f"actions[{position}].candidate_tools contains "
                    "a non-canonical tool name"
                )
            if candidate not in legal_set:
                raise Audio2ToolPerceptionStateError(
                    f"tool {candidate} is outside the authoritative inventory"
                )
            candidates.append(candidate)
            if candidate not in seen_tool_names:
                seen_tool_names.add(candidate)
                unique_tool_names.append(candidate)

        evidence = raw_action["evidence"]
        if not isinstance(evidence, str):
            raise Audio2ToolPerceptionStateError(
                f"actions[{position}].evidence must be text"
            )
        uncertain_arguments = _text_list(
            raw_action["uncertain_arguments"],
            name=f"actions[{position}].uncertain_arguments",
        )
        actions.append(
            Audio2ToolPerceptionAction(
                action_id=action_id,
                candidate_tools=tuple(candidates),
                evidence=evidence,
                uncertain_arguments=uncertain_arguments,
            )
        )

    return Audio2ToolPerceptionState(
        actions=tuple(actions),
        global_constraints=_text_list(
            document["global_constraints"], name="global_constraints"
        ),
        unique_tool_names=tuple(unique_tool_names),
    )
