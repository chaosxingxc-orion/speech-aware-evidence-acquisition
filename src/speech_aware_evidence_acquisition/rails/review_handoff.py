"""Bounded model criticism for an opt-in Reviewer-to-Planner handoff.

Raw responses remain independently sealed by the shared runner. This projection
is criticism, never external evidence, a correctness verdict or a task answer.
"""
import json


def _text(value, limit, *, empty=False):
    if not isinstance(value, str):
        raise ValueError("text required")
    value = value.strip()
    if len(value) > limit or (not value and not empty):
        raise ValueError("text outside bounds")
    return value


def normalize_review_handoff(raw: str) -> str:
    """Validate, trim and deduplicate; malformed output stays explicitly invalid."""
    result = {"schema": "saea-slot-review-handoff-v1", "status": "invalid",
              "evidence_kind": "model-criticism", "findings": [], "checked": []}
    try:
        document = json.loads(raw)
        if not isinstance(document, dict) or set(document) != {"findings", "checked"}:
            raise ValueError("unexpected fields")
        findings, checked = document["findings"], document["checked"]
        if not isinstance(findings, list) or len(findings) > 4:
            raise ValueError("findings outside bounds")
        if not isinstance(checked, list) or len(checked) > 8:
            raise ValueError("checked outside bounds")
        normalized = []
        for item in findings:
            if not isinstance(item, dict) or set(item) != {"kind", "slot_types", "draft_fragment", "reason"}:
                raise ValueError("invalid finding")
            if item["kind"] not in {"type-meaning", "boundary", "existence"}:
                raise ValueError("invalid issue kind")
            types = item["slot_types"]
            if not isinstance(types, list) or not 1 <= len(types) <= 2:
                raise ValueError("invalid slot types")
            clean = {"kind": item["kind"], "slot_types": list(dict.fromkeys(_text(t, 128) for t in types)),
                     "draft_fragment": _text(item["draft_fragment"], 256, empty=True),
                     "reason": _text(item["reason"], 512)}
            if clean not in normalized:
                normalized.append(clean)
        normalized_checks = list(dict.fromkeys(_text(t, 256) for t in checked))
        result.update(status="valid", findings=normalized, checked=normalized_checks)
    except (ValueError, TypeError):
        pass
    return json.dumps(result, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def slot_review_response_format(_lock, _root):
    """Constrain newly registered Reviewer requests to the existing handoff contract.

    The strict consumer remains authoritative. This does not reparse, repair or
    replace any historical response. Empty findings and checked lists are legal.
    """
    def text(limit, *, empty=False):
        spec = {"type": "string", "maxLength": limit}
        if not empty:
            spec["minLength"] = 1
        return spec

    finding = {
        "type": "object", "additionalProperties": False,
        "required": ["kind", "slot_types", "draft_fragment", "reason"],
        "properties": {
            "kind": {"type": "string", "enum": ["type-meaning", "boundary", "existence"]},
            "slot_types": {"type": "array", "minItems": 1, "maxItems": 2, "items": text(128)},
            "draft_fragment": text(256, empty=True),
            "reason": text(512),
        },
    }
    return {"type": "json_schema", "json_schema": {
        "name": "saea_slot_review_handoff_v1", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
                   "required": ["findings", "checked"],
                   "properties": {
                       "findings": {"type": "array", "maxItems": 4, "items": finding},
                       "checked": {"type": "array", "maxItems": 8, "items": text(256)},
                   }},
    }}
