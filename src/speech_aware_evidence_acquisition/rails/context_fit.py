"""E20 (2026-09-19): degrade an over-long request into a retained row.

``native_episode.context_fit_policy`` is the tenth episode-level switch and,
like ``native_episode.finite_completion_policy`` (E13), it is a FAILURE MODE
rather than a factor. ``"raise"`` -- the key absent, or written out loud --
is the pre-E20 behaviour: a request wider than the live slot kills the
flight. ``"compact-or-abstain"`` makes it a row-level disposition instead.

The mechanism has three seams, all of them model-free:

* **Preflight.** ``core.flight.runtime.FlightRuntime._assess_prompt_budget``
  renders the widest request the roster produces per phase and asks
  ``rails.context_budget``. Under ``"raise"`` anything but ``ALLOW`` aborts.
  Under ``"compact-or-abstain"`` a ``COMPACT_REQUIRED`` representative
  sample no longer aborts -- the rail's own verdict is "this is fixable by
  dropping context", and from E20 there IS a live mechanism to fix it with.
  ``REFUSE`` (the required window exceeds the physical slot even with every
  droppable block gone) still aborts: no compaction can repair it.

* **Dispatch.** Every REALISED request is budgeted against the LIVE slot
  immediately before it is sent -- the seam ``rails.context_budget``'s own
  module docstring reserved and nothing ever wired. A request that does not
  fit has droppable blocks removed in the declared order below, at most
  :data:`MAX_COMPACTION_PASSES` passes, and is sent with a
  ``context_compaction`` record. One that still does not fit takes the
  terminal disposition instead of being silently truncated.

* **The wire.** The built fork answers a prompt at or above the slot width
  with HTTP 400 ``exceed_context_size_error``
  (``tools/server/server-common.cpp:59-62``). That ONE error class becomes
  the same terminal disposition, with the server's own message recorded.
  Every other HTTP status keeps the pre-E20 behaviour.

**The declared drop order.** Deterministic, declared, never a heuristic;
lowest authority first:

1. ``exemplar-supply`` -- the ``value:`` knowledge items, from the TAIL.
2. ``candidate-cards`` -- the ``key:``/facet cards, from the TAIL.
3. ``scenario-hints`` -- the whole ``native_episode.solver_hints`` block.
4. ``reviewer-audit`` -- the whole ``native_episode.reviewer_audit`` block.
5. ``agent-states`` -- history entries, OLDEST first.

**Never droppable, byte for byte:** the instruction text and task contract
(the system message), the speech packet reference, the current draft (the
newest Solver state, and the role query the request carries), and the tools
array. They are the request's identity; a request without them is not a
narrower request, it is a different one.

Two passes, and each has its own allowance. Pass 1 spends each block's
SURPLUS tranche -- the exemplar and candidate tails beyond
:data:`RETAINED_FRACTION_DENOMINATOR`-th of the block, the two whole
attachment blocks, and every agent state but the newest. Pass 2 spends what
is left, down to each block's hard floor (nothing for the two evidence
blocks; the newest state for the history). After pass 2 the request either
fits or the row takes the terminal disposition.

This module is pure: no transport, no tokenizer, no framework import. The
caller supplies the token measurement and the limit; this module decides
what to drop and records what it dropped.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace

from .context_budget import MAX_COMPACTION_PASSES

#: The two values ``native_episode.context_fit_policy`` admits. ``"raise"``
#: is the pre-E20 behaviour and the default; the key's null arm is its
#: ABSENCE or this literal, exactly as E13's and E17's are.
CONTEXT_FIT_POLICIES: tuple[str, ...] = ("raise", "compact-or-abstain")

#: The armed value.
COMPACT_OR_ABSTAIN = "compact-or-abstain"

#: The schema of one contact's compaction record.
CONTEXT_COMPACTION_SCHEMA = "saea-context-compaction-v1"

#: The ``terminal_disposition.reason`` a context-fit row carries. Modelled
#: on E13's ``finite_completion``: the row is retained and scored, the
#: latest delivery-eligible Solver draft is delivered, and when there is
#: none the row abstains.
CONTEXT_COMPACTION_DISPOSITION = "context_compaction"

#: The ordered droppable block classes. This tuple IS the drop order.
EXEMPLAR_SUPPLY_BLOCK = "exemplar-supply"
CANDIDATE_CARDS_BLOCK = "candidate-cards"
SCENARIO_HINTS_BLOCK = "scenario-hints"
REVIEWER_AUDIT_BLOCK = "reviewer-audit"
AGENT_STATES_BLOCK = "agent-states"
DROP_ORDER: tuple[str, ...] = (
    EXEMPLAR_SUPPLY_BLOCK,
    CANDIDATE_CARDS_BLOCK,
    SCENARIO_HINTS_BLOCK,
    REVIEWER_AUDIT_BLOCK,
    AGENT_STATES_BLOCK,
)

#: What a compaction never touches, named so a receipt reader does not have
#: to infer it from the absence of an entry.
NEVER_DROPPABLE: tuple[str, ...] = (
    "instruction-text",
    "task-contract",
    "speech-packet-reference",
    "current-draft",
    "tools-array",
)

#: E20: ``rails.context_budget._DROPPABLE_IDENTIFIER_PREFIXES`` admits only
#: ``agent-state:``, ``facet:`` and ``value:`` identifiers, so the two whole
#: attachment blocks (items 3 and 4) become addressable under ``facet:``.
#: That is the one piece of new plumbing the design called for; the
#: identifiers are reserved names, never a facet of any snapshot.
SCENARIO_HINTS_IDENTIFIER = "facet:native-episode-scenario-hints"
REVIEWER_AUDIT_IDENTIFIER = "facet:native-episode-reviewer-audit"

#: Pass 1 keeps ``count // RETAINED_FRACTION_DENOMINATOR`` items of each
#: ordered evidence block and surrenders the tail beyond it -- the analysis'
#: "``value:`` exemplars beyond the first k/2" and "trailing candidates
#: below the retained top-n".
RETAINED_FRACTION_DENOMINATOR = 2


class ContextFitError(ValueError):
    """The rail refused a malformed context-fit declaration or view."""


def parse_context_fit_policy(value: object) -> str:
    """Validate ``native_episode.context_fit_policy``; absent means ``raise``."""

    if value is None:
        return "raise"
    if not isinstance(value, str) or value not in CONTEXT_FIT_POLICIES:
        raise ContextFitError(
            "native episode context_fit_policy must be 'raise' or "
            "'compact-or-abstain'"
        )
    return value


def is_context_fit_null_arm(value: object) -> bool:
    """The key's OFF arm: absent, or the explicit default ``"raise"``."""

    return value is None or value == "raise"


def _text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContextFitError(f"{field} must be non-empty text")
    return value


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BlockAttachment:
    """One appended context block, addressable by exact trailing bytes.

    ``rails.node_context_policy`` appends the scenario-hints and slot-audit
    blocks to a rendered state as ``f"{rendered}\\n{block}"`` and records the
    block's ``sha256`` and character count in the contact's compilation
    receipt -- never its text. That is enough to remove it EXACTLY: the
    suffix is the last ``chars`` characters, the character before it is the
    joining newline, and the removal is refused unless the digest matches.
    """

    state_id: str
    block: str
    chars: int
    sha256: str

    def __post_init__(self) -> None:
        _text(self.state_id, field="attachment state_id")
        if self.block not in (SCENARIO_HINTS_BLOCK, REVIEWER_AUDIT_BLOCK):
            raise ContextFitError("attachment block is not an addressable class")
        if isinstance(self.chars, bool) or not isinstance(self.chars, int) or self.chars <= 0:
            raise ContextFitError("attachment chars must be a positive integer")
        if (
            not isinstance(self.sha256, str)
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ContextFitError("attachment sha256 must be a lowercase digest")

    def strip_from(self, content: str) -> str | None:
        """The state content without this block, or ``None`` if it is absent.

        ``None`` is not an error: a contact whose receipt names an
        attachment the rendered state does not carry (a re-rendered state, a
        cleaned boundary) simply has no droppable item for that block, and
        compaction moves on down the declared order. Nothing is ever removed
        on a digest mismatch.
        """

        if len(content) <= self.chars + 1:
            return None
        if content[-(self.chars + 1)] != "\n":
            return None
        if _sha256_text(content[-self.chars:]) != self.sha256:
            return None
        return content[: -(self.chars + 1)]


@dataclass(frozen=True)
class DroppableItem:
    """One addressable unit a compaction pass may remove."""

    block: str
    identifier: str
    tranche: int
    #: ``"content"`` -- a user-message content part, by index.
    #: ``"agent-state"`` -- a whole agent-state entry, by index.
    #: ``"attachment"`` -- a trailing block of one agent-state entry.
    location: str
    index: int
    attachment: BlockAttachment | None = None


@dataclass(frozen=True)
class CompactableRequest:
    """The typed, addressable view of ONE realised request.

    ``content`` is the user message's content list exactly as the binding
    renders it (the speech packet part plus the ``key:``/``value:`` evidence
    parts); ``agent_states`` is the ordered ``agent_state`` array the request
    carries. Everything else about the request -- system message, role
    query, decoding, tool schemas -- is outside this view because nothing
    here may touch it.
    """

    content: tuple[Mapping[str, object], ...]
    agent_states: tuple[Mapping[str, object], ...]
    attachments: tuple[BlockAttachment, ...] = ()
    #: E21w (item E21, the knowledge index): the ``rails.knowledge_index.
    #: IndexAssembly`` this request's pointer/expansion parts were composed
    #: from, or ``None`` -- which is every request written before E21 and
    #: every episode that does not arm ``native_episode.knowledge_index``.
    #: Set, the index's OWN ladder replaces the ``exemplar-supply`` ladder
    #: for exactly the parts the index authored, so ONE caller drives both
    #: ladders through this module's own :func:`apply_drops`. Declared last,
    #: excluded from :meth:`document`: it names no byte of the request and
    #: the measurement basis must not move.
    index_assembly: object = None

    def __post_init__(self) -> None:
        if not isinstance(self.content, tuple) or not isinstance(
            self.agent_states, tuple
        ):
            raise ContextFitError("a compactable request holds immutable tuples")
        for part in self.content:
            if not isinstance(part, Mapping):
                raise ContextFitError("every content part must be a mapping")
        seen: set[str] = set()
        for state in self.agent_states:
            if not isinstance(state, Mapping):
                raise ContextFitError("every agent state must be a mapping")
            state_id = _text(state.get("state_id"), field="agent state state_id")
            if state_id in seen:
                raise ContextFitError("agent states must carry unique ids")
            seen.add(state_id)
        for attachment in self.attachments:
            if not isinstance(attachment, BlockAttachment):
                raise ContextFitError("attachments must be BlockAttachment")
        if self.index_assembly is not None and not hasattr(
            self.index_assembly, "expansions"
        ):
            # Duck-typed on purpose: ``rails.knowledge_index`` imports THIS
            # module for :class:`DroppableItem`, so naming its type here
            # would be a cycle. The one attribute the ladder needs is the
            # one checked.
            raise ContextFitError(
                "index_assembly must be a rails.knowledge_index.IndexAssembly"
            )

    def document(self) -> dict[str, object]:
        """A JSON-safe view, used only for measurement and for tests."""

        return {
            "content": [dict(part) for part in self.content],
            "agent_state": [dict(state) for state in self.agent_states],
        }


def _identifier(part: Mapping[str, object]) -> str | None:
    """The rail-prefixed identifier of one evidence content part.

    ``rails.runner._agent_messages`` writes a facet part's ``evidence_id`` as
    ``key:<facet_id>`` and a value part's as the bare ``value_id``; the rail
    addresses them as ``facet:`` and ``value:``. This is the one place that
    mapping lives.
    """

    evidence_id = part.get("evidence_id")
    if not isinstance(evidence_id, str) or not evidence_id.strip():
        return None
    role = part.get("knowledge_role")
    if role == "key":
        local = evidence_id[len("key:"):] if evidence_id.startswith("key:") else evidence_id
        return f"facet:{local}" if local else None
    if role == "value":
        if evidence_id.startswith("value:"):
            return evidence_id
        return f"value:{evidence_id}"
    return None


def droppable_items(request: CompactableRequest) -> tuple[DroppableItem, ...]:
    """Every droppable item of one request, in the DECLARED drop order.

    Tranche 1 comes first for every block, then tranche 2, so a pass spends
    each block's surplus before any block's floor. Within a block the order
    is tail-first for the two evidence blocks and oldest-first for the
    history.
    """

    if not isinstance(request, CompactableRequest):
        raise ContextFitError("droppable_items needs a CompactableRequest")
    values: list[tuple[int, str]] = []
    keys: list[tuple[int, str]] = []
    for index, part in enumerate(request.content):
        identifier = _identifier(part)
        if identifier is None:
            continue
        if identifier.startswith("value:"):
            values.append((index, identifier))
        elif identifier.startswith("facet:"):
            keys.append((index, identifier))
    # E21w: the index owns its own parts. Under an armed
    # ``native_episode.knowledge_index`` the pointer block and every
    # expansion are ``value:`` parts, so E20's own tail-first
    # ``exemplar-supply`` ladder would spend them in the wrong order -- it
    # keeps the first half of a block, and the index's rule is "the
    # expansion tail first, the pointer block only once every expansion is
    # gone". The parts the index authored are therefore REMOVED from the
    # exemplar ladder and re-added in the index's declared order.
    index_items = index_ladder(request, {identifier for _i, identifier in values})
    if index_items:
        owned = {item.identifier for item in index_items}
        values = [entry for entry in values if entry[1] not in owned]

    by_state = {
        str(state.get("state_id")): index
        for index, state in enumerate(request.agent_states)
    }
    attachments = {
        SCENARIO_HINTS_BLOCK: [], REVIEWER_AUDIT_BLOCK: [],
    }
    for attachment in request.attachments:
        index = by_state.get(attachment.state_id)
        if index is None:
            continue
        content = request.agent_states[index].get("content")
        if not isinstance(content, str) or attachment.strip_from(content) is None:
            continue
        attachments[attachment.block].append((index, attachment))

    def evidence(entries: Sequence[tuple[int, str]], block: str) -> list[DroppableItem]:
        retained = len(entries) // RETAINED_FRACTION_DENOMINATOR
        items: list[DroppableItem] = []
        for position in range(len(entries) - 1, -1, -1):
            index, identifier = entries[position]
            items.append(
                DroppableItem(
                    block=block,
                    identifier=identifier,
                    tranche=1 if position >= retained else 2,
                    location="content",
                    index=index,
                )
            )
        return items

    def attached(block: str, identifier: str) -> list[DroppableItem]:
        return [
            DroppableItem(
                block=block,
                identifier=identifier,
                tranche=1,
                location="attachment",
                index=index,
                attachment=attachment,
            )
            for index, attachment in attachments[block]
        ]

    # The newest state is the current draft as far as this rail is
    # concerned; it is never droppable, in either tranche.
    history: list[DroppableItem] = []
    for index in range(max(len(request.agent_states) - 1, 0)):
        state_id = str(request.agent_states[index].get("state_id"))
        history.append(
            DroppableItem(
                block=AGENT_STATES_BLOCK,
                identifier=f"agent-state:{state_id}",
                tranche=1,
                location="agent-state",
                index=index,
            )
        )

    per_block = {
        EXEMPLAR_SUPPLY_BLOCK: evidence(values, EXEMPLAR_SUPPLY_BLOCK),
        CANDIDATE_CARDS_BLOCK: evidence(keys, CANDIDATE_CARDS_BLOCK),
        SCENARIO_HINTS_BLOCK: attached(SCENARIO_HINTS_BLOCK, SCENARIO_HINTS_IDENTIFIER),
        REVIEWER_AUDIT_BLOCK: attached(REVIEWER_AUDIT_BLOCK, REVIEWER_AUDIT_IDENTIFIER),
        AGENT_STATES_BLOCK: history,
    }
    ordered: list[DroppableItem] = []
    for tranche in (1, 2):
        # E21w: the index's own tranche, ahead of every other block of the
        # same tranche -- the index is the cheapest context this request
        # carries and the one whose loss the design bounded. With no armed
        # index this list is empty and the loop is exactly its pre-E21 self.
        ordered.extend(item for item in index_items if item.tranche == tranche)
        for block in DROP_ORDER:
            ordered.extend(
                item for item in per_block[block] if item.tranche == tranche
            )
    return tuple(ordered)


def index_ladder(
    request: CompactableRequest, value_identifiers: set,
) -> tuple[DroppableItem, ...]:
    """E21w: the knowledge index's own ladder, bound to THIS request's parts.

    ``rails.knowledge_index.index_droppable_items`` produces the declared
    order -- expansions from the tail, then the pointer block, then the L1
    index falling back to L0 -- addressed by identifier, with the index
    positions of the assembly rather than of the rendered content list.
    This binds each item to the content index the part actually occupies,
    drops an item whose part is no longer in the request, and REFUSES the
    granularity step by name:

    the L1 -> L0 step re-renders the CONSTANT PREFIX, which lives in the
    system message. :class:`CompactableRequest` deliberately excludes the
    system message ("nothing here may touch it"), and re-rendering it on one
    contact would break the constant-prefix property the whole key exists
    for -- the per-slot KV prefix would stop being shared by the row. So the
    step is not executed here; an index-armed row that still does not fit
    after the two content tranches takes E20's terminal
    ``context_compaction`` disposition, exactly as an unarmed one does, and
    the refusal is recorded rather than silent
    (:data:`rails.knowledge_index.INDEX_GRANULARITY_BLOCK`).
    """

    assembly = request.index_assembly
    if assembly is None:
        return ()
    from .knowledge_index import (  # noqa: PLC0415 - cycle guard
        INDEX_GRANULARITY_BLOCK, index_droppable_items,
    )

    position_of = {
        identifier: index
        for index, part in enumerate(request.content)
        for identifier in (_identifier(part),)
        if identifier is not None
    }
    bound: list[DroppableItem] = []
    for item in index_droppable_items(assembly):
        if item.block == INDEX_GRANULARITY_BLOCK:
            continue
        index = position_of.get(item.identifier)
        if index is None or item.identifier not in value_identifiers:
            continue
        bound.append(replace(item, location="content", index=index))
    return tuple(bound)


def apply_drops(
    request: CompactableRequest, items: Sequence[DroppableItem]
) -> CompactableRequest:
    """Remove exactly ``items`` from ``request`` and return the narrowed view."""

    if not isinstance(request, CompactableRequest):
        raise ContextFitError("apply_drops needs a CompactableRequest")
    content_drops = {
        item.index for item in items if item.location == "content"
    }
    state_drops = {
        item.index for item in items if item.location == "agent-state"
    }
    states = [dict(state) for state in request.agent_states]
    for item in items:
        if item.location != "attachment":
            continue
        assert item.attachment is not None
        content = states[item.index].get("content")
        if not isinstance(content, str):
            raise ContextFitError("an attachment drop needs textual state content")
        stripped = item.attachment.strip_from(content)
        if stripped is None:
            raise ContextFitError("an attachment drop lost its exact trailing block")
        states[item.index]["content"] = stripped
    return replace(
        request,
        content=tuple(
            part for index, part in enumerate(request.content)
            if index not in content_drops
        ),
        agent_states=tuple(
            state for index, state in enumerate(states)
            if index not in state_drops
        ),
    )


@dataclass(frozen=True)
class CompactionOutcome:
    """What one dispatch-time compaction did, and whether it was enough."""

    request: CompactableRequest
    fitted: bool
    passes: int
    dropped: tuple[DroppableItem, ...]
    tokens_before: int
    tokens_after: int
    limit_tokens: int

    def dropped_identifiers(self) -> tuple[str, ...]:
        return tuple(item.identifier for item in self.dropped)

    def record(self, *, budget_receipt_sha256: str | None = None) -> dict[str, object]:
        """The per-contact ``context_compaction`` record for the receipt."""

        blocks: list[dict[str, object]] = []
        for block in DROP_ORDER:
            identifiers = [
                item.identifier for item in self.dropped if item.block == block
            ]
            if identifiers:
                blocks.append(
                    {
                        "block": block,
                        "identifiers": identifiers,
                        "items": len(identifiers),
                    }
                )
        return {
            "schema": CONTEXT_COMPACTION_SCHEMA,
            "passes": self.passes,
            "fitted": self.fitted,
            "blocks": blocks,
            "dropped_identifiers": list(self.dropped_identifiers()),
            "never_droppable": list(NEVER_DROPPABLE),
            "tokens_before": self.tokens_before,
            "tokens_after": self.tokens_after,
            "limit_tokens": self.limit_tokens,
            "budget_receipt_sha256": budget_receipt_sha256,
        }


def compact_to_fit(
    request: CompactableRequest,
    *,
    measure: Callable[[CompactableRequest], int],
    limit_tokens: int,
    max_passes: int = MAX_COMPACTION_PASSES,
) -> CompactionOutcome:
    """Drop blocks in the declared order until the request fits, or give up.

    ``measure`` returns the required window of a candidate view in tokens
    and ``limit_tokens`` is the live slot's usable budget. A request that
    already fits is returned untouched, with ``passes`` 0 and no dropped
    identifiers -- so on the happy path this costs one measurement and moves
    no byte.
    """

    if not isinstance(request, CompactableRequest):
        raise ContextFitError("compact_to_fit needs a CompactableRequest")
    if not callable(measure):
        raise ContextFitError("compact_to_fit needs a token measurement")
    if (
        isinstance(limit_tokens, bool)
        or not isinstance(limit_tokens, int)
        or limit_tokens <= 0
    ):
        raise ContextFitError("limit_tokens must be a positive integer")
    if (
        isinstance(max_passes, bool)
        or not isinstance(max_passes, int)
        or not 1 <= max_passes <= MAX_COMPACTION_PASSES
    ):
        raise ContextFitError(
            f"max_passes must be between 1 and {MAX_COMPACTION_PASSES}"
        )
    before = measure(request)
    if before <= limit_tokens:
        return CompactionOutcome(
            request=request, fitted=True, passes=0, dropped=(),
            tokens_before=before, tokens_after=before, limit_tokens=limit_tokens,
        )
    ordered = droppable_items(request)
    dropped: list[DroppableItem] = []
    current = request
    after = before
    passes = 0
    for tranche in range(1, max_passes + 1):
        tranche_items = [item for item in ordered if item.tranche == tranche]
        if not tranche_items:
            continue
        passes = tranche
        for item in tranche_items:
            dropped.append(item)
            current = apply_drops(request, dropped)
            after = measure(current)
            if after <= limit_tokens:
                return CompactionOutcome(
                    request=current, fitted=True, passes=passes,
                    dropped=tuple(dropped), tokens_before=before,
                    tokens_after=after, limit_tokens=limit_tokens,
                )
    return CompactionOutcome(
        request=current, fitted=False, passes=max(passes, 1),
        dropped=tuple(dropped), tokens_before=before, tokens_after=after,
        limit_tokens=limit_tokens,
    )


def terminal_context_disposition(
    *,
    role_id: str,
    stage: str,
    revision_count: int,
    compaction_pass: int,
    dropped_identifiers: Sequence[str],
    tokens_before: int,
    tokens_after: int,
    limit_tokens: int,
    source: str,
    server_message: str | None = None,
) -> dict[str, object]:
    """The E13-shaped ``terminal_disposition`` of a context-compaction row.

    ``source`` is ``"dispatch-budget"`` when the harness's own live-slot
    check refused the request before it was sent, and ``"server-refusal"``
    when the fork answered HTTP 400 ``exceed_context_size_error``; the two
    are the same disposition because they are the same fact, but a verdict
    should be able to tell a predicted overflow from a measured one.
    """

    _text(role_id, field="terminal role_id")
    if stage not in ("perception", "solver", "review", "planner", "acquisition"):
        raise ContextFitError("terminal stage is not a registered role stage")
    if (
        isinstance(revision_count, bool)
        or not isinstance(revision_count, int)
        or revision_count < 0
    ):
        raise ContextFitError("terminal revision_count must be a nonnegative integer")
    if (
        isinstance(compaction_pass, bool)
        or not isinstance(compaction_pass, int)
        or not 0 <= compaction_pass <= MAX_COMPACTION_PASSES
    ):
        raise ContextFitError(
            f"compaction_pass must be an integer from 0 to {MAX_COMPACTION_PASSES}"
        )
    if source not in ("dispatch-budget", "server-refusal"):
        raise ContextFitError("terminal source must name the refusing seam")
    identifiers = [str(identifier) for identifier in dropped_identifiers]
    if server_message is not None and not isinstance(server_message, str):
        raise ContextFitError("server_message must be text or None")
    return {
        "reason": CONTEXT_COMPACTION_DISPOSITION,
        "role_id": role_id,
        "stage": stage,
        "revision_count": revision_count,
        "planner_accepted": False,
        "compaction_pass": compaction_pass,
        "dropped_identifiers": identifiers,
        "tokens_before": int(tokens_before),
        "tokens_after": int(tokens_after),
        "limit_tokens": int(limit_tokens),
        "source": source,
        "server_message": server_message,
    }


def canonical_bytes(document: object) -> bytes:
    """Canonical JSON bytes, the measurement basis a caller tokenizes."""

    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


__all__ = [
    "AGENT_STATES_BLOCK",
    "BlockAttachment",
    "CANDIDATE_CARDS_BLOCK",
    "COMPACT_OR_ABSTAIN",
    "CONTEXT_COMPACTION_DISPOSITION",
    "CONTEXT_COMPACTION_SCHEMA",
    "CONTEXT_FIT_POLICIES",
    "CompactableRequest",
    "CompactionOutcome",
    "ContextFitError",
    "DROP_ORDER",
    "DroppableItem",
    "EXEMPLAR_SUPPLY_BLOCK",
    "NEVER_DROPPABLE",
    "REVIEWER_AUDIT_BLOCK",
    "REVIEWER_AUDIT_IDENTIFIER",
    "RETAINED_FRACTION_DENOMINATOR",
    "SCENARIO_HINTS_BLOCK",
    "SCENARIO_HINTS_IDENTIFIER",
    "apply_drops",
    "canonical_bytes",
    "compact_to_fit",
    "droppable_items",
    "index_ladder",
    "is_context_fit_null_arm",
    "parse_context_fit_policy",
    "terminal_context_disposition",
]
