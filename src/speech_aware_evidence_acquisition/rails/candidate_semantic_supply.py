"""Configuration-only supply of released slot cards from candidate state.

The model contributes only the ranked, source-bound SLURP intent candidates
sealed by an earlier phase.  This module validates those candidates against
the task adapter's authoritative legal inventory, uses the released authored
slot source only as an index, and returns ordinary ``PhaseSupply`` through the
existing named-store custody path.  Sparse intent bindings are indexing hints;
they never declare required, optional, forbidden, or exhaustive slot types.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from threading import Lock
from types import MappingProxyType
from typing import Mapping, Sequence

from ..core.base import (
    KNOWLEDGE_FUSERS,
    KNOWLEDGE_PROVIDERS,
    KNOWLEDGE_RANKERS,
    CoreError,
)
from .controllers import PhaseProgram, PhaseSupply
from .errors import RailsError
from .hashing import content_hash
from .knowledge import AgentStateArtifact
from .knowledge_provider import (
    SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID,
    SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
    SlurpCandidateSemanticProvider,
)
from .semantic_knowledge_build import (
    SLOT_CONTRACT_BUILD_POLICY_ID,
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    SlurpIntentHypothesisError,
)

CANDIDATE_SUPPLY_SCHEMA = "saea-candidate-semantic-supply-v1"
SELECTION_SCHEMA = "saea-candidate-semantic-selection-v1"
AUTHORED_SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
MAX_SLURP_CANDIDATES = 3

_SPEC_KEYS = frozenset(
    {
        "provider",
        "rank_policy",
        "fuse_policy",
        "candidate_state_phase",
        "max_candidates",
        "max_values_per_candidate",
        "max_total_values",
    }
)
_OPTIONAL_SPEC_KEYS = frozenset(
    {
        "candidate_state_selection",
        "compact_source_phase",
        "supply_mode",
        "projection_policy",
    }
)
_SOURCE_KEYS = frozenset(
    {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}
)


class CandidateSemanticSupplyError(RailsError):
    """A candidate supply declaration or released index is invalid."""


def _positive_int(value: object, *, field: str, maximum: int | None = None) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < 1
        or (maximum is not None and value > maximum)
    ):
        suffix = f" through {maximum}" if maximum is not None else " or greater"
        raise CandidateSemanticSupplyError(f"{field} must be an integer from 1{suffix}")
    return value


@dataclass(frozen=True)
class CandidateSemanticSupplySpec:
    phase: str
    store_id: str
    provider: str
    rank_policy: str
    fuse_policy: str
    candidate_state_phase: str
    max_candidates: int
    max_values_per_candidate: int
    max_total_values: int
    compact_source_phase: str | None = None
    supply_mode: str = "provide"
    projection_policy: str | None = None
    candidate_state_selection: str = "single"

    def validate(self, program: PhaseProgram) -> "CandidateSemanticSupplySpec":
        program.validate()
        if self.supply_mode not in ("provide", "withhold"):
            raise CandidateSemanticSupplyError("supply_mode must be provide or withhold")
        if self.candidate_state_selection not in ("single", "latest"):
            raise CandidateSemanticSupplyError(
                "candidate_state_selection must be single or latest"
            )
        if self.projection_policy is not None and (
            self.projection_policy != BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            or self.compact_source_phase is None
        ):
            raise CandidateSemanticSupplyError(
                "projection_policy requires bounded first-occurrence and compact source"
            )
        phases = program.phase_names()
        if self.phase not in phases or self.candidate_state_phase not in phases:
            raise CandidateSemanticSupplyError(
                "candidate supply and candidate_state_phase must name program phases"
            )
        if phases.index(self.candidate_state_phase) >= phases.index(self.phase):
            raise CandidateSemanticSupplyError(
                "candidate supply phase must be later than candidate_state_phase"
            )
        if self.compact_source_phase is not None and (
            self.compact_source_phase != self.candidate_state_phase
            or ":" in self.compact_source_phase
            or any(character.isspace() for character in self.compact_source_phase)
        ):
            raise CandidateSemanticSupplyError(
                "compact_source_phase must equal the candidate_state_phase name"
            )
        if program.phase(self.phase).knowledge != "supplied":
            raise CandidateSemanticSupplyError(
                f"candidate supply phase {self.phase!r} must declare knowledge='supplied'"
            )
        expected = (
            (
                "provider",
                self.provider,
                SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID,
                KNOWLEDGE_PROVIDERS,
            ),
            (
                "rank_policy",
                self.rank_policy,
                SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
                KNOWLEDGE_RANKERS,
            ),
            (
                "fuse_policy",
                self.fuse_policy,
                SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
                KNOWLEDGE_FUSERS,
            ),
        )
        for field, value, policy_id, registry in expected:
            if value != policy_id:
                raise CandidateSemanticSupplyError(
                    f"{field} must be {policy_id!r}, got {value!r}"
                )
            try:
                registry.resolve(value)
            except CoreError as error:
                raise CandidateSemanticSupplyError(str(error)) from None
        _positive_int(self.max_candidates, field="max_candidates", maximum=3)
        _positive_int(self.max_values_per_candidate, field="max_values_per_candidate")
        _positive_int(self.max_total_values, field="max_total_values")
        if self.max_total_values > self.max_candidates * self.max_values_per_candidate:
            raise CandidateSemanticSupplyError(
                "max_total_values cannot exceed max_candidates times "
                "max_values_per_candidate"
            )
        return self

    def as_json(self) -> dict[str, object]:
        result = {
            "phase": self.phase,
            "store_id": self.store_id,
            "provider": self.provider,
            "rank_policy": self.rank_policy,
            "fuse_policy": self.fuse_policy,
            "candidate_state_phase": self.candidate_state_phase,
            "max_candidates": self.max_candidates,
            "max_values_per_candidate": self.max_values_per_candidate,
            "max_total_values": self.max_total_values,
        }
        if self.compact_source_phase is not None:
            result["compact_source_phase"] = self.compact_source_phase
        if self.supply_mode != "provide":
            result["supply_mode"] = self.supply_mode
        if self.projection_policy is not None:
            result["projection_policy"] = self.projection_policy
        if self.candidate_state_selection != "single":
            result["candidate_state_selection"] = self.candidate_state_selection
        return result


def load_candidate_semantic_supply_specs(
    binding: object, program: PhaseProgram
) -> Mapping[str, CandidateSemanticSupplySpec]:
    """Parse every store-local candidate supply and refuse phase collisions."""

    specs: dict[str, CandidateSemanticSupplySpec] = {}
    for store_id in binding.store_ids:
        store = binding.store(store_id)
        declared = store.candidate_supply
        if not declared:
            continue
        if store.store_role != "slot-contracts":
            raise CandidateSemanticSupplyError(
                "candidate semantic supply requires a slot-contracts store"
            )
        for phase, raw in declared.items():
            if not isinstance(phase, str) or not phase or not isinstance(raw, Mapping):
                raise CandidateSemanticSupplyError(
                    "candidate_supply entries must be objects"
                )
            if not _SPEC_KEYS <= set(raw) or set(raw) - (
                _SPEC_KEYS | _OPTIONAL_SPEC_KEYS
            ):
                raise CandidateSemanticSupplyError(
                    f"candidate_supply[{phase!r}] has the wrong fields"
                )
            if phase in specs:
                raise CandidateSemanticSupplyError(
                    f"multiple candidate stores supply phase {phase!r}"
                )
            spec = CandidateSemanticSupplySpec(
                phase=phase,
                store_id=store_id,
                provider=raw["provider"],
                rank_policy=raw["rank_policy"],
                fuse_policy=raw["fuse_policy"],
                candidate_state_phase=raw["candidate_state_phase"],
                max_candidates=raw["max_candidates"],
                max_values_per_candidate=raw["max_values_per_candidate"],
                max_total_values=raw["max_total_values"],
                compact_source_phase=raw.get("compact_source_phase"),
                supply_mode=raw.get("supply_mode", "provide"),
                projection_policy=raw.get("projection_policy"),
                candidate_state_selection=raw.get(
                    "candidate_state_selection", "single"
                ),
            ).validate(program)
            specs[phase] = spec
    return MappingProxyType(specs)


def _read_released_source(store: object, data_root: Path) -> Mapping[str, object]:
    root = Path(data_root).resolve()
    path = (root / store.source_pin["relpath"]).resolve()
    if path == root or root not in path.parents:
        raise CandidateSemanticSupplyError("released authored source escapes data root")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CandidateSemanticSupplyError(
            "cannot read released authored source"
        ) from error
    if hashlib.sha256(raw).hexdigest() != store.source_pin["sha256"]:
        raise CandidateSemanticSupplyError("released authored source SHA-256 mismatch")
    try:
        source = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CandidateSemanticSupplyError(
            "released authored source is not JSON"
        ) from error
    if not isinstance(source, Mapping) or set(source) != _SOURCE_KEYS:
        raise CandidateSemanticSupplyError(
            "released authored source has the wrong fields"
        )
    if (
        source["schema"] != AUTHORED_SOURCE_SCHEMA
        or source["builder_policy_id"] != SLOT_CONTRACT_BUILD_POLICY_ID
        or source["builder_policy_id"] != store.snapshot.builder_policy_id
        or source["source_split_identity_hash"]
        != store.snapshot.source_split_identity_hash
    ):
        raise CandidateSemanticSupplyError(
            "released authored source identity differs from the slot snapshot"
        )
    rows = source["rows"]
    if (
        not isinstance(rows, list)
        or not rows
        or any(not isinstance(row, Mapping) for row in rows)
    ):
        raise CandidateSemanticSupplyError(
            "released authored source rows are malformed"
        )
    return source


def _released_candidate_index(
    store: object,
    *,
    data_root: Path,
    legal_candidate_ids: Sequence[str],
) -> Mapping[str, tuple[str, ...]]:
    source = _read_released_source(store, data_root)
    rows = source["rows"]
    try:
        rebuilt = build_slot_contract_snapshot(
            AuthoredSemanticKnowledgeSpec(
                carrier_lock_key="slurp",
                source_split_identity_hash=store.snapshot.source_split_identity_hash,
                permitted_source_sample_ids=store.snapshot.source_sample_ids,
                source_partition_role=store.snapshot.source_partition_role,
            ),
            rows=rows,
        )
    except RailsError as error:
        raise CandidateSemanticSupplyError(
            f"released authored slot source does not rebuild: {error}"
        ) from error
    if rebuilt.frozen_json() != store.snapshot.frozen_json():
        raise CandidateSemanticSupplyError(
            "released authored slot source differs from the released snapshot"
        )

    legal = frozenset(legal_candidate_ids)
    if not legal or any(not isinstance(item, str) or not item for item in legal):
        raise CandidateSemanticSupplyError(
            "candidate supply requires the full authoritative legal candidate inventory"
        )
    index: dict[str, list[str]] = {}
    for row in rows:
        value_id = f"slot-contract:{row['slot_id']}"
        for binding in row["intent_bindings"]:
            candidate_id = binding["intent_id"]
            if candidate_id not in legal:
                raise CandidateSemanticSupplyError(
                    f"candidate index ID {candidate_id!r} is outside the full released inventory"
                )
            index.setdefault(candidate_id, []).append(value_id)
    return MappingProxyType(
        {
            candidate_id: tuple(sorted(value_ids))
            for candidate_id, value_ids in index.items()
        }
    )


def build_candidate_semantic_supply(
    binding: object,
    specs: Mapping[str, CandidateSemanticSupplySpec],
    *,
    data_root: Path,
    legal_candidate_ids: Sequence[str],
):
    """Build automatic per-phase supply and its mutable run receipt."""

    from .knowledge_stores import qualify_id  # noqa: PLC0415

    if not specs:
        return None
    indexes: dict[str, Mapping[str, tuple[str, ...]]] = {}
    for spec in specs.values():
        if spec.store_id not in indexes:
            indexes[spec.store_id] = _released_candidate_index(
                binding.store(spec.store_id),
                data_root=data_root,
                legal_candidate_ids=legal_candidate_ids,
            )
    audits: dict[str, Mapping[str, object]] = {}
    audit_lock = Lock()

    def candidate_state_for(
        spec: CandidateSemanticSupplySpec,
        *,
        phase: str,
        query_state: object,
        states: object,
        prior_response_sha256s: object,
    ) -> AgentStateArtifact:
        expected_kind = f"phase:{spec.candidate_state_phase}"
        state_rows = tuple(states)
        matches = tuple(
            state
            for state in state_rows
            if isinstance(state, AgentStateArtifact)
            and state.state_kind == expected_kind
        )
        if spec.candidate_state_selection == "single":
            if len(matches) != 1:
                raise CandidateSemanticSupplyError(
                    f"candidate supply for {phase!r} requires exactly one source-bound "
                    f"{spec.candidate_state_phase!r} state, got {len(matches)}"
                )
            return matches[0]

        if any(not isinstance(state, AgentStateArtifact) for state in state_rows):
            raise CandidateSemanticSupplyError(
                "latest candidate state selection requires only AgentStateArtifact context"
            )
        state_ids = tuple(state.state_id for state in state_rows)
        if len(state_ids) != len(set(state_ids)):
            raise CandidateSemanticSupplyError(
                "latest candidate state selection requires unique context state IDs"
            )
        declared_ids = getattr(query_state, "agent_state_ids", None)
        if not isinstance(declared_ids, tuple):
            raise CandidateSemanticSupplyError(
                "latest candidate state selection requires QueryState.agent_state_ids"
            )
        if state_ids == declared_ids:
            staged_state = None
        elif len(state_ids) == len(declared_ids) + 1 and state_ids[:-1] == declared_ids:
            staged_state = state_rows[-1]
        else:
            raise CandidateSemanticSupplyError(
                "latest candidate state context must exactly match committed "
                "QueryState.agent_state_ids in order, with at most one trailing staged state"
            )
        if staged_state is not None:
            query_hash = query_state.content_hash()
            response_hashes = tuple(prior_response_sha256s)
            if staged_state.source_query_state_sha256 != query_hash:
                raise CandidateSemanticSupplyError(
                    "latest staged candidate state is bound to another QueryState"
                )
            if (
                not response_hashes
                or staged_state.source_response_sha256 != response_hashes[-1]
            ):
                raise CandidateSemanticSupplyError(
                    "latest staged candidate state is bound to another final response"
                )
        if not matches:
            raise CandidateSemanticSupplyError(
                f"candidate supply for {phase!r} requires at least one source-bound "
                f"{spec.candidate_state_phase!r} state"
            )
        return matches[-1]

    def automatic_for_phase(phase: str, context: object) -> PhaseSupply | None:
        spec = specs.get(phase)
        if spec is None:
            return None
        sample_id = getattr(context, "sample_id", None)
        query_state = getattr(context, "query_state", None)
        states = getattr(context, "agent_states", ())
        prior_response_sha256s = getattr(context, "prior_response_sha256s", ())
        selected_state = candidate_state_for(
            spec,
            phase=phase,
            query_state=query_state,
            states=states,
            prior_response_sha256s=prior_response_sha256s,
        )
        store = binding.store(spec.store_id)
        provider = SlurpCandidateSemanticProvider(
            candidate_values=indexes[spec.store_id],
            legal_candidate_ids=legal_candidate_ids,
            max_candidates=spec.max_candidates,
            max_values_per_candidate=spec.max_values_per_candidate,
            max_total_values=spec.max_total_values,
            compact_source_phase=spec.compact_source_phase,
            projection_policy=spec.projection_policy,
        ).adopt(
            store.snapshot,
            policy_id=store.snapshot.builder_policy_id,
            source_ids=store.snapshot.source_sample_ids,
            snapshot_sha256=store.snapshot.content_hash(),
        )
        try:
            ranking = provider.candidates(
                {
                    "query_state": query_state,
                    "candidate_state": selected_state,
                    "sample_id": sample_id,
                },
                k=spec.max_total_values,
            )
            decision = provider.fuse(
                [ranking],
                k=spec.max_total_values,
                policy_id=spec.fuse_policy,
            )
        except (RailsError, SlurpIntentHypothesisError) as error:
            raise CandidateSemanticSupplyError(str(error)) from error
        audit = dict(provider.last_selection_audit() or {})
        if not audit:
            raise CandidateSemanticSupplyError(
                "candidate provider produced no selection audit"
            )
        audit.update(binding.store_receipt(spec.store_id))
        selected_ids = tuple(
            qualify_id(spec.store_id, value_id)
            for value_id in decision.selected_value_ids
        )
        visible_ids = set(query_state.retrieved_value_ids)
        already_visible_ids = tuple(
            value_id for value_id in selected_ids if value_id in visible_ids
        )
        added_ids = tuple(
            value_id for value_id in selected_ids if value_id not in visible_ids
        )
        if (
            spec.candidate_state_selection == "single"
            and already_visible_ids
            and len(already_visible_ids) != len(selected_ids)
        ):
            raise CandidateSemanticSupplyError(
                "candidate supply partially overlaps visible values; refuse a changed dose"
            )
        if spec.supply_mode == "withhold" and already_visible_ids:
            raise CandidateSemanticSupplyError(
                "withheld candidate values are already visible; refuse a contaminated control"
            )
        disposition = (
            "withheld" if spec.supply_mode == "withhold"
            else "already-visible"
            if selected_ids and not added_ids
            else "acquired"
            if added_ids
            else "no-mapping"
        )
        query_hash = query_state.content_hash()
        audit.update(
            {
                "query_state_sha256": query_hash,
                "qualified_selected_value_ids": list(selected_ids),
                "supply_disposition": disposition,
            }
        )
        if spec.candidate_state_selection == "latest":
            audit.update(
                {
                    "source_selection_policy": "last-matching-state-in-query-order-v1",
                    "selected_source_state_id": selected_state.state_id,
                    "selected_source_state_sha256": selected_state.content_hash(),
                    "already_visible_value_ids": list(already_visible_ids),
                    "added_value_ids": list(added_ids),
                }
            )
        audit["selection_receipt_sha256"] = content_hash(audit)
        qualified = None
        if disposition == "acquired":
            added_id_set = set(added_ids)
            local_added_ids = tuple(
                value_id
                for value_id, qualified_id in zip(
                    decision.selected_value_ids, selected_ids, strict=True
                )
                if qualified_id in added_id_set
            )
            supplied_decision = replace(
                decision,
                supporting_facet_ids=local_added_ids,
                selected_value_ids=local_added_ids,
            ).validate()
            local_supply = PhaseSupply(
                rank_result=provider.last_rank_result(),
                fusion_decision=supplied_decision,
                action_target_ref=(
                    f"{spec.provider}:{spec.rank_policy}:{spec.fuse_policy}:"
                    f"selection-receipt={audit['selection_receipt_sha256']}"
                ),
            ).validate()
            qualified = binding.qualify_supply(spec.store_id, local_supply, query_state)
        # The provider forms the full bounded selection before this layer
        # removes already-visible cards. Never filter before rank/fuse or page
        # farther into the released index to replace a visible card.
        audit_key = f"{phase}:{sample_id}:{query_hash}"
        with audit_lock:
            prior = audits.get(audit_key)
            if prior is not None and prior != audit:
                raise CandidateSemanticSupplyError(
                    f"candidate selection for {audit_key!r} changed within one query"
                )
            audits[audit_key] = audit
        return qualified

    automatic_for_phase.receipt = {
        "schema": CANDIDATE_SUPPLY_SCHEMA,
        "specs": [specs[phase].as_json() for phase in sorted(specs)],
        "candidate_inventory_authority": "task-adapter-candidate-contract-provider",
        "candidate_inventory_count": len(frozenset(legal_candidate_ids)),
        "candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(frozenset(legal_candidate_ids))}
        ),
        "candidate_selections": audits,
    }
    return automatic_for_phase


__all__ = [
    "AUTHORED_SOURCE_SCHEMA",
    "CANDIDATE_SUPPLY_SCHEMA",
    "MAX_SLURP_CANDIDATES",
    "SELECTION_SCHEMA",
    "CandidateSemanticSupplyError",
    "CandidateSemanticSupplySpec",
    "build_candidate_semantic_supply",
    "load_candidate_semantic_supply_specs",
]
