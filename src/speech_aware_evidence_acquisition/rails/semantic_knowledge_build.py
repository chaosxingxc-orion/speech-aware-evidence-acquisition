"""Builders for authored, source-bound semantic knowledge values."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import re

from .errors import RailsError
from .hashing import content_hash
from .knowledge import (
    EXTERNAL_GOVERNED_PARTITION_ROLE,
    TRAIN_PARTITION_ROLE,
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)

INTENT_BOUNDARY_BUILD_POLICY_ID = "saea-authored-intent-boundaries-v1"
FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID = "saea-authored-intent-boundaries-factored-v1"
SLOT_CONTRACT_BUILD_POLICY_ID = "saea-authored-slot-contracts-v1"
#: Stage-3 S3-5 (2026-09-22): the append-only, provenance-tagged delta store
#: (ACE grow-and-refine). Its authored rows are ALREADY the exact
#: ValueBundle fields (S3-5's curator -- ``scripts/build_slurp_stage3_
#: delta_store.py``, not this module -- computes ``value_id``,
#: ``associated_facet_ids``, ``source_sample_ids``, ``provenance_refs``,
#: ``task_target`` and ``prior_score`` before this builder ever sees them),
#: so this builder compiles rather than derives, unlike every builder above.
STAGE3_DELTA_BUILD_POLICY_ID = "saea-authored-stage3-deltas-v1"
#: Stage-3 S3-4s (owner decision 106, 2026-09-23): the NODE-TARGETED
#: delta store. Registered BESIDE v1, never in place of it: v1 rows stay
#: loadable and v1 releases stay flyable. The only shape difference is
#: one further authored-row key, ``node_target``, and the ``task_target``
#: form it implies (``NODE:DELTA-KIND:TARGET`` instead of v1's
#: ``DELTA-KIND:TARGET``) -- which is what lets one store serve the
#: Perception, Solver, Reviewer and Planner routes from four disjoint
#: slices (``rails.stage3_delta_supply.node_target_of_task_target``).
STAGE3_DELTA_V2_BUILD_POLICY_ID = "saea-authored-stage3-deltas-v2"
STAGE3_DELTA_DIMENSION = "stage3-delta-target"
#: The nodes a v2 row may address, spelled as PHASE names. Restated
#: from ``rails.stage3_delta_supply.STAGE3_DELTA_NODES``; this module
#: keeps no import of the supply side.
STAGE3_DELTA_NODE_TARGETS = ("perception", "solver", "reviewer", "planner")
SHARED_INTENT_GUIDANCE_VALUE_ID = "intent-boundary:shared-guidance"
_SHARED_INTENT_GUIDANCE_SCOPE = (
    "Shared guidance for all intent-boundary values in this store."
)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SEMANTIC_ID = re.compile(r"[a-z0-9]+(?:[_-][a-z0-9]+)*")
_BUILD_ROLES = {TRAIN_PARTITION_ROLE, EXTERNAL_GOVERNED_PARTITION_ROLE}
_SUPPORT_KEYS = {"source_sample_ids", "provenance_refs"}
_INTENT_KEYS = {
    "intent_id", "activation_boundary", "confusable_exclusions",
    "uncertainty_behavior", "limitations", "source_support",
}
_SLOT_KEYS = {
    "slot_id", "intent_bindings", "extraction_cues", "admissible_formats",
    "missing_behavior", "ambiguity_behavior", "limitations", "source_support",
}
_STAGE3_DELTA_KEYS = {
    "value_id", "content", "associated_facet_ids", "source_sample_ids",
    "provenance_refs", "task_target", "prior_score",
}
#: S3-4s: exactly the v1 key set plus ``node_target``.
_STAGE3_DELTA_V2_KEYS = _STAGE3_DELTA_KEYS | {"node_target"}
_DELTA_VALUE_ID = re.compile(r"delta:[0-9]+:[0-9a-f]{12}")


@dataclass(frozen=True)
class AuthoredSemanticKnowledgeSpec:
    """Identity boundary for one reviewed semantic construction source."""

    carrier_lock_key: str
    source_split_identity_hash: str
    permitted_source_sample_ids: tuple[str, ...]
    source_partition_role: str = TRAIN_PARTITION_ROLE

    def validate(self) -> "AuthoredSemanticKnowledgeSpec":
        _text(self.carrier_lock_key, "carrier_lock_key")
        if (
            not isinstance(self.source_split_identity_hash, str)
            or _SHA256.fullmatch(self.source_split_identity_hash) is None
        ):
            raise RailsError(
                "source_split_identity_hash must be a lowercase 64-hex SHA-256"
            )
        if self.source_partition_role not in _BUILD_ROLES:
            raise RailsError("source_partition_role must be train or external-governed")
        _texts(
            self.permitted_source_sample_ids,
            "permitted_source_sample_ids",
            tuple_only=True,
        )
        return self


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RailsError(f"{field} must be a non-empty string")
    return value.strip()


def _identifier(value: object, field: str) -> str:
    value = _text(value, field)
    if _SEMANTIC_ID.fullmatch(value) is None:
        raise RailsError(f"{field} must be a canonical lowercase semantic ID")
    return value


def _texts(value: object, field: str, *, tuple_only: bool = False) -> tuple[str, ...]:
    types = tuple if tuple_only else (list, tuple)
    if not isinstance(value, types) or isinstance(value, (str, bytes)) or not value:
        raise RailsError(f"{field} must be a non-empty sequence")
    result = tuple(_text(item, f"{field} entry") for item in value)
    if len(set(result)) != len(result):
        raise RailsError(f"{field} entries must be unique")
    return result


def _object(value: object, field: str, keys: set[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise RailsError(f"{field} has the wrong fields")
    return value


def _support(value: object, field: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    item = _object(value, field, _SUPPORT_KEYS)
    return (
        _texts(item["source_sample_ids"], f"{field}.source_sample_ids"),
        tuple(sorted(_texts(item["provenance_refs"], f"{field}.provenance_refs"))),
    )


def _intent(row: Mapping[str, object]) -> tuple[str, tuple[str, ...], str]:
    intent_id = _identifier(row["intent_id"], "intent_id")
    activation = _texts(row["activation_boundary"], "activation_boundary")
    raw_exclusions = row["confusable_exclusions"]
    if not isinstance(raw_exclusions, (list, tuple)) or not raw_exclusions:
        raise RailsError("confusable_exclusions must be a non-empty sequence")
    exclusions, seen = [], set()
    for index, raw in enumerate(raw_exclusions):
        item = _object(
            raw,
            f"confusable_exclusions[{index}]",
            {"neighboring_intent_id", "distinction"},
        )
        neighbor = _identifier(
            item["neighboring_intent_id"],
            f"confusable_exclusions[{index}].neighboring_intent_id",
        )
        if neighbor == intent_id or neighbor in seen:
            raise RailsError("confusable exclusions must name unique neighboring intents")
        seen.add(neighbor)
        exclusions.append(
            f"{neighbor}: {_text(item['distinction'], f'confusable_exclusions[{index}].distinction')}"
        )
    uncertainty = _text(row["uncertainty_behavior"], "uncertainty_behavior")
    limits = _texts(row["limitations"], "limitations")
    content = (
        f"Intent {intent_id}.\nActivation boundary:\n- "
        + "\n- ".join(activation)
        + "\nConfusable exclusions:\n- "
        + "\n- ".join(exclusions)
        + f"\nUncertainty behavior: {uncertainty}\nLimitations:\n- "
        + "\n- ".join(limits)
    )
    return intent_id, activation, content


def _slot(row: Mapping[str, object]) -> tuple[str, tuple[str, ...], str]:
    slot_id = _identifier(row["slot_id"], "slot_id")
    raw_bindings = row["intent_bindings"]
    if not isinstance(raw_bindings, (list, tuple)) or not raw_bindings:
        raise RailsError("intent_bindings must be a non-empty sequence")
    bindings, seen = [], set()
    for index, raw in enumerate(raw_bindings):
        item = _object(raw, f"intent_bindings[{index}]", {"intent_id", "semantic_role"})
        intent_id = _identifier(item["intent_id"], f"intent_bindings[{index}].intent_id")
        if intent_id in seen:
            raise RailsError("intent_bindings must name unique intent IDs")
        seen.add(intent_id)
        bindings.append(
            f"{intent_id}: {_text(item['semantic_role'], f'intent_bindings[{index}].semantic_role')}"
        )
    extraction = _texts(row["extraction_cues"], "extraction_cues")
    formats = _texts(row["admissible_formats"], "admissible_formats")
    missing = _text(row["missing_behavior"], "missing_behavior")
    ambiguity = _text(row["ambiguity_behavior"], "ambiguity_behavior")
    limits = _texts(row["limitations"], "limitations")
    content = (
        f"Slot {slot_id}.\nIntent bindings and semantic roles:\n- "
        + "\n- ".join(bindings)
        + "\nExtraction cues:\n- "
        + "\n- ".join(extraction)
        + "\nAdmissible formats:\n- "
        + "\n- ".join(formats)
        + f"\nMissing behavior: {missing}\nAmbiguity behavior: {ambiguity}"
        + "\nLimitations:\n- "
        + "\n- ".join(limits)
    )
    return slot_id, tuple(bindings), content


def _build(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str],
    policy_id: str,
    row_keys: set[str],
    id_field: str,
    dimension: str,
    renderer,
) -> KnowledgeSnapshot:
    if not isinstance(spec, AuthoredSemanticKnowledgeSpec):
        raise RailsError("semantic knowledge builder requires AuthoredSemanticKnowledgeSpec")
    spec.validate()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise RailsError("semantic knowledge builder requires non-empty authored rows")
    facets, values, seen, used_sources, source_rows = [], [], set(), set(), []
    for index, raw in enumerate(rows):
        row = _object(raw, f"rows[{index}]", row_keys)
        semantic_id, key_parts, content = renderer(row)
        if semantic_id in seen:
            raise RailsError(f"duplicate {id_field} {semantic_id!r}")
        seen.add(semantic_id)
        source_ids, provenance = _support(
            row["source_support"], f"rows[{index}].source_support"
        )
        used_sources.update(source_ids)
        facet_id = f"{dimension}:{semantic_id}"
        facets.append(
            KeyFacet(
                facet_id=facet_id,
                dimension=dimension,
                representation_kind="text",
                representation=" ".join((semantic_id, *key_parts)),
                source_sample_ids=source_ids,
            ).validate()
        )
        values.append(
            ValueBundle(
                value_id=facet_id,
                content=content,
                associated_facet_ids=(facet_id,),
                source_sample_ids=source_ids,
                provenance_refs=provenance,
            ).validate()
        )
        source_rows.append(dict(row))
    permitted = set(spec.permitted_source_sample_ids)
    if used_sources != permitted:
        raise RailsError(
            "authored source support must equal the permitted construction roster"
        )
    overlap = used_sources & frozenset(forbidden_sample_ids)
    if overlap:
        raise RailsError(
            f"semantic knowledge source intersects forbidden sample IDs: {sorted(overlap)[:5]}"
        )
    order = sorted(range(len(values)), key=lambda item: values[item].value_id)
    facets = tuple(facets[item] for item in order)
    values = tuple(values[item] for item in order)
    identity = content_hash(
        {
            "schema": "saea-authored-semantic-knowledge-build-v1",
            "carrier_lock_key": spec.carrier_lock_key,
            "source_partition_role": spec.source_partition_role,
            "source_split_identity_hash": spec.source_split_identity_hash,
            "source_sample_ids": sorted(used_sources),
            "builder_policy_id": policy_id,
            "rows": sorted(source_rows, key=lambda row: str(row[id_field])),
        }
    )
    return KnowledgeSnapshot(
        snapshot_id=f"{policy_id}:{identity[:16]}",
        source_split_identity_hash=spec.source_split_identity_hash,
        source_sample_ids=tuple(sorted(used_sources)),
        source_partition_role=spec.source_partition_role,
        builder_policy_id=policy_id,
        facets=facets,
        values=values,
    ).validate()


def build_intent_boundary_snapshot(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str] = frozenset(),
) -> KnowledgeSnapshot:
    """Compile reviewed intent boundaries without deriving task targets."""

    return _build(
        spec,
        rows=rows,
        forbidden_sample_ids=forbidden_sample_ids,
        policy_id=INTENT_BOUNDARY_BUILD_POLICY_ID,
        row_keys=_INTENT_KEYS,
        id_field="intent_id",
        dimension="intent-boundary",
        renderer=_intent,
    )


def _common_intent_guidance(
    rows: Sequence[Mapping[str, object]],
) -> tuple[str, tuple[str, ...]]:
    if len(rows) < 2:
        raise RailsError("factored intent boundaries require at least two rows")
    uncertainties = tuple(
        _text(row["uncertainty_behavior"], "uncertainty_behavior") for row in rows
    )
    if len(set(uncertainties)) != 1:
        raise RailsError(
            "factored intent boundaries require one shared uncertainty_behavior"
        )
    limitations = tuple(_texts(row["limitations"], "limitations") for row in rows)
    common_length = 0
    for entries in zip(*limitations, strict=False):
        if len(set(entries)) != 1:
            break
        common_length += 1
    if common_length == 0:
        raise RailsError(
            "factored intent boundaries require a shared leading limitation"
        )
    return uncertainties[0], limitations[0][:common_length]


def _factored_intent_renderer(
    *, common_uncertainty: str, common_limitations: tuple[str, ...]
):
    shared_segment = (
        f"\nUncertainty behavior: {common_uncertainty}\nLimitations:\n- "
        + "\n- ".join(common_limitations)
    )

    def render(row: Mapping[str, object]) -> tuple[str, tuple[str, ...], str]:
        intent_id, activation, content = _intent(row)
        uncertainty = _text(row["uncertainty_behavior"], "uncertainty_behavior")
        limitations = _texts(row["limitations"], "limitations")
        if uncertainty != common_uncertainty or (
            limitations[: len(common_limitations)] != common_limitations
        ):
            raise RailsError("factored intent guidance is not shared by every row")
        special_limitations = limitations[len(common_limitations) :]
        expected_suffix = shared_segment
        if special_limitations:
            expected_suffix += "\n- " + "\n- ".join(special_limitations)
        if not content.endswith(expected_suffix) or content.count(shared_segment) != 1:
            raise RailsError(
                "factored intent guidance does not have one unambiguous exact removal"
            )
        factored = content[: -len(expected_suffix)]
        if special_limitations:
            factored += "\nLimitations:\n- " + "\n- ".join(special_limitations)
        return intent_id, activation, factored

    return render


def build_factored_intent_boundary_snapshot(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str] = frozenset(),
) -> KnowledgeSnapshot:
    """Factor text shared by every reviewed intent into one associated value."""

    original = build_intent_boundary_snapshot(
        spec, rows=rows, forbidden_sample_ids=forbidden_sample_ids
    )
    common_uncertainty, common_limitations = _common_intent_guidance(rows)
    original_ids = {
        *(facet.facet_id for facet in original.facets),
        *(value.value_id for value in original.values),
    }
    if SHARED_INTENT_GUIDANCE_VALUE_ID in original_ids:
        raise RailsError(
            f"factored intent guidance ID collision: {SHARED_INTENT_GUIDANCE_VALUE_ID}"
        )
    factored = _build(
        spec,
        rows=rows,
        forbidden_sample_ids=forbidden_sample_ids,
        policy_id=FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
        row_keys=_INTENT_KEYS,
        id_field="intent_id",
        dimension="intent-boundary",
        renderer=_factored_intent_renderer(
            common_uncertainty=common_uncertainty,
            common_limitations=common_limitations,
        ),
    )
    shared = ValueBundle(
        value_id=SHARED_INTENT_GUIDANCE_VALUE_ID,
        content=(
            f"{_SHARED_INTENT_GUIDANCE_SCOPE}\n"
            f"Uncertainty behavior: {common_uncertainty}\nLimitations:\n- "
            + "\n- ".join(common_limitations)
        ),
        associated_facet_ids=tuple(facet.facet_id for facet in original.facets),
        source_sample_ids=original.source_sample_ids,
        provenance_refs=tuple(sorted({
            provenance
            for value in original.values
            for provenance in value.provenance_refs
        })),
    ).validate()
    return KnowledgeSnapshot(
        snapshot_id=factored.snapshot_id,
        source_split_identity_hash=factored.source_split_identity_hash,
        source_sample_ids=factored.source_sample_ids,
        source_partition_role=factored.source_partition_role,
        builder_policy_id=factored.builder_policy_id,
        facets=original.facets,
        values=tuple(sorted((*factored.values, shared), key=lambda value: value.value_id)),
    ).validate()


def build_slot_contract_snapshot(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str] = frozenset(),
) -> KnowledgeSnapshot:
    """Compile reviewed slot contracts without deriving mandatory fields."""

    return _build(
        spec,
        rows=rows,
        forbidden_sample_ids=forbidden_sample_ids,
        policy_id=SLOT_CONTRACT_BUILD_POLICY_ID,
        row_keys=_SLOT_KEYS,
        id_field="slot_id",
        dimension="slot-contract",
        renderer=_slot,
    )


def build_stage3_delta_snapshot(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str] = frozenset(),
) -> KnowledgeSnapshot:
    """Compile S3-5's curated, append-only authored delta rows (v1).

    Unlike :func:`build_intent_boundary_snapshot`/
    :func:`build_slot_contract_snapshot` (which derive ONE self-minted
    facet and ONE value per row and require ``source_sample_ids`` to equal
    the permitted roster exactly), a stage3-deltas row is pre-authored by
    S3-5's curator: ``value_id``, ``associated_facet_ids``,
    ``source_sample_ids``, ``provenance_refs``, ``task_target`` and
    ``prior_score`` are already the exact :class:`~.knowledge.ValueBundle`
    fields (spec section S3-5; ``rails.stage3_advantage`` module
    docstring), and only a SUBSET of the permitted construction roster is
    ever used -- only disagreeing rows survive S3-3's selection and S3-5's
    dedup -- so this builder requires ``used_sources.issubset(permitted)``,
    never equality.

    One :class:`~.knowledge.KeyFacet` is minted per DISTINCT
    ``associated_facet_ids`` entry seen across every row (dimension
    :data:`STAGE3_DELTA_DIMENSION`), so a release is self-contained: every
    facet a value names exists in the same snapshot. ``value_id`` must
    match ``delta:<iteration>:<12-hex>`` (the spec's own id form).
    """

    return _build_stage3_delta_snapshot(
        spec,
        rows=rows,
        forbidden_sample_ids=forbidden_sample_ids,
        builder_policy_id=STAGE3_DELTA_BUILD_POLICY_ID,
        row_keys=_STAGE3_DELTA_KEYS,
    )


def build_stage3_delta_snapshot_v2(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str] = frozenset(),
) -> KnowledgeSnapshot:
    """Compile S3-5's NODE-TARGETED authored delta rows (S3-4s, owner
    decision 106).

    Identical to :func:`build_stage3_delta_snapshot` in every rule it
    enforces -- append-only subset of the permitted construction roster, no
    forbidden sample, one self-minted facet per distinct
    ``associated_facet_ids`` entry, ``delta:<iteration>:<12-hex>`` value ids
    -- plus exactly two: every row carries a ``node_target`` in
    :data:`STAGE3_DELTA_NODE_TARGETS`, and its ``task_target`` begins with
    that node (``NODE:DELTA-KIND:TARGET``). ``node_target`` itself is NOT a
    :class:`~.knowledge.ValueBundle` field: the released value carries the
    node inside ``task_target``, which is where every consumer reads it from
    (``rails.stage3_delta_supply.node_target_of_task_target``), so a release
    stays self-describing without a schema change to the shared contract.
    """

    return _build_stage3_delta_snapshot(
        spec,
        rows=rows,
        forbidden_sample_ids=forbidden_sample_ids,
        builder_policy_id=STAGE3_DELTA_V2_BUILD_POLICY_ID,
        row_keys=_STAGE3_DELTA_V2_KEYS,
    )


def _build_stage3_delta_snapshot(
    spec: AuthoredSemanticKnowledgeSpec,
    *,
    rows: Sequence[Mapping[str, object]],
    forbidden_sample_ids: frozenset[str],
    builder_policy_id: str,
    row_keys: set,
) -> KnowledgeSnapshot:
    """The shared compiler behind the v1 and v2 delta builders."""

    node_targeted = "node_target" in row_keys
    if not isinstance(spec, AuthoredSemanticKnowledgeSpec):
        raise RailsError("stage3 delta builder requires AuthoredSemanticKnowledgeSpec")
    spec.validate()
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise RailsError("stage3 delta builder requires non-empty authored rows")

    values: list[ValueBundle] = []
    facet_sources: dict[str, set[str]] = {}
    seen_ids: set[str] = set()
    used_sources: set[str] = set()
    source_rows: list[Mapping[str, object]] = []
    for index, raw in enumerate(rows):
        row = _object(raw, f"rows[{index}]", row_keys)
        value_id = _text(row["value_id"], f"rows[{index}].value_id")
        if _DELTA_VALUE_ID.fullmatch(value_id) is None:
            raise RailsError(
                f"rows[{index}].value_id must match 'delta:<iteration>:<12-hex>', "
                f"got {value_id!r}"
            )
        if value_id in seen_ids:
            raise RailsError(f"duplicate value_id {value_id!r}")
        seen_ids.add(value_id)
        associated = _texts(row["associated_facet_ids"], f"rows[{index}].associated_facet_ids")
        source_ids = _texts(row["source_sample_ids"], f"rows[{index}].source_sample_ids")
        provenance = tuple(
            sorted(_texts(row["provenance_refs"], f"rows[{index}].provenance_refs"))
        )
        task_target = _text(row["task_target"], f"rows[{index}].task_target")
        if node_targeted:
            node_target = _text(row["node_target"], f"rows[{index}].node_target")
            if node_target not in STAGE3_DELTA_NODE_TARGETS:
                raise RailsError(
                    f"rows[{index}].node_target must be one of "
                    f"{STAGE3_DELTA_NODE_TARGETS}, got {node_target!r}"
                )
            if not task_target.startswith(f"{node_target}:"):
                raise RailsError(
                    f"rows[{index}].task_target must be "
                    "'<node_target>:<delta-kind>:<target>'"
                )
        prior_score = row["prior_score"]
        if isinstance(prior_score, bool) or not isinstance(prior_score, (int, float)):
            raise RailsError(f"rows[{index}].prior_score must be a number")
        used_sources.update(source_ids)
        for facet_id in associated:
            facet_sources.setdefault(facet_id, set()).update(source_ids)
        values.append(
            ValueBundle(
                value_id=value_id,
                content=_text(row["content"], f"rows[{index}].content"),
                associated_facet_ids=associated,
                source_sample_ids=source_ids,
                provenance_refs=provenance,
                task_target=task_target,
                prior_score=float(prior_score),
            ).validate()
        )
        source_rows.append(dict(row))

    permitted = set(spec.permitted_source_sample_ids)
    if not used_sources.issubset(permitted):
        raise RailsError(
            "authored delta source_sample_ids must be a subset of the permitted "
            "construction roster"
        )
    overlap = used_sources & frozenset(forbidden_sample_ids)
    if overlap:
        raise RailsError(
            f"stage3 delta source intersects forbidden sample IDs: {sorted(overlap)[:5]}"
        )

    facets = tuple(
        KeyFacet(
            facet_id=facet_id,
            dimension=STAGE3_DELTA_DIMENSION,
            representation_kind="text",
            representation=facet_id.split(":", 1)[-1],
            source_sample_ids=tuple(sorted(source_ids)),
        ).validate()
        for facet_id, source_ids in sorted(facet_sources.items())
    )
    order = sorted(range(len(values)), key=lambda item: values[item].value_id)
    values = tuple(values[item] for item in order)
    identity = content_hash(
        {
            "schema": "saea-authored-semantic-knowledge-build-v1",
            "carrier_lock_key": spec.carrier_lock_key,
            "source_partition_role": spec.source_partition_role,
            "source_split_identity_hash": spec.source_split_identity_hash,
            "source_sample_ids": sorted(used_sources),
            "builder_policy_id": builder_policy_id,
            "rows": sorted(source_rows, key=lambda row: str(row["value_id"])),
        }
    )
    return KnowledgeSnapshot(
        snapshot_id=f"{builder_policy_id}:{identity[:16]}",
        source_split_identity_hash=spec.source_split_identity_hash,
        source_sample_ids=tuple(sorted(used_sources)),
        source_partition_role=spec.source_partition_role,
        builder_policy_id=builder_policy_id,
        facets=facets,
        values=values,
    ).validate()


__all__ = [
    "FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID",
    "INTENT_BOUNDARY_BUILD_POLICY_ID",
    "SHARED_INTENT_GUIDANCE_VALUE_ID",
    "SLOT_CONTRACT_BUILD_POLICY_ID",
    "STAGE3_DELTA_BUILD_POLICY_ID",
    "STAGE3_DELTA_DIMENSION",
    "STAGE3_DELTA_NODE_TARGETS",
    "STAGE3_DELTA_V2_BUILD_POLICY_ID",
    "AuthoredSemanticKnowledgeSpec",
    "build_factored_intent_boundary_snapshot",
    "build_intent_boundary_snapshot",
    "build_slot_contract_snapshot",
    "build_stage3_delta_snapshot",
    "build_stage3_delta_snapshot_v2",
]
