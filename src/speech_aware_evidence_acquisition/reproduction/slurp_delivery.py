"""Pure model-free assembly of registered SLURP delivery responses.

The historical slot-stage rule keeps predecessor intent authority. The joint
hypothesis rule validates its predecessor as alternatives, then makes the
final response authoritative for intent and entities. Neither rule contacts a
model or scorer.
"""

from __future__ import annotations

import json
import re
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


_FINAL_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_FINAL_KEYS = frozenset({"scenario", "action", "entities"})
_ENTITY_KEYS = frozenset({"type", "filler"})


def _strict_joint_response(text: str):
    """Parse the final task contract without duplicate or partial entities."""

    from ..rails.slurp_intent_hypotheses import _unique_json_object  # noqa: PLC0415

    candidates = [match.strip() for match in _FINAL_FENCE_RE.findall(text)]
    candidates.append(text.strip())
    for candidate in candidates:
        if not candidate:
            continue
        try:
            payload = json.loads(candidate, object_pairs_hook=_unique_json_object)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(payload, Mapping) or set(payload) != _FINAL_KEYS:
            continue
        scenario = payload["scenario"]
        action = payload["action"]
        entities = payload["entities"]
        if (
            not isinstance(scenario, str)
            or not scenario
            or not isinstance(action, str)
            or not action
            or not isinstance(entities, list)
        ):
            continue
        if any(
            not isinstance(entity, Mapping)
            or set(entity) != _ENTITY_KEYS
            or not isinstance(entity["type"], str)
            or not isinstance(entity["filler"], str)
            for entity in entities
        ):
            continue
        parsed = parse_slu_response(
            json.dumps(payload, ensure_ascii=False, sort_keys=True)
        )
        if parsed[3]:
            return parsed
    return None, None, [], False


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


def slurp_joint_hypothesis_delivery_rule(
    predecessor: str,
    response: str,
    *,
    legal_intent_ids: set[str] | frozenset[str],
    max_candidates: int,
) -> SlurpDeliveryOutcome:
    """Deliver one final-authoritative intent and entity response.

    The predecessor is validated as ranked alternatives only. It never owns
    delivered fields. A legal final intent outside the shortlist is allowed
    because the shortlist is guidance over the full legal task inventory.
    """

    from ..rails.slurp_intent_hypotheses import (  # noqa: PLC0415
        SlurpIntentHypothesisError,
        parse_slurp_intent_hypothesis_content,
    )

    diagnostics = {
        "rows": 1,
        "hypothesis_state_invalid": 0,
        "final_response_unparsed": 0,
        "final_intent_illegal": 0,
        "final_intent_outside_shortlist": 0,
        "final_authoritative": 0,
    }
    try:
        hypothesis_state = parse_slurp_intent_hypothesis_content(
            predecessor,
            expected_sample_id=None,
            legal_intent_ids=legal_intent_ids,
            max_candidates=max_candidates,
        )
    except SlurpIntentHypothesisError:
        diagnostics["hypothesis_state_invalid"] = 1
        return SlurpDeliveryOutcome(
            text=response,
            refusal_reason="invalid_hypothesis_predecessor",
            diagnostics=diagnostics,
        )

    if not response:
        diagnostics["final_response_unparsed"] = 1
        return SlurpDeliveryOutcome(
            text=response, refusal_reason="empty_response", diagnostics=diagnostics
        )
    scenario, action, entities, parsed = _strict_joint_response(response)
    if not parsed:
        diagnostics["final_response_unparsed"] = 1
        return SlurpDeliveryOutcome(
            text=response,
            refusal_reason="malformed_final_response",
            diagnostics=diagnostics,
        )
    intent_id = (
        f"{scenario}_{action}"
        if isinstance(scenario, str)
        and scenario
        and isinstance(action, str)
        and action
        else ""
    )
    if intent_id not in legal_intent_ids:
        diagnostics["final_intent_illegal"] = 1
        return SlurpDeliveryOutcome(
            text=response,
            refusal_reason="illegal_final_intent",
            diagnostics=diagnostics,
        )

    shortlist = {candidate.intent_id for candidate in hypothesis_state.candidates}
    diagnostics["final_intent_outside_shortlist"] = int(intent_id not in shortlist)
    diagnostics["final_authoritative"] = 1
    payload = {
        "scenario": scenario,
        "action": action,
        "entities": [
            {"type": entity.type, "filler": entity.filler} for entity in entities
        ],
    }
    return SlurpDeliveryOutcome(
        text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        refusal_reason=None,
        diagnostics=diagnostics,
    )


def slurp_joint_hypothesis_delivery_v1(*, max_candidates: int):
    """Build the registered joint delivery rule from the TRAIN legal inventory."""

    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from .slurp_official_eval import load_legal_intent_inventory  # noqa: PLC0415

    inventory = load_legal_intent_inventory(
        load_lock(umbrella_lock_path()), data_root()
    )
    legal_intent_ids = frozenset(
        f"{scenario}_{action}" for scenario, action in inventory.pairs
    )

    def deliver(predecessor: str, response: str) -> SlurpDeliveryOutcome:
        return slurp_joint_hypothesis_delivery_rule(
            predecessor,
            response,
            legal_intent_ids=legal_intent_ids,
            max_candidates=max_candidates,
        )

    return deliver


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


def slurp_hard_first_hypothesis_delivery_rule(
    predecessor: str,
    response: str,
    *,
    legal_intent_pairs: Mapping[str, tuple[str, str]],
    max_candidates: int,
) -> SlurpDeliveryOutcome:
    """Keep the first hypothesis authoritative and deliver strict final entities.

    Use the same predecessor and response validation as the joint rule. Preserve
    the attempted final response in the source bundle; this explicit derivative
    records when intent authority overrode a model revision. Resolve label parts
    through the legal inventory rather than splitting IDs containing underscores.
    """
    from ..rails.slurp_intent_hypotheses import (  # noqa: PLC0415
        parse_slurp_intent_hypothesis_content,
    )

    if not legal_intent_pairs or any(
        not isinstance(pair, (tuple, list))
        or len(pair) != 2
        or any(not isinstance(part, str) or not part for part in pair)
        or intent_id != f"{pair[0]}_{pair[1]}"
        for intent_id, pair in legal_intent_pairs.items()
    ):
        raise ValueError("hard-first delivery requires a consistent legal intent pair map")
    legal_ids = frozenset(legal_intent_pairs)
    validated = slurp_joint_hypothesis_delivery_rule(
        predecessor, response, legal_intent_ids=legal_ids,
        max_candidates=max_candidates,
    )
    diagnostics = {
        **validated.diagnostics,
        "final_authoritative": 0,
        "hard_first_committed": 0,
        "attempted_intent_switch": 0,
    }
    if validated.refusal_reason is not None:
        return SlurpDeliveryOutcome(
            text="", refusal_reason=validated.refusal_reason,
            diagnostics=diagnostics,
        )
    hypotheses = parse_slurp_intent_hypothesis_content(
        predecessor, expected_sample_id=None, legal_intent_ids=legal_ids,
        max_candidates=max_candidates,
    )
    first_id = hypotheses.candidates[0].intent_id
    payload = json.loads(validated.text)
    attempted_id = f"{payload['scenario']}_{payload['action']}"
    payload["scenario"], payload["action"] = legal_intent_pairs[first_id]
    diagnostics["attempted_intent_switch"] = int(attempted_id != first_id)
    diagnostics["hard_first_committed"] = 1
    return SlurpDeliveryOutcome(
        text=json.dumps(payload, ensure_ascii=False, sort_keys=True),
        refusal_reason=None, diagnostics=diagnostics,
    )


def slurp_hard_first_hypothesis_delivery_v1(*, max_candidates: int):
    """Build the registered fixed-intent rule from the pinned TRAIN inventory."""
    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from .slurp_official_eval import load_legal_intent_inventory  # noqa: PLC0415

    inventory = load_legal_intent_inventory(
        load_lock(umbrella_lock_path()), data_root()
    )
    pairs = {f"{scenario}_{action}": (scenario, action)
             for scenario, action in inventory.pairs}

    def deliver(predecessor: str, response: str) -> SlurpDeliveryOutcome:
        return slurp_hard_first_hypothesis_delivery_rule(
            predecessor, response, legal_intent_pairs=pairs,
            max_candidates=max_candidates,
        )

    return deliver

def slurp_shortlist_joint_hypothesis_delivery_rule(
    predecessor: str,
    response: str,
    *,
    legal_intent_ids: set[str] | frozenset[str],
    max_candidates: int,
) -> SlurpDeliveryOutcome:
    """Enforce the closed-shortlist comparison without editing raw responses.

    A refused result delivers no task answer. The generation bundle retains the
    full attempted answer, so an out-of-shortlist correct answer cannot silently
    count as compliance with a closed-candidate experiment.
    """
    validated = slurp_joint_hypothesis_delivery_rule(
        predecessor, response, legal_intent_ids=legal_intent_ids,
        max_candidates=max_candidates,
    )
    reason = validated.refusal_reason
    if reason is None and validated.diagnostics["final_intent_outside_shortlist"]:
        reason = "final_intent_outside_shortlist"
    diagnostics = {
        **validated.diagnostics,
        "final_authoritative": int(reason is None),
        "shortlist_constraint_satisfied": int(reason is None),
    }
    return SlurpDeliveryOutcome(
        text=validated.text if reason is None else "",
        refusal_reason=reason, diagnostics=diagnostics,
    )


def slurp_shortlist_joint_hypothesis_delivery_v1(*, max_candidates: int):
    """Build the registered closed-shortlist rule from the TRAIN inventory."""
    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from .slurp_official_eval import load_legal_intent_inventory  # noqa: PLC0415

    inventory = load_legal_intent_inventory(
        load_lock(umbrella_lock_path()), data_root()
    )
    legal_ids = frozenset(f"{scenario}_{action}" for scenario, action in inventory.pairs)

    def deliver(predecessor: str, response: str) -> SlurpDeliveryOutcome:
        return slurp_shortlist_joint_hypothesis_delivery_rule(
            predecessor, response, legal_intent_ids=legal_ids,
            max_candidates=max_candidates,
        )

    return deliver
