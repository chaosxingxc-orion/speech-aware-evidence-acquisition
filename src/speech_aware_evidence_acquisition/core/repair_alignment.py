"""Second-pass ENTITY REPAIR: a delivered hypothesis that can differ from its
pass-1 predecessor by SUBSTITUTIONS ONLY.

Why this module exists
----------------------
The KC-E1 verdict (``docs/readiness/2026-09-07-e21-kc-e1-pre-meeting-brief-v1-
verdict.md``) is REJECTED with the primary met on both legs: the whole-prompt
pre-meeting brief repaired **152 PERSON substitutions** and paid for them with
**2,242 extra non-entity deletions**, so corpus-WER non-inferiority and numeric
accuracy both failed. The failing guard is transcript COMPLETENESS, and its §12
names one next step -- buy the entity gain without spending the transcript, by
supplying the brief to a SECOND pass that may only correct names in a
first-pass hypothesis it is given.

"May only correct names" cannot be an instruction. An instruction is a request;
this module is the enforcement. It takes the pass-1 hypothesis and the pass-2
response and returns the DELIVERED hypothesis, built so that the only way the
delivery can differ from pass 1 is a bounded, token-count-preserving
substitution. Insertions and deletions are structurally unreachable, which is
what makes "the non-entity deletion profile is the comparator's by
construction" a property of the harness rather than a hope about the model.

The alignment, stated exactly
-----------------------------
1. Both texts are tokenized on whitespace runs (``\\S+``). For the pass-1 side
   the CHARACTER OFFSETS of every token are kept, so an untouched token is
   delivered as its own original bytes and never as a re-joined copy.
2. ``difflib.SequenceMatcher(a=pass1_tokens, b=returned_tokens,
   autojunk=False)`` produces the opcodes. ``autojunk`` is off because the
   heuristic it enables suppresses popular elements in long sequences, and a
   transcript's popular elements are exactly the function words that anchor
   this alignment.
3. Each opcode is dispositioned, and only one disposition can change a byte:

   =============== ======================================================
   opcode          disposition
   =============== ======================================================
   ``equal``       the pass-1 bytes are delivered verbatim.
   ``replace``     ACCEPTED as a substitution iff the two sides have the
                   SAME token count and that count is
                   ``<= max_span_tokens``; otherwise rejected.
   ``insert``      REJECTED -- the returned tokens are dropped.
   ``delete``      REJECTED -- the pass-1 tokens are delivered verbatim.
   =============== ======================================================

   A rejected opcode is counted by class and never changes a byte. An
   unequal-length ``replace`` is rejected because it IS an insertion or a
   deletion wearing a substitution's clothes: accepting it would move the
   token count and reopen the very failure this cell exists to close.
4. Three whole-response REFUSALS, checked after the opcodes and before any
   splice. A refusal delivers the pass-1 text byte for byte and names itself:

   * ``empty_response`` -- the response is empty or all whitespace.
   * ``anchor_ratio_below_floor`` -- the ``equal`` opcodes cover less than
     ``min_anchor_ratio`` of the pass-1 tokens. This is the garbage case: a
     response that answered a different question, summarized, translated, or
     ran away, has no anchor and its "substitutions" are alignment noise.
   * ``substituted_fraction_above_ceiling`` -- the ACCEPTED substitutions
     would rewrite more than ``max_substituted_fraction`` of the pass-1
     tokens. A wholesale rewrite that happens to preserve token counts is
     still a wholesale rewrite.
5. Accepted substitutions are spliced into the pass-1 STRING by character
   offset, right to left, so every unsubstituted byte -- punctuation, casing,
   spacing -- survives exactly.

The invariant, asserted rather than asserted-in-prose
-----------------------------------------------------
``len(delivered.split()) == len(pass1_text.split())`` on every outcome, refusal
and acceptance alike. :func:`accept_entity_repair` checks it before returning
and raises :class:`RepairAlignmentError` if it ever fails, because a delivered
hypothesis whose token count moved is exactly the defect this module exists to
make impossible and it must never be scored silently.

The second registered rule, and why it lives here (DR-1f, 2026-09-09)
---------------------------------------------------------------------
Owner Decision 13-J asks what a draft refresh is worth when the harness does
NOT bound the edit. :func:`accept_free_refresh` is that arm's delivery rule: it
returns the response verbatim, counts the opcodes the bounded rule would have
rejected so the two arms' edit profiles land in one table, and keeps exactly
two of the four whole-response refusals so the two cells differ in one thing
only. It lives beside :func:`accept_entity_repair` deliberately -- one module
is the authority on what a second pass may deliver, and a free delivery
implemented somewhere else would be a second answer to that question. Its
delivered token count is NOT the predecessor's and is not asserted to be: that
invariant belongs to the splice, and giving it up is exactly the risk DR-1f
exists to price.

What this module is NOT
-----------------------
It is not a scorer, it never sees a reference transcript or a gold label, and
it has no opinion about which substitutions are *good* -- it enforces the SHAPE
of an edit, not its truth. Whether the repaired names are the right names is
what the ConEC entity-WER mirror measures afterwards, on the sealed delivery.

It is also not a JSON response format. ``core.base.RESPONSE_FORMATS`` holds
``(lock, root, **params) -> Mapping`` builders that render a structured-decoding
SCHEMA from pinned carrier data; a pass-2 answer here is free transcript text
and no schema can express "the same words, with names fixed". The registry this
module populates is therefore its own -- ``core.base.RESPONSE_POSTPROCESSORS``,
an id a config fragment names exactly the way it names a policy or an evidence
source, so the rule that turns a response into a delivery is pinned by the
composed config hash instead of living in a launcher.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Mapping, Sequence

from .base import RepairAlignmentError

#: The one tokenizer this module aligns on: maximal runs of non-whitespace.
#: The same rule ``str.split()`` applies, but with offsets, so a delivered
#: token that was not substituted is the original bytes rather than a copy.
_TOKEN_PATTERN = re.compile(r"\S+")

#: Registered id of the rule below. A literal, so
#: ``scripts/checks/engineering_base_check.py`` can read the registered name
#: set out of ``core/policies.py`` without importing the package.
E21_ENTITY_REPAIR_SUBSTITUTIONS_V1 = "e21-entity-repair-substitutions-v1"

#: Registered id of :func:`accept_free_refresh` -- the SAME seam with the span
#: bound removed, so DR-1's two refresh cells differ in exactly one registered
#: name (owner Decision 13-J, 2026-09-09). A literal for the same reason.
E21_FREE_REFRESH_DELIVERY_V1 = "e21-free-refresh-delivery-v1"

#: Defaults of :func:`accept_entity_repair`, named here so a preregistration
#: can quote them and a config fragment can pin them into its own hash.
DEFAULT_MAX_SPAN_TOKENS = 4
DEFAULT_MIN_ANCHOR_RATIO = 0.60
DEFAULT_MAX_SUBSTITUTED_FRACTION = 0.10

#: Every refusal reason this module can produce, in the order it checks them.
REFUSAL_REASONS = (
    "empty_predecessor",
    "empty_response",
    "anchor_ratio_below_floor",
    "substituted_fraction_above_ceiling",
)

#: Every rejected-opcode class, so a receipt can report a complete table
#: instead of whatever happened to be non-zero.
REJECTION_CLASSES = (
    "insertion",
    "deletion",
    "unbalanced_replace",
    "oversized_replace",
)


@dataclass(frozen=True)
class RepairSubstitution:
    """One accepted substitution, in pass-1 coordinates.

    ``start_token``/``end_token`` are a half-open token range of the pass-1
    hypothesis; ``before`` and ``after`` are the whitespace-joined surface
    forms. Equal token counts on both sides is an accepted substitution's
    defining property, so ``len(before.split()) == len(after.split())``.
    """

    start_token: int
    end_token: int
    before: str
    after: str

    def as_dict(self) -> dict[str, object]:
        return {
            "start_token": self.start_token,
            "end_token": self.end_token,
            "before": self.before,
            "after": self.after,
        }


@dataclass(frozen=True)
class RepairOutcome:
    """What the harness will actually deliver for one window, and why.

    ``text`` is the delivered hypothesis. ``refused`` says the whole response
    was thrown away and ``text`` is the pass-1 hypothesis byte for byte;
    ``refusal_reason`` names which rule did it. ``substitutions`` is empty
    whenever ``refused`` is true.
    """

    text: str
    refused: bool
    refusal_reason: str | None
    substitutions: tuple[RepairSubstitution, ...]
    rejected: Mapping[str, int]
    predecessor_tokens: int
    response_tokens: int
    anchor_tokens: int
    substituted_tokens: int
    #: WHICH rule produced ``text``. ``substitution-splice`` is
    #: :func:`accept_entity_repair`'s bounded splice and stays the default, so
    #: every outcome built before DR-1 existed reads exactly as it did.
    #: ``verbatim-response`` is :func:`accept_free_refresh`'s free delivery.
    delivery: str = "substitution-splice"
    #: Whether ``text`` differs from the predecessor. A splice knows this from
    #: its own substitutions; a verbatim delivery has to be told, because a
    #: response that happens to equal the draft changed nothing. ``None`` means
    #: "derive it from the substitutions", which is the splice's own answer.
    text_changed: bool | None = None

    @property
    def anchor_ratio(self) -> float:
        if not self.predecessor_tokens:
            return 0.0
        return self.anchor_tokens / self.predecessor_tokens

    @property
    def substituted_fraction(self) -> float:
        if not self.predecessor_tokens:
            return 0.0
        return self.substituted_tokens / self.predecessor_tokens

    @property
    def changed(self) -> bool:
        if self.text_changed is not None:
            return bool(self.text_changed)
        return bool(self.substitutions)

    def trace_view(self) -> dict[str, object]:
        """The audit block a policy puts in its per-window OBS record.

        Every key carries the ``obs_`` prefix because
        ``contracts.boundary.TraceRecord`` refuses an OBS payload key without
        it -- the OBS / ORG / SUPPLY / USE namespaces are disjoint by contract,
        and a delivery decision made about an observation belongs to OBS.

        Deliberately carries no surface forms: the delivered TEXT is already
        traced once by the policy, and a second copy of every repaired name in
        a different record would make two authorities for one byte.
        """

        return {
            "obs_repair_delivery": self.delivery,
            "obs_repair_changed": self.changed,
            "obs_repair_refused": self.refused,
            "obs_repair_refusal_reason": self.refusal_reason,
            "obs_repair_substitutions": len(self.substitutions),
            "obs_repair_substituted_tokens": self.substituted_tokens,
            "obs_repair_predecessor_tokens": self.predecessor_tokens,
            "obs_repair_response_tokens": self.response_tokens,
            "obs_repair_anchor_tokens": self.anchor_tokens,
            "obs_repair_rejected": {
                name: int(self.rejected.get(name, 0)) for name in REJECTION_CLASSES
            },
        }


def _tokens_with_offsets(text: str) -> tuple[tuple[str, int, int], ...]:
    return tuple(
        (match.group(0), match.start(), match.end())
        for match in _TOKEN_PATTERN.finditer(text)
    )


def _refuse(
    predecessor_text: str,
    reason: str,
    *,
    predecessor_tokens: int,
    response_tokens: int,
    anchor_tokens: int = 0,
    substituted_tokens: int = 0,
    rejected: Mapping[str, int] | None = None,
    delivery: str = "substitution-splice",
) -> RepairOutcome:
    return RepairOutcome(
        text=predecessor_text,
        refused=True,
        refusal_reason=reason,
        substitutions=(),
        rejected={name: int((rejected or {}).get(name, 0)) for name in REJECTION_CLASSES},
        predecessor_tokens=predecessor_tokens,
        response_tokens=response_tokens,
        anchor_tokens=anchor_tokens,
        substituted_tokens=substituted_tokens,
        delivery=delivery,
        text_changed=False,
    )


def accept_entity_repair(
    predecessor_text: str,
    response_text: str,
    *,
    max_span_tokens: int = DEFAULT_MAX_SPAN_TOKENS,
    min_anchor_ratio: float = DEFAULT_MIN_ANCHOR_RATIO,
    max_substituted_fraction: float = DEFAULT_MAX_SUBSTITUTED_FRACTION,
) -> RepairOutcome:
    """The pass-2 post-processor: module docstring for the exact rules.

    Never raises on model output -- every malformed, truncated, translated or
    hallucinated response is a REFUSAL that delivers ``predecessor_text``.
    :class:`RepairAlignmentError` is reserved for a caller's bad parameters and
    for the token-count invariant, which is a harness defect rather than a
    model behaviour.
    """

    if not isinstance(predecessor_text, str) or not isinstance(response_text, str):
        raise RepairAlignmentError("predecessor_text and response_text must be strings")
    if isinstance(max_span_tokens, bool) or not isinstance(max_span_tokens, int) or max_span_tokens < 1:
        raise RepairAlignmentError(f"max_span_tokens must be an integer >= 1, got {max_span_tokens!r}")
    for name, value in (
        ("min_anchor_ratio", min_anchor_ratio),
        ("max_substituted_fraction", max_substituted_fraction),
    ):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.0 <= float(value) <= 1.0:
            raise RepairAlignmentError(f"{name} must be a number in [0, 1], got {value!r}")

    predecessor = _tokens_with_offsets(predecessor_text)
    response = _tokens_with_offsets(response_text)

    if not predecessor:
        # A saturated or skipped pass-1 window contributed the empty string to
        # the comparator's own stitch (reproduction.obs_loop's quarantine).
        # There is nothing to repair and nothing a pass-2 answer may add: the
        # delivery stays empty, exactly as the comparator's did, and says so.
        return _refuse(
            predecessor_text,
            "empty_predecessor",
            predecessor_tokens=0,
            response_tokens=len(response),
        )
    if not response:
        return _refuse(
            predecessor_text,
            "empty_response",
            predecessor_tokens=len(predecessor),
            response_tokens=0,
        )

    matcher = SequenceMatcher(
        a=[token for token, _start, _end in predecessor],
        b=[token for token, _start, _end in response],
        autojunk=False,
    )
    anchor_tokens = 0
    accepted: list[RepairSubstitution] = []
    rejected = {name: 0 for name in REJECTION_CLASSES}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            anchor_tokens += i2 - i1
        elif tag == "insert":
            rejected["insertion"] += 1
        elif tag == "delete":
            rejected["deletion"] += 1
        elif tag == "replace":
            if (i2 - i1) != (j2 - j1):
                rejected["unbalanced_replace"] += 1
            elif (i2 - i1) > max_span_tokens:
                rejected["oversized_replace"] += 1
            else:
                accepted.append(
                    RepairSubstitution(
                        start_token=i1,
                        end_token=i2,
                        before=" ".join(token for token, _s, _e in predecessor[i1:i2]),
                        after=" ".join(token for token, _s, _e in response[j1:j2]),
                    )
                )
        else:  # pragma: no cover -- difflib emits no other tag
            raise RepairAlignmentError(f"unknown difflib opcode {tag!r}")

    substituted_tokens = sum(item.end_token - item.start_token for item in accepted)
    if anchor_tokens < min_anchor_ratio * len(predecessor):
        return _refuse(
            predecessor_text,
            "anchor_ratio_below_floor",
            predecessor_tokens=len(predecessor),
            response_tokens=len(response),
            anchor_tokens=anchor_tokens,
            rejected=rejected,
        )
    if substituted_tokens > max_substituted_fraction * len(predecessor):
        return _refuse(
            predecessor_text,
            "substituted_fraction_above_ceiling",
            predecessor_tokens=len(predecessor),
            response_tokens=len(response),
            anchor_tokens=anchor_tokens,
            substituted_tokens=substituted_tokens,
            rejected=rejected,
        )

    delivered = predecessor_text
    for item in reversed(accepted):
        start = predecessor[item.start_token][1]
        end = predecessor[item.end_token - 1][2]
        delivered = delivered[:start] + item.after + delivered[end:]

    if len(delivered.split()) != len(predecessor_text.split()):
        raise RepairAlignmentError(
            "the delivered hypothesis moved the token count "
            f"({len(predecessor_text.split())} -> {len(delivered.split())}); "
            "substitution-only delivery is broken and nothing may be scored"
        )
    return RepairOutcome(
        text=delivered,
        refused=False,
        refusal_reason=None,
        substitutions=tuple(accepted),
        rejected=rejected,
        predecessor_tokens=len(predecessor),
        response_tokens=len(response),
        anchor_tokens=anchor_tokens,
        substituted_tokens=substituted_tokens,
    )


def entity_repair_substitutions_v1(**params: object):
    """``core.base.RESPONSE_POSTPROCESSORS`` entry for
    :data:`E21_ENTITY_REPAIR_SUBSTITUTIONS_V1`.

    A registry ENTRY is a factory taking the config's own ``params`` and
    returning the bound ``(predecessor_text, response_text) -> RepairOutcome``
    rule -- the same shape ``rails.phase_material.PHASE_STATE_FILLS`` uses, and
    for the same reason: the parameters ride in the composed config hash, and
    the bound rule is a plain callable a policy can hold per sample.
    """

    unknown = sorted(
        set(params)
        - {"max_span_tokens", "min_anchor_ratio", "max_substituted_fraction"}
    )
    if unknown:
        raise RepairAlignmentError(
            f"unknown response_postprocessor_params {unknown}; the rule takes "
            "max_span_tokens, min_anchor_ratio and max_substituted_fraction"
        )
    max_span_tokens = int(params.get("max_span_tokens", DEFAULT_MAX_SPAN_TOKENS))
    min_anchor_ratio = float(params.get("min_anchor_ratio", DEFAULT_MIN_ANCHOR_RATIO))
    max_substituted_fraction = float(
        params.get("max_substituted_fraction", DEFAULT_MAX_SUBSTITUTED_FRACTION)
    )

    def rule(predecessor_text: str, response_text: str) -> RepairOutcome:
        return accept_entity_repair(
            predecessor_text,
            response_text,
            max_span_tokens=max_span_tokens,
            min_anchor_ratio=min_anchor_ratio,
            max_substituted_fraction=max_substituted_fraction,
        )

    return rule


#: The two whole-response refusals :func:`accept_free_refresh` keeps. They are
#: a STRICT SUBSET of :func:`accept_entity_repair`'s four, and the two missing
#: ones are exactly the factor DR-1 measures: a free refresh may rewrite as
#: much of the draft as it likes, including all of it.
FREE_REFRESH_REFUSAL_REASONS = ("empty_predecessor", "empty_response")


def accept_free_refresh(predecessor_text: str, response_text: str) -> RepairOutcome:
    """The UNCONSTRAINED sibling of :func:`accept_entity_repair`.

    DR-1f (owner Decision 13-J, 2026-09-09) asks what a refresh of a draft is
    worth when the harness does not bound the edit -- the KC-E1 risk, which
    cost 2,242 non-entity deletions, measured on this seam instead of feared.
    So this rule DELIVERS THE RESPONSE VERBATIM. It counts the opcodes it would
    have rejected, so a verdict can put the two arms' edit profiles in one
    table, but it rejects nothing and splices nothing.

    It keeps exactly two of the constrained rule's four refusals
    (:data:`FREE_REFRESH_REFUSAL_REASONS`), and it keeps them so that the two
    cells differ in ONE thing:

    * ``empty_predecessor`` -- a window whose stitched unit-draft is empty.
      The constrained rule delivers the empty draft there; so does this one, so
      the two arms treat those windows identically and the contrast stays a
      contrast about EDITS.
    * ``empty_response`` -- the base policy's saturation/skip quarantine
      arrives as the empty string, and an empty delivery would throw a window
      away. Both rules deliver the draft.

    What it deliberately does NOT keep is ``anchor_ratio_below_floor`` and
    ``substituted_fraction_above_ceiling``. A summary, a translation or a
    runaway is DELIVERED here, and the corpus-WER and over-generation guards
    are what catch it. That is the whole point of the arm.
    """

    if not isinstance(predecessor_text, str) or not isinstance(response_text, str):
        raise RepairAlignmentError("predecessor_text and response_text must be strings")

    predecessor = _tokens_with_offsets(predecessor_text)
    response = _tokens_with_offsets(response_text)
    if not predecessor:
        return _refuse(
            predecessor_text,
            "empty_predecessor",
            predecessor_tokens=0,
            response_tokens=len(response),
            delivery="verbatim-response",
        )
    if not response:
        return _refuse(
            predecessor_text,
            "empty_response",
            predecessor_tokens=len(predecessor),
            response_tokens=0,
            delivery="verbatim-response",
        )

    matcher = SequenceMatcher(
        a=[token for token, _start, _end in predecessor],
        b=[token for token, _start, _end in response],
        autojunk=False,
    )
    anchor_tokens = 0
    rewritten_tokens = 0
    # Counted, never acted on: the same four classes the constrained rule
    # rejects, so a verdict can say how much of this arm's delivery the
    # constrained arm would have refused.
    would_reject = {name: 0 for name in REJECTION_CLASSES}
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            anchor_tokens += i2 - i1
        elif tag == "insert":
            would_reject["insertion"] += 1
        elif tag == "delete":
            would_reject["deletion"] += 1
        elif tag == "replace":
            rewritten_tokens += i2 - i1
            if (i2 - i1) != (j2 - j1):
                would_reject["unbalanced_replace"] += 1
            elif (i2 - i1) > DEFAULT_MAX_SPAN_TOKENS:
                would_reject["oversized_replace"] += 1
        else:  # pragma: no cover -- difflib emits no other tag
            raise RepairAlignmentError(f"unknown difflib opcode {tag!r}")

    return RepairOutcome(
        text=response_text,
        refused=False,
        refusal_reason=None,
        substitutions=(),
        rejected=would_reject,
        predecessor_tokens=len(predecessor),
        response_tokens=len(response),
        anchor_tokens=anchor_tokens,
        substituted_tokens=rewritten_tokens,
        delivery="verbatim-response",
        text_changed=response_text != predecessor_text,
    )


def free_refresh_delivery_v1(**params: object):
    """``core.base.RESPONSE_POSTPROCESSORS`` entry for
    :data:`E21_FREE_REFRESH_DELIVERY_V1`.

    It takes NO parameters, and says so rather than silently ignoring them: a
    fragment that pinned ``max_span_tokens`` here would be declaring a bound
    this rule does not apply, and the cell's one factor would be a lie in its
    own composed config hash.
    """

    if params:
        raise RepairAlignmentError(
            f"{E21_FREE_REFRESH_DELIVERY_V1} takes no response_postprocessor_params; "
            f"got {sorted(params)}. A free refresh has no span bound, no anchor floor "
            "and no substitution ceiling -- that is what makes it the free arm"
        )

    def rule(predecessor_text: str, response_text: str) -> RepairOutcome:
        return accept_free_refresh(predecessor_text, response_text)

    return rule


def summarize_outcomes(outcomes: Sequence[RepairOutcome]) -> dict[str, object]:
    """Roll a run's per-window outcomes into the block a receipt reports.

    Every refusal reason and every rejection class appears with its count even
    at zero, so a reader sees the complete table rather than the subset that
    happened to fire.
    """

    reasons = {name: 0 for name in REFUSAL_REASONS}
    rejected = {name: 0 for name in REJECTION_CLASSES}
    deliveries: dict[str, int] = {}
    substitutions = 0
    substituted_tokens = 0
    changed = 0
    refused = 0
    for outcome in outcomes:
        deliveries[outcome.delivery] = deliveries.get(outcome.delivery, 0) + 1
        if outcome.refused:
            refused += 1
            if outcome.refusal_reason is not None:
                reasons[outcome.refusal_reason] = reasons.get(outcome.refusal_reason, 0) + 1
        if outcome.changed:
            changed += 1
        substitutions += len(outcome.substitutions)
        substituted_tokens += outcome.substituted_tokens
        for name, count in outcome.rejected.items():
            rejected[name] = rejected.get(name, 0) + int(count)
    return {
        "windows": len(outcomes),
        "windows_refused": refused,
        "windows_changed": changed,
        "windows_unchanged_and_accepted": len(outcomes) - refused - changed,
        "substitutions": substitutions,
        "substituted_tokens": substituted_tokens,
        "refusal_reasons": reasons,
        "rejected_opcodes": rejected,
        # WHICH rule delivered each window. One key on a KC-E1f-shaped run and
        # one on a DR-1f-shaped one; a run carrying both would be a defect and
        # would show as two.
        "deliveries": dict(sorted(deliveries.items())),
    }


__all__ = [
    "DEFAULT_MAX_SPAN_TOKENS",
    "DEFAULT_MAX_SUBSTITUTED_FRACTION",
    "DEFAULT_MIN_ANCHOR_RATIO",
    "E21_ENTITY_REPAIR_SUBSTITUTIONS_V1",
    "E21_FREE_REFRESH_DELIVERY_V1",
    "FREE_REFRESH_REFUSAL_REASONS",
    "REFUSAL_REASONS",
    "REJECTION_CLASSES",
    "RepairAlignmentError",
    "RepairOutcome",
    "RepairSubstitution",
    "accept_entity_repair",
    "accept_free_refresh",
    "entity_repair_substitutions_v1",
    "free_refresh_delivery_v1",
    "summarize_outcomes",
]
