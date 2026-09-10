"""Pure model-free assembly of SLURP slot-stage delivery rows.

A slot-stage arm supplies entity predictions while a sealed predecessor owns
scenario and action. This module joins those two row rosters without file,
model, or scorer access.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .slurp_scoring import parse_slu_response


class DeliveryJoinError(ValueError):
    """Raised when the two delivery rosters cannot be joined safely."""


def _text_of(row: Mapping[str, Any]) -> str:
    text = row.get("text")
    if text is None:
        text = row.get("final_response_text")
    if not isinstance(text, str):
        raise DeliveryJoinError(
            f"row {row.get('sample_id')!r} carries no response text"
        )
    return text


def _roster_index(rows: Sequence[Mapping[str, Any]], name: str) -> dict[str, str]:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        raise DeliveryJoinError(f"{name} roster must be a nonempty sequence")
    if not rows:
        raise DeliveryJoinError(f"{name} roster must be nonempty")
    indexed: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise DeliveryJoinError(f"{name} roster rows must be mappings")
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise DeliveryJoinError(f"{name} roster has an invalid sample_id")
        if sample_id in indexed:
            raise DeliveryJoinError(f"{name} roster has duplicate sample_id {sample_id!r}")
        indexed[sample_id] = _text_of(row)
    return indexed


@dataclass(frozen=True)
class SlurpDeliveryOutcome:
    """Structured live delivery result for the shared response-postprocessor."""

    text: str
    refusal_reason: str | None
    diagnostics: Mapping[str, int]


def join_slurp_response(
    closed_list_text: str, arm_text: str
) -> tuple[str, dict[str, int]]:
    """Join one direct response and one slot response deterministically.

    The direct response owns scenario and action; the slot response owns
    entities. Malformed labels fail closed to empty fields while diagnostics
    preserve the historical roster counters.
    """

    cl_scenario, cl_action, _cl_entities, cl_parsed = parse_slu_response(
        closed_list_text
    )
    arm_scenario, arm_action, arm_entities, arm_parsed = parse_slu_response(arm_text)
    diagnostics = {
        "rows": 1,
        "arm_response_unparsed": int(not arm_parsed),
        "arm_response_carried_scenario_or_action": int(
            bool(arm_scenario or arm_action)
        ),
        "closed_list_unparsed": int(not cl_parsed),
    }
    payload = {
        "scenario": cl_scenario if isinstance(cl_scenario, str) else "",
        "action": cl_action if isinstance(cl_action, str) else "",
        "entities": [
            {"type": entity.type, "filler": entity.filler}
            for entity in arm_entities
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True), diagnostics


def _slurp_intent_slots_delivery_rule(
    predecessor: str, response: str
) -> SlurpDeliveryOutcome:
    """Build a live SLURP delivery from direct intent and slot responses."""

    text, diagnostics = join_slurp_response(predecessor, response)
    return SlurpDeliveryOutcome(
        text=text, refusal_reason=None, diagnostics=diagnostics
    )


def slurp_intent_slots_delivery_v1():
    """Return the live SLURP two-response delivery rule."""

    return _slurp_intent_slots_delivery_rule


def join_slurp_rosters(
    arm_rows: Sequence[Mapping[str, Any]],
    closed_list_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Join arm entities to predecessor intent rows in deterministic order.

    The predecessor is authoritative for scenario and action. The arm is
    authoritative for entities. The returned rows contain only sample_id and
    canonical JSON text; no input is mutated.
    """

    arm = _roster_index(arm_rows, "arm")
    closed = _roster_index(closed_list_rows, "closed-list")
    missing = sorted(set(arm) - set(closed))
    extra = sorted(set(closed) - set(arm))
    if missing or extra:
        raise DeliveryJoinError(
            "join is not total: %d arm rows without a closed-list row, "
            "%d the other way" % (len(missing), len(extra))
        )

    projected: list[dict[str, str]] = []
    stats = {
        "rows": 0,
        "arm_response_unparsed": 0,
        "arm_response_carried_scenario_or_action": 0,
        "closed_list_unparsed": 0,
    }
    for sample_id in sorted(arm):
        text, row_stats = join_slurp_response(closed[sample_id], arm[sample_id])
        projected.append({"sample_id": sample_id, "text": text})
        for key, value in row_stats.items():
            stats[key] += value
    return projected, stats
