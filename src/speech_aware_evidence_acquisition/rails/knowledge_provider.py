"""``KnowledgeProvider``: one interface over the study's three independently
built knowledge layers (consolidation slice C4b, "one knowledge interface").

Before this module existed, a caller that wanted knowledge had to know which
of three unrelated mechanisms it was talking to -- the SLURP facet-KB layer
(``rails.knowledge_build`` + ``rails.kb_policy``: build a
:class:`~.knowledge.KnowledgeSnapshot`, recall/rank/fuse it into a
:class:`~.knowledge.FusionDecision`), the Audio2Tool dense-centroid layer
(``rails.a2t_semantic_router``: build a
:class:`~.a2t_semantic_router.ToolTierSemanticIndex`, rank a query vector,
RRF-fuse several rankings), or the ConEC evidence layer (``core.evidence``:
resolve a registered evidence source, render its
:class:`~.core.base.EvidenceItem`\\ s straight into a prompt) -- each with its
own build/rank/fuse/render vocabulary and, worse, the Audio2Tool layer never
produced a :class:`~.supply.SupplyPacket` at all: its selected-tool cards
were injected as bare instruction text, invisible to
``assert_knowledge_use_binding`` and to the consumption-trace machinery every
other supply path is attributed through.

This module WRAPS all three by importing them -- it never edits
``rails.kb_policy``, ``rails.a2t_semantic_router``, ``core.evidence``, or any
other module it wraps -- behind one four-stage interface every concrete
provider below implements identically: ``build`` (TRAIN-only, model-free,
produces one provider-specific frozen artifact), ``candidates`` (one query ->
one :class:`Ranking`), ``fuse`` (one or more :class:`Ranking`/
:class:`~.knowledge.FusionDecision` -> the provider's selection), and
``materialize`` (one selection -> one :class:`~.supply.SupplyPacket`, so
every provider's output now flows through the same SUPPLY-axis contract
``rails.runner`` and ``core.policies.build_arm_payload`` already enforce for
everything else). :class:`DenseCentroidProvider` is exactly the fix for the
Audio2Tool gap above: its ``materialize`` renders the selected tool cards
into a real :class:`~.supply.SupplyPacket`, not instruction text.

No model, filesystem, GPU, or network access anywhere in this module. Every
concrete provider is built from caller-injected rows/vectors/evidence; a real
flight resolves those upstream (a governed jsonl load, an embedding-server
call, an ``EVIDENCE_SOURCES`` read) and hands the RESULT in here.

``KNOWLEDGE_PROVIDERS`` is the shared ``core.base`` registry (E6,
2026-09-06 -- it used to be a local stopgap here); the three ``register``
calls at the bottom of this module are its canonical population site, so a
baseline fragment's ``phase_supply.provider`` resolves the same way every
other config-declared component id does.
"""

from __future__ import annotations

import abc
import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Mapping, Sequence

from ..core.base import (
    EVIDENCE_SOURCES,
    EvidenceItem,
    KNOWLEDGE_BUILDERS,
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_PROVIDERS as _CORE_KNOWLEDGE_PROVIDERS,
    KNOWLEDGE_RANKERS,
    STAGE3_SUPPLY_GATE_POLICIES,
)
from ..core import evidence as _core_evidence  # noqa: F401 -- side-effect import:
# registers "conec-contexts"/"conec-names"/"conec-bias-list"/... into the
# shared EVIDENCE_SOURCES registry (core.evidence's own module-level
# EVIDENCE_SOURCES.register(...) calls); ConecContextProvider validates its
# evidence_source_id against that registry, so it must be populated.
from .a2t_semantic_router import (
    RRF_CONSTANT,
    SemanticRanking,
    ToolTierSemanticIndex,
    fuse_semantic_rankings,
)
from .a2t_selected_tool_ground import SelectedToolDecisionGround
from .errors import RailsError
from .hashing import content_hash
from .kb_policy import (
    AGREEMENT_DIMENSIONS,
    EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
    FUSE_POLICY_ID,
    RANK_POLICY_ID,
    FuseKnobs,
    RankWeights,
    multidim_recall,
    multidim_segment_recall,
)
from .knowledge import AgentStateArtifact, FusionDecision, KnowledgeSnapshot, QueryState
from .slurp_intent_hypotheses import (
    DEFAULT_FALLBACK_DISTINCTION,
    SlurpIntentHypothesisError,
    validate_fallback_candidate_ids,
    validate_fallback_distinction,
)
from .stage3_delta_supply import (
    STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
    node_target_of_task_target,
    select_unconditional_stage3_delta_values,
    STAGE3_DELTA_CONTEXT_PROVIDER_ID,
    STAGE3_DELTA_SCENARIO_GATE_POLICY_ID,
    DEFAULT_STAGE3_DELTA_CAP,
    DeltaCandidate,
    ScenarioGate,
    parse_scenario_gate,
    select_stage3_delta_values,
)
from .supply import SupplyDose, SupplyForm, SupplyItem, SupplyPacket

_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _require_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_HEX.fullmatch(value) is None:
        raise RailsError(f"{field} must be a 64-hex SHA-256")
    return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Ranking / RankedEntry -- the one candidate-set shape every provider emits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RankedEntry:
    """One candidate a provider's ``candidates()``/``fuse()`` returned.

    ``entry_id`` names whatever the provider's own domain calls a candidate
    (a facet id, a tool name, an evidence id) -- deliberately untyped so one
    ``Ranking`` shape covers all three providers. ``provenance`` carries
    provider-specific numeric context (a rank position, a sub-score) as a
    flat ``str -> float`` mapping, never free text.
    """

    entry_id: str
    score: float
    provenance: Mapping[str, float]

    def validate(self) -> "RankedEntry":
        if not isinstance(self.entry_id, str) or not self.entry_id:
            raise RailsError("RankedEntry.entry_id must be a non-empty string")
        if (
            isinstance(self.score, bool)
            or not isinstance(self.score, (int, float))
            or not math.isfinite(float(self.score))
        ):
            raise RailsError("RankedEntry.score must be a finite number")
        if not isinstance(self.provenance, Mapping):
            raise RailsError("RankedEntry.provenance must be a mapping")
        for key, value in self.provenance.items():
            if not isinstance(key, str) or not key:
                raise RailsError("RankedEntry.provenance keys must be non-empty strings")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                raise RailsError(
                    f"RankedEntry.provenance[{key!r}] must be a finite number"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "entry_id": self.entry_id,
            "score": self.score,
            "provenance": dict(self.provenance),
        }


@dataclass(frozen=True)
class Ranking:
    """One provider's candidate set for one query, sorted and hash-bound.

    ``index_sha256`` names whatever frozen artifact ``build()`` produced
    (never the live object -- the same "hash, not identity" discipline
    :class:`~.knowledge.RankResult` already applies to
    ``snapshot_sha256``); ``query_sha256`` names the query that produced
    this ranking (a :class:`~.knowledge.QueryState` content hash, a query
    vector's own sha256, or an evidence query's identity hash, depending on
    the provider). ``source`` is the ``provider_id`` that produced it, so a
    caller fusing several providers' rankings can tell them apart.
    """

    entries: tuple[RankedEntry, ...]
    index_sha256: str
    query_sha256: str
    source: str

    def validate(self) -> "Ranking":
        _require_sha256(self.index_sha256, field="Ranking.index_sha256")
        _require_sha256(self.query_sha256, field="Ranking.query_sha256")
        if not isinstance(self.source, str) or not self.source:
            raise RailsError("Ranking.source must be a non-empty string")
        if not isinstance(self.entries, tuple):
            raise RailsError("Ranking.entries must be a tuple")
        seen: set[str] = set()
        previous_score: float | None = None
        previous_id: str | None = None
        for entry in self.entries:
            if not isinstance(entry, RankedEntry):
                raise RailsError("Ranking.entries must contain RankedEntry instances")
            entry.validate()
            if entry.entry_id in seen:
                raise RailsError(f"Ranking has duplicate entry_id {entry.entry_id!r}")
            seen.add(entry.entry_id)
            score = float(entry.score)
            if previous_score is not None and (
                score > previous_score
                or (score == previous_score and entry.entry_id < previous_id)
            ):
                raise RailsError(
                    "Ranking.entries must be sorted by score descending, then "
                    "entry_id ascending"
                )
            previous_score = score
            previous_id = entry.entry_id
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "entries": [entry.as_json() for entry in self.entries],
            "index_sha256": self.index_sha256,
            "query_sha256": self.query_sha256,
            "source": self.source,
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())


# ---------------------------------------------------------------------------
# KnowledgeProvider -- the shared base
# ---------------------------------------------------------------------------


class KnowledgeProvider(abc.ABC):
    """Shared BUILD/USE contract over one frozen knowledge artifact.

    Concrete providers own ``build``/``candidates``/``fuse`` (their domain's
    own recall/rank/fuse vocabulary); everything else here -- identity,
    hashing, receipts, decontamination, and a generic ``materialize``
    fallback -- is shared so a new provider gets it for free.
    """

    def __init__(self, *, provider_id: str) -> None:
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise RailsError("KnowledgeProvider.provider_id must be a non-empty string")
        self._provider_id = provider_id
        self._built: object | None = None
        self._build_policy_id: str | None = None
        self._source_ids: tuple[str, ...] = ()
        self._built_at: str | None = None
        self._pinned_sha256: str | None = None

    @property
    def provider_id(self) -> str:
        return self._provider_id

    # -- abstract seam ------------------------------------------------

    @abc.abstractmethod
    def build(self, source_rows: object, *, policy_id: str) -> object:
        """TRAIN-only, model-free: freeze this provider's own artifact from
        caller-supplied rows (never read from disk/network by the provider
        itself) under a named build policy."""

    @abc.abstractmethod
    def candidates(self, query: object, *, k: int) -> Ranking:
        """Recall+rank this provider's own frozen artifact against one query,
        returning at most ``k`` entries, score-descending."""

    @abc.abstractmethod
    def fuse(self, rankings: Sequence[Ranking], *, k: int, policy_id: str) -> object:
        """Fuse one or more :class:`Ranking`\\ s (from ``candidates()``) into
        this provider's own selection shape (a
        :class:`~.knowledge.FusionDecision` or a :class:`Ranking`,
        provider-dependent)."""

    # -- build bookkeeping shared by every provider --------------------

    def _record_build(
        self, built: object, *, policy_id: str, source_ids: Sequence[str]
    ) -> None:
        self._built = built
        self._build_policy_id = policy_id
        self._source_ids = tuple(source_ids)
        self._built_at = _utc_now_iso()

    def adopt(
        self,
        built: object,
        *,
        policy_id: str,
        source_ids: Sequence[str] = (),
        snapshot_sha256: str | None = None,
    ) -> "KnowledgeProvider":
        """Bind an artifact this provider did NOT build itself (E6).

        A flight loads and hash-verifies its frozen ``KnowledgeSnapshot``
        once, in ``core.flight.FlightRuntime._load_knowledge_snapshot``;
        asking the provider to re-derive it from source rows would produce a
        second artifact under a second identity. ``adopt`` is the honest
        alternative: it records the already-frozen object under a named
        policy id, so ``snapshot_sha256``/``receipt``/``candidates`` see
        exactly the artifact the flight pinned.

        ``snapshot_sha256`` pins that artifact's already-computed hash.
        :meth:`snapshot_sha256` otherwise re-canonicalises and re-hashes the
        whole artifact on EVERY call -- three times per supply decision,
        which at SLURP's 23,267 protected payloads times a 1,000-row roster
        is the dominant cost of a supplied cell and buys nothing: the flight
        already computed and verified this exact hash.
        """

        if built is None:
            raise RailsError(f"{self.provider_id}: adopt() needs a built artifact")
        self._record_build(built, policy_id=policy_id, source_ids=tuple(source_ids))
        if snapshot_sha256 is not None:
            self._pinned_sha256 = _require_sha256(
                snapshot_sha256, field=f"{self.provider_id}.adopt snapshot_sha256"
            )
        return self

    def _built_object(self) -> object:
        if self._built is None:
            raise RailsError(f"{self.provider_id}: build() has not been called yet")
        return self._built

    def _built_sample_ids(self) -> frozenset[str]:
        """Every sample id ``build()`` bound this provider's knowledge to;
        used by :meth:`decontaminate`'s identity-overlap check. Every
        concrete provider overrides this -- the base has no generic way to
        recover sample ids from an arbitrary built artifact."""

        raise NotImplementedError(
            f"{type(self).__name__} must override _built_sample_ids for decontaminate()"
        )

    def _canonical_view(self, built: object) -> Mapping[str, object]:
        """A JSON-safe canonical view of ``built``, used by
        :meth:`snapshot_sha256` ONLY when ``built`` has no ``content_hash()``
        of its own. The base handles a bare JSON-safe mapping; a provider
        whose built artifact needs translation (e.g. an ``EvidenceItem``
        carries no ``as_json()``) overrides this."""

        if isinstance(built, Mapping):
            return {str(key): built[key] for key in sorted(built, key=str)}
        raise RailsError(
            f"{self.provider_id}: cannot canonicalize a {type(built).__name__} for "
            "hashing; override _canonical_view"
        )

    def _extra_receipt_fields(self) -> Mapping[str, object]:
        """Provider-specific receipt fields beyond the shared ones
        :meth:`receipt` always includes. Empty by default."""

        return {}

    # -- shared surface -------------------------------------------------

    def snapshot_sha256(self) -> str:
        """Content hash of whatever ``build()`` produced: the built object's
        own ``content_hash()`` when it has one (e.g.
        :class:`~.knowledge.KnowledgeSnapshot`), else the canonical-JSON
        sha256 of :meth:`_canonical_view`."""

        built = self._built_object()
        if self._pinned_sha256 is not None:
            return self._pinned_sha256
        native_hash = getattr(built, "content_hash", None)
        if callable(native_hash):
            return native_hash()
        return content_hash(self._canonical_view(built))

    def receipt(self) -> Mapping[str, object]:
        """Provider id, snapshot hash, build policy id, source ids, and
        ``built_at`` -- plus whatever :meth:`_extra_receipt_fields` adds."""

        document: dict[str, object] = {
            "provider_id": self.provider_id,
            "snapshot_sha256": self.snapshot_sha256(),
            "build_policy_id": self._build_policy_id,
            "source_ids": list(self._source_ids),
            "built_at": self._built_at,
        }
        document.update(self._extra_receipt_fields())
        return document

    def decontaminate(
        self,
        evaluation_sample_ids: Sequence[str],
        *,
        normalized_text_of: Callable[[str], str] | None = None,
        allow_overlap: bool = False,
    ) -> Mapping[str, object]:
        """Identity overlap between this provider's built sample ids and
        ``evaluation_sample_ids``, plus an optional normalized-text overlap
        count when ``normalized_text_of`` is supplied. FAILS CLOSED on any
        identity overlap unless ``allow_overlap=True`` -- the same
        fail-closed discipline ``rails.knowledge_build.build_knowledge_snapshot``
        and ``rails.knowledge_build_a2t.build_a2t_knowledge_snapshot`` already
        apply to their own devel/test/exposed rosters, generalized here so
        every provider gets it uniformly.
        """

        built_ids = self._built_sample_ids()
        eval_ids = frozenset(evaluation_sample_ids)
        overlap = sorted(built_ids & eval_ids)
        if overlap and not allow_overlap:
            preview = overlap[:5]
            raise RailsError(
                f"{self.provider_id}: knowledge overlaps {len(overlap)} evaluation "
                f"sample id(s): {preview}"
                + (f" (+{len(overlap) - 5} more)" if len(overlap) > 5 else "")
            )
        result: dict[str, object] = {
            "provider_id": self.provider_id,
            "identity_overlap_count": len(overlap),
            "identity_overlap_sample_ids": tuple(overlap),
            "allow_overlap": bool(allow_overlap),
        }
        if normalized_text_of is not None:
            built_norms = {normalized_text_of(sid): sid for sid in built_ids}
            eval_norms = {normalized_text_of(sid): sid for sid in eval_ids}
            text_overlap = tuple(sorted(set(built_norms) & set(eval_norms)))
            result["normalized_text_overlap_count"] = len(text_overlap)
            result["normalized_text_overlap_keys"] = text_overlap
        return result

    def materialize(self, selection: object, *, query_state: object) -> SupplyPacket:
        """Generic fallback: render a bare :class:`Ranking`'s entries into a
        :class:`~.supply.SupplyPacket`. Every concrete provider below
        overrides this with its own task-shaped rendering (a
        :class:`~.knowledge.KnowledgeSnapshot`'s ``ValueBundle`` text, a
        selected-tool decision card, an evidence item's content) -- this
        fallback exists only for a provider that has nothing more specific
        to render than bare candidate ids/scores/provenance.
        """

        entries = selection.entries if isinstance(selection, Ranking) else tuple(selection)
        if not entries:
            raise RailsError(f"{self.provider_id}.materialize: selection has no entries")
        items = tuple(
            SupplyItem(
                item_id=f"{self.provider_id}:{entry.entry_id}",
                text=(
                    f"{entry.entry_id} score={entry.score:.6f}"
                    + (
                        " " + " ".join(
                            f"{key}={value:.6f}"
                            for key, value in sorted(entry.provenance.items())
                        )
                        if entry.provenance
                        else ""
                    )
                ),
                evidence_id=entry.entry_id,
            )
            for entry in entries
        )
        return SupplyPacket(
            form=SupplyForm.TEXT,
            dose=SupplyDose(
                n_items=len(items),
                token_count=sum(len(item.text.split()) for item in items),
            ),
            prompt_block="\n".join(item.text for item in items),
            assembly_template_id=f"{self.provider_id}-generic-ranking-v1",
            items=items,
        ).validate()


# ---------------------------------------------------------------------------
# KbFacetProvider -- wraps rails.knowledge_build + rails.kb_policy
# ---------------------------------------------------------------------------


def _visible_kb_values(snapshot: KnowledgeSnapshot, query_state: QueryState):
    """Replicates ``rails.runner._visible_values`` exactly (module docstring:
    providers wrap by importing, never by depending on a private runner
    symbol -- ``rails.runner`` is under concurrent edit elsewhere in this
    program and pulls in ``rails.core_client``/``core.model``, a needless
    production-time coupling for four lines of pure lookup logic). See
    ``tests/unit/test_knowledge_provider.py`` for the identity proof against
    the real ``rails.runner._supply_for_state``."""

    by_id = {value.value_id: value for value in snapshot.values}
    unknown = set(query_state.retrieved_value_ids) - set(by_id)
    if unknown:
        raise RailsError(
            "QueryState references values outside the frozen knowledge snapshot: "
            f"{sorted(unknown)}"
        )
    return tuple(by_id[value_id] for value_id in query_state.retrieved_value_ids)


def _render_kb_supply_packet(
    snapshot: KnowledgeSnapshot, query_state: QueryState
) -> SupplyPacket:
    """Replicates ``rails.runner._supply_for_state`` exactly (same rationale
    as :func:`_visible_kb_values`). A ``query_state`` with no visible values
    still returns a (structurally legal) packet with zero items here, since
    ``KnowledgeProvider.materialize`` always returns a ``SupplyPacket`` --
    unlike the runner's own optional ``SupplyPacket | None`` shape, a
    provider caller decides for itself whether to skip supply entirely."""

    values = _visible_kb_values(snapshot, query_state)
    items = tuple(
        SupplyItem(
            item_id=f"knowledge:{value.value_id}",
            text=value.content,
            evidence_id=value.value_id,
        )
        for value in values
    )
    return SupplyPacket(
        form=SupplyForm.TEXT,
        dose=SupplyDose(
            n_items=len(items),
            token_count=sum(len(item.text.split()) for item in items),
        ),
        prompt_block="\n".join(
            f"[value {item.evidence_id}] {item.text}" for item in items
        ),
        assembly_template_id="knowledge-value-bundle-v1",
        items=items,
    ).validate()


def _validated_agreement_scores(
    table: Mapping[str, Mapping[str, float]],
) -> dict[str, dict[str, float]]:
    """Shape-check a per-row agreement table before it can reach a ranker.

    ``{sample_id: {facet_id: share}}`` with every share a finite float in
    ``[0, 1]``. Fail-closed on anything else, because the ranker sums this
    number against a cosine and an out-of-range value would silently
    outrank the whole recalled set (the defect
    ``rails.kb_policy._dimension_scales`` documents for prior mass).
    """

    if not isinstance(table, Mapping):
        raise RailsError("KbFacetProvider: agreement_scores must be a mapping")
    checked: dict[str, dict[str, float]] = {}
    for sample_id, row in table.items():
        if not isinstance(sample_id, str) or not sample_id:
            raise RailsError("KbFacetProvider: agreement_scores keys must be sample ids")
        if not isinstance(row, Mapping):
            raise RailsError(
                f"KbFacetProvider: agreement_scores[{sample_id!r}] must be a mapping"
            )
        decoded: dict[str, float] = {}
        for facet_id, score in row.items():
            if not isinstance(facet_id, str) or not facet_id:
                raise RailsError(
                    f"KbFacetProvider: agreement_scores[{sample_id!r}] keys must be facet ids"
                )
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(float(score))
                or not 0.0 <= float(score) <= 1.0
            ):
                raise RailsError(
                    f"KbFacetProvider: agreement_scores[{sample_id!r}][{facet_id!r}] "
                    "must be a finite share within [0, 1]"
                )
            decoded[facet_id] = float(score)
        checked[sample_id] = decoded
    return checked


class KbFacetProvider(KnowledgeProvider):
    """Wraps the SLURP facet-KB layer: ``build`` resolves and calls a
    ``core.base.KNOWLEDGE_BUILDERS``-registered builder (e.g.
    ``rails.knowledge_build.build_knowledge_snapshot`` under
    ``saea-kb-distmodel-v1``); ``candidates`` calls
    ``rails.kb_policy.multidim_recall`` plus the ranker registered under
    ``core.base.KNOWLEDGE_RANKERS``; ``fuse`` calls the fuser registered
    under ``core.base.KNOWLEDGE_FUSERS``; ``materialize`` renders the exact
    same :class:`~.supply.SupplyPacket` ``rails.runner._supply_for_state``
    would build for the same snapshot/query_state pair.
    """

    def __init__(
        self,
        *,
        provider_id: str = "kb-facet-v1",
        build_spec: object,
        forbidden_sample_ids: frozenset[str] = frozenset(),
        rank_policy_id: str = RANK_POLICY_ID,
        rank_weights: RankWeights | None = None,
        fuse_knobs: FuseKnobs | None = None,
        top_k_per_dimension: int = 5,
        facet_vectors: Callable[[str], Mapping[str, Sequence[float]]] | None = None,
        prepared_recall: Mapping[str, Mapping[str, Mapping[str, float]]] | None = None,
        agreement_scores: Mapping[str, Mapping[str, float]] | None = None,
        agreement_dimension: str = EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
    ) -> None:
        super().__init__(provider_id=provider_id)
        self._build_spec = build_spec
        self._forbidden_sample_ids = frozenset(forbidden_sample_ids)
        self._rank_policy_id = rank_policy_id
        self._ranker = KNOWLEDGE_RANKERS.resolve(rank_policy_id)(rank_weights)
        self._fuse_knobs = fuse_knobs
        if (
            isinstance(top_k_per_dimension, bool)
            or not isinstance(top_k_per_dimension, int)
            or top_k_per_dimension <= 0
        ):
            raise RailsError("KbFacetProvider: top_k_per_dimension must be a positive int")
        self._top_k_per_dimension = top_k_per_dimension
        self._facet_vectors = facet_vectors or (lambda facet_id: {})
        self._prepared_recall = prepared_recall
        if agreement_dimension not in AGREEMENT_DIMENSIONS:
            raise RailsError(
                "KbFacetProvider: agreement_dimension must name a reserved "
                f"rails.kb_policy.AGREEMENT_DIMENSIONS entry, got "
                f"{agreement_dimension!r}"
            )
        self._agreement_dimension = agreement_dimension
        self._agreement_scores = (
            None if agreement_scores is None else _validated_agreement_scores(agreement_scores)
        )
        self._last_query_state: QueryState | None = None
        self._last_recall_scores: Mapping[str, Mapping[str, float]] | None = None
        self._last_rank_result: object | None = None

    def build(self, source_rows: Sequence[object], *, policy_id: str) -> KnowledgeSnapshot:
        builder = KNOWLEDGE_BUILDERS.resolve(policy_id)
        snapshot = builder(
            self._build_spec,
            rows=tuple(source_rows),
            forbidden_sample_ids=self._forbidden_sample_ids,
        )
        if not isinstance(snapshot, KnowledgeSnapshot):
            raise RailsError(
                f"KbFacetProvider.build: builder {policy_id!r} did not return a "
                "KnowledgeSnapshot"
            )
        self._record_build(
            snapshot, policy_id=policy_id, source_ids=snapshot.source_sample_ids
        )
        return snapshot

    def _built_sample_ids(self) -> frozenset[str]:
        snapshot: KnowledgeSnapshot = self._built_object()
        return frozenset(snapshot.source_sample_ids)

    def _merge_agreement(
        self,
        query_state: object,
        recall_scores: Mapping[str, Mapping[str, float]],
    ) -> Mapping[str, Mapping[str, float]]:
        """Add this row's AGREEMENT signal to the recalled candidates, or
        return the recall untouched when no signal was supplied.

        Three properties, each of them a refusal rather than a default.

        NO SIGNAL, NO CHANGE. Without ``agreement_scores`` the recall is
        returned as the identical object, so the ranker sees byte-identical
        input and the legacy cross-dimension agreement term stays in force
        (``rails.kb_policy._rank_weighted_cosine_prior_agreement``).

        A MISSING ROW IS REFUSED, NEVER SCORED ZERO. A row the signal does not
        cover is a preparation defect -- its exemplar recall was never
        computed -- and scoring it 0.0 would quietly fly the comparator's
        ranking under the treatment's identity on that row. The 2026-09-26
        retrieval read found exactly this shape of silent ``.get()``/``continue``
        skip elsewhere; it is not reproduced here.

        ONLY RECALLED CANDIDATES ARE TOUCHED. A facet the recall did not admit
        gains no entry, because no downstream stage ranks an unrecalled facet
        (same read, section 2: an entry at or below zero cosine has no rank and
        no reweighting reaches it). Within a covered row, a recalled facet the
        table gives no share is a ZERO vote, which is a real measurement, and
        is recorded as ``0.0``.
        """

        if self._agreement_scores is None:
            return recall_scores
        sample_id = getattr(query_state, "query_sample_id", None)
        if not isinstance(sample_id, str) or sample_id not in self._agreement_scores:
            raise RailsError(
                "KbFacetProvider: the supplied agreement signal has no row for "
                f"query sample {sample_id!r}; a missing row is refused rather than "
                "scored 0.0"
            )
        row = self._agreement_scores[sample_id]
        return {
            facet_id: {
                **dim_scores,
                self._agreement_dimension: row.get(facet_id, 0.0),
            }
            for facet_id, dim_scores in recall_scores.items()
        }

    def candidates(self, query: object, *, k: int) -> Ranking:
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise RailsError("KbFacetProvider.candidates: k must be a positive int")
        snapshot: KnowledgeSnapshot = self._built_object()
        if isinstance(query, QueryState):
            query_state, query_vectors, query_segments = query, {}, None
        elif isinstance(query, Mapping):
            if "query_state" not in query:
                raise RailsError("KbFacetProvider.candidates: query mapping needs 'query_state'")
            query_state = query["query_state"]
            query_vectors = query.get("query_vectors", {})
            query_segments = query.get("query_segments")
            if query_segments is not None and query_vectors:
                raise RailsError(
                    "KbFacetProvider.candidates: query_vectors and query_segments are "
                    "mutually exclusive"
                )
        else:
            raise RailsError(
                "KbFacetProvider.candidates: query must be a QueryState or a mapping "
                "with 'query_state'/'query_vectors'"
            )
        if self._prepared_recall is None:
            if query_segments is None:
                recall_scores = multidim_recall(
                    snapshot, query_vectors, self._facet_vectors, self._top_k_per_dimension
                )
            else:
                recall_scores = multidim_segment_recall(
                    snapshot, query_segments, self._facet_vectors, self._top_k_per_dimension
                )
        else:
            sample_id = getattr(query_state, "query_sample_id", None)
            if not isinstance(sample_id, str) or sample_id not in self._prepared_recall:
                raise RailsError(
                    "KbFacetProvider: prepared recall lacks this query sample"
                )
            recall_scores = self._prepared_recall[sample_id]
        recall_scores = self._merge_agreement(query_state, recall_scores)
        rank_result = self._ranker(
            snapshot_sha256=self.snapshot_sha256(),
            query_state=query_state,
            recall_scores=recall_scores,
        )
        self._last_query_state = query_state
        self._last_recall_scores = recall_scores
        self._last_rank_result = rank_result
        entries = tuple(
            RankedEntry(entry_id=candidate.facet_id, score=candidate.score, provenance={})
            for candidate in rank_result.candidates[:k]
        )
        return Ranking(
            entries=entries,
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_state.content_hash(),
            source=self.provider_id,
        ).validate()

    def fuse(
        self, rankings: Sequence[Ranking], *, k: int, policy_id: str = FUSE_POLICY_ID
    ) -> FusionDecision:
        if not rankings:
            raise RailsError("KbFacetProvider.fuse requires at least one Ranking")
        if self._last_query_state is None or self._last_rank_result is None:
            raise RailsError("KbFacetProvider.fuse: call candidates() first")
        expected = self._last_query_state.content_hash()
        if any(ranking.query_sha256 != expected for ranking in rankings):
            raise RailsError(
                "KbFacetProvider.fuse: a ranking does not match the last candidates() call"
            )
        fuser = KNOWLEDGE_FUSERS.resolve(policy_id)(self._fuse_knobs)
        return fuser(
            snapshot=self._built_object(),
            snapshot_sha256=self.snapshot_sha256(),
            query_state=self._last_query_state,
            rank_result=self._last_rank_result,
            recall_scores=self._last_recall_scores,
        )

    def last_rank_result(self) -> object | None:
        """The ``RankResult`` this provider's most recent ``candidates()``
        call produced, or ``None`` before the first call. E6's traced-supply
        seam needs it: an ``acquire`` transition carries the RankResult AND
        the FusionDecision, and ``candidates()`` returns only the flattened
        :class:`Ranking` view."""

        return self._last_rank_result

    def materialize(self, selection: object, *, query_state: QueryState) -> SupplyPacket:
        snapshot: KnowledgeSnapshot = self._built_object()
        if isinstance(selection, FusionDecision):
            selected_ids = set(selection.selected_value_ids)
        elif isinstance(selection, Ranking):
            selected_ids = {entry.entry_id for entry in selection.entries}
        else:
            selected_ids = set(selection)
        visible_ids = set(query_state.retrieved_value_ids)
        if not selected_ids <= visible_ids:
            raise RailsError(
                "KbFacetProvider.materialize: selection is not visible in "
                "query_state.retrieved_value_ids -- update query_state's "
                "retrieved_value_ids to include the selection first (the same "
                "union rails.runner performs before it calls _supply_for_state)"
            )
        return _render_kb_supply_packet(snapshot, query_state)


# ---------------------------------------------------------------------------
# DenseCentroidProvider -- wraps rails.a2t_semantic_router
# ---------------------------------------------------------------------------

DENSE_CENTROID_FUSE_POLICY_ID = "saea-a2t-dense-centroid-rrf-v1"


class DenseCentroidProvider(KnowledgeProvider):
    """Wraps the Audio2Tool dense-centroid layer:
    ``rails.a2t_semantic_router.ToolTierSemanticIndex`` (built from caller-
    supplied construction rows + injected vectors -- never an embedding
    call) and ``rails.a2t_semantic_router.fuse_semantic_rankings`` (RRF over
    several complete rankings from the same frozen index).

    ``materialize`` is the fix this consolidation slice exists for: it
    renders the fused selection's tool names through
    ``rails.a2t_selected_tool_ground.SelectedToolDecisionGround.build`` and
    wraps the result in a real :class:`~.supply.SupplyPacket` (``prompt_block``
    = the card text ``SelectedToolDecisionGround.build`` renders) -- so
    Audio2Tool supply is finally visible to
    ``rails.knowledge.assert_knowledge_use_binding`` and to consumption
    tracing, instead of being injected as instruction text only the model
    could see.
    """

    def __init__(
        self,
        *,
        provider_id: str = "dense-centroid-v1",
        registry_tool_names: Sequence[str],
        decision_ground: SelectedToolDecisionGround,
        rrf_constant: int = RRF_CONSTANT,
    ) -> None:
        super().__init__(provider_id=provider_id)
        self._registry_tool_names = tuple(registry_tool_names)
        self._decision_ground = decision_ground
        self._rrf_constant = rrf_constant
        self._construction_rows: tuple[object, ...] = ()
        self._semantic_rankings_by_query_sha256: dict[str, SemanticRanking] = {}

    def build(self, source_rows: object, *, policy_id: str) -> ToolTierSemanticIndex:
        if isinstance(source_rows, Mapping):
            construction_rows = source_rows.get("construction_rows")
            vectors_by_unit_id = source_rows.get("vectors_by_unit_id")
        elif isinstance(source_rows, tuple) and len(source_rows) == 2:
            construction_rows, vectors_by_unit_id = source_rows
        else:
            raise RailsError(
                "DenseCentroidProvider.build: source_rows must be a mapping with "
                "'construction_rows'/'vectors_by_unit_id', or a "
                "(construction_rows, vectors_by_unit_id) pair"
            )
        if construction_rows is None or vectors_by_unit_id is None:
            raise RailsError(
                "DenseCentroidProvider.build: source_rows must supply both "
                "construction_rows and vectors_by_unit_id"
            )
        index = ToolTierSemanticIndex.build(
            construction_rows=tuple(construction_rows),
            vectors_by_unit_id=vectors_by_unit_id,
            registry_tool_names=self._registry_tool_names,
        )
        self._construction_rows = tuple(construction_rows)
        sample_ids = sorted(
            {sid for row in self._construction_rows for sid in row.sample_ids}
        )
        self._record_build(index, policy_id=policy_id, source_ids=tuple(sample_ids))
        self._semantic_rankings_by_query_sha256 = {}
        return index

    def _built_sample_ids(self) -> frozenset[str]:
        return frozenset(
            sid for row in self._construction_rows for sid in row.sample_ids
        )

    def snapshot_sha256(self) -> str:
        """``ToolTierSemanticIndex`` has no ``content_hash()`` of its own, but
        its ``index_sha256`` IS already exactly that -- a content-addressed
        hash of the frozen centroid matrix (``ToolTierSemanticIndex.build``'s
        own docstring) -- so this overrides the base's generic canonical-JSON
        fallback rather than reimplementing an equivalent hash under a
        different name."""

        index: ToolTierSemanticIndex = self._built_object()
        return index.index_sha256

    def _extra_receipt_fields(self) -> Mapping[str, object]:
        index: ToolTierSemanticIndex = self._built_object()
        return {"index_sha256": index.index_sha256}

    def candidates(self, query: object, *, k: int) -> Ranking:
        index: ToolTierSemanticIndex = self._built_object()
        query_vector = query.get("query_vector") if isinstance(query, Mapping) else query
        semantic_ranking = index.rank(query_vector, top_k=k)
        self._semantic_rankings_by_query_sha256[semantic_ranking.query_vector_sha256] = (
            semantic_ranking
        )
        entries = tuple(
            RankedEntry(
                entry_id=item.tool_name,
                score=(item.score if item.score is not None else 0.0),
                provenance={"rank": float(item.rank)},
            )
            for item in semantic_ranking.selected
        )
        return Ranking(
            entries=entries,
            index_sha256=semantic_ranking.index_sha256,
            query_sha256=semantic_ranking.query_vector_sha256,
            source=self.provider_id,
        ).validate()

    def fuse(
        self,
        rankings: Sequence[Ranking],
        *,
        k: int,
        policy_id: str = DENSE_CENTROID_FUSE_POLICY_ID,
    ) -> Ranking:
        if policy_id != DENSE_CENTROID_FUSE_POLICY_ID:
            raise RailsError(
                f"DenseCentroidProvider.fuse: unknown policy_id {policy_id!r}; only "
                f"{DENSE_CENTROID_FUSE_POLICY_ID!r} is implemented"
            )
        if not rankings:
            raise RailsError("DenseCentroidProvider.fuse requires at least one Ranking")
        semantic_rankings: list[SemanticRanking] = []
        source_names: list[str] = []
        for ranking in rankings:
            semantic = self._semantic_rankings_by_query_sha256.get(ranking.query_sha256)
            if semantic is None:
                raise RailsError(
                    "DenseCentroidProvider.fuse: a ranking was not produced by this "
                    "provider's own candidates()"
                )
            semantic_rankings.append(semantic)
            source_names.append(ranking.source)
        # Two rankings from the SAME provider instance carry duplicate
        # source names (e.g. two candidates() calls for two query variants);
        # fuse_semantic_rankings requires unique source_names, so disambiguate
        # deterministically by call order.
        if len(set(source_names)) != len(source_names):
            source_names = [f"{name}#{index}" for index, name in enumerate(source_names)]
        fused = fuse_semantic_rankings(
            semantic_rankings,
            top_k=k,
            source_names=tuple(source_names),
            constant=self._rrf_constant,
        )
        total = len(fused.selected_tool_names)
        entries = tuple(
            RankedEntry(
                entry_id=name,
                score=float(total - rank + 1),
                provenance={"rank": float(rank)},
            )
            for rank, name in enumerate(fused.selected_tool_names, start=1)
        )
        return Ranking(
            entries=entries,
            index_sha256=fused.index_sha256,
            query_sha256=fused.fusion_sha256,
            source=self.provider_id,
        ).validate()

    def materialize(self, selection: object, *, query_state: object) -> SupplyPacket:
        if isinstance(selection, Ranking):
            ordered = tuple((entry.entry_id, entry.score) for entry in selection.entries)
        else:
            ordered = tuple((name, 0.0) for name in selection)
        if not ordered:
            raise RailsError("DenseCentroidProvider.materialize: selection has no tools")
        selected_names = tuple(name for name, _score in ordered)
        packet = self._decision_ground.build(selected_names)
        # provenance = tool names + scores (module docstring): items carry
        # per-tool provenance (evidence_id=tool name, score encoded in text)
        # rather than literal prompt fragments -- the real prompt content is
        # the single combined card block below, which SelectedToolDecisionGround
        # renders as one unit, not per-tool substrings.
        items = tuple(
            SupplyItem(
                item_id=f"tool:{name}",
                text=f"{name} score={score:.6f}",
                evidence_id=name,
            )
            for name, score in ordered
        )
        return SupplyPacket(
            form=SupplyForm.TEXT,
            dose=SupplyDose(n_items=len(items), token_count=len(packet.text.split())),
            prompt_block=packet.text,
            assembly_template_id="a2t-selected-tool-decision-v1",
            items=items,
        ).validate()


# ---------------------------------------------------------------------------
# ConecContextProvider -- wraps core.evidence
# ---------------------------------------------------------------------------

CONEC_FUSE_POLICY_ID = "saea-conec-passthrough-v1"


class ConecContextProvider(KnowledgeProvider):
    """Wraps ``core.evidence``'s ``conec-contexts``/``conec-names``/
    ``conec-bias-list`` sources: this provider itself never opens a file --
    ``build`` freezes an index over EvidenceItems a caller already resolved
    (e.g. by calling ``core.base.EVIDENCE_SOURCES.resolve(evidence_source_id)``
    with a real lock/root/carrier, exactly as ``core.driver.run_experiment``
    does today) -- ``candidates`` returns a queried sample's own evidence as
    a one-entry-per-item :class:`Ranking`, optionally widened with a rotated
    OTHER sample's context as a negative control; ``materialize`` renders the
    selected items exactly as ``core.policies.build_arm_payload`` presents
    ``supplied_evidence`` (``core.model.transport``'s own
    ``f"[evidence {evidence_id}] {content}"`` line format).
    """

    def __init__(self, *, provider_id: str = "conec-context-v1", evidence_source_id: str) -> None:
        super().__init__(provider_id=provider_id)
        registered = EVIDENCE_SOURCES.names()
        if evidence_source_id not in registered:
            raise RailsError(
                f"ConecContextProvider: evidence_source_id {evidence_source_id!r} is not "
                f"registered in core.base.EVIDENCE_SOURCES ({registered})"
            )
        self._evidence_source_id = evidence_source_id
        self._items_by_sample_id: dict[str, tuple[EvidenceItem, ...]] = {}
        self._items_by_query_sha256: dict[str, tuple[EvidenceItem, ...]] = {}

    def build(
        self, source_rows: Mapping[str, Sequence[EvidenceItem]], *, policy_id: str
    ) -> Mapping[str, tuple[EvidenceItem, ...]]:
        if policy_id != self._evidence_source_id:
            raise RailsError(
                f"ConecContextProvider is bound to evidence_source_id "
                f"{self._evidence_source_id!r}, got policy_id={policy_id!r}"
            )
        if not isinstance(source_rows, Mapping) or not source_rows:
            raise RailsError(
                "ConecContextProvider.build: source_rows must be a non-empty mapping of "
                "sample_id -> EvidenceItem sequence"
            )
        items_by_sample_id: dict[str, tuple[EvidenceItem, ...]] = {}
        for sample_id, items in source_rows.items():
            validated = tuple(item.validate() for item in items)
            if not validated:
                raise RailsError(
                    f"ConecContextProvider.build: sample {sample_id!r} has no evidence items"
                )
            items_by_sample_id[sample_id] = validated
        self._items_by_sample_id = items_by_sample_id
        self._record_build(
            items_by_sample_id,
            policy_id=policy_id,
            source_ids=tuple(sorted(items_by_sample_id)),
        )
        self._items_by_query_sha256 = {}
        return items_by_sample_id

    def _built_sample_ids(self) -> frozenset[str]:
        return frozenset(self._built_object())

    def _canonical_view(self, built: object) -> Mapping[str, object]:
        items_by_sample_id: Mapping[str, Sequence[EvidenceItem]] = built
        return {
            sample_id: [item.runtime_view() for item in items]
            for sample_id, items in sorted(items_by_sample_id.items())
        }

    def _extra_receipt_fields(self) -> Mapping[str, object]:
        return {"evidence_source_id": self._evidence_source_id}

    def candidates(
        self, query: object, *, k: int, negative_control: bool = False
    ) -> Ranking:
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise RailsError("ConecContextProvider.candidates: k must be a positive int")
        items_by_sample_id: Mapping[str, tuple[EvidenceItem, ...]] = self._built_object()
        sample_id = query
        if sample_id not in items_by_sample_id:
            raise RailsError(f"ConecContextProvider.candidates: unknown sample_id {sample_id!r}")
        genuine_items = items_by_sample_id[sample_id]
        entries = [
            RankedEntry(entry_id=item.evidence_id, score=1.0, provenance={"negative_control": 0.0})
            for item in genuine_items
        ]
        combined_items = list(genuine_items)
        if negative_control:
            ordered_sample_ids = tuple(sorted(items_by_sample_id))
            if len(ordered_sample_ids) < 2:
                raise RailsError(
                    "ConecContextProvider.candidates: negative_control requires at least "
                    "2 built sample ids"
                )
            index = ordered_sample_ids.index(sample_id)
            rotated_sample_id = ordered_sample_ids[(index + 1) % len(ordered_sample_ids)]
            rotated_items = items_by_sample_id[rotated_sample_id]
            entries.extend(
                RankedEntry(
                    entry_id=f"negctrl:{item.evidence_id}",
                    score=0.0,
                    provenance={"negative_control": 1.0},
                )
                for item in rotated_items
            )
            combined_items.extend(rotated_items)
        entries.sort(key=lambda entry: (-entry.score, entry.entry_id))
        truncated = tuple(entries[:k])
        kept_ids = {entry.entry_id for entry in truncated}
        kept_items = tuple(
            item
            for item in combined_items
            if item.evidence_id in kept_ids or f"negctrl:{item.evidence_id}" in kept_ids
        )
        query_sha256 = content_hash({"sample_id": sample_id, "negative_control": negative_control})
        ranking = Ranking(
            entries=truncated,
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_sha256,
            source=self.provider_id,
        ).validate()
        self._items_by_query_sha256[query_sha256] = kept_items
        return ranking

    def fuse(
        self, rankings: Sequence[Ranking], *, k: int, policy_id: str = CONEC_FUSE_POLICY_ID
    ) -> Ranking:
        if policy_id != CONEC_FUSE_POLICY_ID:
            raise RailsError(
                f"ConecContextProvider.fuse: unknown policy_id {policy_id!r}; only "
                f"{CONEC_FUSE_POLICY_ID!r} is implemented"
            )
        if not rankings:
            raise RailsError("ConecContextProvider.fuse requires at least one Ranking")
        combined: dict[str, RankedEntry] = {}
        fused_items: list[EvidenceItem] = []
        seen_item_ids: set[str] = set()
        for ranking in rankings:
            items = self._items_by_query_sha256.get(ranking.query_sha256)
            if items is None:
                raise RailsError(
                    "ConecContextProvider.fuse: a ranking was not produced by this "
                    "provider's own candidates()"
                )
            for item in items:
                if item.evidence_id not in seen_item_ids:
                    seen_item_ids.add(item.evidence_id)
                    fused_items.append(item)
            for entry in ranking.entries:
                existing = combined.get(entry.entry_id)
                if existing is None or entry.score > existing.score:
                    combined[entry.entry_id] = entry
        ordered = tuple(
            sorted(combined.values(), key=lambda entry: (-entry.score, entry.entry_id))[:k]
        )
        kept_ids = {entry.entry_id for entry in ordered}
        kept_items = tuple(
            item
            for item in fused_items
            if item.evidence_id in kept_ids or f"negctrl:{item.evidence_id}" in kept_ids
        )
        query_sha256 = content_hash(
            {"fused_query_sha256s": sorted({ranking.query_sha256 for ranking in rankings})}
        )
        ranking = Ranking(
            entries=ordered,
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_sha256,
            source=self.provider_id,
        ).validate()
        self._items_by_query_sha256[query_sha256] = kept_items
        return ranking

    def materialize(self, selection: object, *, query_state: object) -> SupplyPacket:
        if isinstance(selection, Ranking):
            items = self._items_by_query_sha256.get(selection.query_sha256)
            if items is None:
                raise RailsError(
                    "ConecContextProvider.materialize: selection was not produced by "
                    "this provider's own candidates()/fuse()"
                )
        else:
            items = tuple(selection)
        if not items:
            raise RailsError("ConecContextProvider.materialize: selection has no evidence items")
        supply_items = tuple(
            SupplyItem(
                item_id=f"evidence:{item.evidence_id}",
                text=item.content,
                evidence_id=item.evidence_id,
            )
            for item in items
        )
        # core.model.transport's own line format
        # (f"[evidence {item['evidence_id']}] {item['content']}"), the exact
        # rendering core.policies.build_arm_payload's "supplied_evidence"
        # reaches the model through -- newline-joined here into one
        # prompt_block, mirroring rails.runner._supply_for_state's own
        # single-string convention for a multi-item packet.
        prompt_block = "\n".join(
            f"[evidence {item.evidence_id}] {item.content}" for item in items
        )
        return SupplyPacket(
            form=SupplyForm.TEXT,
            dose=SupplyDose(
                n_items=len(supply_items),
                token_count=sum(len(item.text.split()) for item in supply_items),
            ),
            prompt_block=prompt_block,
            assembly_template_id="conec-evidence-bundle-v1",
            items=supply_items,
        ).validate()


# ---------------------------------------------------------------------------
# SlurpIntentCandidateProvider -- wraps rails.slurp_intent_candidates (KU-S4N)
# ---------------------------------------------------------------------------

SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID = "saea-slurp-intent-candidate-passthrough-v1"

SLURP_INTENT_CANDIDATES_RANK_POLICY_ID = "saea-slurp-intent-candidate-bank-v1"


class SlurpIntentCandidateProvider(KnowledgeProvider):
    """Serves the KU-S4N narrowing view: this row's SEALED candidate set.

    The decision this provider returns was made BEFORE the flight, model-free,
    by ``scripts/slurp_kus4_prep.py``: the predicted scenario's legal intents
    led by the TRAIN prior, unioned with the row's speech-vector neighbours'
    distinct intents, capped at k (``rails.slurp_intent_candidates.
    compose_candidate_set``). It is delivered here as a sha256-pinned
    :class:`~.slurp_intent_candidates.CandidateBank` because a cosine over one
    vector file cannot express it -- the scenario half comes from the sealed
    comparator's own response, which is not a vector at all.

    That is exactly the case ``core.flight.FlightRuntime.
    bind_phase_supply_providers`` exists for: the provider id resolves in
    ``core.base.KNOWLEDGE_PROVIDERS`` like every other config-declared
    component, and the INSTANCE -- carrying the bank -- is injected by the
    flight runner, never by a launcher.

    ``candidates()`` does no retrieval: it looks this sample's ordered intents
    up in the bank and returns them as a :class:`Ranking` over the frozen
    snapshot's own facet ids, scored ``k, k-1, ... 1`` so the ranking's
    descending-score contract carries the offered ORDER. ``fuse()`` selects
    the matching value ids, in the same order. Nothing is dropped and nothing
    is re-scored: a filter here could only subtract from the mechanism the
    cell preregisters, which is "these k candidates, in this order" -- the
    same reasoning KU-S3's fragment states for tau 0.0.

    ``selection`` names which of the bank's two selections this instance
    serves -- ``"candidates"`` for KU-S4N, ``"twin_candidates"`` for its form
    twin. It rides the config hash through the fragment key that produced it,
    so an arm and its twin can never resolve to one cell identity.
    """

    def __init__(
        self,
        *,
        provider_id: str = "slurp-intent-candidates-v1",
        bank: object = None,
        selection: str = "candidates",
    ) -> None:
        super().__init__(provider_id=provider_id)
        from .slurp_intent_candidates import (  # noqa: PLC0415 (cycle guard)
            BANK_SELECTIONS,
            CandidateBank,
        )

        if not isinstance(bank, CandidateBank):
            raise RailsError(
                "SlurpIntentCandidateProvider needs a rails.slurp_intent_candidates."
                "CandidateBank; load it with load_candidate_bank() so the file's "
                "sha256 is verified before a single row is served"
            )
        if selection not in BANK_SELECTIONS:
            raise RailsError(
                "SlurpIntentCandidateProvider selection must be one of "
                f"{list(BANK_SELECTIONS)}, got {selection!r}"
            )
        self._bank = bank.validate()
        self._selection = selection
        self._rows = self._bank.selection(selection)
        self._last_query_state: QueryState | None = None
        self._last_rank_result: object | None = None

    @property
    def selection(self) -> str:
        return self._selection

    @property
    def bank_sha256(self) -> str:
        return self._bank.sha256

    def build(self, source_rows: object, *, policy_id: str) -> object:
        raise RailsError(
            "SlurpIntentCandidateProvider does not build: its snapshot is the frozen "
            "60-card artifact the flight already loaded and hash-verified, and its "
            "per-row decision is the sha256-pinned candidate bank. Use adopt()"
        )

    def _ordered_intents(self, sample_id: str) -> tuple[str, ...]:
        return tuple(self._rows.get(sample_id, ()))

    def candidates(self, query: object, *, k: int) -> Ranking:
        from .knowledge import RankedFacet, RankResult  # noqa: PLC0415 (cycle guard)
        from .slurp_intent_candidates import facet_id_for  # noqa: PLC0415 (cycle guard)

        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise RailsError(
                "SlurpIntentCandidateProvider.candidates: k must be a positive int"
            )
        snapshot: KnowledgeSnapshot = self._built_object()
        if isinstance(query, QueryState):
            query_state = query
        elif isinstance(query, Mapping) and "query_state" in query:
            query_state = query["query_state"]
        else:
            raise RailsError(
                "SlurpIntentCandidateProvider.candidates: query must be a QueryState or "
                "a mapping carrying 'query_state'"
            )
        if not isinstance(query_state, QueryState):
            raise RailsError(
                "SlurpIntentCandidateProvider.candidates: 'query_state' must be a "
                "QueryState"
            )
        known_facets = {facet.facet_id for facet in snapshot.facets}
        intents = self._ordered_intents(query_state.query_sample_id)[:k]
        unknown = [
            intent for intent in intents if facet_id_for(intent) not in known_facets
        ]
        if unknown:
            raise RailsError(
                f"the candidate bank offers intent(s) {sorted(unknown)} that the frozen "
                "candidate snapshot does not card; the bank and the snapshot were built "
                "from different label spaces"
            )
        ranked = tuple(
            RankedFacet(facet_id=facet_id_for(intent), score=float(len(intents) - index))
            for index, intent in enumerate(intents)
        )
        rank_result = RankResult(
            snapshot_sha256=self.snapshot_sha256(),
            query_state_sha256=query_state.content_hash(),
            ranking_policy_id=SLURP_INTENT_CANDIDATES_RANK_POLICY_ID,
            candidates=ranked,
        ).validate()
        self._last_query_state = query_state
        self._last_rank_result = rank_result
        return Ranking(
            entries=tuple(
                RankedEntry(
                    entry_id=candidate.facet_id, score=candidate.score, provenance={}
                )
                for candidate in ranked
            ),
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_state.content_hash(),
            source=self.provider_id,
        ).validate()

    def fuse(
        self,
        rankings: Sequence[Ranking],
        *,
        k: int,
        policy_id: str = SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID,
    ) -> FusionDecision:
        from .slurp_intent_candidates import (  # noqa: PLC0415 (cycle guard)
            FACET_ID_PREFIX,
            value_id_for,
        )

        if not rankings:
            raise RailsError("SlurpIntentCandidateProvider.fuse requires a Ranking")
        if self._last_query_state is None or self._last_rank_result is None:
            raise RailsError(
                "SlurpIntentCandidateProvider.fuse: call candidates() first"
            )
        expected = self._last_query_state.content_hash()
        if any(ranking.query_sha256 != expected for ranking in rankings):
            raise RailsError(
                "SlurpIntentCandidateProvider.fuse: a ranking does not match the last "
                "candidates() call"
            )
        facet_ids = tuple(entry.entry_id for entry in rankings[0].entries[:k])
        value_ids = tuple(
            value_id_for(facet_id[len(FACET_ID_PREFIX) :]) for facet_id in facet_ids
        )
        return FusionDecision(
            snapshot_sha256=self.snapshot_sha256(),
            query_state_sha256=expected,
            rank_result_sha256=self._last_rank_result.content_hash(),
            fusion_policy_id=SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID,
            supporting_facet_ids=facet_ids,
            selected_value_ids=value_ids,
        ).validate()

    def last_rank_result(self) -> object | None:
        """The ``RankResult`` the most recent ``candidates()`` produced; E6's
        traced-supply seam records it beside the ``FusionDecision``."""

        return self._last_rank_result

    def materialize(self, selection: object, *, query_state: QueryState) -> SupplyPacket:
        snapshot: KnowledgeSnapshot = self._built_object()
        if isinstance(selection, FusionDecision):
            selected_ids = set(selection.selected_value_ids)
        elif isinstance(selection, Ranking):
            selected_ids = {entry.entry_id for entry in selection.entries}
        else:
            selected_ids = set(selection)
        if not selected_ids <= set(query_state.retrieved_value_ids):
            raise RailsError(
                "SlurpIntentCandidateProvider.materialize: selection is not visible in "
                "query_state.retrieved_value_ids"
            )
        return _render_kb_supply_packet(snapshot, query_state)


# ---------------------------------------------------------------------------
# CandidateSemanticProvider -- candidate-conditioned released cards
# ---------------------------------------------------------------------------

SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID = "slurp-candidate-semantic-v1"
A2T_CANDIDATE_SEMANTIC_PROVIDER_ID = "audio2tool-candidate-semantic-v1"
SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID = (
    "saea-ranked-candidate-round-robin-v1"
)
SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID = (
    "saea-candidate-semantic-passthrough-v1"
)


def select_candidate_semantic_values(
    candidate_ids: Sequence[str],
    candidate_values: Mapping[str, Sequence[str]],
    *,
    max_values_per_candidate: int,
    max_total_values: int,
    already_selected_ids: Sequence[str] = (),
) -> tuple[tuple[str, ...], list[dict[str, object]]]:
    """Apply round-robin selection; optional visible IDs consume no new quota."""
    mapped = [candidate_values.get(candidate_id, ()) for candidate_id in candidate_ids]
    positions = [0 for _ in candidate_ids]
    selected_by = [[] for _ in candidate_ids]
    ignored_by: list[list[dict[str, str]]] = [[] for _ in candidate_ids]
    selected: list[str] = []
    selected_set: set[str] = set(already_selected_ids)

    while len(selected) < max_total_values:
        progressed = False
        for index, values in enumerate(mapped):
            if len(selected) >= max_total_values:
                break
            if len(selected_by[index]) >= max_values_per_candidate:
                continue
            while positions[index] < len(values):
                value_id = values[positions[index]]
                positions[index] += 1
                progressed = True
                if value_id in selected_set:
                    ignored_by[index].append(
                        {"value_id": value_id, "reason": "shared-value-already-selected"}
                    )
                    continue
                selected.append(value_id)
                selected_set.add(value_id)
                selected_by[index].append(value_id)
                break
        if not progressed:
            break
        if all(
            positions[index] >= len(values)
            or len(selected_by[index]) >= max_values_per_candidate
            for index, values in enumerate(mapped)
        ):
            break

    total_full = len(selected) >= max_total_values
    for index, values in enumerate(mapped):
        while positions[index] < len(values):
            value_id = values[positions[index]]
            positions[index] += 1
            if value_id in selected_set:
                reason = "shared-value-already-selected"
            elif len(selected_by[index]) >= max_values_per_candidate:
                reason = "per-candidate-limit"
            elif total_full:
                reason = "total-limit"
            else:  # defensive: the round-robin loop should have selected it
                reason = "not-selected"
            ignored_by[index].append({"value_id": value_id, "reason": reason})

    mappings = [
        {
            "candidate_id": candidate_id,
            "mapped_value_ids": list(mapped[index]),
            "selected_value_ids": list(selected_by[index]),
            "ignored_mappings": sorted(
                ignored_by[index], key=lambda item: (item["value_id"], item["reason"])
            ),
            "status": "mapped" if mapped[index] else "absent",
        }
        for index, candidate_id in enumerate(candidate_ids)
    ]
    return tuple(selected), mappings


class CandidateSemanticProvider(KnowledgeProvider):
    """Select released semantic values from a ranked hypothesis state.

    The provider reads only a source-bound ``AgentStateArtifact`` produced by
    the configured predecessor phase.  Its candidate-to-value index is built
    outside this class from the released authored source and cross-checked
    against the released snapshot.  Selection is deterministic: value IDs are
    sorted within each candidate, then visited round-robin in model rank order.
    A shared value is supplied once, under the first ranked candidate that
    reaches it.  Per-candidate and total caps are independent hard bounds.
    """

    MAX_CANDIDATES: int | None = None

    def __init__(
        self,
        *,
        candidate_values: Mapping[str, Sequence[str]],
        legal_candidate_ids: Sequence[str],
        max_candidates: int,
        max_values_per_candidate: int,
        max_total_values: int,
        compact_source_phase: str | None = None,
        projection_policy: str | None = None,
        fallback_candidates: Sequence[str] = (),
        fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION,
        provider_id: str = SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID,
    ) -> None:
        super().__init__(provider_id=provider_id)
        legal = frozenset(legal_candidate_ids)
        if not legal or any(not isinstance(item, str) or not item for item in legal):
            raise RailsError(
                "CandidateSemanticProvider needs a non-empty legal candidate inventory"
            )
        if fallback_candidates and provider_id != SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID:
            raise RailsError(
                "fallback_candidates is a SLURP-only option"
            )
        try:
            fallback_ids = validate_fallback_candidate_ids(
                fallback_candidates, legal_intent_ids=legal,
            )
            fallback_text = (
                validate_fallback_distinction(fallback_distinction)
                if fallback_ids
                else fallback_distinction
            )
        except SlurpIntentHypothesisError as error:
            raise RailsError(str(error)) from error
        for field, value, maximum in (
            ("max_candidates", max_candidates, self.MAX_CANDIDATES),
            ("max_values_per_candidate", max_values_per_candidate, None),
            ("max_total_values", max_total_values, None),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 1
                or (maximum is not None and value > maximum)
            ):
                suffix = f" and at most {maximum}" if maximum is not None else ""
                raise RailsError(f"{field} must be a positive integer{suffix}")
        self._validate_candidate_capacity(
            max_candidates=max_candidates,
            legal_candidate_count=len(legal),
        )
        if max_total_values > max_candidates * max_values_per_candidate:
            raise RailsError(
                "max_total_values cannot exceed max_candidates times "
                "max_values_per_candidate"
            )
        index: dict[str, tuple[str, ...]] = {}
        for candidate_id, raw_values in candidate_values.items():
            if candidate_id not in legal:
                raise RailsError(
                    f"candidate index ID {candidate_id!r} is outside the legal inventory"
                )
            if isinstance(raw_values, (str, bytes)) or not isinstance(
                raw_values, Sequence
            ):
                raise RailsError("candidate index values must be a sequence")
            values = tuple(sorted(raw_values))
            if any(not isinstance(item, str) or not item for item in values):
                raise RailsError("candidate index value IDs must be non-empty strings")
            if len(values) != len(set(values)):
                raise RailsError("candidate index contains a duplicate value ID")
            index[candidate_id] = values
        self._candidate_values = index
        self._legal_candidate_ids = legal
        self._max_candidates = max_candidates
        self._max_values_per_candidate = max_values_per_candidate
        self._max_total_values = max_total_values
        self._compact_source_phase = compact_source_phase
        self._projection_policy = projection_policy
        self._fallback_candidates = fallback_ids
        self._fallback_distinction = fallback_text
        self._last_query_state: QueryState | None = None
        self._last_rank_result: object | None = None
        self._last_selected_value_ids: tuple[str, ...] = ()
        self._last_selection_audit: Mapping[str, object] | None = None
        self._last_proposal_expected_k: int | None = None

    def _validate_candidate_capacity(
        self, *, max_candidates: int, legal_candidate_count: int
    ) -> None:
        """Validate provider-specific candidate capacity semantics."""

    def build(self, source_rows: object, *, policy_id: str) -> object:
        raise RailsError(
            "CandidateSemanticProvider does not build at runtime; load and "
            "verify the released named store, then use adopt()"
        )

    def adopt(
        self,
        built: object,
        *,
        policy_id: str,
        source_ids: Sequence[str] = (),
        snapshot_sha256: str | None = None,
    ) -> "CandidateSemanticProvider":
        super().adopt(
            built,
            policy_id=policy_id,
            source_ids=source_ids,
            snapshot_sha256=snapshot_sha256,
        )
        snapshot = self._built_object()
        if not isinstance(snapshot, KnowledgeSnapshot):
            raise RailsError("candidate semantic provider requires a KnowledgeSnapshot")
        facet_ids = {facet.facet_id for facet in snapshot.facets}
        value_by_id = {value.value_id: value for value in snapshot.values}
        indexed = {value_id for values in self._candidate_values.values() for value_id in values}
        unknown = indexed - set(value_by_id)
        if unknown:
            raise RailsError(
                "candidate semantic index cites values outside the released snapshot: "
                f"{sorted(unknown)[:5]}"
            )
        for value_id in indexed:
            self._validate_value_facets(value_by_id[value_id], facet_ids)
        self._value_facets = {
            value_id: value.associated_facet_ids
            for value_id, value in value_by_id.items()
        }
        return self

    def _validate_value_facets(self, value: object, facet_ids: set[str]) -> None:
        if not value.associated_facet_ids or not set(value.associated_facet_ids) <= facet_ids:
            raise RailsError("candidate semantic value has invalid released facet associations")

    def supporting_facet_ids(self, value_ids: Sequence[str]) -> tuple[str, ...]:
        """Follow actual released value-to-facet links in first-occurrence order."""
        result: dict[str, None] = {}
        for value_id in value_ids:
            if value_id not in self._value_facets:
                raise RailsError("candidate semantic selection cites an unknown value")
            for facet_id in self._value_facets[value_id]:
                result.setdefault(facet_id, None)
        return tuple(result)

    def _candidate_state(
        self, artifact: AgentStateArtifact, *, sample_id: str
    ) -> tuple[tuple[str, ...], dict[str, object]]:
        raise NotImplementedError("a carrier must parse its source-bound candidate state")

    def _candidate_bounds(self) -> dict[str, int]:
        return {"max_candidates": self._max_candidates}

    def _built_sample_ids(self) -> frozenset[str]:
        snapshot: KnowledgeSnapshot = self._built_object()
        return frozenset(snapshot.source_sample_ids)

    def _select(self, candidate_ids: tuple[str, ...]) -> tuple[tuple[str, ...], list[dict[str, object]]]:
        return select_candidate_semantic_values(
            candidate_ids,
            self._candidate_values,
            max_values_per_candidate=self._max_values_per_candidate,
            max_total_values=self._max_total_values,
        )

    def candidates(self, query: object, *, k: int) -> Ranking:
        from .knowledge import RankedFacet, RankResult  # noqa: PLC0415
        if not isinstance(query, Mapping):
            raise RailsError("candidate semantic query must be a mapping")
        proposal_requested = (
            "candidate_proposal" in query
            or "candidate_proposal_added_value_cap" in query
        )
        added_cap = 0
        if proposal_requested:
            from .slurp_candidate_proposal import CandidateProposal  # noqa: PLC0415

            proposal = query.get("candidate_proposal")
            added_cap = query.get("candidate_proposal_added_value_cap")
            if self.provider_id != SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID:
                raise RailsError("candidate proposals are supported only for SLURP")
            if self._fallback_candidates:
                raise RailsError("candidate proposal cannot combine with standing fallback")
            if not isinstance(proposal, CandidateProposal):
                raise RailsError("candidate_proposal must be a source-bound CandidateProposal")
            if (
                isinstance(added_cap, bool) or not isinstance(added_cap, int)
                or not 1 <= added_cap <= 32 * self._max_values_per_candidate
            ):
                raise RailsError("proposal added-value cap must be a bounded positive integer")
        expected_k = self._max_total_values + added_cap
        if k != expected_k:
            raise RailsError(
                "CandidateSemanticProvider.candidates k must equal the baseline "
                "max_total_values plus the proposal added-value cap"
            )
        query_state = query.get("query_state")
        artifact = query.get("candidate_state")
        sample_id = query.get("sample_id")
        if not isinstance(query_state, QueryState):
            raise RailsError("candidate semantic query needs a QueryState")
        if not isinstance(artifact, AgentStateArtifact):
            raise RailsError("candidate semantic query needs an AgentStateArtifact")
        if sample_id != query_state.query_sample_id:
            raise RailsError("candidate semantic query sample identity mismatch")
        candidate_ids, state_audit = self._candidate_state(artifact, sample_id=str(sample_id))
        selected, mappings = self._select(candidate_ids)
        proposal_audit: dict[str, object] = {}
        if proposal_requested:
            proposal = query["candidate_proposal"]
            original_ids = proposal.original_candidate_ids
            proposed_ids = proposal.candidate_ids
            added_ids = tuple(item.intent_id for item in proposal.additions)
            if (
                proposal.sample_id != sample_id
                or proposal.original_state_id != artifact.state_id
                or proposal.original_state_sha256 != artifact.content_hash()
                or proposal.original_response_sha256 != artifact.source_response_sha256
                or proposal.original_query_state_sha256 != artifact.source_query_state_sha256
                or original_ids != candidate_ids
                or proposed_ids != original_ids + added_ids
                or len(proposed_ids) > proposal.max_candidates
                or len(proposed_ids) > 32
                or len(proposed_ids) != len(set(proposed_ids))
                or not set(proposed_ids) <= self._legal_candidate_ids
            ):
                raise RailsError("candidate proposal differs from its sealed Perception source")
            support = {
                item.value_id: item.task_target for item in proposal.selected_exemplars
            }
            if len(support) != len(proposal.selected_exemplars) or any(
                not addition.supporting_exemplar_value_ids
                or any(support.get(value_id) != addition.intent_id
                       for value_id in addition.supporting_exemplar_value_ids)
                for addition in proposal.additions
            ):
                raise RailsError("candidate proposal additions lack matching exemplar support")
            extra, extra_mappings = select_candidate_semantic_values(
                added_ids, self._candidate_values,
                max_values_per_candidate=self._max_values_per_candidate,
                max_total_values=added_cap,
                already_selected_ids=selected,
            )
            proposal_audit = {
                "candidate_proposal_sha256": proposal.content_hash(),
                "candidate_proposal_original_ids": list(original_ids),
                "candidate_proposal_baseline_value_ids": list(selected),
                "candidate_proposal_added_value_ids": list(extra),
                "candidate_proposal_added_value_cap": added_cap,
            }
            candidate_ids = proposed_ids
            selected = selected + extra
            mappings = mappings + extra_mappings
        supporting_facets = self.supporting_facet_ids(selected)
        ranked = tuple(
            RankedFacet(facet_id=facet_id, score=float(len(supporting_facets) - index))
            for index, facet_id in enumerate(supporting_facets)
        )
        rank_result = RankResult(
            snapshot_sha256=self.snapshot_sha256(),
            query_state_sha256=query_state.content_hash(),
            ranking_policy_id=SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
            candidates=ranked,
        ).validate()
        candidate_state_sha256 = hashlib.sha256(artifact.content.encode("utf-8")).hexdigest()
        audit: dict[str, object] = {
            "schema": "saea-candidate-semantic-selection-v1",
            "snapshot_sha256": self.snapshot_sha256(),
            "sample_id": str(sample_id),
            "candidate_state_id": artifact.state_id,
            "candidate_state_sha256": candidate_state_sha256,
            "candidate_source_response_sha256": artifact.source_response_sha256,
            "candidate_ids": list(candidate_ids),
            "legal_candidate_inventory_sha256": content_hash(
                {"candidate_ids": sorted(self._legal_candidate_ids)}
            ),
            "selection_policy_id": SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
            **self._candidate_bounds(),
            "max_values_per_candidate": self._max_values_per_candidate,
            "max_total_values": self._max_total_values,
            "mappings": mappings,
            "selected_value_ids": list(selected),
        }
        if self._compact_source_phase is not None:
            audit["compact_source_phase"] = self._compact_source_phase
        audit.update(state_audit)
        audit.update(proposal_audit)
        audit["selection_sha256"] = content_hash(audit)
        self._last_query_state = query_state
        self._last_proposal_expected_k = expected_k if proposal_requested else None
        self._last_rank_result = rank_result
        self._last_selected_value_ids = selected
        self._last_selection_audit = audit
        return Ranking(
            entries=tuple(
                RankedEntry(entry_id=item.facet_id, score=item.score, provenance={})
                for item in ranked
            ),
            index_sha256=self.snapshot_sha256(),
            query_sha256=query_state.content_hash(),
            source=self.provider_id,
        ).validate()

    def fuse(
        self,
        rankings: Sequence[Ranking],
        *,
        k: int,
        policy_id: str = SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    ) -> FusionDecision:
        if policy_id != SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID:
            raise RailsError(f"unsupported candidate semantic fuse policy {policy_id!r}")
        if len(rankings) != 1 or self._last_query_state is None or self._last_rank_result is None:
            raise RailsError("candidate semantic fuse requires its one candidates() ranking")
        ranking = rankings[0].validate()
        expected = self._last_query_state.content_hash()
        if ranking.query_sha256 != expected or ranking.index_sha256 != self.snapshot_sha256():
            raise RailsError("candidate semantic ranking has a changed source binding")
        if self._last_proposal_expected_k is not None and k != self._last_proposal_expected_k:
            raise RailsError("candidate proposal fuse k must equal its total selection budget")
        selected = self._last_selected_value_ids[:k]
        return FusionDecision(
            snapshot_sha256=self.snapshot_sha256(),
            query_state_sha256=expected,
            rank_result_sha256=self._last_rank_result.content_hash(),
            fusion_policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
            supporting_facet_ids=self.supporting_facet_ids(selected),
            selected_value_ids=selected,
        ).validate()

    def last_rank_result(self) -> object | None:
        return self._last_rank_result

    def last_selection_audit(self) -> Mapping[str, object] | None:
        return self._last_selection_audit

    def materialize(self, selection: object, *, query_state: QueryState) -> SupplyPacket:
        snapshot: KnowledgeSnapshot = self._built_object()
        selected_ids = (
            set(selection.selected_value_ids)
            if isinstance(selection, FusionDecision)
            else set(selection)
        )
        if not selected_ids <= set(query_state.retrieved_value_ids):
            raise RailsError(
                "candidate semantic selection must be visible before materialization"
            )
        return _render_kb_supply_packet(snapshot, query_state)


class SlurpCandidateSemanticProvider(CandidateSemanticProvider):
    """Retain the original SLURP candidate and same-ID authored-card contract.

    FIX-1 standing fallback (docs/results/2026-09-17-slurp-a3-coverage-
    confusion-audit-v1.md, `perception.fill_params.fallback_candidates`
    mirrored here as ``candidate_supply.<phase>.fallback_candidates`):
    :meth:`_candidate_state` appends every configured fallback id the
    Perception response's own projected candidates omit, LAST, so it is
    visited last by the round-robin in :func:`select_candidate_semantic_values`
    and only within the existing ``max_values_per_candidate`` /
    ``max_total_values`` caps -- it never receives special capacity.

    Measured against the pinned authored slot-contract source (SHA-256
    34f6c3dc192eca4a30ef7208d10c1e2b797a0ae2ffe5122f16b376e10a30e4c5,
    ``prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/authored-slot-contracts-v1.json``),
    ``general_quirky`` binds 16 of the 54 released slot rows (artist_name,
    business_type, date, device_type, drink_type, event_name, food_type,
    meal_type, media_type, movie_name, news_topic, person, place_name,
    relation, time, timeofday) -- NOT the "few or none" a priori guess, and
    exactly at the anchor's own ``max_values_per_candidate`` bound of 16.
    Under the round-robin's per-round one-value-per-candidate interleave, its
    actual per-row selected count is bounded by ``max_total_values`` (28)
    divided across however many candidates are simultaneously active that
    row -- roughly a quarter of 28 when the model itself proposed three
    distinct candidates and the fallback was absent from them, more if the
    model proposed fewer distinct ids.
    """

    def _validate_candidate_capacity(
        self, *, max_candidates: int, legal_candidate_count: int
    ) -> None:
        if max_candidates > legal_candidate_count:
            raise RailsError(
                "max_candidates cannot exceed the legal candidate inventory"
            )

    def _validate_value_facets(self, value: object, facet_ids: set[str]) -> None:
        if value.value_id not in facet_ids or value.associated_facet_ids != (value.value_id,):
            raise RailsError(
                "candidate semantic values must retain their same-ID released facet"
            )

    def _candidate_bounds(self) -> dict[str, object]:
        bounds: dict[str, object] = dict(super()._candidate_bounds())
        if self._fallback_candidates:
            bounds["fallback_candidates"] = list(self._fallback_candidates)
        return bounds

    def _candidate_state(
        self, artifact: AgentStateArtifact, *, sample_id: str
    ) -> tuple[tuple[str, ...], dict[str, object]]:
        from dataclasses import asdict  # noqa: PLC0415

        from .slurp_intent_hypotheses import (  # noqa: PLC0415
            append_fallback_slurp_intent_hypothesis_candidates,
            parse_slurp_intent_hypothesis_state,
        )

        state = parse_slurp_intent_hypothesis_state(
            artifact,
            expected_sample_id=sample_id,
            legal_intent_ids=self._legal_candidate_ids,
            max_candidates=self._max_candidates,
            compact_source_phase=self._compact_source_phase,
            projection_policy=self._projection_policy,
        )
        audit = {}
        if state.projection is not None:
            audit["candidate_projection"] = asdict(state.projection)
        if not self._fallback_candidates:
            # Unconfigured: byte/shape-identical to before this option existed.
            return tuple(item.intent_id for item in state.candidates), audit
        candidates = append_fallback_slurp_intent_hypothesis_candidates(
            state.candidates,
            fallback_candidates=self._fallback_candidates,
            fallback_distinction=self._fallback_distinction,
            legal_intent_ids=self._legal_candidate_ids,
        )
        # Coverage must never silently merge the fallback into "what the
        # model proposed": record both id lists and each retained
        # candidate's source so a downstream coverage diagnostic can report
        # gold-in-candidates WITH and WITHOUT the fallback separately.
        audit["candidate_ids_without_fallback"] = tuple(
            item.intent_id for item in state.candidates
        )
        audit["candidate_sources"] = {
            candidate.intent_id: candidate.source for candidate in candidates
        }
        return tuple(candidate.intent_id for candidate in candidates), audit


class Audio2ToolCandidateSemanticProvider(CandidateSemanticProvider):
    """Deliver parameter explanations for ordered action alternatives."""

    def __init__(
        self, *, candidate_values: Mapping[str, Sequence[str]],
        legal_candidate_ids: Sequence[str], max_actions: int,
        max_candidates_per_action: int, max_values_per_candidate: int,
        max_total_values: int, compact_source_phase: str,
    ) -> None:
        for name, bound in (
            ("max_actions", max_actions),
            ("max_candidates_per_action", max_candidates_per_action),
        ):
            if isinstance(bound, bool) or not isinstance(bound, int) or bound < 1:
                raise RailsError(f"{name} must be a positive integer")
        if (
            not isinstance(compact_source_phase, str) or not compact_source_phase
            or ":" in compact_source_phase
            or any(char.isspace() for char in compact_source_phase)
        ):
            raise RailsError("Audio2Tool candidate state needs an explicit source phase")
        self._max_actions = max_actions
        self._max_candidates_per_action = max_candidates_per_action
        super().__init__(
            candidate_values=candidate_values, legal_candidate_ids=legal_candidate_ids,
            max_candidates=max_actions * max_candidates_per_action,
            max_values_per_candidate=max_values_per_candidate,
            max_total_values=max_total_values, compact_source_phase=compact_source_phase,
            provider_id=A2T_CANDIDATE_SEMANTIC_PROVIDER_ID,
        )

    def _candidate_bounds(self) -> dict[str, int]:
        return {
            "max_actions": self._max_actions,
            "max_candidates_per_action": self._max_candidates_per_action,
        }

    def _candidate_state(
        self, artifact: AgentStateArtifact, *, sample_id: str
    ) -> tuple[tuple[str, ...], dict[str, object]]:
        from .a2t_perception_state import parse_audio2tool_perception_state  # noqa: PLC0415

        artifact.validate()
        phase = self._compact_source_phase
        expected_id = f"{phase}:{sample_id}"
        if artifact.state_kind != f"phase:{phase}" or not (
            artifact.state_id == expected_id or artifact.state_id.endswith(":" + expected_id)
        ):
            raise RailsError("Audio2Tool candidate state phase or sample identity mismatch")
        if hashlib.sha256(artifact.content.encode("utf-8")).hexdigest() != artifact.source_response_sha256:
            raise RailsError("Audio2Tool candidate state content differs from its source response")
        state = parse_audio2tool_perception_state(
            artifact.content, legal_tool_names=tuple(self._legal_candidate_ids),
            max_actions=self._max_actions,
            max_candidates_per_action=self._max_candidates_per_action,
        )
        return state.unique_tool_names, {
            "candidate_occurrences": [
                {"action_id": action.action_id, "candidate_tools": list(action.candidate_tools)}
                for action in state.actions
            ]
        }


# ---------------------------------------------------------------------------
# KNOWLEDGE_PROVIDERS -- registrations into the shared core.base registry
# ---------------------------------------------------------------------------
#
# E6 (2026-09-06): the registry OBJECT now lives in ``core.base`` beside
# ``KNOWLEDGE_BUILDERS``/``KNOWLEDGE_RANKERS``/``KNOWLEDGE_FUSERS`` (the
# residual this module's docstring named), because a baseline fragment's
# ``phase_supply.provider`` has to resolve in a ``core.base`` registry like
# every other config-declared component id. The name below is a plain
# re-export, so every pre-existing importer of
# ``rails.knowledge_provider.KNOWLEDGE_PROVIDERS`` is byte-unaffected. The
# ``register`` calls stay HERE, where the provider classes are, and this
# file is named in ``scripts/checks/engineering_base_check.py``'s canonical
# registration-site list for exactly that reason.

KNOWLEDGE_PROVIDERS = _CORE_KNOWLEDGE_PROVIDERS
if "kb-facet-v1" not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register("kb-facet-v1", KbFacetProvider)
if "dense-centroid-v1" not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register("dense-centroid-v1", DenseCentroidProvider)
if "conec-context-v1" not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register("conec-context-v1", ConecContextProvider)
# KU-S4N (2026-09-09): the SLURP intent-narrowing view. Registered here,
# beside its class, for the same reason the three above are -- this file is
# the canonical population site scripts/checks/engineering_base_check.py
# reads without importing the package.
if "slurp-intent-candidates-v1" not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register(
        "slurp-intent-candidates-v1", SlurpIntentCandidateProvider
    )
if SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register(
        "slurp-candidate-semantic-v1", SlurpCandidateSemanticProvider
    )


if A2T_CANDIDATE_SEMANTIC_PROVIDER_ID not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register(
        "audio2tool-candidate-semantic-v1", Audio2ToolCandidateSemanticProvider
    )


def _candidate_semantic_policy_is_not_callable(_knobs: object = None) -> object:
    raise RailsError(
        "candidate semantic rank/fuse policy IDs name the deterministic decision "
        "inside CandidateSemanticProvider; no independent callable exists"
    )


if SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID not in KNOWLEDGE_RANKERS.names():
    KNOWLEDGE_RANKERS.register(
        "saea-ranked-candidate-round-robin-v1",
        _candidate_semantic_policy_is_not_callable,
    )
if SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID not in KNOWLEDGE_FUSERS.names():
    KNOWLEDGE_FUSERS.register(
        "saea-candidate-semantic-passthrough-v1",
        _candidate_semantic_policy_is_not_callable,
    )


def _slurp_intent_candidate_policy_is_not_callable(_knobs: object = None) -> object:
    """The two KU-S4N policy ids RESOLVE, and every use REFUSES.

    ``rails.phase_supply.PhaseSupplySpec.validate`` requires a fragment's
    ``rank_policy`` and ``fuse_policy`` to resolve in a ``core.base``
    registry, and rightly so -- a cell's component ids are part of what it IS.
    But :class:`SlurpIntentCandidateProvider` runs neither a ranker nor a
    fuser: its ranking IS the sealed bank's order and its fusion IS that order
    carried onto the value ids, both computed model-free before the flight.

    Borrowing ``saea-rank-wcos-prior-agree-v1`` to satisfy the validator would
    put a cosine ranker's name on a cell that never runs one, and the name
    rides the config hash. So the two ids the provider actually applies are
    registered instead, and constructing either raises -- the same "the name
    accounts for it, every use refuses" discipline
    ``core.frozen_historical`` already established for the retired Audio2Tool
    controller ids.
    """

    raise RailsError(
        "the KU-S4N rank/fuse policy ids name a decision SlurpIntentCandidateProvider "
        "makes from its sealed candidate bank; there is no ranker or fuser callable "
        "behind them and nothing should try to construct one"
    )


if SLURP_INTENT_CANDIDATES_RANK_POLICY_ID not in KNOWLEDGE_RANKERS.names():
    KNOWLEDGE_RANKERS.register(
        SLURP_INTENT_CANDIDATES_RANK_POLICY_ID,
        _slurp_intent_candidate_policy_is_not_callable,
    )
if SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID not in KNOWLEDGE_FUSERS.names():
    KNOWLEDGE_FUSERS.register(
        SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID,
        _slurp_intent_candidate_policy_is_not_callable,
    )



def _source_scoped_context_provider(**kwargs):
    from .governed_context_supply import SourceScopedContextProvider

    return SourceScopedContextProvider(**kwargs)


def _source_scoped_context_rank(knobs=None):
    from .governed_context_supply import _source_scoped_rank

    return _source_scoped_rank(knobs)


def _source_scoped_context_fuse(knobs=None):
    from .governed_context_supply import _source_scoped_fuse

    return _source_scoped_fuse(knobs)


def _named_context_rank(knobs=None):
    from .knowledge_stores import _composite_context_rank

    return _composite_context_rank(knobs)


def _named_context_fuse(knobs=None):
    from .knowledge_stores import _composite_context_fuse

    return _composite_context_fuse(knobs)


class Stage3DeltaCandidateProvider(KnowledgeProvider):
    """Stage-3 S3-6: the stage3-deltas store's candidate-bound,
    ``prior_score``-capped selector (``rails.stage3_delta_supply.
    select_stage3_delta_values`` does the actual selection; this class is
    the thin ``KnowledgeProvider`` wrapper the shared registry, and this
    check's registered-name discipline, both require).

    S3-6w (2026-09-22) wired this into a live flight:
    ``rails.knowledge_stores.build_knowledge_store_supply``'s
    ``context_supply`` dispatcher recognises a ``store_role: "stage3-deltas"``
    store declaring ``{"provider": "stage3-delta-candidate-bound-v1",
    "candidate_state_phase", "cap", "rank_by": "prior_score"}`` and routes
    the Solver phase through this class: it reads the row's Perception
    candidate intents off the configured ``candidate_state_phase`` state,
    then selects and caps deltas by ``prior_score`` -- see the router's
    ``_stage3_delta_local_supply`` closure and
    ``tests/unit/test_stage3_delta_supply_router.py``. What remains PENDING
    is only the store's own release (S3-5) and a root admission decision --
    the wiring itself is complete and tested.
    """

    def __init__(
        self,
        *,
        provider_id: str = STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        node_target: str | None = None,
    ) -> None:
        super().__init__(provider_id=provider_id)
        # S3-4s: which node's slice this instance serves. ``None`` -- the
        # default and every pre-S3-4s construction -- applies no node filter.
        self.node_target = node_target

    def build(self, source_rows: Sequence[Mapping[str, object]], *, policy_id: str) -> tuple[DeltaCandidate, ...]:
        candidates = tuple(
            DeltaCandidate(
                value_id=row["value_id"],
                associated_facet_ids=tuple(row["associated_facet_ids"]),
                prior_score=float(row["prior_score"]),
                # S3-4s: a v2 row's ``task_target`` is NODE:DELTA-KIND:TARGET,
                # so the node is read off the released value itself rather
                # than carried beside it. A v1 row names no node and reads
                # ``None``, which is exactly what keeps an unfiltered
                # selection byte-identical to its pre-S3-4s self.
                node_target=node_target_of_task_target(row.get("task_target")),
            ).validate()
            for row in source_rows
        )
        self._record_build(
            candidates, policy_id=policy_id, source_ids=tuple(c.value_id for c in candidates)
        )
        self._index_sha256 = hashlib.sha256(
            "\n".join(sorted(c.value_id for c in candidates)).encode("utf-8")
        ).hexdigest()
        return candidates

    def candidates(self, query: Sequence[str], *, k: int) -> Ranking:
        if self._built is None:
            raise RailsError("Stage3DeltaCandidateProvider.candidates requires build() first")
        facet_ids = tuple(query)
        selected_ids = select_stage3_delta_values(
            facet_ids, self._built, cap=k, node_target=self.node_target
        )
        by_id = {candidate.value_id: candidate for candidate in self._built}
        entries = tuple(
            RankedEntry(entry_id=value_id, score=by_id[value_id].prior_score, provenance={})
            for value_id in selected_ids
        )
        query_sha256 = hashlib.sha256(
            "\n".join(sorted(facet_ids)).encode("utf-8")
        ).hexdigest()
        return Ranking(
            entries=entries,
            index_sha256=self._index_sha256,
            query_sha256=query_sha256,
            source=self.provider_id,
        ).validate()

    def fuse(self, rankings: Sequence[Ranking], *, k: int, policy_id: str) -> Ranking:
        merged: dict[str, RankedEntry] = {}
        for ranking in rankings:
            for entry in ranking.entries:
                existing = merged.get(entry.entry_id)
                if existing is None or entry.score > existing.score:
                    merged[entry.entry_id] = entry
        ordered = sorted(merged.values(), key=lambda entry: (-entry.score, entry.entry_id))[:k]
        base = rankings[0] if rankings else None
        return Ranking(
            entries=tuple(ordered),
            index_sha256=base.index_sha256 if base is not None else getattr(self, "_index_sha256", "0" * 64),
            query_sha256=base.query_sha256 if base is not None else "0" * 64,
            source=self.provider_id,
        ).validate()


def _stage3_delta_candidate_provider(**kwargs: object) -> Stage3DeltaCandidateProvider:
    return Stage3DeltaCandidateProvider(**kwargs)


class Stage3DeltaUnconditionalProvider(Stage3DeltaCandidateProvider):
    """Stage-3 S3-4s: the stage3-deltas store's UNCONDITIONAL, node-filtered,
    ``prior_score``-capped selector.

    The Perception node produces the candidate list, so at the moment it is
    contacted there is no candidate state to bind its deltas against. Its
    route is therefore row-independent: the top ``cap`` deltas whose
    ``node_target`` is the configured node, identical on every row of the
    split (``rails.stage3_delta_supply.
    select_unconditional_stage3_delta_values``). ``query`` is accepted and
    DELIBERATELY IGNORED -- it is recorded in the ranking's ``query_sha256``
    so the receipt still says what the row's state was, and it never changes
    which deltas are selected.
    """

    def __init__(
        self,
        *,
        provider_id: str = STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
        node_target: str = "perception",
    ) -> None:
        super().__init__(provider_id=provider_id, node_target=node_target)

    def candidates(self, query: Sequence[str], *, k: int) -> Ranking:
        if self._built is None:
            raise RailsError(
                "Stage3DeltaUnconditionalProvider.candidates requires build() first"
            )
        facet_ids = tuple(query)
        selected_ids = select_unconditional_stage3_delta_values(
            self._built, cap=k, node_target=str(self.node_target)
        )
        by_id = {candidate.value_id: candidate for candidate in self._built}
        entries = tuple(
            RankedEntry(entry_id=value_id, score=by_id[value_id].prior_score, provenance={})
            for value_id in selected_ids
        )
        query_sha256 = hashlib.sha256(
            "\n".join(sorted(facet_ids)).encode("utf-8")
        ).hexdigest()
        return Ranking(
            entries=entries,
            index_sha256=self._index_sha256,
            query_sha256=query_sha256,
            source=self.provider_id,
        ).validate()


def _stage3_delta_unconditional_provider(**kwargs: object) -> Stage3DeltaUnconditionalProvider:
    return Stage3DeltaUnconditionalProvider(**kwargs)


def _majority_candidate_scenario_gate(**kwargs: object) -> ScenarioGate:
    """Stage-3 iteration 3: the one registered supply-application policy.

    Constructed from a config's own ``scenario_gate`` parameters, exactly as
    every provider factory above is constructed from its route's parameters,
    so the gate a flight applies is the gate the composed config declares and
    nothing else. The RULE itself lives beside the selection it gates
    (``rails.stage3_delta_supply.ScenarioGate``); this is only the registration
    seam, kept at the canonical site with the provider ids.
    """

    return ScenarioGate(
        policy_id=STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, **kwargs
    ).validate()


# Keep all provider/rank/fuse registration at the canonical shared site.
# Lazy construction avoids circular imports between providers and named stores.
if "source-scoped-context-v1" not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register("source-scoped-context-v1", _source_scoped_context_provider)
if "saea-source-scoped-context-rank-v1" not in KNOWLEDGE_RANKERS.names():
    KNOWLEDGE_RANKERS.register("saea-source-scoped-context-rank-v1", _source_scoped_context_rank)
if "saea-source-scoped-context-fuse-v1" not in KNOWLEDGE_FUSERS.names():
    KNOWLEDGE_FUSERS.register("saea-source-scoped-context-fuse-v1", _source_scoped_context_fuse)
if "saea-named-context-composite-rank-v1" not in KNOWLEDGE_RANKERS.names():
    KNOWLEDGE_RANKERS.register("saea-named-context-composite-rank-v1", _named_context_rank)
if "saea-named-context-composite-fuse-v1" not in KNOWLEDGE_FUSERS.names():
    KNOWLEDGE_FUSERS.register("saea-named-context-composite-fuse-v1", _named_context_fuse)
if STAGE3_DELTA_CONTEXT_PROVIDER_ID not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register(
        STAGE3_DELTA_CONTEXT_PROVIDER_ID, _stage3_delta_candidate_provider
    )
if STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID not in KNOWLEDGE_PROVIDERS.names():
    KNOWLEDGE_PROVIDERS.register(
        STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID, _stage3_delta_unconditional_provider
    )
if STAGE3_DELTA_SCENARIO_GATE_POLICY_ID not in STAGE3_SUPPLY_GATE_POLICIES.names():
    STAGE3_SUPPLY_GATE_POLICIES.register(
        STAGE3_DELTA_SCENARIO_GATE_POLICY_ID, _majority_candidate_scenario_gate
    )


def resolve_provider(provider_id: str, **kwargs: object) -> KnowledgeProvider:
    """Construct the registered provider class named ``provider_id`` with
    ``kwargs``, through the shared ``core.base.KNOWLEDGE_PROVIDERS``
    registry."""

    factory = KNOWLEDGE_PROVIDERS.resolve(provider_id)
    return factory(**kwargs)


def resolve_scenario_gate(raw_gate: object, *, legal_intent_ids) -> ScenarioGate:
    """Validate a config's ``scenario_gate`` spec and construct it through the
    REGISTERED policy, exactly as :func:`resolve_provider` constructs a
    provider through the registered provider id.

    Two refusals, deliberately in this order: the spec is parsed against the
    carrier's own scenario catalog first (so a misspelling or an intent id
    written where a scenario belongs names ITSELF in the error), and the
    policy id is then resolved in ``core.base.STAGE3_SUPPLY_GATE_POLICIES``, so
    the registration is load-bearing rather than decorative.
    """

    spec = parse_scenario_gate(raw_gate, legal_intent_ids=legal_intent_ids)
    factory = STAGE3_SUPPLY_GATE_POLICIES.resolve(spec.policy_id)
    return factory(scenarios=spec.scenarios)


__all__ = [
    "A2T_CANDIDATE_SEMANTIC_PROVIDER_ID",
    "Audio2ToolCandidateSemanticProvider",
    "CandidateSemanticProvider",
    "CONEC_FUSE_POLICY_ID",
    "DENSE_CENTROID_FUSE_POLICY_ID",
    "KNOWLEDGE_PROVIDERS",
    "SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID",
    "SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID",
    "SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID",
    "SLURP_INTENT_CANDIDATES_FUSE_POLICY_ID",
    "SLURP_INTENT_CANDIDATES_RANK_POLICY_ID",
    "ConecContextProvider",
    "DenseCentroidProvider",
    "KbFacetProvider",
    "KnowledgeProvider",
    "RankedEntry",
    "Ranking",
    "SlurpCandidateSemanticProvider",
    "SlurpIntentCandidateProvider",
    "resolve_provider",
    "resolve_scenario_gate",
    "select_candidate_semantic_values",
]
