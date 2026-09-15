"""Independent pinned knowledge stores composed behind the shared KB rails."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import re
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .controllers import PhaseSupply
from .knowledge import FusionDecision, RankResult
from .errors import RailsError
from .hashing import content_hash
from .knowledge import KnowledgeSnapshot

KNOWLEDGE_STORE_RELEASE_SCHEMA = "saea-knowledge-store-release-v1"
STORE_SEPARATOR = "::"
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
    context_supply: Mapping[str, object]


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
        SourceScopedContextProvider,
    )

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
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        for phase, raw_spec in store.context_supply.items():
            if (
                not isinstance(phase, str)
                or not isinstance(raw_spec, Mapping)
                or set(raw_spec) != {"provider"}
                or raw_spec["provider"] != SOURCE_SCOPED_CONTEXT_PROVIDER_ID
                or phase not in program.phase_names()
                or phase == first_phase
                or program.phase(phase).knowledge != "supplied"
            ):
                raise KnowledgeStoreError(
                    "context_supply requires a later supplied phase and the source-scoped provider"
                )
            context_specs[(store_id, phase)] = raw_spec
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        specs = load_phase_supply_specs({"phase_supply": store.phase_supply}, program)
        scoped_phases = {phase for (owner, phase) in context_specs if owner == store_id}
        collisions = (set(specs) | scoped_phases).intersection(candidate_specs)
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
        if not specs and not store_candidate_specs and not scoped_phases:
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
            query_state = getattr(context, "query_state", None)
            provider = SourceScopedContextProvider(snapshot=store.snapshot)
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
            return binding.qualify_supply(store_id, local, query_state)
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
        candidates = tuple(
            candidate
            for supply in supplies
            for candidate in supply.rank_result.candidates
        )
        rank = RankResult(
            snapshot_sha256=binding.binding_sha256,
            query_state_sha256=query_state.content_hash(),
            ranking_policy_id="saea-named-context-composite-rank-v1",
            candidates=tuple(sorted(candidates, key=lambda item: (-item.score, item.facet_id))),
        ).validate()
        decision = FusionDecision(
            snapshot_sha256=binding.binding_sha256,
            query_state_sha256=query_state.content_hash(),
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id="saea-named-context-composite-fuse-v1",
            supporting_facet_ids=tuple(candidate.facet_id for candidate in rank.candidates),
            selected_value_ids=tuple(
                value_id for supply in supplies for value_id in supply.fusion_decision.selected_value_ids
            ),
        ).validate()
        return PhaseSupply(rank, decision, "source-scoped-context-composite-v1").validate()

    def automatic_for_phase(phase, context):
        query_state = getattr(context, "query_state", None)
        if query_state is None:
            raise KnowledgeStoreError("automatic context supply requires a QueryState")
        supplies = [
            route(store_id, phase, context)
            for store_id in binding.store_ids
            if (store_id, phase) in context_specs
        ]
        if candidate_callback is not None:
            candidate_supply = candidate_callback(phase, context)
            if candidate_supply is not None:
                supplies.append(candidate_supply)
        return _compose_supplies(supplies, query_state)

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
    if candidate_callback is not None or context_specs:
        route.automatic_for_phase = automatic_for_phase
        route.receipt["candidate_supply"] = candidate_receipt
        route.receipt["candidate_selections"] = candidate_receipt[
            "candidate_selections"
        ]
    return route


__all__ = [
    "KNOWLEDGE_STORE_RELEASE_SCHEMA",
    "KnowledgeStore",
    "KnowledgeStoreBinding",
    "KnowledgeStoreError",
    "build_knowledge_store_supply",
    "load_knowledge_store_binding",
    "qualify_id",
]
