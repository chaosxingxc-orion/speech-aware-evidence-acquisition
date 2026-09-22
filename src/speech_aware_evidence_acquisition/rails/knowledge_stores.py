"""Independent pinned knowledge stores composed behind the shared KB rails."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from ..core.base import KNOWLEDGE_FUSERS, KNOWLEDGE_RANKERS

from .controllers import PhaseSupply
from .knowledge import AgentStateArtifact, FusionDecision, RankedFacet, RankResult
from .errors import RailsError
from .hashing import content_hash
from .knowledge import KnowledgeSnapshot

KNOWLEDGE_STORE_RELEASE_SCHEMA = "saea-knowledge-store-release-v1"
STORE_SEPARATOR = "::"
COMPOSITE_CONTEXT_RANK_POLICY_ID = "saea-named-context-composite-rank-v1"
COMPOSITE_CONTEXT_FUSE_POLICY_ID = "saea-named-context-composite-fuse-v1"
_STORE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STORE_KEYS = frozenset({"store_role", "snapshot", "release"})
_STORE_OPTIONAL_KEYS = frozenset(
    {"phase_supply", "candidate_supply", "context_supply"}
)
_PIN_KEYS = frozenset({"relpath", "sha256"})
_RELEASE_KEYS = frozenset(
    {
        "schema",
        "store_id",
        "store_role",
        "snapshot_sha256",
        "source_split_identity_hash",
        "builder_policy_id",
        "source",
    }
)


class KnowledgeStoreError(RailsError):
    """A named knowledge store or one of its independent pins is invalid."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise KnowledgeStoreError(f"{field} must be a lowercase 64-hex SHA-256")
    return value


def _relpath(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise KnowledgeStoreError(f"{field} must be a canonical relative path")
    return value


def _pin(value: object, field: str) -> Mapping[str, str]:
    if not isinstance(value, Mapping) or set(value) != _PIN_KEYS:
        raise KnowledgeStoreError(f"{field} must contain exactly relpath and sha256")
    return MappingProxyType(
        {
            "relpath": _relpath(value["relpath"], f"{field}.relpath"),
            "sha256": _sha(value["sha256"], f"{field}.sha256"),
        }
    )


def _confined(root: Path, relpath: str, field: str) -> Path:
    base = Path(root).resolve()
    path = (base / relpath).resolve()
    if path == base or base not in path.parents:
        raise KnowledgeStoreError(f"{field} escapes the data root")
    return path


def _read_pinned(root: Path, pin: Mapping[str, str], field: str) -> bytes:
    path = _confined(root, pin["relpath"], field)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise KnowledgeStoreError(f"cannot read {field}: {path}") from error
    if hashlib.sha256(raw).hexdigest() != pin["sha256"]:
        raise KnowledgeStoreError(f"{field} SHA-256 mismatch")
    return raw


def qualify_id(store_id: str, local_id: str) -> str:
    return f"{store_id}{STORE_SEPARATOR}{local_id}"


@dataclass(frozen=True)
class KnowledgeStore:
    store_id: str
    store_role: str
    snapshot: KnowledgeSnapshot
    snapshot_pin: Mapping[str, str]
    release_pin: Mapping[str, str]
    source_pin: Mapping[str, str]
    phase_supply: Mapping[str, object]
    candidate_supply: Mapping[str, object]
    context_supply: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class KnowledgeStoreBinding:
    """Named releases plus a lossless namespaced snapshot for legacy rails."""

    stores: Mapping[str, KnowledgeStore]
    composite_snapshot: KnowledgeSnapshot
    binding_sha256: str

    @property
    def store_ids(self) -> tuple[str, ...]:
        return tuple(self.stores)

    def store(self, store_id: str) -> KnowledgeStore:
        try:
            return self.stores[store_id]
        except KeyError as error:
            raise KnowledgeStoreError(
                f"unknown knowledge store {store_id!r}"
            ) from error

    def snapshot_for(self, store_id: str) -> KnowledgeSnapshot:
        return self.store(store_id).snapshot

    def qualify_supply(
        self, store_id: str, supply: PhaseSupply, query_state: object
    ) -> PhaseSupply:
        store = self.store(store_id)
        supply.validate()
        local = store.snapshot
        local_hash = local.content_hash()
        query_hash = query_state.content_hash()
        rank, fusion = supply.rank_result, supply.fusion_decision
        if rank.snapshot_sha256 != local_hash or fusion.snapshot_sha256 != local_hash:
            raise KnowledgeStoreError(
                "knowledge supply is bound to another store snapshot"
            )
        if (
            rank.query_state_sha256 != query_hash
            or fusion.query_state_sha256 != query_hash
        ):
            raise KnowledgeStoreError(
                "knowledge supply is bound to another query state"
            )
        if fusion.rank_result_sha256 != rank.content_hash():
            raise KnowledgeStoreError("knowledge supply has a changed rank binding")
        facet_ids = {facet.facet_id for facet in local.facets}
        value_ids = {value.value_id for value in local.values}
        ranked = {entry.facet_id for entry in rank.candidates}
        if (
            not ranked <= facet_ids
            or not set(fusion.supporting_facet_ids) <= ranked
            or not set(fusion.selected_value_ids) <= value_ids
        ):
            raise KnowledgeStoreError(
                "knowledge supply cites IDs outside the selected store"
            )
        qualified_rank = replace(
            rank,
            snapshot_sha256=self.binding_sha256,
            candidates=tuple(
                replace(entry, facet_id=qualify_id(store_id, entry.facet_id))
                for entry in rank.candidates
            ),
        ).validate()
        qualified_fusion = replace(
            fusion,
            snapshot_sha256=self.binding_sha256,
            rank_result_sha256=qualified_rank.content_hash(),
            supporting_facet_ids=tuple(
                qualify_id(store_id, item) for item in fusion.supporting_facet_ids
            ),
            selected_value_ids=tuple(
                qualify_id(store_id, item) for item in fusion.selected_value_ids
            ),
        ).validate()
        return replace(
            supply,
            rank_result=qualified_rank,
            fusion_decision=qualified_fusion,
            action_target_ref=f"knowledge-store:{store_id}:{supply.action_target_ref}",
        ).validate()

    def store_receipt(self, store_id: str) -> Mapping[str, object]:
        store = self.store(store_id)
        return {
            "store_id": store.store_id,
            "store_role": store.store_role,
            "store_snapshot_sha256": store.snapshot_pin["sha256"],
            "store_release_sha256": store.release_pin["sha256"],
            "store_source_sha256": store.source_pin["sha256"],
            "composite_snapshot_sha256": self.binding_sha256,
        }

    def model_evidence_block(
        self, store_id: str, *, local_evidence_id: str, content: str
    ) -> Mapping[str, str]:
        """Return the exact compact, independently pinned model-facing block."""

        store = self.store(store_id)
        qualified = qualify_id(store_id, local_evidence_id)
        return {
            "evidence_id": qualified,
            "text": (
                f"[knowledge store={store_id} role={store.store_role}] {content}"
            ),
            "store_id": store_id,
        }


def _composite(stores: Mapping[str, KnowledgeStore]) -> KnowledgeSnapshot:
    source_roles = {store.snapshot.source_partition_role for store in stores.values()}
    if len(source_roles) != 1:
        raise KnowledgeStoreError(
            "mixed source partition roles require an explicit composition contract"
        )
    source_role = next(iter(source_roles))
    facets, values, sources = [], [], set()
    for store_id, store in stores.items():
        sources.update(store.snapshot.source_sample_ids)
        facets.extend(
            replace(
                facet,
                facet_id=qualify_id(store_id, facet.facet_id),
                parent_facet_ids=tuple(
                    qualify_id(store_id, item) for item in facet.parent_facet_ids
                ),
            )
            for facet in store.snapshot.facets
        )
        values.extend(
            replace(
                value,
                value_id=qualify_id(store_id, value.value_id),
                associated_facet_ids=tuple(
                    qualify_id(store_id, item) for item in value.associated_facet_ids
                ),
                provenance_refs=tuple(value.provenance_refs),
            )
            for value in store.snapshot.values
        )
    identity = content_hash(
        {
            store_id: {
                "snapshot_sha256": store.snapshot_pin["sha256"],
                "release_sha256": store.release_pin["sha256"],
            }
            for store_id, store in stores.items()
        }
    )
    return KnowledgeSnapshot(
        snapshot_id=f"named-knowledge-stores:{identity}",
        source_split_identity_hash=content_hash(
            {
                store_id: store.snapshot.source_split_identity_hash
                for store_id, store in stores.items()
            }
        ),
        source_sample_ids=tuple(sorted(sources)),
        builder_policy_id="saea-named-knowledge-store-router-v1",
        source_partition_role=source_role,
        facets=tuple(facets),
        values=tuple(values),
    ).validate()


def load_knowledge_store_binding(
    config: Mapping[str, object], *, data_root: Path
) -> KnowledgeStoreBinding | None:
    raw = config.get("knowledge_stores")
    if raw is None:
        return None
    if not isinstance(raw, Mapping) or not raw:
        raise KnowledgeStoreError("knowledge_stores must be a non-empty mapping")
    stores = {}
    for store_id in sorted(raw):
        if not isinstance(store_id, str) or _STORE_ID.fullmatch(store_id) is None:
            raise KnowledgeStoreError(
                f"knowledge store ID {store_id!r} must be a canonical slug"
            )
        spec = raw[store_id]
        if (
            not isinstance(spec, Mapping)
            or not _STORE_KEYS <= set(spec)
            or set(spec) - _STORE_KEYS - _STORE_OPTIONAL_KEYS
        ):
            raise KnowledgeStoreError(
                f"knowledge_stores[{store_id!r}] has the wrong fields"
            )
        role = spec["store_role"]
        if not isinstance(role, str) or _STORE_ID.fullmatch(role) is None:
            raise KnowledgeStoreError(
                f"knowledge store {store_id!r} role must be a canonical slug"
            )
        snapshot_pin, release_pin = (
            _pin(spec["snapshot"], f"knowledge_stores[{store_id!r}].snapshot"),
            _pin(spec["release"], f"knowledge_stores[{store_id!r}].release"),
        )
        release_raw = _read_pinned(
            Path(data_root), release_pin, f"knowledge store {store_id} release"
        )
        try:
            release = json.loads(release_raw)
        except (UnicodeError, json.JSONDecodeError) as error:
            raise KnowledgeStoreError(
                f"knowledge store {store_id} release is not JSON"
            ) from error
        if (
            not isinstance(release, Mapping)
            or set(release) != _RELEASE_KEYS
            or release.get("schema") != KNOWLEDGE_STORE_RELEASE_SCHEMA
            or release.get("store_id") != store_id
            or release.get("store_role") != role
        ):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} release identity mismatch"
            )
        source_pin = _pin(
            release["source"], f"knowledge store {store_id} release.source"
        )
        _read_pinned(
            Path(data_root),
            source_pin,
            f"knowledge store {store_id} construction source",
        )
        snapshot_path = _confined(
            Path(data_root),
            snapshot_pin["relpath"],
            f"knowledge store {store_id} snapshot",
        )
        try:
            snapshot = KnowledgeSnapshot.from_frozen_json(
                json.loads(snapshot_path.read_text(encoding="utf-8"))
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            RailsError,
        ) as error:
            raise KnowledgeStoreError(
                f"cannot load knowledge store {store_id} snapshot"
            ) from error
        if (
            snapshot.content_hash() != snapshot_pin["sha256"]
            or release["snapshot_sha256"] != snapshot_pin["sha256"]
        ):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} snapshot SHA-256 mismatch"
            )
        if (
            release["source_split_identity_hash"] != snapshot.source_split_identity_hash
            or release["builder_policy_id"] != snapshot.builder_policy_id
        ):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} release differs from its snapshot"
            )
        phase_supply = spec.get("phase_supply", {})
        if not isinstance(phase_supply, Mapping):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} phase_supply must be a mapping"
            )
        candidate_supply = spec.get("candidate_supply", {})
        if not isinstance(candidate_supply, Mapping):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} candidate_supply must be a mapping"
            )
        context_supply = spec.get("context_supply", {})
        if not isinstance(context_supply, Mapping):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} context_supply must be a mapping"
            )
        stores[store_id] = KnowledgeStore(
            store_id,
            role,
            snapshot,
            snapshot_pin,
            release_pin,
            source_pin,
            MappingProxyType(dict(phase_supply)),
            MappingProxyType(dict(candidate_supply)),
            MappingProxyType(dict(context_supply)),
        )
    proxy = MappingProxyType(stores)
    composite = _composite(proxy)
    return KnowledgeStoreBinding(proxy, composite, composite.content_hash())


def build_knowledge_store_supply(
    binding: KnowledgeStoreBinding,
    *,
    program: object,
    data_root: Path,
    source_audio_bindings=None,
    legal_candidate_ids=None,
    candidate_inventory_source_sha256=None,
    candidate_inventory_authority="task-adapter-candidate-contract-provider",
    on_demand_store_ids=(),
):
    """Build explicit store routes and automatic candidate-conditioned supply."""
    from .phase_supply import (
        build_bootstrap_selection,
        build_supply_for_phase,
        load_phase_supply_specs,
        phase_supply_receipt,
    )

    from .candidate_semantic_supply import (
        build_candidate_semantic_supply,
        load_candidate_semantic_supply_specs,
    )
    from .governed_context_supply import (
        SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID,
        SOURCE_SCOPED_CONTEXT_PROVIDER_ID,
    )

    from .knowledge_provider import resolve_provider

    from .stage3_delta_supply import (
        STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        STAGE3_DELTA_STORE_ROLE,
    )
    from .slurp_intent_hypotheses import (
        SlurpIntentHypothesisError,
        parse_slurp_intent_hypothesis_state,
    )

    if isinstance(on_demand_store_ids, (str, bytes)):
        raise KnowledgeStoreError("on-demand stores must be an explicit sequence of store IDs")
    requested = tuple(on_demand_store_ids)
    if (any(not isinstance(item, str) or not item for item in requested)
            or len(set(requested)) != len(requested)
            or not set(requested) <= set(binding.store_ids)):
        raise KnowledgeStoreError("on-demand stores must name unique bound stores")
    on_demand = frozenset(requested)
    from .released_target_index import build_released_target_index

    target_indices = {}
    for store_id in requested:
        index = build_released_target_index(
            binding.store(store_id), data_root=data_root,
            legal_candidate_ids=tuple(legal_candidate_ids or ()),
        )
        if index is not None:
            target_indices[store_id] = index
    callbacks, explicit_specs_by_store, specs_by_store, receipts = {}, {}, {}, {}
    context_specs: dict[tuple[str, str], object] = {}
    candidate_specs = load_candidate_semantic_supply_specs(binding, program)
    if candidate_specs and legal_candidate_ids is None:
        raise KnowledgeStoreError(
            "candidate semantic supply requires the task adapter's authoritative "
            "legal candidate inventory"
        )
    candidate_callback = build_candidate_semantic_supply(
        binding,
        candidate_specs,
        data_root=data_root,
        legal_candidate_ids=tuple(legal_candidate_ids or ()),
        candidate_inventory_source_sha256=candidate_inventory_source_sha256,
        candidate_inventory_authority=candidate_inventory_authority,
    )
    first_phase = program.phase_names()[0]

    def _build_stage3_delta_provider(store):
        """Resolve and build the registered Stage3DeltaCandidateProvider
        over one store released delta pool. Re-derived per call, never
        cached on the router, mirroring the source-scoped provider own
        re-resolve-per-call precedent just below."""

        provider = resolve_provider(STAGE3_DELTA_CONTEXT_PROVIDER_ID)
        provider.build(
            [value.as_json() for value in store.snapshot.values],
            policy_id=store.snapshot.builder_policy_id,
        )
        return provider

    def _validate_stage3_delta_context_spec(raw_spec, *, store, phase):
        phases = program.phase_names()
        candidate_state_phase = raw_spec.get("candidate_state_phase")
        cap = raw_spec.get("cap")
        if (
            store.store_role != STAGE3_DELTA_STORE_ROLE
            or set(raw_spec) != {"provider", "candidate_state_phase", "cap", "rank_by"}
            or raw_spec.get("rank_by") != "prior_score"
            or not isinstance(candidate_state_phase, str)
            or candidate_state_phase not in phases
            or phase not in phases
            or phase == first_phase
            or program.phase(phase).knowledge != "supplied"
            or phases.index(candidate_state_phase) >= phases.index(phase)
            or isinstance(cap, bool)
            or not isinstance(cap, int)
            or cap < 1
        ):
            raise KnowledgeStoreError(
                "stage3-deltas context_supply requires a candidate-bound, capped, "
                "prior_score-ranked spec on a later supplied phase"
            )

    def _stage3_delta_local_supply(store, raw_spec, context):
        """Candidate-bound, prior_score-capped Solver supply for one
        stage3-deltas store (S3-6): read the row Perception candidate
        intents off the configured candidate_state_phase state, then
        route them through the registered Stage3DeltaCandidateProvider
        (rails.stage3_delta_supply.select_stage3_delta_values does the
        actual selection)."""

        candidate_state_phase = raw_spec["candidate_state_phase"]
        cap = raw_spec["cap"]
        query_state = getattr(context, "query_state", None)
        if query_state is None:
            raise KnowledgeStoreError("stage3-deltas context_supply requires a QueryState")
        sample_id = getattr(context, "sample_id", None)
        states = getattr(context, "agent_states", ())
        expected_kind = f"phase:{candidate_state_phase}"
        matches = tuple(
            state for state in states
            if isinstance(state, AgentStateArtifact) and state.state_kind == expected_kind
        )
        if len(matches) != 1:
            raise KnowledgeStoreError(
                f"stage3-deltas context_supply requires exactly one source-bound "
                f"{candidate_state_phase!r} state, got {len(matches)}"
            )
        legal = tuple(legal_candidate_ids or ())
        if not legal:
            raise KnowledgeStoreError(
                "stage3-deltas context_supply requires the task adapter authoritative "
                "legal candidate inventory"
            )
        try:
            hypothesis_state = parse_slurp_intent_hypothesis_state(
                matches[0],
                expected_sample_id=str(sample_id),
                legal_intent_ids=legal,
                max_candidates=len(frozenset(legal)),
            )
        except SlurpIntentHypothesisError as error:
            raise KnowledgeStoreError(str(error)) from error
        candidate_facet_ids = tuple(item.intent_id for item in hypothesis_state.candidates)

        provider = _build_stage3_delta_provider(store)
        ranking = provider.candidates(candidate_facet_ids, k=cap)
        selected_ids = tuple(entry.entry_id for entry in ranking.entries)
        by_id = {value.value_id: value for value in store.snapshot.values}
        supporting: dict[str, None] = {}
        for value_id in selected_ids:
            for facet_id in by_id[value_id].associated_facet_ids:
                supporting.setdefault(facet_id, None)
        supporting_facet_ids = tuple(supporting)
        query_hash = query_state.content_hash()
        rank_result = RankResult(
            snapshot_sha256=store.snapshot.content_hash(),
            query_state_sha256=query_hash,
            ranking_policy_id=STAGE3_DELTA_CONTEXT_PROVIDER_ID,
            candidates=tuple(
                RankedFacet(facet_id=facet_id, score=float(len(supporting_facet_ids) - index))
                for index, facet_id in enumerate(supporting_facet_ids)
            ),
        ).validate()
        fusion_decision = FusionDecision(
            snapshot_sha256=store.snapshot.content_hash(),
            query_state_sha256=query_hash,
            rank_result_sha256=rank_result.content_hash(),
            fusion_policy_id=STAGE3_DELTA_CONTEXT_PROVIDER_ID,
            supporting_facet_ids=supporting_facet_ids,
            selected_value_ids=selected_ids,
        ).validate()
        return PhaseSupply(
            rank_result=rank_result,
            fusion_decision=fusion_decision,
            action_target_ref=f"{STAGE3_DELTA_CONTEXT_PROVIDER_ID}:cap={cap}",
        ).validate()

    for store_id in binding.store_ids:
        store = binding.store(store_id)
        for phase, raw_spec in store.context_supply.items():
            if not isinstance(phase, str) or not isinstance(raw_spec, Mapping):
                raise KnowledgeStoreError(
                    "context_supply requires a later supplied phase and a recognised provider"
                )
            provider_id = raw_spec.get("provider")
            if provider_id == SOURCE_SCOPED_CONTEXT_PROVIDER_ID:
                if (
                    set(raw_spec) != {"provider"}
                    or phase not in program.phase_names()
                    or phase == first_phase
                    or program.phase(phase).knowledge != "supplied"
                ):
                    raise KnowledgeStoreError(
                        "context_supply requires a later supplied phase and the source-scoped provider"
                    )
            elif provider_id == STAGE3_DELTA_CONTEXT_PROVIDER_ID:
                _validate_stage3_delta_context_spec(raw_spec, store=store, phase=phase)
            else:
                raise KnowledgeStoreError(
                    f"context_supply names an unrecognised provider {provider_id!r}"
                )
            context_specs[(store_id, phase)] = raw_spec
        if store.context_supply:
            providers_used = {raw["provider"] for raw in store.context_supply.values()}
            if SOURCE_SCOPED_CONTEXT_PROVIDER_ID in providers_used:
                # Prove scope/provenance compatibility before any runtime contact.
                resolve_provider(
                    SOURCE_SCOPED_CONTEXT_PROVIDER_ID,
                    snapshot=store.snapshot, value_id_namespace=store_id,
                )
            if STAGE3_DELTA_CONTEXT_PROVIDER_ID in providers_used:
                # Prove the delta pool builds cleanly before any runtime contact.
                _build_stage3_delta_provider(store)
    if (
        legal_candidate_ids is None
        and any(
            raw_spec["provider"] == STAGE3_DELTA_CONTEXT_PROVIDER_ID
            for raw_spec in context_specs.values()
        )
    ):
        raise KnowledgeStoreError(
            "stage3-deltas context_supply requires the task adapter authoritative "
            "legal candidate inventory"
        )
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        scoped_phases = {phase for (owner, phase) in context_specs if owner == store_id}
        if set(store.phase_supply).intersection(scoped_phases):
            raise KnowledgeStoreError("explicit and scoped supply cannot overlap on one store phase")
        specs = load_phase_supply_specs({"phase_supply": store.phase_supply}, program)
        # E3b fix: the E3 fix (module comment above, plain_later_phase_specs)
        # composes a store's own plain, later-phase phase_supply alongside a
        # DIFFERENT store's candidate_supply on the SAME phase -- this
        # program's anchor case (slot-contracts candidate_supply.solver plus
        # train-exemplars phase_supply.solver) -- but this guard, unchanged
        # since before E3, tested every store's explicit/scoped specs
        # against the GLOBAL candidate_specs with no regard for phase order
        # or store identity, so it refused the very pairing E3 was written
        # to compose. Three refusals stay exactly as they were:
        #   1. scoped (context_supply) and candidate supply collide
        #      wherever they meet, on any phase, from any store: this router
        #      never composes a source-scoped context provider alongside a
        #      candidate semantic provider on the same phase.
        #   2. this store's own explicit phase_supply and ANY store's
        #      candidate supply collide on the program's FIRST phase,
        #      unconditionally. The first phase is decided by
        #      bootstrap_first_phase before any flight, never by this live
        #      dispatcher, so there is no live composition seam there to
        #      reconcile the two. (CandidateSemanticSupplySpec.validate
        #      already makes this unreachable today -- a candidate supply's
        #      phase must be strictly later than its own
        #      candidate_state_phase, so candidate_specs can never key the
        #      first phase -- kept anyway as a defensive equal to the
        #      pre-fix behaviour rather than relying on that invariant
        #      holding forever.)
        #   3. this store's own explicit phase_supply and a candidate supply
        #      FROM THE SAME STORE collide on any later phase: one store
        #      cannot serve one phase through both mechanisms at once.
        # The ONLY new admission: this store's own explicit phase_supply on
        # a LATER phase may now coexist with a DIFFERENT store's candidate
        # supply on that same phase.
        #
        # S3-6 (2026-09-22) ONE MORE admission, deliberately narrow: a
        # stage3-deltas store's OWN context_supply (the new candidate-bound,
        # prior_score-capped route) may ALSO coexist with a DIFFERENT
        # store's candidate_supply on the same phase -- this program's
        # anchor case, stage3-deltas context_supply.solver alongside
        # slot-contracts candidate_supply.solver. The source-scoped
        # context_supply provider keeps refusing that overlap exactly as
        # before; only phases the CURRENT store routes through the
        # stage3-delta provider are excused from rule 1.
        stage3_delta_scoped_phases = {
            phase for phase in scoped_phases
            if context_specs[(store_id, phase)]["provider"] == STAGE3_DELTA_CONTEXT_PROVIDER_ID
        }
        collisions = (scoped_phases - stage3_delta_scoped_phases).intersection(candidate_specs)
        if first_phase in specs and first_phase in candidate_specs:
            collisions.add(first_phase)
        for phase in specs:
            if phase == first_phase:
                continue
            candidate_spec = candidate_specs.get(phase)
            if candidate_spec is not None and candidate_spec.store_id == store_id:
                collisions.add(phase)
        if collisions:
            raise KnowledgeStoreError(
                "candidate, explicit, and scoped supply cannot overlap on phase(s) "
                f"{sorted(collisions)}"
            )
        callback = None
        if specs:
            callback = build_supply_for_phase(
                specs,
                snapshot=store.snapshot,
                snapshot_sha256=store.snapshot.content_hash(),
                data_root=data_root,
                seed_phases=(first_phase,) if first_phase in specs else (),
                source_audio_bindings=source_audio_bindings,
            )
            callbacks[store_id] = callback
        explicit_specs_by_store[store_id] = specs
        store_candidate_specs = {
            phase: spec
            for phase, spec in candidate_specs.items()
            if spec.store_id == store_id
        }
        if not specs and not store_candidate_specs and not scoped_phases and store_id not in on_demand:
            raise KnowledgeStoreError(f"knowledge store {store_id} has no phase_supply")
        specs_by_store[store_id] = {**specs, **store_candidate_specs}
        specs_by_store[store_id].update({phase: raw for phase, raw in store.context_supply.items()})
        receipts[store_id] = {
            **binding.store_receipt(store_id),
            "phase_supply": (
                None
                if callback is None
                else phase_supply_receipt(
                    specs, callback.query_vector_rows, callback.facet_vector_rows
                )
            ),
        }
        if store_id in on_demand:
            receipts[store_id]["on_demand_target_lookup"] = True
            if store_id in target_indices:
                receipts[store_id]["target_index"] = dict(target_indices[store_id].receipt)
        if store_candidate_specs:
            receipts[store_id]["candidate_supply"] = [
                store_candidate_specs[phase].as_json()
                for phase in sorted(store_candidate_specs)
            ]
        if scoped_phases:
            receipts[store_id]["context_supply"] = sorted(scoped_phases)

    def bootstrap_first_phase(
        *,
        speech_packet_bindings: Mapping[str, Mapping[str, object]],
        split_identity_hash: str,
        workers: int = 1,
        lease_metadata_present: bool = False,
    ) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
        """Select and qualify every named store routed to the first phase."""

        facets_by_sample: dict[str, list[str]] = {}
        values_by_sample: dict[str, list[str]] = {}
        for store_id in binding.store_ids:
            spec = explicit_specs_by_store[store_id].get(first_phase)
            callback = callbacks.get(store_id)
            if spec is None or callback is None:
                continue
            local_facets, local_values = build_bootstrap_selection(
                spec,
                provider=callback.provider_factories[first_phase](),
                query_vectors_by_sample=callback.query_tables[first_phase],
                speech_packet_bindings=speech_packet_bindings,
                split_identity_hash=split_identity_hash,
                source_audio_bindings=callback.source_audio_bindings,
                workers=workers,
                lease_metadata_present=lease_metadata_present,
            )
            for sample_id in sorted(local_facets):
                facets_by_sample.setdefault(sample_id, []).extend(
                    qualify_id(store_id, facet_id)
                    for facet_id in local_facets[sample_id]
                )
            for sample_id in sorted(local_values):
                values_by_sample.setdefault(sample_id, []).extend(
                    qualify_id(store_id, value_id)
                    for value_id in local_values[sample_id]
                )
        return (
            {
                sample_id: tuple(facet_ids)
                for sample_id, facet_ids in sorted(facets_by_sample.items())
            },
            {
                sample_id: tuple(value_ids)
                for sample_id, value_ids in sorted(values_by_sample.items())
            },
        )

    def route(store_id, phase, context):
        if (store_id, phase) in context_specs:
            store = binding.store(store_id)
            raw_spec = context_specs[(store_id, phase)]
            if raw_spec["provider"] == STAGE3_DELTA_CONTEXT_PROVIDER_ID:
                return _stage3_delta_local_supply(store, raw_spec, context)
            query_state = getattr(context, "query_state", None)
            provider = resolve_provider(
                SOURCE_SCOPED_CONTEXT_PROVIDER_ID,
                snapshot=store.snapshot, value_id_namespace=store_id,
            )
            ranking = provider.candidates(
                {"context": context, "query_state": query_state}, k=1
            )
            decision = provider.fuse(
                [ranking], k=1, policy_id=SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID
            )
            local = PhaseSupply(
                rank_result=provider.last_rank_result(), fusion_decision=decision,
                action_target_ref=SOURCE_SCOPED_CONTEXT_PROVIDER_ID,
            ).validate()
            return local
        try:
            callback = callbacks[store_id]
        except KeyError as error:
            raise KnowledgeStoreError(
                f"unknown knowledge store {store_id!r}"
            ) from error
        if phase not in specs_by_store[store_id]:
            raise KnowledgeStoreError(
                f"knowledge store {store_id!r} is unavailable for phase {phase!r}"
            )
        return callback(phase, context)

    def _compose_supplies(supplies, query_state):
        if not supplies:
            return None
        if len(supplies) == 1:
            return supplies[0]
        for supply in supplies:
            supply.validate()
            if (
                supply.packet is not None or supply.retain_prior or supply.expose_facets
                or supply.rank_result.snapshot_sha256 != binding.binding_sha256
                or supply.fusion_decision.snapshot_sha256 != binding.binding_sha256
                or supply.rank_result.query_state_sha256 != query_state.content_hash()
                or supply.fusion_decision.query_state_sha256 != query_state.content_hash()
                or supply.fusion_decision.rank_result_sha256 != supply.rank_result.content_hash()
            ):
                raise KnowledgeStoreError("context composition requires aligned value-only supplies")
        ranks = tuple(supply.rank_result for supply in supplies)
        decisions = tuple(supply.fusion_decision for supply in supplies)
        rank = KNOWLEDGE_RANKERS.resolve(COMPOSITE_CONTEXT_RANK_POLICY_ID)()(ranks)
        decision = KNOWLEDGE_FUSERS.resolve(COMPOSITE_CONTEXT_FUSE_POLICY_ID)()(
            rank=rank, decisions=decisions
        )
        return PhaseSupply(
            rank_result=rank, fusion_decision=decision,
            action_target_ref="source-scoped-context-composite-v1",
        ).validate()

    # Every store phase this router can serve at RUNTIME (never the first
    # phase: a first-phase selection has no preceding advance and is decided
    # by bootstrap_first_phase instead, per store, before the flight). A
    # store's plain phase_supply entry for a later phase used to be built
    # into callbacks[store_id] and then never called by anything the
    # FlightRuntime reads back out (core.flight.runtime.RuntimeAssembly only
    # ever reads `router.automatic_for_phase`) unless the SAME phase also
    # carried a context_supply or a candidate_supply on some store -- so a
    # named store's OWN phase_supply on a non-first phase (e.g. this
    # program's E3 'train-exemplars' store, phase_supply.solver) was parsed,
    # validated and receipted, and then silently never consulted at runtime.
    # This is the E3 fix: every later-phase plain phase_supply entry is
    # routed here too, alongside context_supply and candidate_supply,
    # composed the same way context_supply already was.
    plain_later_phase_specs = {
        (store_id, phase)
        for store_id in binding.store_ids
        for phase in explicit_specs_by_store.get(store_id, {})
        if phase != first_phase
    }

    def automatic_for_phase(phase, context):
        query_state = getattr(context, "query_state", None)
        if query_state is None:
            raise KnowledgeStoreError("automatic context supply requires a QueryState")
        supplies = [
            binding.qualify_supply(store_id, route(store_id, phase, context), query_state)
            for store_id in binding.store_ids
            if (store_id, phase) in context_specs
        ]
        for store_id in binding.store_ids:
            if (store_id, phase) in context_specs or (store_id, phase) not in plain_later_phase_specs:
                continue
            local_supply = route(store_id, phase, context)
            if local_supply is not None:
                supplies.append(binding.qualify_supply(store_id, local_supply, query_state))
        if candidate_callback is not None:
            candidate_supply = candidate_callback(phase, context)
            if candidate_supply is not None:
                supplies.append(candidate_supply)
        return _compose_supplies(supplies, query_state)

    route.target_indices = MappingProxyType(target_indices)
    route.specs_by_store = specs_by_store
    route.bootstrap_first_phase = bootstrap_first_phase
    candidate_receipt = (
        None if candidate_callback is None else candidate_callback.receipt
    )
    route.receipt = {
        "schema": "saea-named-knowledge-store-routing-v1",
        "binding_sha256": binding.binding_sha256,
        "stores": receipts,
    }
    # DELIBERATELY NOT WIDENED (E3): a config whose stores declare later-phase
    # plain phase_supply and NOTHING ELSE (no context_supply anywhere, no
    # candidate_supply anywhere) still gets no `automatic_for_phase` -- exactly
    # the pre-E3 behavior, and exactly what
    # test_knowledge_stores.test_real_request_gate_retains_exact_qualified_
    # store_evidence pins (`assert not hasattr(router, "automatic_for_phase")`
    # against a config whose two stores declare ONLY phase_supply on
    # non-first phases "decision-2"/"final", consumed there through the
    # NATIVE-TOOL dispatcher's explicit `store_id` selection instead). That
    # scenario is deliberately outside automatic dispatch: a store meant to be
    # reached only by an explicit knowledge-target tool call must not ALSO
    # fire automatically, or a flight wiring both mechanisms would deliver it
    # twice. The E3 fix below only ENRICHES what `automatic_for_phase`
    # already does once something else (context_supply or candidate_supply)
    # already earns it a dispatcher: a later-phase plain phase_supply store
    # bound alongside one of those (this program's anchor: 'slot-contracts'
    # candidate_supply.solver plus the new 'train-exemplars'
    # phase_supply.solver) now actually gets composed in, where before it was
    # parsed, validated and receipted and then silently never called.
    if context_specs or candidate_callback is not None:
        route.automatic_for_phase = automatic_for_phase
    if candidate_receipt is not None:
        route.receipt["candidate_supply"] = candidate_receipt
        route.receipt["candidate_selections"] = candidate_receipt["candidate_selections"]
    return route


def _composite_context_rank(_knobs=None):
    def rank(ranks):
        if not ranks:
            raise KnowledgeStoreError("context composition requires nonempty ranks")
        for item in ranks:
            item.validate()
            if (item.snapshot_sha256, item.query_state_sha256) != (
                ranks[0].snapshot_sha256, ranks[0].query_state_sha256
            ):
                raise KnowledgeStoreError("context ranks have different source/query bindings")
        return RankResult(
            snapshot_sha256=ranks[0].snapshot_sha256,
            query_state_sha256=ranks[0].query_state_sha256,
            ranking_policy_id=COMPOSITE_CONTEXT_RANK_POLICY_ID,
            candidates=tuple(sorted(
                (candidate for item in ranks for candidate in item.candidates),
                key=lambda item: (-item.score, item.facet_id),
            )),
        ).validate()
    return rank


def _composite_context_fuse(_knobs=None):
    def fuse(*, rank, decisions):
        rank.validate()
        if not decisions:
            raise KnowledgeStoreError("context composition requires nonempty decisions")
        for decision in decisions:
            decision.validate()
            if (decision.snapshot_sha256, decision.query_state_sha256) != (
                rank.snapshot_sha256, rank.query_state_sha256
            ):
                raise KnowledgeStoreError("context decisions have different source/query bindings")
        supporting = tuple(dict.fromkeys(
            facet_id for decision in decisions for facet_id in decision.supporting_facet_ids
        ))
        if not set(supporting) <= {item.facet_id for item in rank.candidates}:
            raise KnowledgeStoreError("context decisions refer to unranked facets")
        return FusionDecision(
            snapshot_sha256=rank.snapshot_sha256,
            query_state_sha256=rank.query_state_sha256,
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id=COMPOSITE_CONTEXT_FUSE_POLICY_ID,
            supporting_facet_ids=supporting,
            selected_value_ids=tuple(
                value_id for decision in decisions for value_id in decision.selected_value_ids
            ),
        ).validate()
    return fuse



__all__ = [
    "KNOWLEDGE_STORE_RELEASE_SCHEMA",
    "KnowledgeStore",
    "KnowledgeStoreBinding",
    "KnowledgeStoreError",
    "build_knowledge_store_supply",
    "load_knowledge_store_binding",
    "qualify_id",
]
