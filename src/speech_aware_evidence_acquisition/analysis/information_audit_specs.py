"""Carrier information-spec builders for the Part B dataset information audit
(2026-09-03 recovery plan, "one template, three carriers").

:class:`CarrierInformationSpec` is a frozen, carrier-agnostic description of
what :mod:`.information_audit` needs to answer its eight standing questions
about one carrier's task-information supply. This module is the INTERIM
home for the three builders below (:func:`audio2tool_spec`,
:func:`slurp_spec`, :func:`earnings21_conec_spec`); the planned C2 slice's
``TaskAdapter.information_spec()`` method is expected to return the same
shape directly from each adapter, at which point these free functions
become thin compatibility wrappers or are retired.

Design notes (why the shape here is a superset of the literal field list in
the recovery plan's Part B goal 1):

* Every "row" a loader or roster returns is a plain ``Mapping[str, object]``
  carrying at minimum ``"item_id"``. This keeps :mod:`.information_audit`'s
  eight question functions pure and carrier-blind: they only ever call the
  four supplied callables (``stratum_of``, ``labels_of``, ``key_text_of``,
  ``group_of``) on these dicts, so a unit test can feed synthetic dict rows
  without touching any governed dataset.
* ``retrieval_mode`` distinguishes the two structurally different Q5
  (retrieval-reachability) computations the recovery plan itself specifies:
  ``"grouped_bm25"`` (SLURP and Audio2Tool -- a shared TRAIN/construction
  corpus is queried by held-out text, exactly the label-blind grouped
  out-of-fold protocol
  ``analysis.a2t_grouped_candidate_validation.analyze_grouped_candidate_validation``
  already established) versus ``"self_supplied_membership"`` (Earnings21 +
  ConEC -- each evaluation call ships its OWN knowledge document, so
  reachability is a direct own-call-vs-random-other-call membership check,
  not a corpus ranking).
* :class:`EvaluationRoster` carries pre-aggregated ``stratum_counts`` (Q3)
  and a lazy ``identity_loader`` (Q6) rather than a second row-producing
  callable: several real rosters (the SLURP DEV-100/500/1000 ladder) already
  publish their own per-stratum allocation and identity list in a committed
  receipt, so re-deriving them from raw per-item rows would mean reading
  data this audit does not need to touch (see :func:`slurp_spec`'s own
  docstring for why DEV-* utterance TEXT is deliberately never read here).
* ``obs_org_supply_use`` (Q2) and ``external_supplementation`` (Q7) are
  genuinely carrier-specific narrative judgments, not something derivable
  from rows; they are still spec data (not hardcoded in the runner) so a
  future carrier only has to add a builder here, never edit
  ``information_audit.py``.

Zero model, GPU, network, or embedding contact anywhere in this module.
Every GOVERNED-DATASET read (SLURP train material, ConEC evidence, the
entity-mention inventory) is LAZY -- a closure over ``lock``/``root`` inside
``construction_loader`` -- so building a spec never itself opens a dataset
byte under ``SPEECHRL_DATA_DIR``; ``lock``/``root`` can be placeholder
values at build time. The one exception is :func:`slurp_spec`'s own
DEV-100/500/1000 roster receipts: those are small, already-committed
``docs/receipts/probe-samples/*.json`` files (not governed dataset bytes),
read EAGERLY at build time because their own ``scenario_allocation``/
``selection_rule``/``items[].id`` fields ARE the roster facts this spec
carries (module docstring below, :func:`_slurp_roster_from_receipt`) --
building that spec therefore needs a real ``repo_root``, even though
``lock``/``root`` stay untouched until ``construction_loader()`` is called.
Earnings21+ConEC's entity-mention
labels are read from the already-committed, gold-derived, offline entity
inventory (``scripts/build_entity_inventory.py``'s own output under
``$SPEECHRL_DATA_DIR/derived/entity-inventory/v1/``) rather than importing
``data.references`` directly: that module's raw reference-token/wer_tags
join is import-restricted to ``core/scorers.py``
(``tests/contract/test_reference_import_isolation.py``), and
``scripts/build_entity_inventory.py``'s own module docstring explains why an
entity-data consumer cannot itself live under ``src/`` -- this module
respects that boundary by consuming the sanctioned derived cache instead of
re-implementing the restricted join.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

LEGALITY_CLASSES = frozenset(
    {
        "runtime-legal-input",
        "construction-only-knowledge",
        "gold-scoring-only",
        "forbidden",
    }
)

RETRIEVAL_MODES = frozenset({"grouped_bm25", "self_supplied_membership"})

#: The unit-separator character joining ``entity_type`` and a normalized
#: mention filler inside one ``"entity_mention"`` label-field string
#: (Earnings21+ConEC only) -- chosen because it can never occur in
#: alphanumeric filler text and is itself never emitted into any document
#: this study authors (only aggregate counts derived from it are).
MENTION_FIELD_SEPARATOR = "␟"


class CarrierInformationSpecError(ValueError):
    """A spec, a builder input, or an ``EvaluationRoster`` is malformed."""


def _nonempty_str(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CarrierInformationSpecError(f"{label} must be non-empty text")
    return value


@dataclass(frozen=True)
class EvaluationRoster:
    """One evaluation roster's Q3/Q6/Q8 facts, pre-aggregated where the
    roster's own committed receipt already publishes them (module
    docstring)."""

    name: str
    split_role: str
    intended_n: int
    stratum_counts: Mapping[str, int]
    selection_rule_note: str
    identity_loader: Callable[[], frozenset[str]]
    path: Path | None = None

    def __post_init__(self) -> None:
        _nonempty_str(self.name, "EvaluationRoster.name")
        _nonempty_str(self.split_role, "EvaluationRoster.split_role")
        if isinstance(self.intended_n, bool) or not isinstance(self.intended_n, int) or self.intended_n <= 0:
            raise CarrierInformationSpecError("EvaluationRoster.intended_n must be a positive int")
        if not isinstance(self.stratum_counts, Mapping) or not self.stratum_counts:
            raise CarrierInformationSpecError("EvaluationRoster.stratum_counts must be non-empty")
        for key, value in self.stratum_counts.items():
            if not isinstance(key, str) or not key:
                raise CarrierInformationSpecError("EvaluationRoster.stratum_counts keys must be text")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise CarrierInformationSpecError(
                    "EvaluationRoster.stratum_counts values must be non-negative ints"
                )
        _nonempty_str(self.selection_rule_note, "EvaluationRoster.selection_rule_note")
        if not callable(self.identity_loader):
            raise CarrierInformationSpecError("EvaluationRoster.identity_loader must be callable")


@dataclass(frozen=True)
class CarrierInformationSpec:
    """A carrier's complete, carrier-agnostic information-audit description.

    Field order mirrors the recovery plan's Part B goal 1 literal list
    (``carrier_lock_key`` .. ``group_of``); every field after ``group_of``
    is an addition this module's own docstring justifies.
    """

    carrier_lock_key: str
    task_kind: str
    strata_key: str
    label_fields: tuple[str, ...]
    field_legality: Mapping[str, str]
    knowledge_source: str
    construction_loader: Callable[[], Sequence[Mapping[str, object]]]
    evaluation_rosters: tuple[EvaluationRoster, ...]
    stratum_of: Callable[[Mapping[str, object]], str]
    labels_of: Callable[[Mapping[str, object]], Mapping[str, tuple[str, ...]]]
    key_text_of: Callable[[Mapping[str, object]], str]
    group_of: Callable[[Mapping[str, object]], str]
    retrieval_mode: str
    corpus_structure_legality: Mapping[str, str]
    obs_org_supply_use: Mapping[str, str]
    external_supplementation: tuple[Mapping[str, str], ...]

    def __post_init__(self) -> None:
        _nonempty_str(self.carrier_lock_key, "carrier_lock_key")
        _nonempty_str(self.task_kind, "task_kind")
        _nonempty_str(self.strata_key, "strata_key")
        if not isinstance(self.label_fields, tuple) or not self.label_fields:
            raise CarrierInformationSpecError("label_fields must be a non-empty tuple")
        if any(not isinstance(field, str) or not field for field in self.label_fields):
            raise CarrierInformationSpecError("label_fields entries must be non-empty text")
        if not isinstance(self.field_legality, Mapping) or not self.field_legality:
            raise CarrierInformationSpecError("field_legality must be a non-empty mapping")
        for key, value in self.field_legality.items():
            if not isinstance(key, str) or not key:
                raise CarrierInformationSpecError("field_legality keys must be non-empty text")
            if value not in LEGALITY_CLASSES:
                raise CarrierInformationSpecError(
                    f"field_legality[{key!r}] = {value!r} is not one of {sorted(LEGALITY_CLASSES)}"
                )
        if not isinstance(self.corpus_structure_legality, Mapping):
            raise CarrierInformationSpecError("corpus_structure_legality must be a mapping")
        for key, value in self.corpus_structure_legality.items():
            if not isinstance(key, str) or not key:
                raise CarrierInformationSpecError(
                    "corpus_structure_legality keys must be non-empty text"
                )
            if value not in LEGALITY_CLASSES:
                raise CarrierInformationSpecError(
                    f"corpus_structure_legality[{key!r}] = {value!r} is not one of "
                    f"{sorted(LEGALITY_CLASSES)}"
                )
        _nonempty_str(self.knowledge_source, "knowledge_source")
        if not callable(self.construction_loader):
            raise CarrierInformationSpecError("construction_loader must be callable")
        if not isinstance(self.evaluation_rosters, tuple) or not self.evaluation_rosters:
            raise CarrierInformationSpecError("evaluation_rosters must be a non-empty tuple")
        if any(not isinstance(roster, EvaluationRoster) for roster in self.evaluation_rosters):
            raise CarrierInformationSpecError("evaluation_rosters entries must be EvaluationRoster")
        names = [roster.name for roster in self.evaluation_rosters]
        if len(names) != len(set(names)):
            raise CarrierInformationSpecError("evaluation_rosters names must be unique")
        for callable_field in ("stratum_of", "labels_of", "key_text_of", "group_of"):
            if not callable(getattr(self, callable_field)):
                raise CarrierInformationSpecError(f"{callable_field} must be callable")
        if self.retrieval_mode not in RETRIEVAL_MODES:
            raise CarrierInformationSpecError(
                f"retrieval_mode {self.retrieval_mode!r} is not one of {sorted(RETRIEVAL_MODES)}"
            )
        if not isinstance(self.obs_org_supply_use, Mapping) or set(self.obs_org_supply_use) != {
            "obs",
            "org",
            "supply",
            "use",
        }:
            raise CarrierInformationSpecError(
                "obs_org_supply_use must carry exactly the four keys obs/org/supply/use"
            )
        for key, value in self.obs_org_supply_use.items():
            _nonempty_str(value, f"obs_org_supply_use[{key!r}]")
        if not isinstance(self.external_supplementation, tuple) or not self.external_supplementation:
            raise CarrierInformationSpecError("external_supplementation must be a non-empty tuple")
        for row in self.external_supplementation:
            if not isinstance(row, Mapping) or set(row) != {"need", "source", "legality"}:
                raise CarrierInformationSpecError(
                    "external_supplementation rows must carry exactly need/source/legality"
                )
            _nonempty_str(row["need"], "external_supplementation need")
            _nonempty_str(row["source"], "external_supplementation source")
            if row["legality"] not in LEGALITY_CLASSES:
                raise CarrierInformationSpecError(
                    f"external_supplementation legality {row['legality']!r} is not one of "
                    f"{sorted(LEGALITY_CLASSES)}"
                )


# ---------------------------------------------------------------------------
# Audio2Tool
# ---------------------------------------------------------------------------

_AUDIO2TOOL_FIELD_LEGALITY: Mapping[str, str] = {
    "tier": "runtime-legal-input",
    "query_idx": "construction-only-knowledge",
    "text (construction utterance)": "construction-only-knowledge",
    "tool_name (primary gold call)": "gold-scoring-only",
    "extra_call_names (gold call tail)": "gold-scoring-only",
    "arg_signature / arg_pairs (gold value bindings)": "gold-scoring-only",
    "public tool registry (name/domain/category/description)": "runtime-legal-input",
}
_AUDIO2TOOL_CORPUS_STRUCTURE_LEGALITY: Mapping[str, str] = {
    "query_idx block (voice renderings of one task)": "construction-only-knowledge",
    "ordered call multiset per unit": "gold-scoring-only",
    "tier7 complete-dialogue manifest": "construction-only-knowledge",
}
_AUDIO2TOOL_OBS_ORG_SUPPLY_USE: Mapping[str, str] = {
    "obs": (
        "Recover a bounded English actionable span from the rendered speech, "
        "surviving corrections, prior-turn dependencies, requested multiplicity, "
        "and typed value spans -- never the reference transcript."
    ),
    "org": (
        "Segment-aware label retrieval over the 152-tool registry; primary metric "
        "is full required-label-set coverage at k (label recall/precision/distractor "
        "burden are required diagnostics)."
    ),
    "supply": (
        "Load only the retrieved labels' canonical values: exact tool name, "
        "operation meaning, legal skeletons, types, enum casing, defaults, "
        "omission rules, canonicalization rules -- never a construction example value."
    ),
    "use": (
        "A genuine frozen-core call choosing the ordered call set and binding values "
        "from speech/OBS under the supplied contracts."
    ),
}
_AUDIO2TOOL_EXTERNAL_SUPPLEMENTATION: tuple[Mapping[str, str], ...] = (
    {
        "need": "Canonical per-tool operation/type/default/omission semantics beyond a bare name",
        "source": "The frozen public tool registry (tools_registry.csv) already shipped with the carrier",
        "legality": "runtime-legal-input",
    },
    {
        "need": "A semantic (not lexical) key that survives paraphrase for implicit/multiturn requests",
        "source": (
            "A pinned local embedding retriever over the SAME public registry/construction text "
            "(no gold, no second answering LLM) -- registered as a future comparison, not yet promoted"
        ),
        "legality": "runtime-legal-input",
    },
    {
        "need": "Prior dialogue state for multiturn/correction requests when OBS alone is information-poor",
        "source": "Presented prior agent turns already available to the runtime session",
        "legality": "runtime-legal-input",
    },
)


def audio2tool_spec(
    lock: Mapping[str, object], root: Path, repo_root: Path
) -> CarrierInformationSpec:
    """Audio2Tool's information spec. NOT exercised end-to-end by this audit
    (the 2026-09-03 prototype at
    ``docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-construction-task-information-audit/``
    already answers these eight questions for this carrier); this builder
    exists so the spec SHAPE is registered for the three carriers together
    and so a future ``TaskAdapter.information_spec()`` has one existing
    reference implementation to converge on. ``construction_loader`` is
    real and lazy (imports ``rails.*`` only inside this function body, so
    importing this module never touches the concurrently-edited
    ``rails`` package) but is not called by this recovery-plan submission."""

    def _construction_loader() -> Sequence[Mapping[str, object]]:
        # Deferred imports: rails.* is concurrently edited by other agents in
        # this program; importing it only when this callable is actually
        # invoked keeps `import information_audit_specs` itself safe even if
        # rails.* is momentarily broken mid-edit.
        from ..data.audio2tool import AUDIO2TOOL_LOCK_KEY  # noqa: F401  (identity check only)
        from ..rails.knowledge_build_a2t import a2t_pool_rows, exposed_sample_ids, propose_partition

        rows, _inventory = a2t_pool_rows(lock, root)
        partition = propose_partition(rows, exposed_sample_ids(repo_root), seed=20260807)
        return tuple(
            {
                "item_id": row.unit_id,
                "tier": row.tier,
                "query_idx": row.query_idx,
                "tool_name": row.tool_name,
                "extra_call_names": row.extra_call_names,
                "text": row.text,
            }
            for row in partition.construction
        )

    def _stratum_of(row: Mapping[str, object]) -> str:
        return str(row["tier"])

    def _labels_of(row: Mapping[str, object]) -> Mapping[str, tuple[str, ...]]:
        names = (str(row["tool_name"]), *row["extra_call_names"])
        return {"tool_name": names}

    def _key_text_of(row: Mapping[str, object]) -> str:
        return str(row["text"])

    def _group_of(row: Mapping[str, object]) -> str:
        return str(row["query_idx"])

    return CarrierInformationSpec(
        carrier_lock_key="audio2tool",
        task_kind="speech-tool-use",
        strata_key="tier",
        label_fields=("tool_name",),
        field_legality=_AUDIO2TOOL_FIELD_LEGALITY,
        knowledge_source="frozen public tool registry (152 tools) plus construction query-block text",
        construction_loader=_construction_loader,
        evaluation_rosters=(
            EvaluationRoster(
                name="exposed-discovery-400",
                split_role="discovery",
                intended_n=400,
                # Placeholder counts: the real per-tier allocation is already
                # published in the prototype's own README/summary.json and is
                # not re-derived here (construction_loader is not exercised by
                # this submission -- module docstring).
                stratum_counts={"direct": 50, "parametric": 50, "multi-intent": 50,
                                 "implicit": 50, "needle": 50, "correction": 50,
                                 "multiturn": 50, "intent-blending": 50},
                selection_rule_note=(
                    "Equal-tier stress roster (50 rows/tier), not the natural construction "
                    "mixture -- see the prototype README's own population section"
                ),
                identity_loader=lambda: frozenset(),
            ),
        ),
        stratum_of=_stratum_of,
        labels_of=_labels_of,
        key_text_of=_key_text_of,
        group_of=_group_of,
        retrieval_mode="grouped_bm25",
        corpus_structure_legality=_AUDIO2TOOL_CORPUS_STRUCTURE_LEGALITY,
        obs_org_supply_use=_AUDIO2TOOL_OBS_ORG_SUPPLY_USE,
        external_supplementation=_AUDIO2TOOL_EXTERNAL_SUPPLEMENTATION,
    )


# ---------------------------------------------------------------------------
# SLURP
# ---------------------------------------------------------------------------

_SLURP_FIELD_LEGALITY: Mapping[str, str] = {
    "scenario": "runtime-legal-input",
    "action": "gold-scoring-only",
    "intent (scenario_action)": "gold-scoring-only",
    "entities (type + filler span)": "gold-scoring-only",
    "sample_id / utterance_id / media_relpath": "runtime-legal-input",
    "audio_seconds": "runtime-legal-input",
    "train sentence text (SlurpTrainMaterial.sentence)": "construction-only-knowledge",
    "train speaker_id": "construction-only-knowledge",
    "devel/test sentence text": "forbidden",
}
_SLURP_CORPUS_STRUCTURE_LEGALITY: Mapping[str, str] = {
    "utterance (one or more recordings sharing one sentence/scenario/action/entities)": (
        "construction-only-knowledge"
    ),
    "train_synthetic split": "forbidden",
    "test split": "forbidden",
}
_SLURP_OBS_ORG_SUPPLY_USE: Mapping[str, str] = {
    "obs": (
        "Perceive the spoken command from AUDIO only (SlurpRecord carries no sentence "
        "field at runtime); recover scenario/action/entity-bearing spans without a "
        "reference transcript."
    ),
    "org": (
        "Multi-dimensional key retrieval (content/speaker/label/prior) over the "
        "TRAIN-modeled knowledge base; a ranking policy fuses dimensions -- Q-K-V "
        "doctrine, owner ruling 2026-08-23 section 1."
    ),
    "supply": (
        "Consume retrieved TRAIN-derived value cards (scenario/action exemplars, "
        "entity-type fillers) as priors, sample-linked, never embedded as ground truth."
    ),
    "use": (
        "The frozen core commits to one scenario_action intent and a set of "
        "(type, filler) entity slots per utterance."
    ),
}
_SLURP_EXTERNAL_SUPPLEMENTATION: tuple[Mapping[str, str], ...] = (
    {
        "need": "A user/domain ontology of legal scenario/action/entity-type names",
        "source": "data.slurp.load_slurp_ontology (mined from train only, include_synthetic=False)",
        "legality": "construction-only-knowledge",
    },
    {
        "need": "Entity-type example fillers for value-card construction",
        "source": "The KB build (slurp-kb-distmodel-v1) TRAIN-modeled datastore, decontaminated vs devel/test",
        "legality": "construction-only-knowledge",
    },
    {
        "need": "A larger action-support pool for long-tail scenarios/entities",
        "source": "The T500 train-side discovery tier (approved in principle, 2026-08-23 ruling section 2)",
        "legality": "construction-only-knowledge",
    },
)


def _slurp_roster_from_receipt(path: Path) -> EvaluationRoster:
    """Build one DEV-* :class:`EvaluationRoster` from its own committed
    receipt (module docstring: never re-derives per-item scenario labels by
    loading ``devel`` text -- ``scenario_allocation``/``items[].id`` are
    already published fields of the receipt itself)."""

    def _identity_loader() -> frozenset[str]:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        items = document["items"]
        ids: set[str] = set()
        for item in items:
            raw_id = str(item["id"])
            # "slurp:devel:000090:audio-1498567209" -> the bare, unpadded
            # SLURP utterance number "90" -- the SAME comparable identity
            # namespace `slurp_spec`'s own construction rows use (their
            # "item_id" is `SlurpTrainMaterial.utterance_id`, already a bare
            # decimal string), so Q6 can intersect the two sets directly
            # without reading devel sentence content at all.
            parts = raw_id.split(":")
            if len(parts) < 3 or parts[0] != "slurp" or parts[1] != "devel":
                raise CarrierInformationSpecError(f"unexpected SLURP roster id shape: {raw_id!r}")
            ids.add(str(int(parts[2])))
        return frozenset(ids)

    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return EvaluationRoster(
        name=str(document["probe"]),
        split_role=str(document["split_role"]),
        intended_n=int(document["n_items"]),
        stratum_counts={
            str(scenario): int(count)
            for scenario, count in document["scenario_allocation"].items()
        },
        selection_rule_note=str(document["selection_rule"]),
        identity_loader=_identity_loader,
        path=path,
    )


def slurp_spec(lock: Mapping[str, object], root: Path, repo_root: Path) -> CarrierInformationSpec:
    """SLURP's information spec.

    ``construction_loader`` reads ONLY ``train`` (never ``train_synthetic``,
    which recurs verbatim in 64.8% of ``devel`` -- ``data.slurp.
    load_slurp_ontology``'s own docstring finding, cited here rather than
    re-derived; never ``devel``/``test`` sentence content). Evaluation
    rosters are read from the DEV-100/500/1000 ladder receipts already
    committed under ``docs/receipts/probe-samples/`` -- their own
    ``scenario_allocation``/``selection_rule``/``items[].id`` fields are
    read directly, so no devel utterance TEXT is ever opened by this spec,
    following the same identity-only decontamination discipline
    ``docs/receipts/knowledge/slurp-split-identity.json``'s own generator
    already established for SLURP dev/test.
    """

    from ..data.slurp import load_slurp_train_material

    def _construction_loader() -> Sequence[Mapping[str, object]]:
        material = load_slurp_train_material(lock, root)
        return tuple(
            {
                "item_id": row.utterance_id,
                "scenario": row.scenario,
                "action": row.action,
                "intent": f"{row.scenario}_{row.action}",
                "entity_types": row.entity_types,
                "text": row.sentence,
                "recording_count": len(row.recordings),
            }
            for row in material
        )

    def _stratum_of(row: Mapping[str, object]) -> str:
        return str(row["scenario"])

    def _labels_of(row: Mapping[str, object]) -> Mapping[str, tuple[str, ...]]:
        return {
            "intent": (str(row["intent"]),),
            "entity_type": tuple(str(value) for value in row["entity_types"]),
        }

    def _key_text_of(row: Mapping[str, object]) -> str:
        return str(row["text"])

    def _group_of(row: Mapping[str, object]) -> str:
        return str(row["item_id"])

    roster_dir = Path(repo_root) / "docs" / "receipts" / "probe-samples"
    rosters = tuple(
        _slurp_roster_from_receipt(roster_dir / name)
        for name in ("DEV-100.json", "DEV-500.json", "DEV-1000.json")
    )

    return CarrierInformationSpec(
        carrier_lock_key="slurp",
        task_kind="slot-slu",
        strata_key="scenario",
        label_fields=("intent", "entity_type"),
        field_legality=_SLURP_FIELD_LEGALITY,
        knowledge_source="SLURP train split (SlurpTrainMaterial): sentence text + scenario/action/entity_types",
        construction_loader=_construction_loader,
        evaluation_rosters=rosters,
        stratum_of=_stratum_of,
        labels_of=_labels_of,
        key_text_of=_key_text_of,
        group_of=_group_of,
        retrieval_mode="grouped_bm25",
        corpus_structure_legality=_SLURP_CORPUS_STRUCTURE_LEGALITY,
        obs_org_supply_use=_SLURP_OBS_ORG_SUPPLY_USE,
        external_supplementation=_SLURP_EXTERNAL_SUPPLEMENTATION,
    )


# ---------------------------------------------------------------------------
# Earnings21 + ConEC
# ---------------------------------------------------------------------------

_EARNINGS_FIELD_LEGALITY: Mapping[str, str] = {
    "sample_id / media_relpath / audio_seconds / sample_rate_hz": "runtime-legal-input",
    "ConEC context document (evidence_source=conec-contexts)": "runtime-legal-input",
    "ConEC participant-names roster (evidence_source=conec-names)": "runtime-legal-input",
    "ConEC-derived bias list (evidence_source=conec-bias-list)": "runtime-legal-input",
    "reference transcript tokens (.nlp)": "forbidden",
    "wer_tags entity id -> entity_type sidecar": "gold-scoring-only",
    "entity mention filler text (token join of a wer_tags span)": "gold-scoring-only",
}
_EARNINGS_CORPUS_STRUCTURE_LEGALITY: Mapping[str, str] = {
    "one ConEC evidence document per call (no shared corpus)": "runtime-legal-input",
    "earnings21-original confirmatory remainder (beyond the 44-call discovery split)": "forbidden",
    "call 4320211 (pre-existing wer_tags sidecar defect: entity id 1057 has no usable entity_type; excluded from entity-mention rows, n=43 of 44)": (
        "gold-scoring-only"
    ),
}
_EARNINGS_OBS_ORG_SUPPLY_USE: Mapping[str, str] = {
    "obs": "Transcribe/segment the earnings-call speech into entity-bearing spans, ASR-free at the knowledge layer.",
    "org": (
        "No cross-call retrieval: ConEC ships one context/names/bias-list document PER call, so "
        "organization here is selecting WHICH of the three self-supplied documents (or their "
        "extraction) to expose, not ranking across a corpus."
    ),
    "supply": "Expose the call's own ConEC context, names roster, and/or extracted bias-list terms as evidence.",
    "use": "The frozen core produces a transcript hypothesis whose entity spans are scored against wer_tags gold.",
}
_EARNINGS_EXTERNAL_SUPPLEMENTATION: tuple[Mapping[str, str], ...] = (
    {
        "need": "Company/ticker/person canonical spellings beyond what one call's own ConEC document lists",
        "source": "Another call's ConEC document (explicitly a NEGATIVE-CONTROL / cross-contamination risk, not a legal supply)",
        "legality": "forbidden",
    },
    {
        "need": "A budget-bounded distillation of the raw ConEC context to fit prompt budgets",
        "source": "core.bias_lists.extract_bias_candidates / reconstruct_bias_phrases over the SAME call's own context",
        "legality": "runtime-legal-input",
    },
)

_CONEC_TEXT_KINDS = ("context", "names", "bias_list")


def _normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def _earnings_construction_rows(
    lock: Mapping[str, object],
    root: Path,
    repo_root: Path,
) -> tuple[dict[str, object], ...]:
    """Lazy loader body shared by ``earnings21_conec_spec``'s
    ``construction_loader`` (module docstring: entity-mention labels come
    from the already-committed offline entity inventory, never from
    ``data.references`` directly)."""

    from ..core.evidence import _conec_bias_list, _conec_contexts, _conec_names
    from ..core.base import EvidenceError
    from ..data.splits import discovery_split

    split = discovery_split(lock, root)
    ids = sorted(sample_id.split("/", 1)[1] for sample_id in split.ids)
    inventory_dir = Path(root) / "derived" / "entity-inventory" / "v1"

    rows: list[dict[str, object]] = []
    excluded: list[str] = []
    for sample_id in ids:
        inventory_path = inventory_dir / f"{sample_id}.json"
        if not inventory_path.is_file():
            # Known pre-existing gold-data defect (not caused by this study):
            # scripts/build_entity_inventory.py's own manifest.json records
            # exactly one failure -- sample 4320211's wer_tag.json sidecar
            # has an entity id ('1057') with no usable entity_type, so
            # reference_entity_mentions refuses that call closed rather than
            # silently dropping the malformed mention. This audit excludes
            # that one call from entity-mention-dependent rows (reported
            # honestly via a construction_unit_count < 44 and this print)
            # rather than treating the whole 44-call discovery census as
            # unreadable.
            excluded.append(sample_id)
            print(
                f"information_audit: excluding {sample_id!r} from Earnings21+ConEC construction "
                f"rows -- no cached entity inventory at {inventory_path} (known pre-existing "
                "wer_tags sidecar defect; see scripts/build_entity_inventory.py's own manifest.json "
                "failures)",
                file=sys.stderr,
            )
            continue
        document = json.loads(inventory_path.read_text(encoding="utf-8"))
        mentions = document["mentions"]

        evidence_text: dict[str, str] = {}
        for kind, reader in (
            ("context", _conec_contexts),
            ("names", _conec_names),
            ("bias_list", _conec_bias_list),
        ):
            try:
                items = reader(lock, root, sample_id, "earnings21-original")
            except EvidenceError:
                evidence_text[kind] = ""
                continue
            evidence_text[kind] = _normalize(" ".join(item.content for item in items))

        entity_type_labels = tuple(str(mention["entity_type"]) for mention in mentions)
        mention_labels = tuple(
            f"{mention['entity_type']}{MENTION_FIELD_SEPARATOR}{_normalize(' '.join(mention['tokens']))}"
            for mention in mentions
        )
        rows.append(
            {
                "item_id": sample_id,
                "entity_count": len(mentions),
                "entity_type": entity_type_labels,
                "entity_mention": mention_labels,
                "evidence_context": evidence_text["context"],
                "evidence_names": evidence_text["names"],
                "evidence_bias_list": evidence_text["bias_list"],
            }
        )
    if not rows:
        raise CarrierInformationSpecError(
            "every one of the 44 discovery calls was excluded from the entity inventory; "
            "run scripts/build_entity_inventory.py for the discovery split first"
        )
    if excluded:
        print(
            f"information_audit: {len(excluded)} of {len(ids)} discovery calls excluded from "
            f"Earnings21+ConEC construction rows: {excluded}",
            file=sys.stderr,
        )
    return tuple(rows)


def earnings21_conec_spec(
    lock: Mapping[str, object], root: Path, repo_root: Path
) -> CarrierInformationSpec:
    """Earnings21 + ConEC's information spec: knowledge is the 44-call
    discovery split's OWN ConEC context/names/bias-list documents (no
    separate construction corpus), and evaluation IS the same 44 calls --
    Q3's "roster deviation from natural" is therefore degenerate (a census,
    not a sample) and Q6's decontamination question is answered by Q5's own
    own-call-vs-random-other-call membership contrast instead of a
    construction-vs-roster identity check (this spec's own
    ``retrieval_mode="self_supplied_membership"`` routes the runner there).
    """

    def _construction_loader() -> Sequence[Mapping[str, object]]:
        return _earnings_construction_rows(lock, root, repo_root)

    def _stratum_of(row: Mapping[str, object]) -> str:
        return str(row["item_id"])

    def _labels_of(row: Mapping[str, object]) -> Mapping[str, tuple[str, ...]]:
        return {
            "entity_type": tuple(row["entity_type"]),
            "entity_mention": tuple(row["entity_mention"]),
        }

    def _key_text_of(row: Mapping[str, object]) -> str:
        return " ".join(
            str(row[f"evidence_{kind}"]) for kind in _CONEC_TEXT_KINDS if row[f"evidence_{kind}"]
        )

    def _group_of(row: Mapping[str, object]) -> str:
        return str(row["item_id"])

    def _roster_identity() -> frozenset[str]:
        from ..data.splits import discovery_split

        split = discovery_split(lock, root)
        return frozenset(sample_id.split("/", 1)[1] for sample_id in split.ids)

    # Strata are call ids (module docstring: "strata = call id"), and the
    # roster IS the full 44-call population, so the per-stratum allocation
    # is trivially one call each; a single placeholder stratum count is used
    # instead of enumerating all 44 ids here (which would mean duplicating
    # the discovery_split media listing at spec-build time -- module
    # docstring: builders stay lazy about GOVERNED-DATASET reads).
    roster = EvaluationRoster(
        name="discovery-44",
        split_role="discovery",
        intended_n=44,
        stratum_counts={"discovery-44": 44},
        selection_rule_note=(
            "Census, not a sample: every earnings21-original discovery-split call is both the "
            "knowledge source and the evaluation roster (module docstring); strata are call ids, "
            "so the natural distribution is uniform by construction"
        ),
        identity_loader=_roster_identity,
    )

    return CarrierInformationSpec(
        carrier_lock_key="earnings21-original",
        task_kind="entity-recall-conec",
        strata_key="call_id",
        label_fields=("entity_type", "entity_mention"),
        field_legality=_EARNINGS_FIELD_LEGALITY,
        knowledge_source="per-call ConEC context/participant-names/bias-list documents (self-supplied, no shared corpus)",
        construction_loader=_construction_loader,
        evaluation_rosters=(roster,),
        stratum_of=_stratum_of,
        labels_of=_labels_of,
        key_text_of=_key_text_of,
        group_of=_group_of,
        retrieval_mode="self_supplied_membership",
        corpus_structure_legality=_EARNINGS_CORPUS_STRUCTURE_LEGALITY,
        obs_org_supply_use=_EARNINGS_OBS_ORG_SUPPLY_USE,
        external_supplementation=_EARNINGS_EXTERNAL_SUPPLEMENTATION,
    )


__all__ = [
    "LEGALITY_CLASSES",
    "RETRIEVAL_MODES",
    "MENTION_FIELD_SEPARATOR",
    "CarrierInformationSpecError",
    "EvaluationRoster",
    "CarrierInformationSpec",
    "audio2tool_spec",
    "slurp_spec",
    "earnings21_conec_spec",
]
