"""Pure terminal-response preparation shared by live delivery and replay.

The raw model response is immutable evidence. Only the delivery input is
stripped, and a saturated or exhausted request contributes an empty input
so the registered rule can fall back to its bound predecessor.
"""

from __future__ import annotations

import hashlib
import json

from typing import Callable, Mapping, Protocol, TypeVar


class TerminalDeliveryOutcome(Protocol):
    """Structural result required by shared terminal delivery."""

    text: str
    refusal_reason: str | None


_TerminalOutcome = TypeVar("_TerminalOutcome", bound=TerminalDeliveryOutcome)


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
