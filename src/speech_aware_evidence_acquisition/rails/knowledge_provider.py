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

``KNOWLEDGE_PROVIDERS`` (this module's own registry, module docstring
"Residual") is a stopgap: ``core.base`` should eventually host it alongside
``KNOWLEDGE_BUILDERS``/``KNOWLEDGE_RANKERS``/``KNOWLEDGE_FUSERS`` (this slice
does not own ``core/base.py`` and cannot add it there).
"""

from __future__ import annotations

import abc
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
    KNOWLEDGE_RANKERS,
    Registry,
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
from .kb_policy import FUSE_POLICY_ID, RANK_POLICY_ID, FuseKnobs, RankWeights, multidim_recall
from .knowledge import FusionDecision, KnowledgeSnapshot, QueryState
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

    def candidates(self, query: object, *, k: int) -> Ranking:
        if isinstance(k, bool) or not isinstance(k, int) or k <= 0:
            raise RailsError("KbFacetProvider.candidates: k must be a positive int")
        snapshot: KnowledgeSnapshot = self._built_object()
        if isinstance(query, QueryState):
            query_state, query_vectors = query, {}
        elif isinstance(query, Mapping):
            if "query_state" not in query:
                raise RailsError("KbFacetProvider.candidates: query mapping needs 'query_state'")
            query_state = query["query_state"]
            query_vectors = query.get("query_vectors", {})
        else:
            raise RailsError(
                "KbFacetProvider.candidates: query must be a QueryState or a mapping "
                "with 'query_state'/'query_vectors'"
            )
        recall_scores = multidim_recall(
            snapshot, query_vectors, self._facet_vectors, self._top_k_per_dimension
        )
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
# KNOWLEDGE_PROVIDERS -- a local registry (core.base is not owned by this slice)
# ---------------------------------------------------------------------------

KNOWLEDGE_PROVIDERS = Registry("knowledge provider")
KNOWLEDGE_PROVIDERS.register("kb-facet-v1", KbFacetProvider)
KNOWLEDGE_PROVIDERS.register("dense-centroid-v1", DenseCentroidProvider)
KNOWLEDGE_PROVIDERS.register("conec-context-v1", ConecContextProvider)


def resolve_provider(provider_id: str, **kwargs: object) -> KnowledgeProvider:
    """Construct the registered provider class named ``provider_id`` with
    ``kwargs``. ``core.base`` should eventually host ``KNOWLEDGE_PROVIDERS``
    alongside ``KNOWLEDGE_BUILDERS``/``KNOWLEDGE_RANKERS``/``KNOWLEDGE_FUSERS``
    (module docstring) -- this slice does not own ``core/base.py``.
    """

    factory = KNOWLEDGE_PROVIDERS.resolve(provider_id)
    return factory(**kwargs)


__all__ = [
    "CONEC_FUSE_POLICY_ID",
    "DENSE_CENTROID_FUSE_POLICY_ID",
    "KNOWLEDGE_PROVIDERS",
    "ConecContextProvider",
    "DenseCentroidProvider",
    "KbFacetProvider",
    "KnowledgeProvider",
    "RankedEntry",
    "Ranking",
    "resolve_provider",
]
