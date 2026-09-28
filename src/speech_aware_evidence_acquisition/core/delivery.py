"""Pure terminal-response preparation shared by live delivery and replay.

The raw model response is immutable evidence. Only the delivery input is
stripped, and a saturated or exhausted request contributes an empty input
so the registered rule can fall back to its bound predecessor.
"""

from __future__ import annotations

import hashlib
import json

from typing import Callable, Mapping, Protocol, Sequence, TypeVar

from ..rails.errors import RailsError
from ..rails.execution_units import ExecutionUnitRoster


_SHA256_LENGTH = 64
_EXECUTION_UNIT_RESULT_KEYS = {
    "sample_id",
    "execution_unit_id",
    "execution_unit_binding",
    "request_id",
    "request_sha256",
    "response_sha256",
    "response_text_sha256",
    "text",
    "saturated",
    "skipped",
}


class TerminalDeliveryOutcome(Protocol):
    """Structural result required by shared terminal delivery."""

    text: str
    refusal_reason: str | None


_TerminalOutcome = TypeVar("_TerminalOutcome", bound=TerminalDeliveryOutcome)


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != _SHA256_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"execution unit {label} must be a lowercase SHA256")
    return value


def stitch_ordered_text(parts: Sequence[str]) -> str:
    """Join nonempty ordered delivery parts with the historical OBS separator."""

    if not isinstance(parts, Sequence) or isinstance(parts, (str, bytes)):
        raise ValueError("ordered stitch parts must be a sequence of strings")
    if any(not isinstance(part, str) for part in parts):
        raise ValueError("ordered stitch parts must be strings")
    return " ".join(part for part in parts if part)


def stitch_execution_unit_results(
    roster: ExecutionUnitRoster,
    parent_sample_ids: Sequence[str],
    terminal_results: Sequence[Mapping[str, object]],
) -> tuple[dict[str, object], ...]:
    """Validate and stitch one complete ordered result for every execution unit."""

    if not isinstance(roster, ExecutionUnitRoster):
        raise ValueError("execution unit delivery requires an ExecutionUnitRoster")
    parents = tuple(parent_sample_ids)
    try:
        roster.validate(
            parent_sample_ids=parents, max_contacts=max(1, len(roster.units))
        )
    except (RailsError, TypeError, ValueError) as error:
        raise ValueError(str(error)) from error
    if not isinstance(terminal_results, Sequence) or isinstance(
        terminal_results, (str, bytes)
    ):
        raise ValueError("execution unit terminal results must be an ordered sequence")
    if len(terminal_results) != len(roster.units):
        raise ValueError(
            "execution unit terminal results do not exactly cover the roster"
        )

    roster_sha256 = roster.content_hash()
    parent_roster_sha256 = _canonical_digest(list(parents))
    by_parent: dict[str, list[dict[str, object]]] = {parent: [] for parent in parents}
    request_ids: set[str] = set()

    for position, (unit, result) in enumerate(
        zip(roster.units, terminal_results, strict=True)
    ):
        if not isinstance(result, Mapping) or not _EXECUTION_UNIT_RESULT_KEYS.issubset(
            result
        ):
            raise ValueError(
                f"execution unit terminal result {position} lacks registered keys"
            )
        if (
            result["sample_id"] != unit.parent_sample_id
            or result["execution_unit_id"] != unit.request_key
        ):
            raise ValueError(
                f"execution unit terminal result {position} is out of roster order"
            )
        binding = result["execution_unit_binding"]
        if not isinstance(binding, Mapping) or _canonical_digest(
            binding
        ) != _canonical_digest(unit.as_json()):
            raise ValueError(
                f"execution unit terminal result {position} changed its source binding"
            )
        request_id = result["request_id"]
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("execution unit request_id must be a nonempty string")
        if request_id in request_ids:
            raise ValueError("execution unit terminal results repeat a request_id")
        request_ids.add(request_id)
        request_sha256 = _require_sha256(result["request_sha256"], "request_sha256")
        response_sha256 = _require_sha256(result["response_sha256"], "response_sha256")
        response_text_sha256 = _require_sha256(
            result["response_text_sha256"], "response_text_sha256"
        )
        text = result["text"]
        if not isinstance(text, str):
            raise ValueError("execution unit raw delivery text must be a string")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != response_text_sha256:
            raise ValueError(
                "execution unit raw delivery text hash differs from its receipt"
            )
        saturated, skipped = result["saturated"], result["skipped"]
        if not isinstance(saturated, bool) or not isinstance(skipped, bool):
            raise ValueError("execution unit terminal flags must be booleans")
        if saturated and skipped:
            raise ValueError(
                "execution unit terminal result cannot be saturated and skipped"
            )
        delivered = normalize_terminal_response(
            text, saturated=saturated, skipped=skipped
        )
        by_parent[unit.parent_sample_id].append(
            {
                "execution_unit_id": unit.request_key,
                "execution_unit_binding": json.loads(
                    json.dumps(unit.as_json(), allow_nan=False)
                ),
                "request_id": request_id,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "raw_text_sha256": response_text_sha256,
                "delivery_text_sha256": hashlib.sha256(
                    delivered.encode("utf-8")
                ).hexdigest(),
                "saturated": saturated,
                "skipped": skipped,
                "delivery_text": delivered,
            }
        )

    rows: list[dict[str, object]] = []
    for parent in parents:
        sources = by_parent[parent]
        stitched = stitch_ordered_text(
            [str(source["delivery_text"]) for source in sources]
        )
        stitched_request_ids = [str(source["request_id"]) for source in sources]
        source_request_sha256s = [str(source["request_sha256"]) for source in sources]
        source_response_sha256s = [str(source["response_sha256"]) for source in sources]
        request_sha256 = _canonical_digest(
            {
                "stitched_request_ids": stitched_request_ids,
                "iteration_request_sha256s": source_request_sha256s,
            }
        )
        response_sha256 = _canonical_digest(
            {
                "stitched_text": stitched,
                "stitched_from_response_sha256s": source_response_sha256s,
            }
        )
        public_sources = []
        for source in sources:
            public_source = dict(source)
            del public_source["delivery_text"]
            public_sources.append(public_source)
        rows.append(
            {
                "schema": "saea-execution-unit-stitched-result-v1",
                "sample_id": parent,
                "execution_unit_roster_sha256": roster_sha256,
                "parent_roster_sha256": parent_roster_sha256,
                "text": stitched,
                "request_ids": stitched_request_ids,
                "source_request_sha256s": source_request_sha256s,
                "source_response_sha256s": source_response_sha256s,
                "sources": public_sources,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "response_text_sha256": hashlib.sha256(
                    stitched.encode("utf-8")
                ).hexdigest(),
            }
        )
    return tuple(rows)


def normalize_terminal_response(
    text: str | None, *, saturated: bool = False, skipped: bool = False
) -> str:
    """Return the exact input that a terminal response contributes to delivery."""
    if not isinstance(saturated, bool) or not isinstance(skipped, bool):
        raise ValueError("terminal saturated/skipped flags must be booleans")
    if skipped or saturated:
        return ""
    if not isinstance(text, str):
        raise ValueError("a successful terminal response must carry text")
    return text.strip()


def deliver_terminal_response(
    predecessor: str,
    text: str | None,
    *,
    rule: Callable[[str, str], _TerminalOutcome],
    saturated: bool = False,
    skipped: bool = False,
) -> _TerminalOutcome:
    """Apply an existing registered rule to the normalized terminal input."""
    return rule(
        predecessor,
        normalize_terminal_response(text, saturated=saturated, skipped=skipped),
    )


def terminal_response_saturated(
    usage: Mapping[str, object] | None, max_tokens: object
) -> bool:
    """Use the live cap rule; missing or malformed usage cannot imply saturation."""
    if (
        max_tokens is None
        or isinstance(max_tokens, bool)
        or not isinstance(max_tokens, (int, float))
    ):
        return False
    if not isinstance(usage, Mapping):
        return False
    completion_tokens = usage.get("completion_tokens")
    if isinstance(completion_tokens, bool) or not isinstance(
        completion_tokens, (int, float)
    ):
        return False
    return completion_tokens >= max_tokens


def native_context_abstention_records(
    *, sample_id: str, disposition: Mapping[str, object],
) -> tuple[str, dict[str, object], dict[str, object]]:
    """E20 (2026-09-19): derive empty delivery for a row refused for width.

    The finite abstention above derives its identity from the quarantined
    SOURCE CONTACT. A context-fit abstention has none: the request that
    would have been the Solver's first was refused before it was answered
    (or the server refused it), so the only custody the row owns is its own
    terminal disposition. That disposition -- the refusing seam, the
    compaction pass, the identifiers dropped and the token counts -- is
    what this derivation is bound to, and it is deterministic: the same
    disposition always derives the same record.

    No model call, no new bytes on the wire, and the delivered text is the
    same normalized empty answer the finite abstention delivers.
    """

    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("native abstention requires a sample identity")
    if (
        not isinstance(disposition, Mapping)
        or disposition.get("reason") != "context_compaction"
        or disposition.get("source") not in ("dispatch-budget", "server-refusal")
    ):
        raise ValueError("context abstention requires its context-fit disposition")

    def digest(value):
        return hashlib.sha256(json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")).hexdigest()

    disposition_sha256 = digest(dict(disposition))
    request_id = f"{sample_id}/{disposition_sha256}/delivery/native-context-abstention-v1"
    request = {
        "tool_id": "native-context-abstention-v1",
        "sample_id": sample_id,
        "source": {
            "source_request_id": None,
            "terminal_disposition_sha256": disposition_sha256,
            "refusal_source": disposition["source"],
        },
        "reason": "context_compaction",
        "policy": "compact-or-abstain",
        "disposition": "no-completed-solver",
    }
    request["payload_sha256"] = digest(request)
    response = {
        "text": normalize_terminal_response(None, skipped=True),
        "source_request_id": None,
        "delivery_kind": "abstention",
        "request_sha256": request["payload_sha256"],
    }
    response["response_sha256"] = digest(response)
    response["response_text_sha256"] = hashlib.sha256(b"").hexdigest()
    return request_id, request, response


def native_seal_refusal_abstention_records(
    *, sample_id: str, source_contact: Mapping[str, object],
    seal_refusal: Mapping[str, object],
) -> tuple[str, dict[str, object], dict[str, object]]:
    """Item E43 (2026-09-28): derive empty delivery for a row whose deciding
    completion a structured-output contract's own seal refused.

    Mirrors :func:`native_abstention_records` -- the SAME
    ``deliver-latest-or-abstain`` policy, the SAME quarantined-source
    derivation, no new model call -- with the one difference the facts
    force: there is no ``finish_reason`` to record. The refused completion
    is always a grammar-valid ``"stop"`` finish (the seal, never the wire,
    refused it), so the disposition's own ``seal_refusal`` record -- the
    refusal's exception class and message, never the answer -- takes that
    field's place.
    """

    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("native abstention requires a sample identity")
    if (
        not isinstance(seal_refusal, Mapping)
        or set(seal_refusal) != {"error_class", "message"}
        or not isinstance(seal_refusal["error_class"], str) or not seal_refusal["error_class"]
        or not isinstance(seal_refusal["message"], str) or not seal_refusal["message"]
    ):
        raise ValueError("native abstention requires its seal-refusal record")
    fields = ("agent_contact_id", "request_id", "request_sha256",
              "response_sha256", "response_text_sha256")
    if not isinstance(source_contact, Mapping):
        raise ValueError("native abstention requires source contact custody")
    source = {key: source_contact.get(key) for key in fields}
    for key, value in source.items():
        if not isinstance(value, str) or not value:
            raise ValueError("native abstention source identity is invalid")
        if key.endswith("sha256") and (
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("native abstention source hash is invalid")

    def digest(value):
        return hashlib.sha256(json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")).hexdigest()

    request_id = f"{source['request_id']}/delivery/native-seal-refusal-abstention-v1"
    request = {
        "tool_id": "native-terminal-seal-refusal-abstention-v1",
        "sample_id": sample_id,
        "source": {"source_request_id": source["request_id"], "contact": source},
        "seal_refusal": dict(seal_refusal),
        "policy": "deliver-latest-or-abstain",
        "disposition": "no-completed-solver",
    }
    request["payload_sha256"] = digest(request)
    response = {
        "text": normalize_terminal_response(None, skipped=True),
        "source_request_id": source["request_id"],
        "delivery_kind": "abstention",
        "request_sha256": request["payload_sha256"],
    }
    response["response_sha256"] = digest(response)
    response["response_text_sha256"] = hashlib.sha256(b"").hexdigest()
    return request_id, request, response


def native_abstention_records(
    *, sample_id: str, source_contact: Mapping[str, object], finish_reason: str,
) -> tuple[str, dict[str, object], dict[str, object]]:
    """Derive empty delivery from a quarantined source without a new model call.

    The returned request and response are deterministic derivation records.
    Keep the original metered response under its original request ID. Callers
    validate the complete episode receipt before selecting this no-Solver rule.
    """
    if not isinstance(sample_id, str) or not sample_id:
        raise ValueError("native abstention requires a sample identity")
    if finish_reason not in ("length", "content_filter"):
        raise ValueError("native abstention requires a finite completion")
    fields = ("agent_contact_id", "request_id", "request_sha256",
              "response_sha256", "response_text_sha256")
    if not isinstance(source_contact, Mapping):
        raise ValueError("native abstention requires source contact custody")
    source = {key: source_contact.get(key) for key in fields}
    for key, value in source.items():
        if not isinstance(value, str) or not value:
            raise ValueError("native abstention source identity is invalid")
        if key.endswith("sha256") and (
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
        ):
            raise ValueError("native abstention source hash is invalid")

    def digest(value):
        return hashlib.sha256(json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")).hexdigest()

    request_id = f"{source['request_id']}/delivery/native-abstention-v1"
    request = {
        "tool_id": "native-terminal-abstention-v1",
        "sample_id": sample_id,
        "source": {"source_request_id": source["request_id"], "contact": source},
        "finish_reason": finish_reason,
        "policy": "deliver-latest-or-abstain",
        "disposition": "no-completed-solver",
    }
    request["payload_sha256"] = digest(request)
    response = {
        "text": normalize_terminal_response(None, skipped=True),
        "source_request_id": source["request_id"],
        "delivery_kind": "abstention",
        "request_sha256": request["payload_sha256"],
    }
    response["response_sha256"] = digest(response)
    response["response_text_sha256"] = hashlib.sha256(b"").hexdigest()
    return request_id, request, response
