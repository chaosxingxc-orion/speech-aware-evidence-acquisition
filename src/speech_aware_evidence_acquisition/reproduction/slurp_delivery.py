"""Pure model-free assembly of SLURP slot-stage delivery rows.

A slot-stage arm supplies entity predictions while a sealed predecessor owns
scenario and action. This module joins those two row rosters without file,
model, or scorer access. Callers that need a JSONL artifact are responsible
for writing the returned rows.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
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
        cl_scenario, cl_action, _cl_entities, cl_parsed = parse_slu_response(
            closed[sample_id]
        )
        arm_scenario, arm_action, arm_entities, arm_parsed = parse_slu_response(
            arm[sample_id]
        )
        if not cl_parsed:
            stats["closed_list_unparsed"] += 1
        if not arm_parsed:
            stats["arm_response_unparsed"] += 1
        if arm_scenario or arm_action:
            stats["arm_response_carried_scenario_or_action"] += 1
        payload = {
            "scenario": cl_scenario if isinstance(cl_scenario, str) else "",
            "action": cl_action if isinstance(cl_action, str) else "",
            "entities": [
                {"type": entity.type, "filler": entity.filler}
                for entity in arm_entities
            ],
        }
        projected.append(
            {
                "sample_id": sample_id,
                "text": json.dumps(payload, ensure_ascii=False, sort_keys=True),
            }
        )
        stats["rows"] += 1
    return projected, stats
