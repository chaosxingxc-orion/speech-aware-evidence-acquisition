"""Deliver released task-specific semantic values from source-bound candidate state.

The shared route validates task candidates against an authoritative inventory,
selects from released knowledge and returns ordinary PhaseSupply through the
existing named-store custody path. Candidate hypotheses are evidence selectors;
they never restrict the Solver's legal answer space.
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
from .a2t_perception_state import Audio2ToolPerceptionStateError
from .controllers import PhaseProgram, PhaseSupply
from .errors import RailsError
from .hashing import content_hash
from .knowledge import AgentStateArtifact
from .knowledge_provider import (
    SLURP_CANDIDATE_SEMANTIC_FUSE_POLICY_ID,
    SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID,
    SLURP_CANDIDATE_SEMANTIC_RANK_POLICY_ID,
    A2T_CANDIDATE_SEMANTIC_PROVIDER_ID,
)
from .semantic_knowledge_build import (
    SLOT_CONTRACT_BUILD_POLICY_ID,
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    DEFAULT_FALLBACK_DISTINCTION,
    MAX_FALLBACK_CANDIDATES,
    SlurpIntentHypothesisError,
    validate_fallback_candidate_ids,
)

CANDIDATE_SUPPLY_SCHEMA = "saea-candidate-semantic-supply-v1"
SELECTION_SCHEMA = "saea-candidate-semantic-selection-v1"
AUTHORED_SOURCE_SCHEMA = "saea-authored-semantic-knowledge-source-v1"
DEFAULT_MAX_SLURP_CANDIDATES = 3
MAX_SLURP_CANDIDATES = DEFAULT_MAX_SLURP_CANDIDATES

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
_A2T_SPEC_KEYS = (_SPEC_KEYS - {"max_candidates"}) | {
    "max_actions", "max_candidates_per_action"
}
_OPTIONAL_SPEC_KEYS = frozenset(
    {
        "candidate_state_selection",
        "compact_source_phase",
        "supply_mode",
        "projection_policy",
        "fallback_candidates",
        "fallback_distinction",
        "exemplar_candidate_proposal",
        "candidate_legality_source",
    }
)
_SOURCE_KEYS = frozenset(
    {"schema", "builder_policy_id", "source_split_identity_hash", "rows"}
)

#: W1 card selection (owner decision 164). A SLURP candidate route may pin a
#: pre-computed intent -> slot-type LEGALITY table exactly the way a phase
#: supply pins its agreement table: ``kind``, ``relpath`` (under the data
#: root), ``sha256``, ``tool_contact_ledger_row`` and ``embedded_signal``.
#: When present, the released authored candidate index is NARROWED to the
#: (intent, slot type) pairs the table admits -- a table can only remove an
#: authored binding, never add one. Absent (every cell committed before
#: 2026-09-27), the index is the authored bindings, byte for byte.
SLOT_LEGALITY_SOURCE_KIND = "sealed-intent-slot-legality"
SLOT_LEGALITY_SCHEMA = "saea-slurp-intent-slot-legality-v1"
_LEGALITY_SOURCE_KEYS = frozenset(
    {"kind", "relpath", "sha256", "tool_contact_ledger_row", "embedded_signal"}
)


def validate_candidate_legality_source(raw: object) -> Mapping[str, object]:
    """Validate a ``candidate_legality_source`` declaration (no file is read)."""

    if not isinstance(raw, Mapping) or set(raw) != _LEGALITY_SOURCE_KEYS:
        raise CandidateSemanticSupplyError(
            "candidate_legality_source must carry exactly "
            f"{sorted(_LEGALITY_SOURCE_KEYS)}"
        )
    if raw["kind"] != SLOT_LEGALITY_SOURCE_KIND:
        raise CandidateSemanticSupplyError(
            f"candidate_legality_source.kind must be {SLOT_LEGALITY_SOURCE_KIND!r}"
        )
    relpath = raw["relpath"]
    if (
        not isinstance(relpath, str)
        or not relpath
        or relpath.startswith("/")
        or "\\" in relpath
        or any(part in ("", ".", "..") for part in relpath.split("/"))
    ):
        raise CandidateSemanticSupplyError(
            "candidate_legality_source.relpath must be a plain relative data-root path"
        )
    sha = raw["sha256"]
    if (
        not isinstance(sha, str)
        or len(sha) != 64
        or any(character not in "0123456789abcdef" for character in sha)
    ):
        raise CandidateSemanticSupplyError(
            "candidate_legality_source.sha256 must be a lowercase SHA-256"
        )
    for field in ("tool_contact_ledger_row", "embedded_signal"):
        if not isinstance(raw[field], str) or not raw[field].strip():
            raise CandidateSemanticSupplyError(
                f"candidate_legality_source.{field} must be non-empty text"
            )
    return MappingProxyType(dict(raw))


def load_sealed_slot_legality(
    source: Mapping[str, object], data_root: Path
) -> Mapping[str, frozenset[str]]:
    """Read and verify a pinned legality table: ``{intent id: slot types}``."""

    source = validate_candidate_legality_source(source)
    root = Path(data_root).resolve()
    path = (root / str(source["relpath"])).resolve()
    if path == root or root not in path.parents:
        raise CandidateSemanticSupplyError("legality table escapes the data root")
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise CandidateSemanticSupplyError("cannot read the legality table") from error
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise CandidateSemanticSupplyError("legality table SHA-256 mismatch")
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise CandidateSemanticSupplyError("legality table is not JSON") from error
    if not isinstance(document, Mapping) or document.get("schema") != SLOT_LEGALITY_SCHEMA:
        raise CandidateSemanticSupplyError(
            f"legality table schema must be {SLOT_LEGALITY_SCHEMA!r}"
        )
    table = document.get("legal_slot_types")
    if not isinstance(table, Mapping) or not table:
        raise CandidateSemanticSupplyError("legality table carries no legal_slot_types")
    out: dict[str, frozenset[str]] = {}
    for intent_id, types in table.items():
        if (
            not isinstance(intent_id, str)
            or not intent_id
            or not isinstance(types, list)
            or any(not isinstance(item, str) or not item for item in types)
            or types != sorted(set(types))
        ):
            raise CandidateSemanticSupplyError(
                "legal_slot_types must map intent ids to sorted unique slot types"
            )
        out[intent_id] = frozenset(types)
    return MappingProxyType(out)


def narrow_candidate_index(
    index: Mapping[str, Sequence[str]],
    legality: Mapping[str, frozenset[str]],
    *,
    legal_candidate_ids: Sequence[str],
) -> Mapping[str, tuple[str, ...]]:
    """Keep only the authored (intent, slot-contract) bindings the table admits.

    A table that names an intent outside the legal inventory, or a pair the
    authored index does not bind, is refused: the legality table is a
    SELECTION over released knowledge, never a source of new bindings.
    """

    legal = frozenset(legal_candidate_ids)
    for intent_id, types in legality.items():
        if intent_id not in legal:
            raise CandidateSemanticSupplyError(
                f"legality table names {intent_id!r}, outside the legal inventory"
            )
        bound = set(index.get(intent_id, ()))
        for slot_type in types:
            if f"slot-contract:{slot_type}" not in bound:
                raise CandidateSemanticSupplyError(
                    f"legality table admits ({intent_id!r}, {slot_type!r}), which the "
                    "released authored bindings do not carry; a table may only narrow"
                )
    narrowed: dict[str, tuple[str, ...]] = {}
    for intent_id, value_ids in index.items():
        admitted = legality.get(intent_id, frozenset())
        kept = tuple(
            value_id
            for value_id in value_ids
            if value_id.split("slot-contract:", 1)[-1] in admitted
        )
        if kept:
            narrowed[intent_id] = kept
    return MappingProxyType(narrowed)


def max_candidate_selection_value_ids(
    index: Mapping[str, Sequence[str]],
    *,
    weight: Mapping[str, int],
    max_candidates: int,
    max_total_values: int,
) -> tuple[str, ...]:
    """The heaviest value set ANY ``max_candidates`` distinct candidates can reach.

    A conservative pre-flight volume bound for a NARROWED index: over every
    combination of ``max_candidates`` indexed intents, the ``max_total_values``
    heaviest values in the union of their bindings. It relaxes the
    per-candidate cap and the round-robin order (so it can only over-count a
    real selection) and returns the value ids of the heaviest such set, ties
    broken by value id.
    """

    from itertools import combinations  # noqa: PLC0415

    intents = sorted(index)
    width = min(max_candidates, len(intents))
    best: tuple[int, tuple[str, ...]] = (-1, ())
    for combo in combinations(intents, width):
        union = {value_id for intent_id in combo for value_id in index[intent_id]}
        chosen = tuple(
            sorted(union, key=lambda value_id: (-weight[value_id], value_id))[
                :max_total_values
            ]
        )
        total = sum(weight[value_id] for value_id in chosen)
        if total > best[0]:
            best = (total, chosen)
    return best[1]


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
    max_actions: int | None = None
    max_candidates_per_action: int | None = None
    #: FIX-1 standing fallback (docs/results/2026-09-17-slurp-a3-coverage-
    #: confusion-audit-v1.md): SLURP-only, at most
    #: :data:`~.slurp_intent_hypotheses.MAX_FALLBACK_CANDIDATES` legal ids,
    #: appended LAST in the round-robin slot-card selection, never
    #: displacing or reordering a model-proposed candidate. Declared here,
    #: beside ``projection_policy``, because this is the codebase's existing
    #: home for "how Perception's candidate output is post-processed before
    #: this phase consumes it" -- the same role ``projection_policy``
    #: already plays.
    fallback_candidates: tuple[str, ...] = ()
    fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION
    exemplar_candidate_proposal: Mapping[str, object] | None = None
    #: W1 (owner decision 164): the pinned intent -> slot-type legality table
    #: that narrows the authored candidate index; ``None`` is the authored
    #: index unchanged.
    candidate_legality_source: Mapping[str, object] | None = None

    def validate(self, program: PhaseProgram) -> "CandidateSemanticSupplySpec":
        program.validate()
        if self.candidate_legality_source is not None:
            validate_candidate_legality_source(self.candidate_legality_source)
            if self.provider != SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID:
                raise CandidateSemanticSupplyError(
                    "candidate_legality_source is a SLURP slot-contract option"
                )
        if self.supply_mode not in ("provide", "withhold"):
            raise CandidateSemanticSupplyError("supply_mode must be provide or withhold")
        if (
            not isinstance(self.fallback_candidates, tuple)
            or len(self.fallback_candidates) > MAX_FALLBACK_CANDIDATES
            or any(
                not isinstance(item, str) or not item
                for item in self.fallback_candidates
            )
            or len(set(self.fallback_candidates)) != len(self.fallback_candidates)
        ):
            raise CandidateSemanticSupplyError(
                "fallback_candidates must be at most "
                f"{MAX_FALLBACK_CANDIDATES} unique non-empty strings"
            )
        if not isinstance(self.fallback_distinction, str) or not self.fallback_distinction.strip():
            raise CandidateSemanticSupplyError(
                "fallback_distinction must be a non-empty string"
            )
        if self.fallback_candidates and self.provider != SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID:
            raise CandidateSemanticSupplyError(
                "fallback_candidates is a SLURP-only option; Audio2Tool selection "
                "has no standing fallback"
            )
        if (
            not self.fallback_candidates
            and self.fallback_distinction != DEFAULT_FALLBACK_DISTINCTION
        ):
            raise CandidateSemanticSupplyError(
                "fallback_distinction requires a non-empty fallback_candidates"
            )
        if self.candidate_state_selection not in ("single", "latest"):
            raise CandidateSemanticSupplyError(
                "candidate_state_selection must be single or latest"
            )
        if self.projection_policy is not None and (
            self.projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
            or self.compact_source_phase is None
            or (
                self.max_candidates > DEFAULT_MAX_SLURP_CANDIDATES
                and self.projection_policy
                != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            )
        ):
            raise CandidateSemanticSupplyError(
                "projection_policy requires bounded first-occurrence and compact source"
            )
        if self.exemplar_candidate_proposal is not None:
            from .slurp_intent_hypotheses import BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            validate_exemplar_candidate_proposal(self.exemplar_candidate_proposal)
            if self.exemplar_candidate_proposal["max_added_slot_values"] > 32 * self.max_values_per_candidate:
                raise CandidateSemanticSupplyError("proposal added-value budget exceeds its candidate bounds")
            if not (
                self.provider == SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID
                and self.phase == "solver" and self.candidate_state_phase == "perception"
                and self.compact_source_phase == "perception"
                and self.max_candidates == 3 and not self.fallback_candidates
                and self.candidate_state_selection == "single" and self.supply_mode == "provide"
                and self.projection_policy == BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            ):
                raise CandidateSemanticSupplyError(
                    "exemplar proposal requires the ordinary single Perception to Solver route"
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
        if self.provider not in (
            SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID, A2T_CANDIDATE_SEMANTIC_PROVIDER_ID
        ):
            raise CandidateSemanticSupplyError(f"unsupported candidate provider {self.provider!r}")
        if self.provider == A2T_CANDIDATE_SEMANTIC_PROVIDER_ID:
            actions = _positive_int(self.max_actions, field="max_actions")
            alternatives = _positive_int(
                self.max_candidates_per_action, field="max_candidates_per_action"
            )
            if self.max_candidates != actions * alternatives:
                raise CandidateSemanticSupplyError("candidate bound differs from action alternatives")
            if self.compact_source_phase is None or self.projection_policy is not None:
                raise CandidateSemanticSupplyError(
                    "Audio2Tool requires an explicit compact source phase and no projection"
                )
        elif self.max_actions is not None or self.max_candidates_per_action is not None:
            raise CandidateSemanticSupplyError("SLURP does not declare action occurrence bounds")
        expected = (
            (
                "provider",
                self.provider,
                self.provider,
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
        _positive_int(
            self.max_candidates, field="max_candidates",
        )
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
        if self.provider == A2T_CANDIDATE_SEMANTIC_PROVIDER_ID:
            result.pop("max_candidates")
            result.update(
                max_actions=self.max_actions,
                max_candidates_per_action=self.max_candidates_per_action,
            )
        if self.exemplar_candidate_proposal is not None:
            result["exemplar_candidate_proposal"] = dict(self.exemplar_candidate_proposal)
        if self.compact_source_phase is not None:
            result["compact_source_phase"] = self.compact_source_phase
        if self.supply_mode != "provide":
            result["supply_mode"] = self.supply_mode
        if self.projection_policy is not None:
            result["projection_policy"] = self.projection_policy
        if self.candidate_state_selection != "single":
            result["candidate_state_selection"] = self.candidate_state_selection
        if self.fallback_candidates:
            result["fallback_candidates"] = list(self.fallback_candidates)
            if self.fallback_distinction != DEFAULT_FALLBACK_DISTINCTION:
                result["fallback_distinction"] = self.fallback_distinction
        if self.candidate_legality_source is not None:
            result["candidate_legality_source"] = dict(self.candidate_legality_source)
        return result



def validate_exemplar_candidate_proposal(raw):
    """Validate the existing SLURP provider's bounded proposal-consumption option."""
    required = {
        "mode", "exemplar_store_id", "intent_store_id",
        "max_candidates", "max_added_slot_values",
    }
    if not isinstance(raw, Mapping) or set(raw) != required:
        raise CandidateSemanticSupplyError("exemplar candidate proposal has the wrong fields")
    if raw["mode"] not in ("original-only", "append-selected-exemplars"):
        raise CandidateSemanticSupplyError("unknown exemplar candidate proposal mode")
    for field in ("exemplar_store_id", "intent_store_id"):
        if not isinstance(raw[field], str) or not raw[field] or "::" in raw[field]:
            raise CandidateSemanticSupplyError("proposal store IDs must be explicit local IDs")
    _positive_int(raw["max_candidates"], field="proposal max_candidates", maximum=32)
    if raw["max_candidates"] < 3:
        raise CandidateSemanticSupplyError("proposal must preserve up to three original candidates")
    _positive_int(raw["max_added_slot_values"], field="proposal max_added_slot_values", maximum=512)
    return MappingProxyType(dict(raw))


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
        for phase, raw in declared.items():
            if not isinstance(phase, str) or not phase or not isinstance(raw, Mapping):
                raise CandidateSemanticSupplyError(
                    "candidate_supply entries must be objects"
                )
            is_a2t = raw.get("provider") == A2T_CANDIDATE_SEMANTIC_PROVIDER_ID
            expected_role = "parameter-meaning" if is_a2t else "slot-contracts"
            if store.store_role != expected_role:
                raise CandidateSemanticSupplyError(
                    f"candidate semantic supply requires a {expected_role} store"
                )
            required = _A2T_SPEC_KEYS if is_a2t else _SPEC_KEYS
            if not required <= set(raw) or set(raw) - (
                required | _OPTIONAL_SPEC_KEYS
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
                max_candidates=(
                    _positive_int(raw["max_actions"], field="max_actions")
                    * _positive_int(
                        raw["max_candidates_per_action"], field="max_candidates_per_action"
                    )
                    if is_a2t else raw["max_candidates"]
                ),
                max_values_per_candidate=raw["max_values_per_candidate"],
                max_total_values=raw["max_total_values"],
                compact_source_phase=raw.get("compact_source_phase"),
                supply_mode=raw.get("supply_mode", "provide"),
                projection_policy=raw.get("projection_policy"),
                candidate_state_selection=raw.get(
                    "candidate_state_selection", "single"
                ),
                max_actions=raw.get("max_actions"),
                max_candidates_per_action=raw.get("max_candidates_per_action"),
                fallback_candidates=tuple(raw.get("fallback_candidates") or ()),
                exemplar_candidate_proposal=(
                    validate_exemplar_candidate_proposal(raw["exemplar_candidate_proposal"])
                    if "exemplar_candidate_proposal" in raw else None
                ),
                fallback_distinction=raw.get(
                    "fallback_distinction", DEFAULT_FALLBACK_DISTINCTION
                ),
                candidate_legality_source=(
                    validate_candidate_legality_source(raw["candidate_legality_source"])
                    if "candidate_legality_source" in raw else None
                ),
            ).validate(program)
            specs[phase] = spec
    return MappingProxyType(specs)


def candidate_state_read_parameters(
    specs: Mapping[str, "CandidateSemanticSupplySpec"],
    *,
    candidate_state_phase: str,
) -> tuple[int, str | None] | None:
    """How this plan's candidate routes read ``candidate_state_phase``.

    The answer is ``(max_candidates, projection_policy)`` -- the reading a
    plan's OWN candidate routes perform on that phase's sealed COMPACT
    Perception state. This is the ONE place it lives, so a sibling route over
    the same bytes can be neither stricter nor more lenient than the plan's
    candidate supply is.

    2026-09-23, the CELL-1 ARM abort. The locked plan reads one sealed
    Perception state through TWO routes: the slot-contracts candidate supply
    (this module) and the stage3-deltas candidate-bound context supply
    (``rails.knowledge_stores._stage3_delta_local_supply``). The plan's own
    route reads it with ``projection_policy=
    "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"`` and
    ``max_candidates=3``; the delta route was reading the same bytes with NO
    projection policy, so a Perception answer that names one intent three
    times -- 25 of the sealed PLAN arm's 1,080 rows do, and the PLAN arm
    completed every one of them -- projected cleanly for the plan and raised
    ``candidate intent_ids must be unique and ordered`` for the delta route,
    killing the row and, with it, the flight.

    The two routes now derive that reading from the SAME function. Returns
    ``None`` when no SLURP candidate route in this plan reads that phase's
    compact output, which leaves the caller its own documented default.
    Routes that disagree about the same phase are a config defect and are
    refused here, at build time, rather than per row.
    """

    if not isinstance(candidate_state_phase, str) or not candidate_state_phase:
        raise CandidateSemanticSupplyError(
            "candidate_state_phase must be one non-empty phase name"
        )
    readings = {
        (spec.max_candidates, spec.projection_policy)
        for spec in specs.values()
        if spec.provider == SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID
        and spec.candidate_state_phase == candidate_state_phase
        and spec.compact_source_phase == candidate_state_phase
    }
    if not readings:
        return None
    if len(readings) != 1:
        raise CandidateSemanticSupplyError(
            f"candidate routes disagree on how to read {candidate_state_phase!r}: "
            f"{sorted(readings)}"
        )
    return next(iter(readings))


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
    if not isinstance(source, Mapping):
        raise CandidateSemanticSupplyError("released source must be a JSON object")
    return source


def _read_released_authored_source(store: object, data_root: Path) -> Mapping[str, object]:
    source = _read_released_source(store, data_root)
    if set(source) != _SOURCE_KEYS:
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
    legality_source: Mapping[str, object] | None = None,
) -> Mapping[str, tuple[str, ...]]:
    index = _authored_candidate_index(
        store, data_root=data_root, legal_candidate_ids=legal_candidate_ids,
    )
    if legality_source is None:
        return index
    return narrow_candidate_index(
        index,
        load_sealed_slot_legality(legality_source, data_root),
        legal_candidate_ids=legal_candidate_ids,
    )


def _authored_candidate_index(
    store: object,
    *,
    data_root: Path,
    legal_candidate_ids: Sequence[str],
) -> Mapping[str, tuple[str, ...]]:
    source = _read_released_authored_source(store, data_root)
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



def _released_audio2tool_candidate_index(
    store: object, *, data_root: Path, legal_candidate_ids: Sequence[str],
    candidate_inventory_source_sha256: str | None,
) -> Mapping[str, tuple[str, ...]]:
    from .knowledge_compile_a2t import validate_compiled_knowledge_snapshot  # noqa: PLC0415

    source = _read_released_source(store, data_root)
    root = Path(data_root).resolve()
    path = (root / store.snapshot_pin["relpath"]).resolve()
    if path == root or root not in path.parents:
        raise CandidateSemanticSupplyError("compiled snapshot escapes data root")
    try:
        raw_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        metadata = validate_compiled_knowledge_snapshot(
            source, store.snapshot, store_role=store.store_role,
            snapshot_file_sha256=raw_hash, snapshot_path=path,
        )
    except (OSError, RailsError, ValueError, TypeError) as error:
        raise CandidateSemanticSupplyError(str(error)) from error
    if (
        not candidate_inventory_source_sha256
        or metadata["tool_registry_sha256"] != candidate_inventory_source_sha256
    ):
        raise CandidateSemanticSupplyError(
            "compiled parameter knowledge and authoritative tool registry source differ"
        )
    legal = tuple(legal_candidate_ids)
    if not legal or len(legal) != len(set(legal)):
        raise CandidateSemanticSupplyError("authoritative tool inventory must be nonempty and unique")
    snapshot = store.snapshot
    index: dict[str, tuple[str, ...]] = {}
    for value in snapshot.values:
        target = value.task_target
        if target not in legal or target in index:
            raise CandidateSemanticSupplyError(
                "compiled parameter targets must match the complete legal tool inventory"
            )
        expected_provenance = {
            f"a2t-native-card-compilation-source-sha256:{snapshot.source_split_identity_hash}",
            f"a2t-native-card-corpus-sha256:{metadata['corpus_sha256']}",
            "a2t-native-card-sha256:" + hashlib.sha256(value.content.encode("utf-8")).hexdigest(),
            "a2t-native-card-value-view:parameter-meaning",
        }
        if not expected_provenance <= set(value.provenance_refs):
            raise CandidateSemanticSupplyError("compiled parameter value provenance differs")
        index[target] = (value.value_id,)
    if set(index) != set(legal):
        raise CandidateSemanticSupplyError(
            "compiled parameter targets must cover the complete legal tool inventory"
        )
    return MappingProxyType(index)

def _index_key(spec: CandidateSemanticSupplySpec) -> tuple[str, str | None]:
    source = spec.candidate_legality_source
    return (spec.store_id, None if source is None else str(source["sha256"]))


def build_candidate_semantic_supply(
    binding: object,
    specs: Mapping[str, CandidateSemanticSupplySpec],
    *,
    data_root: Path,
    legal_candidate_ids: Sequence[str],
    candidate_inventory_source_sha256: str | None = None,
    candidate_inventory_authority: str = "task-adapter-candidate-contract-provider",
):
    """Build automatic per-phase supply and its mutable run receipt."""

    from .knowledge_stores import qualify_id  # noqa: PLC0415

    if not specs:
        return None
    legal_candidate_count = len(frozenset(legal_candidate_ids))
    if legal_candidate_count < 1:
        raise CandidateSemanticSupplyError(
            "candidate supply requires a nonempty legal candidate inventory"
        )
    for spec in specs.values():
        if spec.provider == SLURP_CANDIDATE_SEMANTIC_PROVIDER_ID:
            if spec.max_candidates > legal_candidate_count:
                raise CandidateSemanticSupplyError(
                    "max_candidates cannot exceed the legal candidate inventory"
                )
            if spec.fallback_candidates:
                try:
                    validate_fallback_candidate_ids(
                        spec.fallback_candidates, legal_intent_ids=legal_candidate_ids,
                    )
                except SlurpIntentHypothesisError as error:
                    raise CandidateSemanticSupplyError(str(error)) from error
    # Keyed by (store, legality table): two routes over one store share an
    # index only when they narrow it identically (W1, owner decision 164).
    indexes: dict[tuple[str, str | None], Mapping[str, tuple[str, ...]]] = {}
    for spec in specs.values():
        if _index_key(spec) not in indexes:
            if spec.provider == A2T_CANDIDATE_SEMANTIC_PROVIDER_ID:
                if candidate_inventory_authority != "audio2tool-public-tool-registry":
                    raise CandidateSemanticSupplyError(
                        "Audio2Tool requires its public tool registry authority"
                    )
                indexes[_index_key(spec)] = _released_audio2tool_candidate_index(
                    binding.store(spec.store_id), data_root=data_root,
                    legal_candidate_ids=legal_candidate_ids,
                    candidate_inventory_source_sha256=candidate_inventory_source_sha256,
                )
            else:
                indexes[_index_key(spec)] = _released_candidate_index(
                    binding.store(spec.store_id),
                    data_root=data_root,
                    legal_candidate_ids=legal_candidate_ids,
                    legality_source=spec.candidate_legality_source,
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

    def automatic_for_phase(phase: str, context: object, *, candidate_proposal=None) -> PhaseSupply | None:
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
        provider_args = {
            "candidate_values": indexes[_index_key(spec)],
            "legal_candidate_ids": legal_candidate_ids,
            "max_values_per_candidate": spec.max_values_per_candidate,
            "max_total_values": spec.max_total_values,
            "compact_source_phase": spec.compact_source_phase,
        }
        if spec.provider == A2T_CANDIDATE_SEMANTIC_PROVIDER_ID:
            provider_args.update(
                max_actions=spec.max_actions,
                max_candidates_per_action=spec.max_candidates_per_action,
            )
        else:
            provider_args.update(
                max_candidates=spec.max_candidates,
                projection_policy=spec.projection_policy,
                fallback_candidates=spec.fallback_candidates,
                fallback_distinction=spec.fallback_distinction,
            )
        provider = KNOWLEDGE_PROVIDERS.resolve(spec.provider)(**provider_args).adopt(
            store.snapshot,
            policy_id=store.snapshot.builder_policy_id,
            source_ids=store.snapshot.source_sample_ids,
            snapshot_sha256=store.snapshot.content_hash(),
        )
        query = {
            "query_state": query_state,
            "candidate_state": selected_state,
            "sample_id": sample_id,
        }
        total_k = spec.max_total_values
        if spec.exemplar_candidate_proposal is not None:
            if candidate_proposal is None:
                raise CandidateSemanticSupplyError("declared proposal lacks its bound exemplar selection")
            cap = spec.exemplar_candidate_proposal["max_added_slot_values"]
            query.update(candidate_proposal=candidate_proposal, candidate_proposal_added_value_cap=cap)
            total_k += cap
        elif candidate_proposal is not None:
            raise CandidateSemanticSupplyError("undeclared candidate proposal was supplied")
        try:
            ranking = provider.candidates(query, k=total_k)
            decision = provider.fuse([ranking], k=total_k, policy_id=spec.fuse_policy)
        except (RailsError, SlurpIntentHypothesisError, Audio2ToolPerceptionStateError) as error:
            raise CandidateSemanticSupplyError(str(error)) from error
        audit = dict(provider.last_selection_audit() or {})
        if not audit:
            raise CandidateSemanticSupplyError(
                "candidate provider produced no selection audit"
            )
        audit.update(binding.store_receipt(spec.store_id))
        if candidate_inventory_source_sha256 is not None:
            audit.update(
                candidate_inventory_source_sha256=candidate_inventory_source_sha256,
                candidate_inventory_authority=candidate_inventory_authority,
            )
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
            supplied_decision = decision
            if spec.candidate_state_selection == "latest":
                supplied_decision = replace(
                    decision,
                    supporting_facet_ids=provider.supporting_facet_ids(local_added_ids),
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

    def selected_state_for(phase, context):
        spec = specs[phase]
        return candidate_state_for(
            spec, phase=phase, query_state=context.query_state,
            states=context.agent_states,
            prior_response_sha256s=context.prior_response_sha256s,
        )

    automatic_for_phase.candidate_state_for = selected_state_for
    automatic_for_phase.receipt = {
        "schema": CANDIDATE_SUPPLY_SCHEMA,
        "specs": [specs[phase].as_json() for phase in sorted(specs)],
        "candidate_inventory_authority": candidate_inventory_authority,
        "candidate_inventory_count": len(frozenset(legal_candidate_ids)),
        "candidate_inventory_sha256": content_hash(
            {"candidate_ids": sorted(frozenset(legal_candidate_ids))}
        ),
        "candidate_selections": audits,
    }
    if candidate_inventory_source_sha256 is not None:
        automatic_for_phase.receipt["candidate_inventory_source_sha256"] = candidate_inventory_source_sha256
    return automatic_for_phase


__all__ = [
    "AUTHORED_SOURCE_SCHEMA",
    "CANDIDATE_SUPPLY_SCHEMA",
    "MAX_SLURP_CANDIDATES",
    "SELECTION_SCHEMA",
    "SLOT_LEGALITY_SCHEMA",
    "SLOT_LEGALITY_SOURCE_KIND",
    "CandidateSemanticSupplyError",
    "CandidateSemanticSupplySpec",
    "build_candidate_semantic_supply",
    "candidate_state_read_parameters",
    "load_candidate_semantic_supply_specs",
    "load_sealed_slot_legality",
    "max_candidate_selection_value_ids",
    "narrow_candidate_index",
    "released_candidate_index",
    "validate_candidate_legality_source",
]

#: Public name for the verified released index a route selects from (used by
#: the pre-flight prompt bound and by the W1 measurement script).
released_candidate_index = _released_candidate_index
