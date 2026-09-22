"""Item E37 (owner decision 84): the Reviewer's verdict as a closed set of
primitives.

Design: ``docs/superpowers/specs/2026-09-22-slurp-reviewer-primitive-verdict-design.md``.
Owner decision 84 of 2026-09-21 (``docs/readiness/
2026-09-16-slurp-next-stage-owner-decisions-v1.md``): the Reviewer's verdict
becomes a fixed vocabulary of verdict tokens the parser matches exactly; the
free-text rationale beside them is never parsed. NOT a JSON schema (decision
32's closure of cell B7r stands; see ``rails.review_findings`` for that
declared-but-unreachable JSON contract).

**Vocabulary** ``saea-review-primitives-v1`` (closed, case-sensitive, exact),
in the fixed order the Reviewer's instruction states it:

============================ ===================================================
token                        meaning the Reviewer asserts about the current draft
============================ ===================================================
``ACCEPT``                   no supported issue
``REVISE-INTENT``            the scenario_action is wrong or missing
``REVISE-SLOT-MISSING``      a slot the speech supports is absent
``REVISE-SLOT-EXTRA``        a slot the speech does not support is present
``REVISE-SLOT-VALUE``        a slot type is right, its filler is wrong
``REVISE-FORMAT``            the draft does not follow the task contract's form
``UNSURE``                   the Reviewer cannot decide from the speech
============================ ===================================================

**Output contract.** The Reviewer's response is: line 1 = exactly one token
of the vocabulary; every following line = free-text rationale (never parsed,
never validated, never truncated by this parser).

**The verdict is a recommendation, not a route.** The Planner keeps routing
authority
(``tests/unit/test_review_findings.py::
test_framework_carries_review_report_but_planner_keeps_routing_authority``
stays green): this module never touches ``state["plan"]`` or the router, and
the raw Reviewer text -- token and rationale together, byte for byte -- keeps
rendering into the Planner's query exactly as it does when this module is
never imported.

This module mirrors ``reproduction.ojw.native_episode._planner_action``'s own
shape: the harness never raises on a model's malformed output, so an illegal
token retains the row under a disposition, exactly as an illegal Planner
action does (``PLANNER_ACTION_ILLEGAL`` / ``PLANNER_ACTION_RECORD_CHARS``).
"""

from __future__ import annotations

REVIEW_PRIMITIVES_VOCABULARY = "saea-review-primitives-v1"

#: The closed vocabulary, in the FIXED order the Reviewer's instruction
#: states it. Case-sensitive, exact: a near-miss (``Accept``, ``REVISE``,
#: ``REVISE-SLOT``) is not a member.
ACCEPT = "ACCEPT"
REVISE_INTENT = "REVISE-INTENT"
REVISE_SLOT_MISSING = "REVISE-SLOT-MISSING"
REVISE_SLOT_EXTRA = "REVISE-SLOT-EXTRA"
REVISE_SLOT_VALUE = "REVISE-SLOT-VALUE"
REVISE_FORMAT = "REVISE-FORMAT"
UNSURE = "UNSURE"

REVIEW_PRIMITIVE_TOKENS: tuple[str, ...] = (
    ACCEPT,
    REVISE_INTENT,
    REVISE_SLOT_MISSING,
    REVISE_SLOT_EXTRA,
    REVISE_SLOT_VALUE,
    REVISE_FORMAT,
    UNSURE,
)

#: E37: the routing value this module returns instead of raising when the
#: Reviewer's first non-empty line names no vocabulary token. It is a
#: parser-internal marker only: no role is ever asked to emit it, and the
#: caller (``reproduction.ojw.native_episode._ApplyRole``) turns it into a
#: row-level receipt disposition, never a flight failure -- the same
#: treatment ``reproduction.ojw.native_episode.PLANNER_ACTION_ILLEGAL``
#: already gets for the Planner's own closed vocabulary.
REVIEW_VERDICT_ILLEGAL = "__saea_review_verdict_illegal__"

#: How much of the offending head a receipt mark retains, exactly as
#: ``reproduction.ojw.native_episode.PLANNER_ACTION_RECORD_CHARS`` bounds the
#: Planner's own illegal token. Beyond this the text is simply not kept: a
#: Reviewer's malformed line may quote the draft, which a receipt is not a
#: place for.
REVIEW_PRIMITIVE_RECORD_CHARS = 32


class ReviewPrimitiveError(ValueError):
    """A response could not even be treated as text for this parser."""


def parse_review_primitive(text: str) -> tuple[str, str | None, str | None]:
    """Parse one Reviewer response's primitive verdict.

    Returns ``(token, rationale, head)``.

    Legal: ``token`` is one of :data:`REVIEW_PRIMITIVE_TOKENS`, exactly the
    first non-empty line, stripped; ``rationale`` is every line after that
    one, joined with ``"\\n"``, kept byte-exact (never parsed, never
    validated, never truncated); ``head`` is ``None``.

    Illegal -- including empty or whitespace-only text, and a near-miss
    token: ``token`` is :data:`REVIEW_VERDICT_ILLEGAL`, ``rationale`` is
    ``None``, ``head`` is the first :data:`REVIEW_PRIMITIVE_RECORD_CHARS`
    characters of the offending first non-empty line (or of the whole text,
    when it carries no non-empty line at all).
    """

    if not isinstance(text, str):
        raise ReviewPrimitiveError("a review primitive response must be text")
    lines = text.split("\n")
    first_index = None
    for index, line in enumerate(lines):
        if line.strip():
            first_index = index
            break
    if first_index is None:
        return REVIEW_VERDICT_ILLEGAL, None, text[:REVIEW_PRIMITIVE_RECORD_CHARS]
    candidate = lines[first_index].strip()
    if candidate not in REVIEW_PRIMITIVE_TOKENS:
        return REVIEW_VERDICT_ILLEGAL, None, candidate[:REVIEW_PRIMITIVE_RECORD_CHARS]
    rationale = "\n".join(lines[first_index + 1:])
    return candidate, rationale, None


__all__ = [
    "REVIEW_PRIMITIVES_VOCABULARY",
    "REVIEW_PRIMITIVE_TOKENS",
    "REVIEW_VERDICT_ILLEGAL",
    "REVIEW_PRIMITIVE_RECORD_CHARS",
    "ReviewPrimitiveError",
    "parse_review_primitive",
    "ACCEPT",
    "REVISE_INTENT",
    "REVISE_SLOT_MISSING",
    "REVISE_SLOT_EXTRA",
    "REVISE_SLOT_VALUE",
    "REVISE_FORMAT",
    "UNSURE",
]
