"""Strict shared parsing for declared Reviewer findings."""

from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator, ValidationError

REVIEW_FINDINGS_SCHEMA = "saea-review-findings-v1"
_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "schema", "verdict", "findings", "recommendation", "remaining_uncertainty",
    ],
    "properties": {
        "schema": {"const": REVIEW_FINDINGS_SCHEMA},
        "verdict": {
            "enum": ["no-supported-issue", "supported-issue", "insufficient-evidence"],
        },
        "recommendation": {"enum": ["retain", "reconsider", "seek-evidence"]},
        "remaining_uncertainty": {"type": "string", "maxLength": 240},
        "findings": {
            "type": "array", "maxItems": 2,
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["dimension", "rationale", "evidence_ids"],
                "properties": {
                    "dimension": {"enum": [
                        "intent", "slot-presence", "slot-type", "slot-span", "schema",
                    ]},
                    "rationale": {"type": "string", "minLength": 1, "maxLength": 240},
                    "evidence_ids": {
                        "type": "array", "maxItems": 3, "uniqueItems": True,
                        "items": {"type": "string", "minLength": 1, "maxLength": 160},
                    },
                },
            },
        },
    },
}
_VALIDATOR = Draft202012Validator(_REPORT_SCHEMA)


class ReviewFindingsError(ValueError):
    """A response has no unambiguous report under the registered contract."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReviewFindingsError("review report repeats a JSON key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ReviewFindingsError("review report contains a nonfinite JSON constant")


def parse_review_findings(text: str) -> dict[str, Any]:
    """Return the exact structured declaration, or reject without text repair."""
    if not isinstance(text, str) or not text.strip() or len(text) > 16384:
        raise ReviewFindingsError("review report requires bounded nonempty text")
    try:
        report = json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
        _VALIDATOR.validate(report)
    except (json.JSONDecodeError, ValidationError) as error:
        raise ReviewFindingsError("review report does not match its JSON contract") from error
    verdict = report["verdict"]
    findings = report["findings"]
    recommendation = report["recommendation"]
    if verdict == "no-supported-issue":
        if findings or recommendation != "retain":
            raise ReviewFindingsError("no supported issue requires empty findings and retain")
    elif not findings or recommendation == "retain":
        raise ReviewFindingsError("a concern requires findings and a non-retain recommendation")
    if verdict == "insufficient-evidence" and not report["remaining_uncertainty"].strip():
        raise ReviewFindingsError("insufficient evidence requires an explicit uncertainty")
    for finding in findings:
        if not finding["rationale"].strip() or any(
            not evidence_id.strip() for evidence_id in finding["evidence_ids"]
        ):
            raise ReviewFindingsError("finding text and evidence IDs cannot be blank")
    return report


def review_findings_response_format(
    _lock: Any = None, _root: Any = None, **params: Any
) -> dict[str, Any]:
    """The ``core.base.RESPONSE_FORMATS`` entry ``"saea-review-findings-v1"``.

    E8a (coordinator decision 1 of 2026-09-17): the node-context policy's
    ``review-finding`` PRODUCER may declare a structured output contract, so
    that the boundary's consumer template has something to structure. The
    schema rendered here is :data:`_REPORT_SCHEMA` itself, minus the
    ``uniqueItems`` keyword that constrained decoding does not express -- so a
    response generated under this format satisfies
    :func:`parse_review_findings` by construction, and the parser stays the
    authority on everything the schema cannot say (the verdict/findings/
    recommendation agreement rules below it).

    The audit measured 0 of 2,167 anchor Reviewer outputs parsing under that
    parser, because the Reviewer prompt asks for prose and its phase declares
    no response format (``docs/results/2026-09-17-slurp-node-context-audit-v1.md``
    section 6). This id is what a cell config binds to close that gap; nothing
    here changes any phase by itself.
    """

    if params:
        raise ReviewFindingsError("review findings response format takes no parameters")
    schema = json.loads(json.dumps(_REPORT_SCHEMA))
    del schema["properties"]["findings"]["items"]["properties"]["evidence_ids"][
        "uniqueItems"
    ]
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_review_findings_v1",
            "strict": True,
            "schema": schema,
        },
    }


__all__ = [
    "REVIEW_FINDINGS_SCHEMA",
    "ReviewFindingsError",
    "parse_review_findings",
    "review_findings_response_format",
]
