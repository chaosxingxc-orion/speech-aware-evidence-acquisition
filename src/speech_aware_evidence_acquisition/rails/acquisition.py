"""E18: the Acquisition node -- the generic ``acquire`` primitive.

Owner decisions 43 and 44 of 2026-09-19
(``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``, section
"Owner decisions 42-44"): every carrier instantiates all SIX nodes of the
agent base, and Acquisition is a component of everyday inference rather than a
research extra -- SUPPLY governs the TIMING of evidence, and today the
Planner's ``ACQUIRE`` action reaches no node at all (E15 turns it into a
retained row). This module is the primitive half of the sixth node.

THE PRIMITIVE, stated once and carrier-neutrally (base-lock draft section 5.6,
``AC-1``)::

    acquire(acquire_action, trajectory state) -> typed evidence bound into
                                                 the successor state

One acquisition visit reads the episode's own state, executes exactly one
registered :class:`AcquisitionPolicy`, and returns exactly one
:class:`AcquiredEvidence` record. The record shape is the same for every kind,
so a consumer, a receipt and a later cell all read one object:

* ``kind`` and ``policy_id`` -- what was run;
* ``provenance_ids`` -- the ids of what was brought in (knowledge value ids, a
  re-observation contact id, a tool registry row id);
* ``content`` -- the ONE rendered typed block the next Solver revision reads,
  produced through the committed template
  ``configs/probes/ncp_acquired_evidence_solver_v1.txt`` at the NEW boundary
  ``acquisition -> solver`` (semantic class ``acquired-evidence``,
  ``rails.node_context_policy.ACQUIRED_EVIDENCE_BOUNDARY``);
* ``cost`` / ``cost_unit`` / ``contacts_used`` -- what the visit spent;
* ``inputs_sha256`` and ``evidence_sha256`` -- the two digests the episode
  receipt binds, so an auditor can re-derive what the node was asked and what
  it answered without the receipt carrying either text.

THE THREE KINDS, each a registered policy in ``core.base.ACQUISITION_POLICIES``
and each carrier-neutral by construction:

``knowledge-requery`` (:data:`KNOWLEDGE_REQUERY_POLICY_ID`) -- MODEL-FREE.
    Re-runs the phase supply for the Solver against the row's already sealed
    SPEECH key, restricted by STATE (the Reviewer finding's slot types and the
    Planner's brief fields, :func:`derive_state_filters`), and returns typed
    content the Solver has not yet been supplied (deduped against
    ``supplied_value_ids``). ZERO model contacts; the cost unit is supply
    calls. The state-derived tokens are a RESTRICTION on a speech-keyed
    ranking, never themselves a retrieval key: the owner ruling of 2026-09-06
    ("retrieval queries are speech or speech plus state, never text alone")
    is what forbids the second reading, and the callback this policy is handed
    is the one that owns the sealed speech vector.

``speech-reobserve`` (:data:`SPEECH_REOBSERVE_POLICY_ID`) -- ONE Perception
    contact. Re-runs Perception on a RE-SCOPED observation unit and returns
    the new candidate hypotheses as typed content. The scope is declared by
    configuration, never invented here: for SLURP the same recording with a
    different candidate cap (``fill_params.max_candidates``) or a declared
    re-listen prompt variant; for contextual ASR the neighbouring window; for
    Audio2Tool the same request with the domain-grouped registry. It spends
    exactly one contact against the row ceiling.

``tool-acquire`` (:data:`TOOL_ACQUIRE_POLICY_ID`) -- the Audio2Tool first
    instance: a registry lookup by domain group. It is REGISTERED on every
    carrier and ARMED on none: with no carrier registry bound it fails closed
    with a named refusal rather than returning an empty acquisition, because
    an acquisition that silently returns nothing is indistinguishable from one
    that found nothing.

WHAT THIS MODULE MAY NOT DO, on any carrier (study ``CLAUDE.md``, research
boundary; base-lock draft section 3.9):

* no gold, no reference transcript, no test annotation and no future turn ever
  reaches an acquisition -- the callbacks it is handed are the same frozen,
  TRAIN-only supply and the same frozen core every other node uses;
* no construction-pool row of an evaluated roster (the 2026-09-13 exclusion)
  may be acquired: the exclusion is enforced where the store is BUILT, and an
  acquisition may only return material a bound callback handed it;
* no transcript or ASR state may be used as a retrieval key;
* the Acquisition node never answers, never routes and never delivers -- only
  a Solver completion can become delivered text.

This module registers policies and computes records. It owns no contact
allocation, no request history, no routing and no scoring; the episode graph
(``reproduction.ojw.native_episode``) owns the node position and
``rails.runner`` owns the custody the record is sealed into.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from ..core.base import ACQUISITION_POLICIES, CoreError
from .node_context_policy import (
    ACQUIRED_EVIDENCE_RENDERER,
    ACQUIRED_EVIDENCE_TEMPLATE,
    NO_ACQUIRED_EVIDENCE,
    NodeContextTemplate,
    load_node_context_template,
    render_acquired_evidence,
)


class AcquisitionError(ValueError):
    """An acquisition refuses: the base fails closed rather than acquiring."""


#: The record schema one acquisition visit seals.
ACQUISITION_EVIDENCE_SCHEMA = "saea-acquired-evidence-v1"

#: The per-row receipt block schema ``rails.runner`` writes into the episode
#: receipt, one entry per acquisition visit.
ACQUISITION_RECEIPT_SCHEMA = "saea-native-acquisition-v1"

KIND_KNOWLEDGE_REQUERY = "knowledge-requery"
KIND_SPEECH_REOBSERVE = "speech-reobserve"
KIND_TOOL_ACQUIRE = "tool-acquire"

#: Every acquisition kind the base admits, in a fixed order.
ACQUISITION_KINDS: tuple[str, ...] = (
    KIND_KNOWLEDGE_REQUERY,
    KIND_SPEECH_REOBSERVE,
    KIND_TOOL_ACQUIRE,
)

KNOWLEDGE_REQUERY_POLICY_ID = "saea-acquire-knowledge-requery-v1"
SPEECH_REOBSERVE_POLICY_ID = "saea-acquire-speech-reobserve-v1"
TOOL_ACQUIRE_POLICY_ID = "saea-acquire-tool-registry-v1"

#: The most state-derived restriction tokens one acquisition may carry. The
#: bound exists so a long Reviewer finding cannot turn into an unbounded
#: filter list, and so the acquisition's ``inputs_sha256`` stays a digest over
#: a bounded object.
MAX_STATE_FILTERS = 8

#: The most items one acquisition may render. Beyond this the block would
#: dominate the Solver's context, which is a supply-volume change wearing an
#: acquisition's clothes.
MAX_ACQUIRED_ITEMS = 16

#: The shape a state-derived restriction token must have. Lowercase words and
#: underscores only: slot types (``time``, ``place_name``), scenario and
#: action names, and the Planner's own brief fields all have it, and free
#: prose punctuation, digits and casing do not survive it.
_FILTER_TOKEN = re.compile(r"[a-z][a-z_]{2,31}")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class AcquisitionBudget:
    """What one ROW may spend on acquisition, declared by configuration.

    ``max_acquisitions_per_row`` bounds the number of acquisition VISITS (each
    one costs a revision, because the ``ACQUIRE`` route advances the revision
    counter exactly as ``REVISE`` does). ``contact_budget`` bounds the model
    CONTACTS those visits may spend in total; it is 0 for a model-free kind,
    and ``rails.native_episode_config`` refuses a declaration whose
    ``contact_budget`` is not exactly the arithmetic of its own policy, role
    and revision allowance.

    ``max_items_per_acquisition`` (item E36b, 2026-09-22) is the OPTIONAL
    third knob: the most items one ``knowledge-requery`` visit may return
    when it searches the WHOLE released composite snapshot instead of
    filtering the Solver's own already-supplied selection (the E36 root
    cause: filtering a phase's own supply against its own exclusion set is
    empty by construction). ``None`` -- every budget declared before E36b and
    every OFF arm -- means the key is ABSENT and ``as_json`` renders exactly
    the two legacy keys, so a config that never mentions it composes and
    hashes byte-identically to the pre-E36b tree. Present, it must be a
    positive integer; ``core.flight.runtime.FlightRuntime.
    _acquisition_requery_binding`` reads it (through
    ``NativeEpisodeConfig.max_items_per_acquisition``) to decide which of the
    two re-query implementations to build.
    """

    max_acquisitions_per_row: int
    contact_budget: int
    max_items_per_acquisition: int | None = None

    def validate(self) -> "AcquisitionBudget":
        for name in ("max_acquisitions_per_row", "contact_budget"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AcquisitionError(
                    f"acquisition budget {name} must be a nonnegative integer"
                )
        if self.max_acquisitions_per_row < 1:
            raise AcquisitionError(
                "acquisition budget max_acquisitions_per_row must be at least 1; "
                "an armed acquisition node that may never acquire is the absent key"
            )
        if self.max_items_per_acquisition is not None:
            value = self.max_items_per_acquisition
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
                or value > MAX_ACQUIRED_ITEMS
            ):
                raise AcquisitionError(
                    "acquisition budget max_items_per_acquisition must be an "
                    f"integer between 1 and {MAX_ACQUIRED_ITEMS}"
                )
        return self

    def as_json(self) -> dict[str, int]:
        self.validate()
        document: dict[str, int] = {
            "max_acquisitions_per_row": self.max_acquisitions_per_row,
            "contact_budget": self.contact_budget,
        }
        if self.max_items_per_acquisition is not None:
            document["max_items_per_acquisition"] = self.max_items_per_acquisition
        return document


#: The one registered E36b retrieval policy id. A retrieval block names it
#: explicitly (rather than leaving it implicit) for the same reason every
#: other policy id in this module is spelled out: a future second retrieval
#: rule must not silently change what an existing config runs.
KNOWLEDGE_REQUERY_RETRIEVAL_POLICY_ID = "saea-requery-idf-v1"

#: Every retrieval policy id ``native_episode.acquisition.retrieval.policy``
#: may name.
RETRIEVAL_POLICY_IDS: tuple[str, ...] = (KNOWLEDGE_REQUERY_RETRIEVAL_POLICY_ID,)


@dataclass(frozen=True)
class RetrievalPolicy:
    """The E36b findings-keyed search rule, and its own tunable parameters.

    Read directly off ``native_episode.acquisition.retrieval`` by
    ``rails.native_episode_config``; ``core.flight.runtime.
    FlightRuntime._acquisition_requery_binding`` is the only reader of the
    validated object. ``min_token_chars`` drops short, low-information query
    tokens; ``max_document_frequency`` drops query tokens that occur in more
    than that SHARE of the composite snapshot's values (too common to
    discriminate); ``exclude_visible_tokens`` drops a query token already
    present in a value the row already holds, so the search cannot merely
    re-find what the Solver's own context already covers by type -- exactly
    the failure mode the 2026-09-22 replay diagnosed in the un-weighted E36
    predicate (generic slot-contract cards at the top of every row's match
    list).
    """

    policy_id: str
    min_token_chars: int
    max_document_frequency: float
    exclude_visible_tokens: bool

    def validate(self) -> "RetrievalPolicy":
        if self.policy_id not in RETRIEVAL_POLICY_IDS:
            raise AcquisitionError(
                f"acquisition retrieval policy {self.policy_id!r} is not registered"
            )
        if (
            isinstance(self.min_token_chars, bool)
            or not isinstance(self.min_token_chars, int)
            or self.min_token_chars < 1
        ):
            raise AcquisitionError(
                "acquisition retrieval min_token_chars must be a positive integer"
            )
        if (
            isinstance(self.max_document_frequency, bool)
            or not isinstance(self.max_document_frequency, (int, float))
            or not 0.0 < float(self.max_document_frequency) <= 1.0
        ):
            raise AcquisitionError(
                "acquisition retrieval max_document_frequency must be in (0, 1]"
            )
        if not isinstance(self.exclude_visible_tokens, bool):
            raise AcquisitionError(
                "acquisition retrieval exclude_visible_tokens must be a boolean"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "policy": self.policy_id,
            "min_token_chars": self.min_token_chars,
            "max_document_frequency": float(self.max_document_frequency),
            "exclude_visible_tokens": self.exclude_visible_tokens,
        }


@dataclass(frozen=True)
class AcquiredItem:
    """One piece of typed content an acquisition callback handed the policy."""

    evidence_id: str
    source_id: str
    content: str

    def validate(self) -> "AcquiredItem":
        for name in ("evidence_id", "source_id", "content"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise AcquisitionError(f"acquired item {name} must be non-empty text")
        return self

    def as_block_row(self) -> dict[str, str]:
        self.validate()
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "content": self.content,
        }


@dataclass(frozen=True)
class AcquisitionRequest:
    """Everything one acquisition visit may read, and nothing else.

    The callbacks are FLIGHT-OWNED, exactly as ``material_for_phase``,
    ``supply_for_phase``, ``review_for_phase`` and ``tools_for_phase`` are:
    this module never reaches for a store, a packet, a server or a tokenizer
    of its own. ``requery`` is required by the knowledge kind, ``reobserve``
    by the re-observation kind and ``tool_registry`` by the tool kind; a
    policy handed none of its own fails closed.
    """

    policy_id: str
    kind: str
    sample_id: str
    visit_index: int
    revision_count: int
    planner_route_index: int
    planner_action: str
    state_filters: tuple[str, ...]
    supplied_value_ids: tuple[str, ...]
    budget: AcquisitionBudget
    contacts_used: int
    scope: Mapping[str, object] = field(default_factory=dict)
    requery: Callable[..., Sequence[AcquiredItem]] | None = None
    reobserve: Callable[..., object] | None = None
    tool_registry: Mapping[str, object] | None = None

    def validate(self) -> "AcquisitionRequest":
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise AcquisitionError("acquisition policy_id must be non-empty text")
        if self.kind not in ACQUISITION_KINDS:
            raise AcquisitionError(f"unknown acquisition kind {self.kind!r}")
        if not isinstance(self.sample_id, str) or not self.sample_id.strip():
            raise AcquisitionError("acquisition sample_id must be non-empty text")
        for name in ("visit_index", "revision_count", "planner_route_index",
                     "contacts_used"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AcquisitionError(
                    f"acquisition {name} must be a nonnegative integer"
                )
        if not isinstance(self.planner_action, str) or not self.planner_action:
            raise AcquisitionError("acquisition planner_action must be non-empty text")
        for name in ("state_filters", "supplied_value_ids"):
            value = getattr(self, name)
            if not isinstance(value, tuple) or any(
                not isinstance(item, str) or not item for item in value
            ):
                raise AcquisitionError(f"acquisition {name} must be a tuple of ids")
        if len(self.state_filters) > MAX_STATE_FILTERS:
            raise AcquisitionError(
                f"acquisition state_filters exceeds {MAX_STATE_FILTERS}"
            )
        self.budget.validate()
        if self.visit_index >= self.budget.max_acquisitions_per_row:
            raise AcquisitionError(
                "acquisition budget max_acquisitions_per_row is exhausted"
            )
        if not isinstance(self.scope, Mapping):
            raise AcquisitionError("acquisition scope must be a mapping")
        return self

    def inputs_sha256(self) -> str:
        """The digest of exactly what this visit was asked.

        Deterministic and callback-free by construction: a callback is a live
        object, so hashing it would make the digest un-rederivable. What an
        auditor needs is the QUESTION -- the policy, the kind, the row, the
        visit, the route that triggered it, the state restriction and the
        dedupe set -- and that is what this hashes.
        """

        self.validate()
        return _sha256_text(_canonical_json({
            "policy_id": self.policy_id,
            "kind": self.kind,
            "sample_id": self.sample_id,
            "visit_index": self.visit_index,
            "revision_count": self.revision_count,
            "planner_route_index": self.planner_route_index,
            "planner_action": self.planner_action,
            "state_filters": list(self.state_filters),
            "supplied_value_ids": list(self.supplied_value_ids),
            "scope": dict(self.scope),
            "budget": self.budget.as_json(),
        }))


@dataclass(frozen=True)
class AcquiredEvidence:
    """The ONE record every acquisition kind returns."""

    kind: str
    policy_id: str
    provenance_ids: tuple[str, ...]
    content: str
    contacts_used: int
    cost: int
    cost_unit: str
    inputs_sha256: str
    item_count: int
    schema: str = ACQUISITION_EVIDENCE_SCHEMA

    def validate(self) -> "AcquiredEvidence":
        if self.schema != ACQUISITION_EVIDENCE_SCHEMA:
            raise AcquisitionError("acquired evidence schema is invalid")
        if self.kind not in ACQUISITION_KINDS:
            raise AcquisitionError(f"unknown acquisition kind {self.kind!r}")
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise AcquisitionError("acquired evidence policy_id must be text")
        if not isinstance(self.provenance_ids, tuple) or any(
            not isinstance(item, str) or not item for item in self.provenance_ids
        ):
            raise AcquisitionError("acquired evidence provenance_ids must be ids")
        if len(set(self.provenance_ids)) != len(self.provenance_ids):
            raise AcquisitionError("acquired evidence provenance_ids must be unique")
        if not isinstance(self.content, str) or not self.content.strip():
            raise AcquisitionError("acquired evidence content must be non-empty text")
        for name in ("contacts_used", "cost", "item_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise AcquisitionError(
                    f"acquired evidence {name} must be a nonnegative integer"
                )
        if not isinstance(self.cost_unit, str) or not self.cost_unit.strip():
            raise AcquisitionError("acquired evidence cost_unit must be text")
        if len(self.inputs_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.inputs_sha256
        ):
            raise AcquisitionError("acquired evidence inputs_sha256 must be a sha256")
        if self.item_count > MAX_ACQUIRED_ITEMS:
            raise AcquisitionError(
                f"acquired evidence item_count exceeds {MAX_ACQUIRED_ITEMS}"
            )
        return self

    def evidence_sha256(self) -> str:
        self.validate()
        return _sha256_text(self.content)

    def receipt(self, **extra: object) -> dict[str, object]:
        """The block one acquisition visit contributes to the episode receipt.

        It names the kind, the policy, what was brought in and what it cost --
        never the acquired TEXT: a speech carrier's acquired content can quote
        this row's own material, and a receipt is not a place for it. The two
        digests are what bind the text.
        """

        self.validate()
        record: dict[str, object] = {
            "schema": ACQUISITION_RECEIPT_SCHEMA,
            "kind": self.kind,
            "policy_id": self.policy_id,
            "provenance_ids": list(self.provenance_ids),
            "item_count": self.item_count,
            "contacts_used": self.contacts_used,
            "cost": self.cost,
            "cost_unit": self.cost_unit,
            "inputs_sha256": self.inputs_sha256,
            "evidence_sha256": self.evidence_sha256(),
            "evidence_chars": len(self.content),
        }
        record.update(extra)
        return record


# ---------------------------------------------------------------------------
# The state restriction (SUPPLY + the 2026-09-06 query-modality ruling)
# ---------------------------------------------------------------------------


def derive_state_filters(
    state: Mapping[str, object], *, max_filters: int = MAX_STATE_FILTERS,
) -> tuple[str, ...]:
    """The deterministic STATE restriction one acquisition carries.

    Read from the trajectory the node already holds -- the latest Reviewer
    finding (which slot types and fields it criticised) and the Planner's own
    action token -- as lowercase word tokens, deduplicated in first-occurrence
    order and bounded by ``max_filters``. Zero contacts, no parser that can
    fail a row: a finding that yields no token yields an empty restriction and
    the acquisition then re-queries unrestricted.

    These tokens RESTRICT a speech-keyed ranking; they are never themselves a
    retrieval key. The owner ruling of 2026-09-06 forbids a text-only query,
    and the callback this restriction is handed to is the one that owns the
    row's sealed speech vector -- which is why the restriction can be derived
    from model text at all.
    """

    if isinstance(max_filters, bool) or not isinstance(max_filters, int) or max_filters < 0:
        raise AcquisitionError("max_filters must be a nonnegative integer")
    sources: list[str] = []
    for key in ("review", "plan"):
        value = state.get(key)
        if isinstance(value, str) and value:
            sources.append(value)
    seen: list[str] = []
    for source in sources:
        for token in _FILTER_TOKEN.findall(source.lower()):
            if token not in seen:
                seen.append(token)
            if len(seen) >= max_filters:
                return tuple(seen)
    return tuple(seen)


def supplied_value_ids(state: Mapping[str, object]) -> tuple[str, ...]:
    """The value ids this trajectory has already been supplied, deduped.

    The dedupe set of the knowledge re-query kind: an acquisition that returned
    what the Solver already holds would spend a revision to change nothing.
    """

    value = state.get("supplied_value_ids")
    if value is None:
        return ()
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AcquisitionError("supplied_value_ids must be an ordered sequence of ids")
    ids: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item:
            raise AcquisitionError("supplied_value_ids must contain non-empty ids")
        if item not in ids:
            ids.append(item)
    return tuple(ids)


# ---------------------------------------------------------------------------
# The rendered block
# ---------------------------------------------------------------------------


def acquired_evidence_template(repo_root: object) -> NodeContextTemplate:
    """Load the committed, hash-pinned block template (E18)."""

    return load_node_context_template(repo_root, ACQUIRED_EVIDENCE_TEMPLATE)


def render_evidence_block(
    template: NodeContextTemplate,
    *,
    kind: str,
    policy_id: str,
    items: Sequence[AcquiredItem],
    reason: str = NO_ACQUIRED_EVIDENCE,
) -> str:
    """The one text form every acquisition kind's evidence takes."""

    if template.renderer != ACQUIRED_EVIDENCE_RENDERER:
        raise AcquisitionError(
            "the acquired-evidence block requires a "
            f"{ACQUIRED_EVIDENCE_RENDERER!r} template"
        )
    rows = [item.validate().as_block_row() for item in items]
    if len(rows) > MAX_ACQUIRED_ITEMS:
        raise AcquisitionError(
            f"an acquisition may render at most {MAX_ACQUIRED_ITEMS} items"
        )
    return render_acquired_evidence(
        template, kind=kind, policy_id=policy_id, items=rows, reason=reason,
    ).text


# ---------------------------------------------------------------------------
# The policies
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AcquisitionPolicy:
    """One registered acquisition kind, with the cost it is allowed to spend."""

    policy_id: str
    kind: str
    contacts_per_acquisition: int
    cost_unit: str
    run: Callable[..., object] = field(compare=False, repr=False)

    def __post_init__(self) -> None:
        if self.kind not in ACQUISITION_KINDS:
            raise AcquisitionError(f"unknown acquisition kind {self.kind!r}")
        if (
            isinstance(self.contacts_per_acquisition, bool)
            or not isinstance(self.contacts_per_acquisition, int)
            or not 0 <= self.contacts_per_acquisition <= 1
        ):
            raise AcquisitionError(
                "an acquisition policy spends 0 or 1 model contacts per visit"
            )
        if not callable(self.run):
            raise AcquisitionError("an acquisition policy must be callable")

    async def __call__(
        self, request: AcquisitionRequest, *, template: NodeContextTemplate,
    ) -> AcquiredEvidence:
        request.validate()
        if request.policy_id != self.policy_id or request.kind != self.kind:
            raise AcquisitionError(
                "acquisition request names a different policy than the one running it"
            )
        if (
            request.contacts_used + self.contacts_per_acquisition
            > request.budget.contact_budget
        ):
            raise AcquisitionError("acquisition contact budget is exhausted")
        evidence = await self.run(request, template=template, policy=self)
        if not isinstance(evidence, AcquiredEvidence):
            raise AcquisitionError("an acquisition policy must return AcquiredEvidence")
        evidence.validate()
        if evidence.contacts_used != self.contacts_per_acquisition:
            raise AcquisitionError(
                "acquisition spent a different number of contacts than its policy "
                "declares"
            )
        return evidence


async def _knowledge_requery(
    request: AcquisitionRequest, *, template: NodeContextTemplate, policy: AcquisitionPolicy,
) -> AcquiredEvidence:
    """Kind (a): re-run the phase supply for the Solver. Zero contacts."""

    if request.requery is None:
        raise AcquisitionError(
            "the knowledge re-query acquisition requires a bound requery callback; "
            "this base never reaches for a store of its own"
        )
    returned = request.requery(
        filters=request.state_filters,
        exclude_value_ids=frozenset(request.supplied_value_ids),
        scope=dict(request.scope),
    )
    if isinstance(returned, (str, bytes)) or not isinstance(returned, Sequence):
        raise AcquisitionError("a requery callback must return an ordered sequence")
    items: list[AcquiredItem] = []
    already = set(request.supplied_value_ids)
    for entry in returned:
        if not isinstance(entry, AcquiredItem):
            raise AcquisitionError("a requery callback must return AcquiredItem values")
        entry.validate()
        # Dedupe is the policy's own job, not the callback's: a callback that
        # forgets the exclusion must not be able to re-supply what the Solver
        # already holds.
        if entry.evidence_id in already:
            continue
        already.add(entry.evidence_id)
        items.append(entry)
        if len(items) >= MAX_ACQUIRED_ITEMS:
            break
    content = render_evidence_block(
        template, kind=policy.kind, policy_id=policy.policy_id, items=items,
    )
    return AcquiredEvidence(
        kind=policy.kind,
        policy_id=policy.policy_id,
        provenance_ids=tuple(item.evidence_id for item in items),
        content=content,
        contacts_used=0,
        cost=1,
        cost_unit=policy.cost_unit,
        inputs_sha256=request.inputs_sha256(),
        item_count=len(items),
    ).validate()


async def _speech_reobserve(
    request: AcquisitionRequest, *, template: NodeContextTemplate, policy: AcquisitionPolicy,
) -> AcquiredEvidence:
    """Kind (b): one re-scoped Perception contact. Costs one contact."""

    if request.reobserve is None:
        raise AcquisitionError(
            "the speech re-observation acquisition requires a bound reobserve "
            "callback; this base never contacts the core of its own accord"
        )
    observation = await request.reobserve(scope=dict(request.scope))
    if not isinstance(observation, AcquiredItem):
        raise AcquisitionError(
            "a reobserve callback must return one AcquiredItem carrying the "
            "re-observation's candidate hypotheses"
        )
    observation.validate()
    content = render_evidence_block(
        template, kind=policy.kind, policy_id=policy.policy_id, items=(observation,),
    )
    return AcquiredEvidence(
        kind=policy.kind,
        policy_id=policy.policy_id,
        provenance_ids=(observation.evidence_id,),
        content=content,
        contacts_used=1,
        cost=1,
        cost_unit=policy.cost_unit,
        inputs_sha256=request.inputs_sha256(),
        item_count=1,
    ).validate()


async def _tool_acquire(
    request: AcquisitionRequest, *, template: NodeContextTemplate, policy: AcquisitionPolicy,
) -> AcquiredEvidence:
    """Kind (c): a registry lookup by domain group. STUB -- fails closed.

    The Audio2Tool instance of the primitive: given the row's domain group,
    look the group's rows up in the carrier's frozen tool registry and return
    them as typed content. It is registered on every carrier and armed on
    none, because only Audio2Tool has a registry (``core.base.TOOL_CATALOG``
    plus the ``rails/a2t_*`` grounds) and SLURP has none at all. With no
    registry bound it REFUSES by name rather than returning an empty
    acquisition: an acquisition that found nothing and an acquisition that
    could never have found anything must not look alike.
    """

    if request.tool_registry is None:
        raise AcquisitionError(
            "the tool-registry acquisition is registered but not armed on this "
            "carrier: no tool registry is bound. It is the Audio2Tool instance of "
            "the acquire primitive and it needs that carrier's frozen registry; "
            "SLURP has no registry and must not arm it"
        )
    raise AcquisitionError(
        "the tool-registry acquisition has no carrier implementation yet; the "
        "Audio2Tool instance lands with the carrier's own cell, not with E18"
    )


KNOWLEDGE_REQUERY_POLICY = ACQUISITION_POLICIES.register(
    KNOWLEDGE_REQUERY_POLICY_ID,
    AcquisitionPolicy(
        policy_id=KNOWLEDGE_REQUERY_POLICY_ID,
        kind=KIND_KNOWLEDGE_REQUERY,
        contacts_per_acquisition=0,
        cost_unit="supply-calls",
        run=_knowledge_requery,
    ),
)

SPEECH_REOBSERVE_POLICY = ACQUISITION_POLICIES.register(
    SPEECH_REOBSERVE_POLICY_ID,
    AcquisitionPolicy(
        policy_id=SPEECH_REOBSERVE_POLICY_ID,
        kind=KIND_SPEECH_REOBSERVE,
        contacts_per_acquisition=1,
        cost_unit="model-contacts",
        run=_speech_reobserve,
    ),
)

TOOL_ACQUIRE_POLICY = ACQUISITION_POLICIES.register(
    TOOL_ACQUIRE_POLICY_ID,
    AcquisitionPolicy(
        policy_id=TOOL_ACQUIRE_POLICY_ID,
        kind=KIND_TOOL_ACQUIRE,
        contacts_per_acquisition=0,
        cost_unit="registry-lookups",
        run=_tool_acquire,
    ),
)


def resolve_acquisition_policy(policy_id: str) -> AcquisitionPolicy:
    """The registered policy, or a refusal naming what is registered."""

    try:
        policy = ACQUISITION_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise AcquisitionError(f"acquisition policy is invalid: {error}") from error
    if not isinstance(policy, AcquisitionPolicy):
        raise AcquisitionError(
            f"acquisition policy {policy_id!r} is not an AcquisitionPolicy"
        )
    return policy


__all__ = [
    "ACQUISITION_EVIDENCE_SCHEMA",
    "ACQUISITION_KINDS",
    "ACQUISITION_RECEIPT_SCHEMA",
    "AcquiredEvidence",
    "AcquiredItem",
    "AcquisitionBudget",
    "AcquisitionError",
    "AcquisitionPolicy",
    "AcquisitionRequest",
    "KIND_KNOWLEDGE_REQUERY",
    "KIND_SPEECH_REOBSERVE",
    "KIND_TOOL_ACQUIRE",
    "KNOWLEDGE_REQUERY_POLICY_ID",
    "KNOWLEDGE_REQUERY_RETRIEVAL_POLICY_ID",
    "MAX_ACQUIRED_ITEMS",
    "MAX_STATE_FILTERS",
    "RETRIEVAL_POLICY_IDS",
    "RetrievalPolicy",
    "SPEECH_REOBSERVE_POLICY_ID",
    "TOOL_ACQUIRE_POLICY_ID",
    "acquired_evidence_template",
    "derive_state_filters",
    "render_evidence_block",
    "resolve_acquisition_policy",
    "supplied_value_ids",
]
