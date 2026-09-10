"""Pure terminal-response preparation shared by live delivery and replay.

The raw model response is immutable evidence. Only the delivery input is
stripped, and a saturated or exhausted request contributes an empty input
so the registered rule can fall back to its bound predecessor.
"""

from __future__ import annotations

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
