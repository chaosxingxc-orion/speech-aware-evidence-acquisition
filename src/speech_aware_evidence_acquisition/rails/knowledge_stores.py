"""Independent pinned knowledge stores composed behind the shared KB rails."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
import re
import threading
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

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
#: ``alternates`` (coordinator amendment, 2026-09-28, docs/superpowers/specs/
#: 2026-09-27-same-flight-supply-variant-instrument-design.md, "Coordinator
#: amendment (2026-09-28)"): zero or more ADDITIONAL pinned release+snapshot
#: pairs this store also declares, reachable only through a supply-variant
#: arm's release-swap route (``rails.supply_variants.SupplyVariantReleaseSwap``)
#: -- never loaded onto the ordinary composite snapshot every arm's router
#: builds from by default. Absent, every store composes exactly as it always
#: did.
_STORE_OPTIONAL_KEYS = frozenset(
    {"phase_supply", "candidate_supply", "context_supply", "alternates"}
)
_ALTERNATE_KEYS = frozenset({"release", "snapshot"})
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
class KnowledgeStoreAlternate:
    """One additional pinned release+snapshot a store's base config declares.

    Coordinator amendment, 2026-09-28: the arm's own release-swap override
    names an alternate by its ``release_pin["relpath"]``; the alternate's
    bytes are validated with the SAME rigor as the primary (schema, hash and
    cross-check) only at the point a router actually resolves it
    (``core.flight.runtime.FlightRuntime._supply_action_router``), by
    substituting these pins for the store's primary ones and re-running
    :func:`load_knowledge_store_binding` -- so declaring an alternate that is
    never selected by any arm costs no extra load at flight assembly.
    """

    release_pin: Mapping[str, str]
    snapshot_pin: Mapping[str, str]

    def as_json(self) -> dict[str, object]:
        return {"release": dict(self.release_pin), "snapshot": dict(self.snapshot_pin)}


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
    # Coordinator amendment, 2026-09-28: declared LAST, so every store parsed
    # before this field existed composes byte-identically (empty tuple).
    alternates: tuple[KnowledgeStoreAlternate, ...] = field(default_factory=tuple)

    def alternate(self, release_relpath: str) -> "KnowledgeStoreAlternate":
        for alt in self.alternates:
            if alt.release_pin["relpath"] == release_relpath:
                return alt
        raise KnowledgeStoreError(
            f"knowledge store {self.store_id!r} declares no alternate release "
            f"{release_relpath!r}; declared alternates are "
            f"{[a.release_pin['relpath'] for a in self.alternates]}"
        )


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
        raw_alternates = spec.get("alternates", [])
        if not isinstance(raw_alternates, Sequence) or isinstance(
            raw_alternates, (str, bytes)
        ):
            raise KnowledgeStoreError(
                f"knowledge store {store_id} alternates must be a list"
            )
        alternates: list[KnowledgeStoreAlternate] = []
        seen_release_relpaths = {release_pin["relpath"]}
        for index, raw_alternate in enumerate(raw_alternates):
            if not isinstance(raw_alternate, Mapping) or set(raw_alternate) != _ALTERNATE_KEYS:
                raise KnowledgeStoreError(
                    f"knowledge_stores[{store_id!r}].alternates[{index}] must "
                    f"carry exactly {sorted(_ALTERNATE_KEYS)}"
                )
            alt_release_pin = _pin(
                raw_alternate["release"],
                f"knowledge_stores[{store_id!r}].alternates[{index}].release",
            )
            alt_snapshot_pin = _pin(
                raw_alternate["snapshot"],
                f"knowledge_stores[{store_id!r}].alternates[{index}].snapshot",
            )
            if alt_release_pin["relpath"] in seen_release_relpaths:
                raise KnowledgeStoreError(
                    f"knowledge store {store_id} declares the same alternate "
                    f"release relpath twice: {alt_release_pin['relpath']!r}"
                )
            seen_release_relpaths.add(alt_release_pin["relpath"])
            alternates.append(
                KnowledgeStoreAlternate(
                    release_pin=alt_release_pin, snapshot_pin=alt_snapshot_pin,
                )
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
            tuple(alternates),
        )
    proxy = MappingProxyType(stores)
    composite = _composite(proxy)
    return KnowledgeStoreBinding(proxy, composite, composite.content_hash())


def declared_alternate_release_relpaths(
    raw_stores: object,
) -> Mapping[str, tuple[str, ...]]:
    """Best-effort ``{store_id: (alternate release relpath, ...)}`` off the
    RAW, not-yet-loaded ``knowledge_stores`` config mapping.

    Coordinator amendment, 2026-09-28: this is what
    ``rails.native_episode_config`` passes to
    ``rails.supply_variants.parse_supply_variants`` as
    ``declared_alternate_relpaths``, so an arm's release-swap override is
    refused by NAME before any contact when it names a release the store's
    base config does not also declare. Malformed shapes are ignored here
    rather than raised: this function only narrows what a knob path may
    legally name; :func:`load_knowledge_store_binding` is what actually
    hash-verifies an alternate's bytes once an arm selects it, and raises by
    name on anything this pre-check let through.
    """

    if not isinstance(raw_stores, Mapping):
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for store_id, spec in raw_stores.items():
        if not isinstance(store_id, str) or not isinstance(spec, Mapping):
            continue
        raw_alternates = spec.get("alternates")
        if not isinstance(raw_alternates, Sequence) or isinstance(
            raw_alternates, (str, bytes)
        ):
            continue
        relpaths = []
        for alternate in raw_alternates:
            if not isinstance(alternate, Mapping):
                continue
            release = alternate.get("release")
            if isinstance(release, Mapping) and isinstance(release.get("relpath"), str):
                relpaths.append(release["relpath"])
        result[store_id] = tuple(relpaths)
    return result


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
        DEFAULT_MAX_SLURP_CANDIDATES,
        build_candidate_semantic_supply,
        candidate_state_read_parameters,
        load_candidate_semantic_supply_specs,
    )
    from .governed_context_supply import (
        SOURCE_SCOPED_CONTEXT_FUSE_POLICY_ID,
        SOURCE_SCOPED_CONTEXT_PROVIDER_ID,
    )

    from .knowledge_provider import resolve_provider, resolve_scenario_gate

    from .stage3_delta_supply import (
        STAGE3_DELTA_CONTEXT_PROVIDER_ID,
        STAGE3_DELTA_NODES,
        STAGE3_DELTA_SCENARIO_GATE_KEY,
        STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON,
        STAGE3_DELTA_STORE_ROLE,
        STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID,
    )
    from .artifact_results import SLURP_HYPOTHESIS_CONTENT_ID
    from .slurp_intent_hypotheses import (
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
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
    slot_target_indices = {}
    for store_id in requested:
        index = build_released_target_index(
            binding.store(store_id), data_root=data_root,
            legal_candidate_ids=tuple(legal_candidate_ids or ()),
        )
        if index is not None:
            target_indices[store_id] = index
            if index.receipt["relation_policy_id"] == "authored-slot-intent-bindings-v1":
                slot_target_indices[store_id] = build_released_target_index(
                    binding.store(store_id), data_root=data_root,
                    legal_candidate_ids=tuple(legal_candidate_ids or ()), target_axis="slot-type",
                )
    callbacks, explicit_specs_by_store, specs_by_store, receipts = {}, {}, {}, {}
    context_specs: dict[tuple[str, str], object] = {}
    # S3-4s (owner decision 106, 2026-09-23): a stage3-deltas store's
    # UNCONDITIONAL route on the program's FIRST phase. Kept in its OWN map,
    # never in ``context_specs``, for two reasons: (1) ``route`` /
    # ``automatic_for_phase`` are never consulted for the first phase (a
    # first-phase selection has no preceding ``advance``; see the comment
    # above ``plain_later_phase_specs``), so a first-phase entry there would
    # be dead weight that only risked being dispatched by mistake; and
    # (2) ``specs_by_store`` feeds ``core.flight.runtime._resolve_phase_supply``'s
    # ``merged`` map, whose first-phase entry must stay the retrieval
    # ``PhaseSupplySpec`` the prepared-seed loader expects. The route is
    # served by ``bootstrap_first_phase`` / ``unconditional_first_phase``.
    first_phase_context_specs: dict[str, object] = {}
    #: Per-row receipt of every stage3-deltas route that supplied NOTHING
    #: (2026-09-23 fix, ``_stage3_delta_local_supply``). Keyed exactly as the
    #: candidate route's own per-row audits are
    #: (``phase:sample_id:query_state_sha256``) and published on
    #: ``route.receipt["delta_supply"]``, so a flight receipt says which node
    #: of which row took no supply step and why, instead of the skip being
    #: invisible.
    delta_supply_audits: dict[str, object] = {}
    #: Per-row receipt of every first-occurrence projection this route applied
    #: to a sealed Perception state that named one intent more than once
    #: (2026-09-23 ARM fix). Recorded ONLY when the projection actually
    #: dropped a position, keyed exactly as the skip audits are, and published
    #: on ``route.receipt["delta_candidate_projection"]`` -- so "this row's
    #: candidate list was deduplicated, exactly as the plan's own candidate
    #: route deduplicated it" is a count a reader can assert on, never a
    #: silent normalisation.
    delta_candidate_projection_audits: dict[str, object] = {}
    #: ITERATION 3 (2026-09-24): the parsed, registry-resolved row-level
    #: APPLICATION gate of each candidate-bound route that declares one,
    #: keyed ``(store_id, phase)``. Built ONCE, at config load, by
    #: ``_validate_stage3_delta_context_spec`` -- a route without a
    #: ``scenario_gate`` key has no entry here and behaves byte-identically
    #: to its ungated self.
    delta_scenario_gates: dict[tuple[str, str], object] = {}
    #: Per-row receipt of EVERY gate decision, open and closed alike, keyed
    #: exactly as the skip audits are and published on
    #: ``route.receipt["delta_scenario_gate"]`` ONLY when some route declares a
    #: gate. Both outcomes are recorded because "the gate closed here" is only
    #: readable against "and it was open there": a receipt carrying closures
    #: alone cannot say what share of rows the gate actually withheld. Labels
    #: and counts only -- a scenario name, a candidate count and a boolean.
    delta_scenario_gate_audits: dict[str, object] = {}
    #: How this route reads each candidate state phase, memoised at BUILD time
    #: from the plan's own candidate routes
    #: (``rails.candidate_semantic_supply.candidate_state_read_parameters``).
    delta_candidate_reads: dict[str, object] = {}
    delta_supply_lock = threading.Lock()
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

    def _build_stage3_delta_provider(store, *, raw_spec=None):
        """Resolve and build the registered stage3-delta provider over one
        store released delta pool. Re-derived per call, never cached on the
        router, mirroring the source-scoped provider own re-resolve-per-call
        precedent just below.

        S3-4s: ``raw_spec`` selects WHICH registered provider and which
        node slice. Without it (every pre-S3-4s call site, and the
        pre-flight "does the pool build cleanly" proof) the candidate-bound
        provider is built with no node filter -- byte-identically to its
        pre-S3-4s self.
        """

        provider_id = STAGE3_DELTA_CONTEXT_PROVIDER_ID
        options: dict[str, object] = {}
        if isinstance(raw_spec, Mapping):
            provider_id = str(raw_spec.get("provider", provider_id))
            node_target = raw_spec.get("node_target")
            if isinstance(node_target, str) and node_target:
                options["node_target"] = node_target
        provider = resolve_provider(provider_id, **options)
        provider.build(
            [value.as_json() for value in store.snapshot.values],
            policy_id=store.snapshot.builder_policy_id,
        )
        return provider

    def _validate_stage3_delta_context_spec(raw_spec, *, store, phase):
        """The CANDIDATE-BOUND branch: a later supplied phase only.

        S3-4s admits ONE further optional key, ``node_target``: which node's
        slice of the store this phase is served from (spec S3-4s, "filtered
        to the rows whose ``node_target`` is that phase's node"). A spec
        without it is the exact pre-S3-4s spec and validates identically.

        Iteration 3 (2026-09-24) admits ONE more, ``scenario_gate``: on WHICH
        ROWS this node takes the supply at all. Optional in exactly the same
        sense -- a spec without it is the pre-iteration-3 spec and validates,
        selects and supplies identically.
        """

        phases = program.phase_names()
        candidate_state_phase = raw_spec.get("candidate_state_phase")
        cap = raw_spec.get("cap")
        node_target = raw_spec.get("node_target")
        if (
            store.store_role != STAGE3_DELTA_STORE_ROLE
            or not (
                {"provider", "candidate_state_phase", "cap", "rank_by"}
                <= set(raw_spec)
                <= {
                    "provider", "candidate_state_phase", "cap", "rank_by",
                    "node_target", STAGE3_DELTA_SCENARIO_GATE_KEY,
                }
            )
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
            or (
                "node_target" in raw_spec
                and (node_target not in STAGE3_DELTA_NODES or node_target == first_phase)
            )
        ):
            raise KnowledgeStoreError(
                "stage3-deltas context_supply requires a candidate-bound, capped, "
                "prior_score-ranked spec on a later supplied phase"
            )
        # 2026-09-23, the CELL-1 ARM abort. Resolve HOW this state is read
        # here, at build time, not per row: a plan whose candidate routes
        # disagree about one Perception phase is a config defect and must be
        # refused before a contact is spent, never discovered on row 75.
        _delta_candidate_read(candidate_state_phase)
        # ITERATION 3: the OPTIONAL row-level application gate, parsed and
        # resolved in the SAME place and for the SAME reason -- a gate naming
        # a scenario this carrier does not have, or an intent id written where
        # a scenario belongs, is a config defect, and the only authority on
        # which scenarios exist is the legal candidate inventory this route
        # already binds against. An explicit ``null`` is refused too: a spec
        # that carries the key is asking for a gate.
        if STAGE3_DELTA_SCENARIO_GATE_KEY in raw_spec:
            legal = tuple(legal_candidate_ids or ())
            if not legal:
                raise KnowledgeStoreError(
                    "stage3-deltas context_supply requires the task adapter "
                    "authoritative legal candidate inventory"
                )
            try:
                delta_scenario_gates[(store.store_id, phase)] = resolve_scenario_gate(
                    raw_spec[STAGE3_DELTA_SCENARIO_GATE_KEY], legal_intent_ids=legal
                )
            except RailsError as error:
                raise KnowledgeStoreError(str(error)) from error

    def _validate_stage3_delta_unconditional_spec(raw_spec, *, store, phase):
        """The UNCONDITIONAL branch (S3-4s), the FIRST phase's own.

        The pre-S3-4s ``context_supply`` contract insisted on a LATER
        supplied phase, for a real reason: a later phase has a preceding
        ``advance`` to carry its per-row decision, and the first phase has
        none. The Perception node's deltas are admitted here without
        weakening that reason rather than around it: the selection carries
        NO per-row term at all (``rails.stage3_delta_supply.
        select_unconditional_stage3_delta_values``), so it is decided once
        per flight and seeded, exactly as every other first-phase selection
        in this router is (``bootstrap_first_phase``). ``candidate_state_phase``
        is therefore REFUSED here, not merely optional: a spec that names one
        is asking for a per-row binding this route cannot honour.

        Iteration 3's ``scenario_gate`` is refused for exactly that reason and
        by exactly that rule (the key set below is an EQUALITY): the gate reads
        the row's Perception candidates, and this is the node that produces
        them, so at the moment it is served there is nothing to gate on. A cell
        that wants the Perception deltas withheld simply omits this route.
        """

        cap = raw_spec.get("cap")
        node_target = raw_spec.get("node_target")
        if (
            store.store_role != STAGE3_DELTA_STORE_ROLE
            or set(raw_spec) != {"provider", "cap", "rank_by", "node_target"}
            or raw_spec.get("rank_by") != "prior_score"
            or phase != first_phase
            or program.phase(phase).knowledge != "supplied"
            or node_target != phase
            or node_target not in STAGE3_DELTA_NODES
            or isinstance(cap, bool)
            or not isinstance(cap, int)
            or cap < 1
        ):
            raise KnowledgeStoreError(
                "stage3-deltas unconditional context_supply requires a capped, "
                "prior_score-ranked, node-targeted spec on the program's first "
                "supplied phase, with no candidate_state_phase"
            )

    def _delta_candidate_read(candidate_state_phase):
        """``(compact_source_phase, max_candidates, projection_policy)`` for one
        candidate state phase -- the reading the plan's OWN candidate routes
        perform over the very same sealed bytes.

        2026-09-23, the CELL-1 ARM abort after 304 contacts. WHICH FORM the
        state has was already read off the phase's declared output contract
        (the comment in ``_stage3_delta_local_supply``); WHICH TOLERANCE it is
        read with was not, and the delta route was the only reader of that
        state in the whole plan that read it without the bounded
        first-occurrence projection. The sealed PLAN arm carries 25 rows in
        1,080 whose Perception answer names one legal intent more than once,
        and it completed every one of them, because its only reader of that
        state -- the slot-contracts candidate supply -- declares
        ``projection_policy`` and ``max_candidates`` and the parser projects
        the duplicates away by first occurrence. The delta route asked the
        SAME parser entry for the strict canonical reading and raised
        "candidate intent_ids must be unique and ordered".

        There is no second implementation and no new config key: the tuple
        comes from ``rails.candidate_semantic_supply.
        candidate_state_read_parameters`` over the specs this router already
        loaded, so the two routes cannot drift apart. Where a plan declares no
        SLURP candidate route over that phase there is no sibling to match, and
        the documented default keeps the route's own pre-fix bound while
        adopting the same first-occurrence projection every other reader of a
        compact SLURP Perception state in this codebase uses
        (``rails.role_context``, ``rails.node_context_policy``,
        ``rails.slot_binding_view``).
        """

        memo = delta_candidate_reads.get(candidate_state_phase)
        if memo is not None:
            return memo
        candidate_format_id = getattr(
            program.phase(candidate_state_phase), "response_format_id", None
        )
        if candidate_format_id != SLURP_HYPOTHESIS_CONTENT_ID:
            # Not the compact contract: the canonical four-key reading, byte-
            # identically to the pre-fix router. A projection policy is not
            # even legal without a compact source phase.
            memo = (None, len(frozenset(legal_candidate_ids or ())), None)
            delta_candidate_reads[candidate_state_phase] = memo
            return memo
        try:
            sibling = candidate_state_read_parameters(
                candidate_specs, candidate_state_phase=candidate_state_phase
            )
        except RailsError as error:
            raise KnowledgeStoreError(str(error)) from error
        if sibling is not None:
            memo = (candidate_state_phase, sibling[0], sibling[1])
        else:
            maximum = len(frozenset(legal_candidate_ids or ())) or 1
            memo = (
                candidate_state_phase,
                maximum,
                (
                    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
                    if maximum > DEFAULT_MAX_SLURP_CANDIDATES
                    else BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
                ),
            )
        delta_candidate_reads[candidate_state_phase] = memo
        return memo

    def _record_delta_candidate_projection(
        *,
        store_id,
        phase,
        node_target,
        sample_id,
        query_state,
        projection,
    ):
        """Record one first-occurrence projection that DROPPED a position.

        Identities, counts and hashes only -- never a candidate's text --
        matching every other receipt in this study. A clean list projects to
        itself and is never recorded, so a non-empty map means exactly "these
        rows named an intent more than once".
        """

        key = f"{phase}:{sample_id}:{query_state.content_hash()}"
        entry = {
            "node": node_target,
            "phase": phase,
            "sample_id": sample_id,
            "store_id": store_id,
            "raw_positions": len(projection.raw_positions),
            "retained_positions": len(
                {item.intent_id for item in projection.raw_positions}
            ),
            "projection_policy_id": projection.projection_policy_id,
            "projection_policy_sha256": projection.projection_policy_sha256,
            "original_text_sha256": projection.original_text_sha256,
            "projected_content_sha256": projection.projected_content_sha256,
        }
        with delta_supply_lock:
            delta_candidate_projection_audits[key] = entry

    def _record_delta_scenario_gate(
        *,
        store_id,
        phase,
        node_target,
        sample_id,
        query_state,
        gate,
        decision,
    ):
        """Record ONE row-level gate decision at one node, open or closed.

        Labels and counts only -- the majority scenario NAME, how many
        candidates it was read from, and whether the gate closed. No utterance,
        no transcript, no gold label, no candidate text and no statement. Keyed
        and locked exactly as the skip audits beside it are, and idempotent for
        the same reason: one router serves every row of a split, a campaign
        walks rows in parallel, and re-deciding the same (phase, row, query
        state) is a pure function that returns the same answer.
        """

        key = f"{phase}:{sample_id}:{query_state.content_hash()}"
        entry = {
            "node": node_target,
            "phase": phase,
            "sample_id": sample_id,
            "store_id": store_id,
            "policy_id": decision.policy_id,
            "gated_scenarios": list(gate.scenarios),
            "majority_scenario": decision.majority_scenario,
            "candidate_count": decision.candidate_count,
            "closed": decision.closed,
        }
        with delta_supply_lock:
            delta_scenario_gate_audits[key] = entry

    def _record_delta_supply_skip(
        *,
        store_id,
        phase,
        node_target,
        sample_id,
        query_state,
        already_acquired,
        reason,
        majority_scenario=None,
    ):
        """Record one stage3-deltas route that introduced nothing.

        Identities and counts only -- never a statement, never a candidate's
        text -- matching every other supply receipt in this study. Written
        under a lock because one router serves every row of a split and a
        campaign walks rows in parallel; re-recording the SAME key with the
        same decision is idempotent, exactly as the candidate route's audits
        are.
        """

        key = f"{phase}:{sample_id}:{query_state.content_hash()}"
        entry = {
            "node": node_target,
            "phase": phase,
            "sample_id": sample_id,
            "store_id": store_id,
            "selected": 0,
            "already_acquired": already_acquired,
            "reason": reason,
        }
        # Declared LAST and omitted when absent, so every skip receipt this
        # router has ever written for an ungated route is byte-identical to
        # its pre-iteration-3 self.
        if majority_scenario is not None:
            entry["majority_scenario"] = majority_scenario
        with delta_supply_lock:
            delta_supply_audits[key] = entry

    def _stage3_delta_local_supply(store, raw_spec, context, *, phase=None):
        """Candidate-bound, prior_score-capped Solver supply for one
        stage3-deltas store (S3-6): read the row Perception candidate
        intents off the configured candidate_state_phase state, then
        route them through the registered Stage3DeltaCandidateProvider
        (rails.stage3_delta_supply.select_stage3_delta_values does the
        actual selection).

        Returns ``None`` -- no supply step at all for this phase -- when the
        route introduces nothing new; see the SUPPLIES NOTHING note below the
        selection.
        """

        candidate_state_phase = raw_spec["candidate_state_phase"]
        cap = raw_spec["cap"]
        node_target = raw_spec.get("node_target")
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
        # 2026-09-23, the CELL-1 generation smoke's second failure. A role
        # state is sealed as the model's OWN response bytes
        # (``rails.controllers.seal_phase_response_state`` is handed
        # ``completion.text``). When the candidate state phase answers under
        # the registered ``slurp-intent-hypotheses-v1`` structured-output
        # contract, those bytes are the COMPACT document -- ``{"candidates":
        # [...]}`` and nothing else, because that is the whole schema
        # (``rails.artifact_results.slurp_intent_hypotheses_response_format``:
        # ``required: ["candidates"]``, ``additionalProperties: false``).
        # The four-key document (``schema``, ``semantics``, ``sample_id``,
        # ``candidates``) is the CONSUMPTION view, rebuilt at each reading
        # site from those sealed bytes plus that site's own trusted
        # phase/sample identity; it is never what the wire carried and never
        # what was sealed. Reading the state without naming a compact source
        # phase therefore demands three keys a native episode can never have
        # sealed, and the smoke died at ``solver_0_input`` after four
        # Perception contacts with "hypothesis state must contain exactly
        # ['candidates', 'sample_id', 'schema', 'semantics']".
        #
        # WHICH form to expect is not guessed from the bytes: it is read off
        # the phase's own DECLARED output contract, exactly as
        # ``rails.slot_binding_view`` already decides the same question
        # ("response_format_id != 'slurp-intent-hypotheses-v1'"). A phase
        # that declares the compact contract is read through the compact
        # branch -- which additionally binds ``state_kind``/``state_id`` to
        # that phase and sample, a STRONGER check than the canonical branch
        # makes -- and every other phase is read canonically, byte-
        # identically to the pre-fix router. Nothing is relaxed: the parser
        # stays strict on both sides, and a fragment cannot forget to say
        # which it is, because it never says it at all.
        #
        # 2026-09-23, the CELL-1 ARM abort after 304 metered contacts, at row
        # ~75 of 1,080. WHICH TOLERANCE the state is read with is decided the
        # same way and in the same ONE place the plan's own candidate route
        # decides it (``_delta_candidate_read``): same parser entry, same
        # bound, same first-occurrence projection, so a Perception answer that
        # names one legal intent three times -- 2.3 % of the sealed PLAN arm's
        # rows do -- projects for this route exactly as it projects for the
        # slot-contracts candidate supply beside it.
        compact_source_phase, max_candidates, projection_policy = (
            _delta_candidate_read(candidate_state_phase)
        )
        try:
            hypothesis_state = parse_slurp_intent_hypothesis_state(
                matches[0],
                expected_sample_id=str(sample_id),
                legal_intent_ids=legal,
                max_candidates=max_candidates,
                compact_source_phase=compact_source_phase,
                projection_policy=projection_policy,
            )
        except SlurpIntentHypothesisError as error:
            # The DISPOSITION is the sibling's too, and deliberately so. The
            # plan's own candidate route raises
            # (``rails.candidate_semantic_supply``'s
            # ``CandidateSemanticSupplyError``) on a state it cannot read, and
            # it reads the SAME bytes with the SAME parameters at the SOLVER,
            # which the native role graph visits BEFORE the Reviewer and the
            # Planner (``analysis.native_episode_dry_run.
            # NATIVE_ROLE_GRAPH_ORDER``). So after this fix the delta route
            # can never be the first reader to refuse a row: anything it
            # refuses, the plan's own route already refused one node earlier,
            # and a row this route kills is a row the PLAN arm would have
            # killed too. Degrading here instead would hide exactly the
            # wiring defects the two strictness regressions in
            # ``tests/unit/test_stage3_delta_node_routes.py`` exist to catch
            # (a canonical document under the compact contract; a state
            # sealed for another sample).
            raise KnowledgeStoreError(str(error)) from error
        if hypothesis_state.projection is not None and len(
            {item.intent_id for item in hypothesis_state.projection.raw_positions}
        ) != len(hypothesis_state.projection.raw_positions):
            _record_delta_candidate_projection(
                store_id=store.store_id,
                phase=phase,
                node_target=node_target,
                sample_id=sample_id,
                query_state=query_state,
                projection=hypothesis_state.projection,
            )
        candidate_facet_ids = tuple(item.intent_id for item in hypothesis_state.candidates)

        # ITERATION 3 (2026-09-24), the coverage-gated application policy. The
        # general-scenario diagnostic (docs/results/2026-09-24-slurp-general-
        # scenario-diagnostic.md) established that on the strata the store has
        # no reach into, the DERANGEMENT TWIN loses as much as the arm does:
        # the loss there is the FORM cost of carrying a supply, not the content
        # of any delta. So the fix is not a better delta, it is not applying
        # the store where it should not apply.
        #
        # The gate reads the SAME projected candidate list the selection below
        # reads -- after the first-occurrence projection, before any store
        # lookup -- and NOTHING ELSE. No gold, no reference transcript, no
        # future turn, no scorer: only the sealed Perception state of this same
        # episode, which this route already holds. A CLOSED gate takes no
        # supply step at all, returning ``None`` exactly as the "introduces
        # nothing new" branch below does, so a withheld node seals as an
        # ordinary ``organize`` step rather than an empty acquisition. An OPEN
        # gate changes nothing: control falls through to the identical
        # selection, and the supply is byte-identical to the ungated route's.
        gate = delta_scenario_gates.get((store.store_id, phase))
        if gate is not None:
            decision = gate.decide(candidate_facet_ids)
            _record_delta_scenario_gate(
                store_id=store.store_id,
                phase=phase,
                node_target=node_target,
                sample_id=sample_id,
                query_state=query_state,
                gate=gate,
                decision=decision,
            )
            if decision.closed:
                _record_delta_supply_skip(
                    store_id=store.store_id,
                    phase=phase,
                    node_target=node_target,
                    sample_id=sample_id,
                    query_state=query_state,
                    already_acquired=0,
                    reason=STAGE3_DELTA_SCENARIO_GATE_SKIP_REASON,
                    majority_scenario=decision.majority_scenario,
                )
                return None

        provider = _build_stage3_delta_provider(store, raw_spec=raw_spec)
        # 2026-09-23, the CELL-1 generation smoke's THIRD failure -- SUPPLIES
        # NOTHING. A node-filtered, candidate-bound slice can legitimately
        # select NOTHING for a row: the Reviewer slice of the released
        # stage3-deltas store addresses 30 of the 39 legal intents, so a row
        # whose Perception candidates all fall in the other 9 matches no
        # Reviewer delta at all (rows 2 and 4 of the four-row smoke). The
        # pre-fix route still returned a PhaseSupply for that row, and
        # ``rails.controllers.advance_phase_response_state`` makes a supply --
        # ANY supply -- an ``action_kind="acquire"`` transition, so the wave
        # carried neither a new value nor a new facet and
        # ``AgentStepTransition.validate`` refused it ("acquire must introduce
        # at least one new value or facet"): the episode died at the openJiuwen
        # vertex ``reviewer_0_input`` after 12 metered contacts. The Solver
        # never showed it because the Solver phase composes THREE supplies
        # (slot-contracts candidate_supply, train-exemplars phase_supply and
        # this route), so a sibling always carried a value; the Reviewer and
        # the Planner are served by this store ALONE.
        #
        # Two ways a route can introduce nothing, and both end here rather
        # than in a transition:
        #
        # * no delta of this node's slice matches the row's candidates; or
        # * every one that does is ALREADY in this episode's
        #   ``QueryState.retrieved_value_ids`` -- what a REVISITED node sees,
        #   because a prepared per-node selection is a pure function of
        #   (phase, sample) and the agent's value set is cumulative across
        #   phases (the same hazard ``rails.controllers.
        #   restrict_repeat_visit_supply`` caught at the runner seam after the
        #   2026-09-17 cell B1 abort; this route now refuses to hand that seam
        #   an empty acquisition in the first place).
        #
        # The pool is ranked in FULL and capped AFTER the already-acquired ids
        # are dropped, so the per-node cap counts NEW values (owner ruling,
        # 2026-09-23). On a first visit nothing is visible, ``fresh`` is the
        # whole ranking and ``fresh[:cap]`` is byte-identically the pre-fix
        # ``k=cap`` selection.
        pool_size = max(len(store.snapshot.values), 1)
        ranking = provider.candidates(candidate_facet_ids, k=pool_size)
        ranked_ids = tuple(entry.entry_id for entry in ranking.entries)
        visible_value_ids = frozenset(
            getattr(query_state, "retrieved_value_ids", ()) or ()
        )
        fresh_ids = tuple(
            value_id
            for value_id in ranked_ids
            if qualify_id(store.store_id, value_id) not in visible_value_ids
        )
        already_acquired = len(ranked_ids) - len(fresh_ids)
        selected_ids = fresh_ids[:cap]
        if not selected_ids:
            _record_delta_supply_skip(
                store_id=store.store_id,
                phase=phase,
                node_target=node_target,
                sample_id=sample_id,
                query_state=query_state,
                already_acquired=already_acquired,
                reason=(
                    "every ranked delta of this node slice is already acquired "
                    "in this episode"
                    if already_acquired
                    else "no delta of this node slice matches the row candidates"
                ),
            )
            return None
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
            action_target_ref=(
                f"{STAGE3_DELTA_CONTEXT_PROVIDER_ID}:cap={cap}"
                if node_target is None
                else f"{STAGE3_DELTA_CONTEXT_PROVIDER_ID}:node={node_target}:cap={cap}"
            ),
        ).validate()

    def _stage3_delta_unconditional_ids(store, raw_spec):
        """The UNCONDITIONAL first-phase selection (S3-4s): the same capped,
        ``prior_score``-ranked, node-filtered value ids on every row of the
        split. A pure function of the store, so it is computed ONCE per
        flight and seeded per sample."""

        provider = _build_stage3_delta_provider(store, raw_spec=raw_spec)
        ranking = provider.candidates((), k=raw_spec["cap"])
        return tuple(entry.entry_id for entry in ranking.entries)

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
            elif provider_id == STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID:
                # S3-4s: the first phase's own branch (see the validator).
                _validate_stage3_delta_unconditional_spec(
                    raw_spec, store=store, phase=phase
                )
                if store_id in first_phase_context_specs:
                    raise KnowledgeStoreError(
                        "one store declares two unconditional first-phase routes"
                    )
                first_phase_context_specs[store_id] = raw_spec
                continue
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
            if providers_used & {
                STAGE3_DELTA_CONTEXT_PROVIDER_ID, STAGE3_DELTA_UNCONDITIONAL_PROVIDER_ID
            }:
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
        # S3-4s: the unconditional first-phase route is scoped supply too --
        # for the overlap guard and for the receipt -- even though it is not
        # dispatched through ``route``.
        unconditional_phases = (
            {first_phase} if store_id in first_phase_context_specs else set()
        )
        if set(store.phase_supply).intersection(scoped_phases | unconditional_phases):
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
        if (
            not specs and not store_candidate_specs and not scoped_phases
            and not unconditional_phases and store_id not in on_demand
            and not any(
                spec.exemplar_candidate_proposal is not None
                and spec.exemplar_candidate_proposal["intent_store_id"] == store_id
                for spec in candidate_specs.values()
            )
        ):
            raise KnowledgeStoreError(f"knowledge store {store_id} has no phase_supply")
        specs_by_store[store_id] = {**specs, **store_candidate_specs}
        # S3-4s: the FIRST-phase unconditional entry is deliberately left out
        # of ``specs_by_store`` (see ``first_phase_context_specs`` above);
        # everything else is recorded exactly as before.
        specs_by_store[store_id].update({
            phase: raw for phase, raw in store.context_supply.items()
            if (store_id, phase) in context_specs
        })
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
        if scoped_phases or unconditional_phases:
            receipts[store_id]["context_supply"] = sorted(
                scoped_phases | unconditional_phases
            )
        if unconditional_phases:
            receipts[store_id]["unconditional_context_supply"] = {
                "phase": first_phase,
                "provider": first_phase_context_specs[store_id]["provider"],
                "node_target": first_phase_context_specs[store_id]["node_target"],
                "cap": first_phase_context_specs[store_id]["cap"],
                "selected_value_ids": list(
                    _stage3_delta_unconditional_ids(
                        store, first_phase_context_specs[store_id]
                    )
                ),
            }

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
        # S3-4s: every store with an unconditional first-phase route
        # contributes the SAME capped, node-filtered, prior_score-ranked
        # value ids to every row of the split. No facets: the route supplies
        # values only, exactly as the candidate-bound route does.
        for store_id, raw_spec in first_phase_context_specs.items():
            selected = _stage3_delta_unconditional_ids(
                binding.store(store_id), raw_spec
            )
            if not selected:
                continue
            for sample_id in sorted(speech_packet_bindings):
                values_by_sample.setdefault(sample_id, []).extend(
                    qualify_id(store_id, value_id) for value_id in selected
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
                return _stage3_delta_local_supply(
                    store, raw_spec, context, phase=phase
                )
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

    # Optional consumption of one source-bound proposal by the existing SLURP
    # candidate provider. The same proposal is later exposed to every native
    # continuation role; raw Perception is never replaced.
    proposal_specs = {
        phase: spec for phase, spec in candidate_specs.items()
        if spec.exemplar_candidate_proposal is not None
    }
    proposal_objects, proposal_audits, proposal_required_ids = {}, {}, {}
    proposal_lock = threading.Lock()
    proposal_intent_indexes = {}
    if proposal_specs:
        if len(proposal_specs) != 1:
            raise KnowledgeStoreError("candidate proposal requires exactly one Solver route")
        for phase, spec in proposal_specs.items():
            option = spec.exemplar_candidate_proposal
            exemplar_id, intent_id = option["exemplar_store_id"], option["intent_store_id"]
            if exemplar_id not in binding.store_ids or intent_id not in binding.store_ids:
                raise KnowledgeStoreError("candidate proposal names an unbound store")
            if (
                binding.store(exemplar_id).store_role != "train-exemplars"
                or binding.store(exemplar_id).snapshot.source_partition_role != "train"
                or (exemplar_id, phase) not in plain_later_phase_specs
                or (exemplar_id, phase) in context_specs
                or binding.store(intent_id).store_role != "intent-boundaries"
                or option["max_candidates"] > len(tuple(legal_candidate_ids))
            ):
                raise KnowledgeStoreError("candidate proposal stores or candidate bound are incompatible")
            index = build_released_target_index(
                binding.store(intent_id), data_root=data_root,
                legal_candidate_ids=tuple(legal_candidate_ids),
            )
            if index is None:
                raise KnowledgeStoreError("candidate proposal needs a released authored intent index")
            proposal_intent_indexes[phase] = index

    def proposal_key(context, original):
        return f"{context.sample_id}:{original.content_hash()}"

    def resolve_proposal(phase, context, local_supplies):
        from .slurp_candidate_proposal import build_candidate_proposal_from_selection
        spec = proposal_specs[phase]
        option = spec.exemplar_candidate_proposal
        original = candidate_callback.candidate_state_for(phase, context)
        # Require exactly the committed context order or its one real trailing
        # Perception response staged by the shared native transition.
        state_ids = tuple(item.state_id for item in context.agent_states)
        declared = context.query_state.agent_state_ids
        if state_ids != declared and not (
            len(state_ids) == len(declared) + 1 and state_ids[:-1] == declared
            and context.agent_states[-1].source_query_state_sha256 == context.query_state.content_hash()
            and context.prior_response_sha256s
            and context.agent_states[-1].source_response_sha256 == context.prior_response_sha256s[-1]
        ):
            raise KnowledgeStoreError("proposal source differs from the actual native context")
        parsed = parse_slurp_intent_hypothesis_state(
            original, expected_sample_id=context.sample_id,
            legal_intent_ids=tuple(legal_candidate_ids), max_candidates=3,
            compact_source_phase="perception",
            projection_policy=BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        )
        original_ids = tuple(item.intent_id for item in parsed.candidates)
        cap = (len(original_ids) if option["mode"] == "original-only"
               else option["max_candidates"])
        exemplar_id = option["exemplar_store_id"]
        if exemplar_id not in local_supplies:
            raise KnowledgeStoreError("proposal requires the actual same-visit exemplar selection")
        fresh = build_candidate_proposal_from_selection(
            sample_id=context.sample_id, original_state=original,
            parsed_candidates=original_ids, exemplar_snapshot=binding.store(exemplar_id).snapshot,
            exemplar_supply=local_supplies[exemplar_id], query_state=context.query_state,
            legal_candidate_ids=tuple(legal_candidate_ids), max_candidates=cap,
        )
        key = proposal_key(context, original)
        with proposal_lock:
            prior = proposal_objects.get(key)
            if prior is not None:
                # Revisions rebind rank/fusion to their current QueryState. The
                # first selection remains the proposal source; its values and
                # interpretation must be unchanged, not silently recomputed.
                fixed = {"exemplar_selection_sha256"}
                if ({k: v for k, v in fresh.as_json().items() if k not in fixed}
                        != {k: v for k, v in prior.as_json().items() if k not in fixed}):
                    raise KnowledgeStoreError("proposal changed after its first Solver visit")
                return prior, key
            proposal_objects[key] = fresh
            local = local_supplies[exemplar_id]
            proposal_audits[key] = {
                "schema": "saea-source-bound-candidate-proposal-supply-v1",
                "proposal": fresh.as_json(), "proposal_sha256": fresh.content_hash(),
                "config": dict(option),
                "selection_query_state_sha256": context.query_state.content_hash(),
                "exemplar_store": binding.store_receipt(exemplar_id),
                "exemplar_rank": local.rank_result.as_json(),
                "exemplar_fusion": local.fusion_decision.as_json(),
                "intent_index": dict(proposal_intent_indexes[phase].receipt),
            }
        return fresh, key

    def proposal_intent_supply(phase, context, proposal):
        from .knowledge import RankedFacet, RankResult, FusionDecision
        from .knowledge_provider import (
            SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
            SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
        )
        spec = proposal_specs[phase]
        store_id = spec.exemplar_candidate_proposal["intent_store_id"]
        store = binding.store(store_id)
        index = proposal_intent_indexes[phase]
        selected = tuple(dict.fromkeys(
            value_id for label in proposal.candidate_ids
            for value_id in index.mappings.get(label, ())
        ))
        missing = [label for label in proposal.candidate_ids if not index.mappings.get(label)]
        if missing:
            raise KnowledgeStoreError("candidate proposal has no released intent distinction")
        values = {value.value_id: value for value in store.snapshot.values}
        facets = tuple(dict.fromkeys(
            facet_id for value_id in selected for facet_id in values[value_id].associated_facet_ids
        ))
        rank = RankResult(
            snapshot_sha256=store.snapshot.content_hash(),
            query_state_sha256=context.query_state.content_hash(),
            ranking_policy_id=SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
            candidates=tuple(RankedFacet(facet_id=fid, score=float(len(facets)-i))
                             for i, fid in enumerate(facets)),
        ).validate()
        visible = set(context.query_state.retrieved_value_ids)
        added = tuple(vid for vid in selected if qualify_id(store_id, vid) not in visible)
        needed = tuple(qualify_id(store_id, vid) for vid in selected)
        if not added:
            return None, needed
        decision = FusionDecision(
            snapshot_sha256=store.snapshot.content_hash(),
            query_state_sha256=context.query_state.content_hash(),
            rank_result_sha256=rank.content_hash(),
            fusion_policy_id=SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
            supporting_facet_ids=tuple(dict.fromkeys(
                fid for vid in added for fid in values[vid].associated_facet_ids
            )),
            selected_value_ids=added,
        ).validate()
        local = PhaseSupply(rank_result=rank, fusion_decision=decision,
                            action_target_ref="candidate-proposal-intent-distinction").validate()
        return binding.qualify_supply(store_id, local, context.query_state), needed

    def candidate_proposal_for_context(context):
        matches = [item for item in context.agent_states if item.state_kind == "phase:perception"]
        if len(matches) != 1:
            raise KnowledgeStoreError("candidate proposal context requires one original Perception")
        key = proposal_key(context, matches[0])
        with proposal_lock:
            proposal = proposal_objects.get(key)
            required = proposal_required_ids.get(key)
        if proposal is None or required is None:
            raise KnowledgeStoreError("candidate proposal has not been supplied by its Solver visit")
        if (matches[0].state_id not in context.query_state.agent_state_ids
                or not set(required) <= set(context.query_state.retrieved_value_ids)):
            raise KnowledgeStoreError("candidate proposal sources and cards are not all visible")
        return proposal

    def automatic_for_phase(phase, context):
        query_state = getattr(context, "query_state", None)
        if query_state is None:
            raise KnowledgeStoreError("automatic context supply requires a QueryState")
        supplies = []
        local_supplies = {}
        for store_id in binding.store_ids:
            if (store_id, phase) not in context_specs:
                continue
            # A context route may decline this phase on this row: the
            # stage3-deltas route returns None when its node slice introduces
            # nothing new (``_stage3_delta_local_supply``, SUPPLIES NOTHING).
            # The phase then simply takes no supply step -- the same shape the
            # plain later-phase branch below has always had.
            context_supply = route(store_id, phase, context)
            if context_supply is None:
                continue
            supplies.append(
                binding.qualify_supply(store_id, context_supply, query_state)
            )
        for store_id in binding.store_ids:
            if (store_id, phase) in context_specs or (store_id, phase) not in plain_later_phase_specs:
                continue
            local_supply = route(store_id, phase, context)
            if local_supply is not None:
                local_supplies[store_id] = local_supply
                supplies.append(binding.qualify_supply(store_id, local_supply, query_state))
        proposal, proposal_id = (
            resolve_proposal(phase, context, local_supplies)
            if phase in proposal_specs else (None, None)
        )
        if candidate_callback is not None:
            candidate_supply = candidate_callback(
                phase, context, **({"candidate_proposal": proposal} if proposal else {}),
            )
            if candidate_supply is not None:
                supplies.append(candidate_supply)
        if proposal is not None:
            intent_supply, intent_ids = proposal_intent_supply(phase, context, proposal)
            if intent_supply is not None:
                supplies.append(intent_supply)
            spec = proposal_specs[phase]
            audit_key = f"{phase}:{context.sample_id}:{query_state.content_hash()}"
            selection = candidate_callback.receipt["candidate_selections"][audit_key]
            exemplar_id = spec.exemplar_candidate_proposal["exemplar_store_id"]
            required = (
                tuple(qualify_id(exemplar_id, item.value_id) for item in proposal.selected_exemplars)
                + tuple(selection["qualified_selected_value_ids"]) + intent_ids
            )
            with proposal_lock:
                if proposal_id in proposal_required_ids and proposal_required_ids[proposal_id] != required:
                    raise KnowledgeStoreError("proposal knowledge selection changed on a later visit")
                proposal_required_ids[proposal_id] = required
                audit = proposal_audits[proposal_id]
                if "required_value_ids" not in audit:
                    audit["required_value_ids"] = list(required)
                    audit["slot_selection_receipt_sha256"] = selection["selection_receipt_sha256"]
                    audit["supply_receipt_sha256"] = content_hash(audit)
        return _compose_supplies(supplies, query_state)

    def unconditional_first_phase(*, speech_packet_bindings, **_ignored):
        """S3-4s: ``{phase: {sample_id: (qualified value ids,)}}`` for every
        store declaring an unconditional first-phase route, or ``{}``.

        Published SEPARATELY from :func:`bootstrap_first_phase` so a flight
        that pins a ``prepared_phase_supply`` artifact for the first phase's
        RETRIEVAL store still gets this route composed on top of it
        (``core.flight.runtime._phase_supply_seeds``): the prepared artifact
        is a frozen selection of ONE store and cannot be asked about a store
        that did not exist when it was prepared. Absent as an attribute
        when no store declares the route, so every existing flight reads
        ``getattr(..., 'unconditional_first_phase', None) is None`` and
        behaves byte-identically.
        """

        by_sample: dict[str, list[str]] = {}
        for store_id, raw_spec in first_phase_context_specs.items():
            selected = _stage3_delta_unconditional_ids(
                binding.store(store_id), raw_spec
            )
            if not selected:
                continue
            for sample_id in sorted(speech_packet_bindings):
                by_sample.setdefault(sample_id, []).extend(
                    qualify_id(store_id, value_id) for value_id in selected
                )
        if not by_sample:
            return {}
        return {
            first_phase: {
                sample_id: tuple(value_ids)
                for sample_id, value_ids in sorted(by_sample.items())
            }
        }

    route.target_indices = MappingProxyType(target_indices)
    route.slot_target_indices = MappingProxyType(slot_target_indices)
    route.specs_by_store = specs_by_store
    route.bootstrap_first_phase = bootstrap_first_phase
    if first_phase_context_specs:
        route.unconditional_first_phase = unconditional_first_phase
    candidate_receipt = (
        None if candidate_callback is None else candidate_callback.receipt
    )
    route.receipt = {
        "schema": "saea-named-knowledge-store-routing-v1",
        "binding_sha256": binding.binding_sha256,
        "stores": receipts,
    }
    if any(
        raw_spec["provider"] == STAGE3_DELTA_CONTEXT_PROVIDER_ID
        for raw_spec in context_specs.values()
    ):
        # Grows during the flight, exactly as ``candidate_selections`` does:
        # one entry per (phase, row, query state) whose stage3-deltas route
        # supplied nothing. Published ONLY when such a route exists, so every
        # receipt this router has ever produced for a cell without one is
        # byte-identical to its pre-fix self (the identity
        # ``tests/unit/test_candidate_semantic_supply.py`` pins).
        route.receipt["delta_supply"] = delta_supply_audits
        route.receipt["delta_candidate_projection"] = (
            delta_candidate_projection_audits
        )
        if delta_scenario_gates:
            # ITERATION 3: published ONLY when a route actually declares a
            # gate, so every receipt an ungated cell produces stays byte-
            # identical to its pre-iteration-3 self.
            route.receipt["delta_scenario_gate"] = delta_scenario_gate_audits
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

        def prefetch_recall(sample_id, submit):
            """Owner decision 159 (``recall_prefetch``): forward the row to
            every store whose plain later-phase retrieval ``automatic_for_phase``
            composes. Nothing reads what this starts until that store's own
            supply step for the row, which consumes it in place of the
            identical recall it would otherwise compute."""

            submitted = 0
            for store_id in binding.store_ids:
                if not any(
                    (store_id, phase) in plain_later_phase_specs
                    and (store_id, phase) not in context_specs
                    for phase in specs_by_store.get(store_id, ())
                ):
                    continue
                forward = getattr(callbacks.get(store_id), "prefetch_recall", None)
                if callable(forward):
                    submitted += forward(sample_id, submit)
            return submitted

        automatic_for_phase.prefetch_recall = prefetch_recall
    if proposal_specs:
        route.candidate_proposal_for_context = candidate_proposal_for_context
        automatic_for_phase.candidate_proposal_for_context = candidate_proposal_for_context
        route.receipt["candidate_proposals"] = proposal_audits
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
    "KnowledgeStoreAlternate",
    "KnowledgeStoreBinding",
    "KnowledgeStoreError",
    "build_knowledge_store_supply",
    "declared_alternate_release_relpaths",
    "load_knowledge_store_binding",
    "qualify_id",
]
