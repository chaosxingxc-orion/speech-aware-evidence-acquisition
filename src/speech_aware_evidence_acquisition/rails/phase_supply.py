"""E6 config seam: a phase program's per-phase TRACED knowledge supply,
from config alone.

``rails.phase_material`` closed the "what does this phase SAY" seam; this
module closes the "what does this phase SEE" one. A baseline fragment
declares

.. code-block:: json

    "phase_supply": {
      "evidence": {
        "provider": "kb-facet-v1",
        "rank_policy": "saea-rank-wcos-prior-agree-v1",
        "fuse_policy": "saea-fuse-supplyfilter-v1",
        "k": 5,
        "tau": 0.65,
        "dimensions": ["content"],
        "query_source": {
          "kind": "sealed-vectors",
          "relpath": "vectors/<cell>/query-vectors.jsonl",
          "sha256": "<64 hex>",
          "tool_contact_ledger_row": "<exposure-ledger row id>",
          "embedded_signal": "<what was embedded, in English>"
        }
      }
    }

and :func:`load_phase_supply_specs` turns it into one
:class:`PhaseSupplySpec` per declared phase, fail-closed against the
program's own ``PhaseSpec`` list. ``core.flight.FlightRuntime`` resolves
those specs into the ``supply_for_phase`` callable
``rails.controllers.EvidenceAgentController`` consults, with NO launcher
and no new class outside the bases.

Identity is the same discipline as everything else in this study: the
config hash pins the provider/rank/fuse ids and the knobs, and the query
source pins the vector file by sha256. Every id resolves in a
``core.base`` registry (``KNOWLEDGE_PROVIDERS``, ``KNOWLEDGE_RANKERS``,
``KNOWLEDGE_FUSERS``), which is what
``scripts/checks/engineering_base_check.py`` reads.

Where the query vectors come from, and why only one kind ships
---------------------------------------------------------------

The DEV-1000 BLEND lock (``docs/readiness/
2026-08-24-dev1000-baseline-lock-preregistration.md``, launcher
``docs/checks/speech-aware-evidence-acquisition/
2026-08-25-dev1000-baseline-lock/launcher/launch_dev1000_baseline_lock.py``)
did NOT embed the query. It embedded, IN FLIGHT and one tool contact per
row, **the trajectory's own direct-decode response text**
(``RuntimeEmbeddedBlendController.advance`` -> ``LazyQueryVector.fill``),
through a CPU llama.cpp ``--embedding --pooling last`` sidecar running
``models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf``
(sha256 ``06507c7b...e439``, 1,024 dimensions), metered against a per-attempt
tool ceiling. The facet (KEY) vectors were the opposite: a pre-flight,
receipt-pinned matrix (``docs/receipts/knowledge/
slurp-kb-size-full-embeddings.json`` plus its ``vectors-facets.npz``); the
value vectors were sealed and never loaded.

Only :data:`SEALED_VECTORS_KIND` ships here, for both sides. A pre-flight
file can be hashed, pinned in the config, and re-verified at preflight,
which is what makes a supplied cell reproducible; an in-flight embedding
sidecar is a second serving geometry, a per-row tool-contact ledger row and
a plan clause, and this module refuses that kind by name rather than
half-implementing it (see :func:`_load_query_source`). A cell that wants the
lock's own in-flight signal embeds a SEALED prior run's responses before the
flight, under its own tool-contact ledger row, and pins the result here --
the same signal, paid for once, outside the flight.

The vector file is one JSON object per line::

    {"id": "<sample id or facet id>", "vectors": {"content": [0.1, ...]}}

read from ``SPEECHRL_DATA_DIR``; no vectors are ever committed to Git.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import KNOWLEDGE_FUSERS, KNOWLEDGE_PROVIDERS, KNOWLEDGE_RANKERS, CoreError
from . import knowledge_provider as _knowledge_provider  # noqa: F401 -- side-effect
# import: registers "kb-facet-v1"/"dense-centroid-v1"/"conec-context-v1" into the
# shared core.base.KNOWLEDGE_PROVIDERS registry (that module's own register()
# calls). PhaseSupplySpec.validate resolves a fragment's `provider` against that
# registry, so it has to be populated before the first spec is loaded -- the same
# discipline rails.knowledge_provider itself uses for core.evidence's
# EVIDENCE_SOURCES.
from .controllers import PhaseProgram, PhaseSupply
from .errors import RailsError
from .knowledge import KnowledgeSnapshot, QueryState
from .kb_policy import (
    FuseKnobs,
    RankWeights,
    _argmax_labels,
    _blend_scores,
    _fused_label_scores,
    _label_identities,
    default_label_normalizer,
)

#: The one query/facet vector source kind this module implements: a
#: receipt-pinned JSONL file under ``SPEECHRL_DATA_DIR``, produced BEFORE
#: the flight under its own tool-contact ledger row (module docstring).
SEALED_VECTORS_KIND = "sealed-vectors"

#: Named and REFUSED (module docstring): an in-flight embedding-server
#: contact. Declaring it keeps the refusal specific instead of generic.
EMBEDDING_SERVER_KIND = "embedding-server"

VECTOR_SOURCE_KINDS = frozenset({SEALED_VECTORS_KIND, EMBEDDING_SERVER_KIND})

_SPEC_KEYS = frozenset(
    {
        "provider",
        "rank_policy",
        "fuse_policy",
        "k",
        "tau",
        "dimensions",
        "query_source",
        "facet_source",
        "rank_weights",
        "fuse_coverage",
        "alpha",
        "expose_facets",
    }
)
_SOURCE_KEYS = frozenset(
    {"kind", "relpath", "sha256", "tool_contact_ledger_row", "embedded_signal"}
)
_RANK_WEIGHT_KEYS = frozenset({"w_cos", "w_prior", "w_agree"})
_FUSE_COVERAGE_KEYS = frozenset({"m", "c", "top_l"})

_SHA256_CHARS = frozenset("0123456789abcdef")


class PhaseSupplyError(RailsError):
    """A ``phase_supply`` config fragment, or the binding built from it, is
    invalid."""


def _require_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or not set(value) <= _SHA256_CHARS
    ):
        raise PhaseSupplyError(f"{field} must be a 64-hex SHA-256")
    return value


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PhaseSupplyError(f"{field} must be a non-empty string")
    return value


def _require_relpath(value: object, *, field: str) -> str:
    text = _require_text(value, field=field)
    if text.startswith("/") or ".." in text.split("/") or "\\" in text:
        raise PhaseSupplyError(
            f"{field} must be a plain relative path under SPEECHRL_DATA_DIR "
            "(no absolute paths, no '..', no backslashes)"
        )
    return text


def _require_positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PhaseSupplyError(f"{field} must be a positive integer")
    return value


def _require_unit_float(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PhaseSupplyError(f"{field} must be a number within [0, 1]")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise PhaseSupplyError(f"{field} must be a number within [0, 1]")
    return number


def _validated_source(
    source: object, *, field: str, required: bool
) -> Mapping[str, object] | None:
    if source is None:
        if required:
            raise PhaseSupplyError(f"{field} is required")
        return None
    if not isinstance(source, Mapping):
        raise PhaseSupplyError(f"{field} must be an object")
    extra = sorted(set(source) - _SOURCE_KEYS)
    if extra:
        raise PhaseSupplyError(
            f"{field} carries unknown key(s) {extra}; known keys are "
            f"{sorted(_SOURCE_KEYS)}"
        )
    kind = source.get("kind")
    if kind not in VECTOR_SOURCE_KINDS:
        raise PhaseSupplyError(
            f"{field}.kind must be one of {sorted(VECTOR_SOURCE_KINDS)}, got {kind!r}"
        )
    if kind == EMBEDDING_SERVER_KIND:
        # Structurally legal to DECLARE so the refusal below can name it, but
        # never resolvable here: an in-flight embedding contact needs its own
        # serving geometry, its own ExecutionPlan clause and a per-row
        # tool-contact ledger row, none of which this seam owns.
        return dict(source)
    _require_relpath(source.get("relpath"), field=f"{field}.relpath")
    _require_sha256(source.get("sha256"), field=f"{field}.sha256")
    _require_text(
        source.get("tool_contact_ledger_row"),
        field=f"{field}.tool_contact_ledger_row",
    )
    _require_text(source.get("embedded_signal"), field=f"{field}.embedded_signal")
    return dict(source)


@dataclass(frozen=True)
class PhaseSupplySpec:
    """One phase's config-declared supply, before any file is read."""

    phase: str
    provider: str
    rank_policy: str
    fuse_policy: str
    k: int
    tau: float
    dimensions: tuple[str, ...]
    query_source: Mapping[str, object]
    facet_source: Mapping[str, object] | None = None
    rank_weights: Mapping[str, object] | None = None
    fuse_coverage: Mapping[str, object] | None = None
    alpha: float | None = None
    expose_facets: bool = False

    def validate(self) -> "PhaseSupplySpec":
        _require_text(self.phase, field="PhaseSupplySpec.phase")
        for name, registry, label in (
            ("provider", KNOWLEDGE_PROVIDERS, "KNOWLEDGE_PROVIDERS"),
            ("rank_policy", KNOWLEDGE_RANKERS, "KNOWLEDGE_RANKERS"),
            ("fuse_policy", KNOWLEDGE_FUSERS, "KNOWLEDGE_FUSERS"),
        ):
            value = _require_text(
                getattr(self, name), field=f"phase_supply[{self.phase!r}].{name}"
            )
            try:
                registry.resolve(value)
            except CoreError as error:
                raise PhaseSupplyError(
                    f"phase_supply[{self.phase!r}].{name}={value!r} does not resolve "
                    f"in core.base.{label}: {error}"
                ) from None
        _require_positive_int(self.k, field=f"phase_supply[{self.phase!r}].k")
        _require_unit_float(self.tau, field=f"phase_supply[{self.phase!r}].tau")
        if (
            not isinstance(self.dimensions, tuple)
            or not self.dimensions
            or any(not isinstance(name, str) or not name for name in self.dimensions)
        ):
            raise PhaseSupplyError(
                f"phase_supply[{self.phase!r}].dimensions must be a non-empty list of "
                "dimension names"
            )
        if len(set(self.dimensions)) != len(self.dimensions):
            raise PhaseSupplyError(
                f"phase_supply[{self.phase!r}].dimensions has duplicates"
            )
        _validated_source(
            self.query_source,
            field=f"phase_supply[{self.phase!r}].query_source",
            required=True,
        )
        _validated_source(
            self.facet_source,
            field=f"phase_supply[{self.phase!r}].facet_source",
            required=False,
        )
        if self.rank_weights is not None:
            if (
                not isinstance(self.rank_weights, Mapping)
                or set(self.rank_weights) != _RANK_WEIGHT_KEYS
            ):
                raise PhaseSupplyError(
                    f"phase_supply[{self.phase!r}].rank_weights must carry exactly "
                    f"{sorted(_RANK_WEIGHT_KEYS)}"
                )
        if self.fuse_coverage is not None:
            if (
                not isinstance(self.fuse_coverage, Mapping)
                or set(self.fuse_coverage) != _FUSE_COVERAGE_KEYS
            ):
                raise PhaseSupplyError(
                    f"phase_supply[{self.phase!r}].fuse_coverage must carry exactly "
                    f"{sorted(_FUSE_COVERAGE_KEYS)}"
                )
            for key in sorted(_FUSE_COVERAGE_KEYS):
                _require_positive_int(
                    self.fuse_coverage[key],
                    field=f"phase_supply[{self.phase!r}].fuse_coverage.{key}",
                )
        if self.alpha is not None:
            _require_unit_float(self.alpha, field=f"phase_supply[{self.phase!r}].alpha")
        if not isinstance(self.expose_facets, bool):
            raise PhaseSupplyError(
                f"phase_supply[{self.phase!r}].expose_facets must be a bool"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "phase": self.phase,
            "provider": self.provider,
            "rank_policy": self.rank_policy,
            "fuse_policy": self.fuse_policy,
            "k": self.k,
            "tau": self.tau,
            "dimensions": list(self.dimensions),
            "query_source": dict(self.query_source),
            "facet_source": (
                dict(self.facet_source) if self.facet_source is not None else None
            ),
            "rank_weights": (
                dict(self.rank_weights) if self.rank_weights is not None else None
            ),
            "fuse_coverage": (
                dict(self.fuse_coverage) if self.fuse_coverage is not None else None
            ),
            "alpha": self.alpha,
            "expose_facets": self.expose_facets,
        }

    def rank_weights_or_none(self) -> RankWeights | None:
        if self.rank_weights is None:
            return None
        return RankWeights(
            w_cos=float(self.rank_weights["w_cos"]),
            w_prior=float(self.rank_weights["w_prior"]),
            w_agree=float(self.rank_weights["w_agree"]),
        ).validate()

    def fuse_knobs(self) -> FuseKnobs:
        coverage = self.fuse_coverage or {}
        return FuseKnobs(
            tau=float(self.tau),
            m=int(coverage.get("m", self.k)),
            c=int(coverage.get("c", 2)),
            top_l=int(coverage.get("top_l", 3)),
        ).validate()


def load_phase_supply_specs(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseSupplySpec]:
    """Parse the baseline fragment's ``phase_supply`` object against
    ``program``.

    Absent or empty: no phase is supplied and an empty mapping is returned
    (every pre-E6 fragment). Present: refuses a non-object; a phase the
    program does not declare; an unknown key in a phase entry; and a phase
    whose ``PhaseSpec.knowledge`` is not ``"supplied"`` -- a phase that sees
    knowledge has to say so in the program, where the config hash and the
    controller both read it.
    """

    program.validate()
    declared = values.get("phase_supply")
    if declared is None or declared == {}:
        return {}
    if not isinstance(declared, Mapping):
        raise PhaseSupplyError(
            "'phase_supply' must be an object keyed by phase name "
            f"({list(program.phase_names())})"
        )
    known = set(program.phase_names())
    unknown = sorted(set(declared) - known)
    if unknown:
        raise PhaseSupplyError(
            f"phase_supply names phase(s) {unknown} that program "
            f"{program.program_id!r} does not declare; its phases are {sorted(known)}"
        )
    specs: dict[str, PhaseSupplySpec] = {}
    for phase in program.phases:
        if phase.name not in declared:
            continue
        entry = declared[phase.name]
        if not isinstance(entry, Mapping):
            raise PhaseSupplyError(f"phase_supply[{phase.name!r}] must be an object")
        extra = sorted(set(entry) - _SPEC_KEYS)
        if extra:
            raise PhaseSupplyError(
                f"phase_supply[{phase.name!r}] carries unknown key(s) {extra}; known "
                f"keys are {sorted(_SPEC_KEYS)}"
            )
        if phase.knowledge != "supplied":
            raise PhaseSupplyError(
                f"phase_supply[{phase.name!r}] supplies a phase whose program "
                f"{program.program_id!r} declares knowledge={phase.knowledge!r}; a "
                "supplied phase must declare knowledge='supplied' in "
                "configs/policy/<program>.json"
            )
        dimensions = entry.get("dimensions")
        specs[phase.name] = PhaseSupplySpec(
            phase=phase.name,
            provider=entry.get("provider"),
            rank_policy=entry.get("rank_policy"),
            fuse_policy=entry.get("fuse_policy"),
            k=entry.get("k"),
            tau=entry.get("tau"),
            dimensions=(
                tuple(dimensions) if isinstance(dimensions, (list, tuple)) else ()
            ),
            query_source=entry.get("query_source"),
            facet_source=entry.get("facet_source"),
            rank_weights=entry.get("rank_weights"),
            fuse_coverage=entry.get("fuse_coverage"),
            alpha=entry.get("alpha"),
            expose_facets=bool(entry.get("expose_facets", False)),
        ).validate()
    return specs


def load_sealed_vectors(
    path: Path, *, expected_sha256: str, dimensions: Sequence[str]
) -> Mapping[str, Mapping[str, tuple[float, ...]]]:
    """``{id: {dimension: vector}}`` from a receipt-pinned JSONL file.

    Fail-closed on: a missing file; a sha256 that is not the configured one;
    a malformed line; a duplicate id; a dimension the spec does not declare;
    a non-numeric or empty vector; or two vectors of different length within
    one dimension (a mixed-model file would silently produce meaningless
    cosines).
    """

    resolved = Path(path)
    if not resolved.is_file():
        raise PhaseSupplyError(f"sealed vector file {resolved} does not exist")
    raw = resolved.read_bytes()
    measured = hashlib.sha256(raw).hexdigest()
    if measured != _require_sha256(expected_sha256, field="expected_sha256"):
        raise PhaseSupplyError(
            f"sealed vector file {resolved} hashes to {measured}, not the configured "
            f"{expected_sha256}"
        )
    allowed = set(dimensions)
    widths: dict[str, int] = {}
    table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PhaseSupplyError(
                f"{resolved} line {number} is not valid JSON: {error}"
            ) from None
        if not isinstance(document, Mapping) or set(document) != {"id", "vectors"}:
            raise PhaseSupplyError(
                f"{resolved} line {number} must be an object with exactly 'id' and "
                "'vectors'"
            )
        entry_id = _require_text(document["id"], field=f"{resolved} line {number} id")
        if entry_id in table:
            raise PhaseSupplyError(f"{resolved} has a duplicate id {entry_id!r}")
        vectors = document["vectors"]
        if not isinstance(vectors, Mapping) or not vectors:
            raise PhaseSupplyError(
                f"{resolved} line {number} 'vectors' must be a non-empty object"
            )
        row: dict[str, tuple[float, ...]] = {}
        for dimension, vector in vectors.items():
            if dimension not in allowed:
                raise PhaseSupplyError(
                    f"{resolved} line {number} carries dimension {dimension!r}, which "
                    f"the fragment does not declare ({sorted(allowed)})"
                )
            if not isinstance(vector, list) or not vector:
                raise PhaseSupplyError(
                    f"{resolved} line {number} dimension {dimension!r} must be a "
                    "non-empty list of numbers"
                )
            if any(
                isinstance(value, bool) or not isinstance(value, (int, float))
                for value in vector
            ):
                raise PhaseSupplyError(
                    f"{resolved} line {number} dimension {dimension!r} carries a "
                    "non-numeric component"
                )
            width = widths.setdefault(dimension, len(vector))
            if len(vector) != width:
                raise PhaseSupplyError(
                    f"{resolved} dimension {dimension!r} mixes widths {width} and "
                    f"{len(vector)}; one file is one embedding model"
                )
            row[dimension] = tuple(float(value) for value in vector)
        table[entry_id] = row
    if not table:
        raise PhaseSupplyError(f"sealed vector file {resolved} carries no rows")
    return table


def _load_query_source(
    spec: PhaseSupplySpec,
    source: Mapping[str, object],
    data_root: Path,
    *,
    label: str,
) -> Mapping[str, Mapping[str, tuple[float, ...]]]:
    kind = source["kind"]
    if kind == EMBEDDING_SERVER_KIND:
        raise PhaseSupplyError(
            f"phase_supply[{spec.phase!r}].{label}.kind={EMBEDDING_SERVER_KIND!r} is "
            "declared but not implemented: an in-flight embedding contact needs its "
            "own serving geometry, its own ExecutionPlan tool-contact clause and one "
            "exposure-ledger row per contact, none of which this config seam owns. "
            f"Embed the signal BEFORE the flight and pin it as {SEALED_VECTORS_KIND!r} "
            "(module docstring)"
        )
    return load_sealed_vectors(
        data_root / str(source["relpath"]),
        expected_sha256=str(source["sha256"]),
        dimensions=spec.dimensions,
    )


ProviderForPhase = Callable[[str], object]


def build_supply_for_phase(
    specs: Mapping[str, PhaseSupplySpec],
    *,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    data_root: Path,
    provider_for_phase: ProviderForPhase | None = None,
    seed_phases: Sequence[str] = (),
):
    """Build the ``rails.controllers.SupplyForPhase`` callable, or ``None``
    when no phase declares supply.

    ``(phase_name, context) -> PhaseSupply | None``. For each supplied phase
    the callable recalls/ranks/fuses the FROZEN ``snapshot`` against that
    sample's sealed query vectors and returns the decision; the values it
    names then travel the successor ``QueryState`` as typed content blocks.
    Nothing here writes prompt text.

    ``provider_for_phase`` is the injection seam for a provider this module
    cannot construct from a ``KnowledgeSnapshot`` alone (the Audio2Tool
    ``dense-centroid-v1`` index, or a test double). Without it, only
    ``kb-facet-v1`` -- whose whole state IS the frozen snapshot -- is
    constructible, and any other registered provider id is refused by name
    rather than silently degraded.

    A sample with no row in the sealed vector file, or whose recall admits
    nothing, yields ``None``: that phase simply runs unsupplied, which is
    lawful (the successor state gains no values) and is exactly what
    ``KbAlphaBlendController`` does when recall finds nothing.
    """

    if not specs:
        return None

    query_tables: dict[str, Mapping[str, Mapping[str, tuple[float, ...]]]] = {}
    facet_tables: dict[str, Mapping[str, Mapping[str, tuple[float, ...]]]] = {}
    provider_factories: dict[str, Callable[[], object]] = {}
    for phase, spec in sorted(specs.items()):
        query_tables[phase] = _load_query_source(
            spec, spec.query_source, data_root, label="query_source"
        )
        facet_tables[phase] = (
            {}
            if spec.facet_source is None
            else _load_query_source(
                spec, spec.facet_source, data_root, label="facet_source"
            )
        )
        provider_factories[phase] = _provider_factory(
            spec,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            facet_vectors=facet_tables[phase],
            provider_for_phase=provider_for_phase,
        )

    seeded = set(seed_phases)
    # The alpha-blend head, when a spec declares ``alpha`` -- computed from
    # rails.kb_policy's OWN functions, not reimplemented, so the decision is
    # the locked ``saea-kb-alpha-blend-v1`` decision expressed on the base.
    label_targets = _label_identities(snapshot)
    values_by_id = {value.value_id: value for value in snapshot.values}

    def supply_for_phase(phase_name: str, context: object) -> PhaseSupply | None:
        spec = specs.get(phase_name)
        if spec is None or phase_name in seeded:
            # A seeded phase's selection already rode the initial QueryState
            # (build_bootstrap_selection); asking again here would claim
            # values that are already visible and the controller would
            # refuse -- correctly, but for the wrong reason.
            return None
        query_state = getattr(context, "query_state", None)
        sample_id = getattr(context, "sample_id", None)
        if not isinstance(query_state, QueryState) or not isinstance(sample_id, str):
            raise PhaseSupplyError(
                "supply_for_phase needs an AgentRuntimeContext carrying a sample_id "
                "and a QueryState"
            )
        query_vectors = query_tables[phase_name].get(sample_id)
        if not query_vectors:
            return None
        # A FRESH provider per decision: KbFacetProvider carries the
        # last-candidates() rank result on the instance, and
        # rails.runner runs trajectories concurrently, so one shared
        # instance would let two samples interleave their decisions.
        provider = provider_factories[phase_name]()
        ranking = provider.candidates(
            {"query_state": query_state, "query_vectors": dict(query_vectors)},
            k=spec.k,
        )
        fusion_decision = provider.fuse(
            [ranking], k=spec.k, policy_id=spec.fuse_policy
        )
        rank_result = provider.last_rank_result()
        if rank_result is None:
            raise PhaseSupplyError(
                f"provider {spec.provider!r} produced no RankResult for phase "
                f"{phase_name!r}; an acquire transition cannot be traced without one"
            )
        if not fusion_decision.selected_value_ids and not (
            spec.expose_facets and fusion_decision.supporting_facet_ids
        ):
            return None
        return PhaseSupply(
            rank_result=rank_result,
            fusion_decision=fusion_decision,
            expose_facets=spec.expose_facets,
            retain_prior=_retains_prior(spec, context, rank_result, fusion_decision),
            action_target_ref=(
                f"{spec.provider}:{spec.rank_policy}:{spec.fuse_policy}:k={spec.k}"
            ),
        ).validate()

    def _retains_prior(spec, context, rank_result, fusion_decision) -> bool:
        """``KbAlphaBlendController``'s retain-primary shortcut, expressed on
        the base (E6).

        A spec declaring ``alpha`` re-ranks the fused evidence's own label
        distribution against the completed phase's answer as
        ``alpha * kb + (1 - alpha) * [label == prior answer]``; when the
        prior answer's label is the UNIQUE winner, the retrieval decision
        itself says no further contact is needed and the trajectory stops on
        that answer. A tie that merely includes it is dispatched, so the
        supplied contact can break it -- exactly
        ``rails.kb_policy.KbAlphaBlendController._advance_after_direct``,
        whose own ``_fused_label_scores``/``_blend_scores``/
        ``_argmax_labels`` this calls rather than reimplementing.

        Absent ``alpha``: never retains, and the program runs every phase.
        The registered default normalizer reads a SLURP-shaped compact JSON
        answer (``rails.kb_policy.default_label_normalizer``), so a carrier
        whose answers are not shaped that way must not declare ``alpha``.
        """

        if spec.alpha is None or not label_targets:
            return False
        states = getattr(context, "agent_states", ())
        if not states:
            return False
        prior_label = default_label_normalizer(states[-1].content, label_targets)
        if prior_label is None:
            return False
        blended = _blend_scores(
            label_targets,
            _fused_label_scores(
                label_targets,
                values_by_id,
                fusion_decision.selected_value_ids,
                rank_result,
            ),
            prior_label,
            float(spec.alpha),
        )
        return _argmax_labels(blended) == (prior_label,)

    # ``snapshot_sha256`` is the caller's already-computed hash of the same
    # frozen snapshot; recorded here so a binding built against one snapshot
    # can never be handed a different one later.
    supply_for_phase.snapshot_sha256 = snapshot_sha256  # type: ignore[attr-defined]
    supply_for_phase.provider_factories = provider_factories  # type: ignore[attr-defined]
    supply_for_phase.query_tables = query_tables  # type: ignore[attr-defined]
    supply_for_phase.query_vector_rows = {  # type: ignore[attr-defined]
        phase: len(table) for phase, table in query_tables.items()
    }
    supply_for_phase.facet_vector_rows = {  # type: ignore[attr-defined]
        phase: len(table) for phase, table in facet_tables.items()
    }
    return supply_for_phase


def _provider_factory(
    spec: PhaseSupplySpec,
    *,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    facet_vectors: Mapping[str, Mapping[str, tuple[float, ...]]],
    provider_for_phase: ProviderForPhase | None,
) -> Callable[[], object]:
    """A zero-argument factory producing a provider ready for ONE decision.

    ``kb-facet-v1`` is rebuilt per decision because its recall/rank state
    lives on the instance and trajectories run concurrently. An INJECTED
    provider is returned as the same object every time -- the caller that
    built it owns its concurrency, and says so at
    ``core.flight.FlightRuntime.bind_phase_supply_providers``.
    """

    if provider_for_phase is not None:
        provider = provider_for_phase(spec.phase)
        if provider is not None:
            return lambda: provider
    if spec.provider != "kb-facet-v1":
        raise PhaseSupplyError(
            f"phase_supply[{spec.phase!r}].provider={spec.provider!r} resolves in "
            "core.base.KNOWLEDGE_PROVIDERS but this seam can only CONSTRUCT "
            "'kb-facet-v1' (whose whole state is the frozen KnowledgeSnapshot this "
            "flight already loaded and hash-verified). Supply the built provider "
            "through FlightRuntime.bind_phase_supply_providers"
        )
    rank_weights = spec.rank_weights_or_none()
    fuse_knobs = spec.fuse_knobs()

    def factory() -> object:
        provider = _knowledge_provider.KbFacetProvider(
            build_spec=None,
            rank_policy_id=spec.rank_policy,
            rank_weights=rank_weights,
            fuse_knobs=fuse_knobs,
            top_k_per_dimension=spec.k,
            facet_vectors=lambda facet_id: facet_vectors.get(facet_id, {}),
        )
        provider.adopt(
            snapshot,
            policy_id=f"frozen-snapshot:{spec.phase}",
            source_ids=(),
            snapshot_sha256=snapshot_sha256,
        )
        return provider

    return factory


#: The ``query_id`` prefix of the throwaway ``QueryState`` a PRE-FLIGHT
#: seed decision is ranked against (:func:`build_bootstrap_selection`). It
#: is never sent, never hashed into a transition, and never equals the
#: initial state the runner later builds (that one already carries the
#: seeded ids) -- the prefix says so out loud.
SEED_QUERY_ID_PREFIX = "phase-supply-seed"


def build_bootstrap_selection(
    spec: PhaseSupplySpec,
    *,
    provider: object,
    query_vectors_by_sample: Mapping[str, Mapping[str, tuple[float, ...]]],
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    split_identity_hash: str,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
    """``({sample: facet_ids}, {sample: value_ids})`` for a supplied FIRST
    phase, decided BEFORE the flight.

    A first phase has no preceding ``advance``, so no wave can carry an
    ``acquire`` transition for it (``rails.controllers``, "Traced supply").
    Its selection is therefore decided here -- a pure function of the pinned
    query vectors, the frozen snapshot and the pinned knobs, so it is
    reproducible from the config hash plus two sha256s -- and seeded into
    each sample's initial ``QueryState`` through ``rails.runner``'s
    ``bootstrap_value_ids`` mapping form. It still reaches the model ONLY as
    typed content blocks with ``evidence_id``/``source_uri``/
    ``knowledge_role``, and the SUPPLY trace record reports it per sample.

    What this route does NOT get, stated plainly: an ``acquire`` transition
    and therefore an ``assert_knowledge_use_binding`` call at contact time.
    The compensating evidence is that the decision is pre-flight and
    hash-pinned rather than runtime and unrecorded.
    """

    facets: dict[str, tuple[str, ...]] = {}
    values: dict[str, tuple[str, ...]] = {}
    for sample_id in sorted(speech_packet_bindings):
        query_vectors = query_vectors_by_sample.get(sample_id)
        if not query_vectors:
            continue
        descriptor = speech_packet_bindings[sample_id]
        seed_state = QueryState(
            query_id=f"{SEED_QUERY_ID_PREFIX}:{spec.phase}:{sample_id}",
            query_sample_id=sample_id,
            speech_packet_id=str(descriptor["packet_id"]),
            speech_packet_sha256=str(descriptor["sha256"]),
            use_split_identity_hash=split_identity_hash,
        ).validate()
        ranking = provider.candidates(
            {"query_state": seed_state, "query_vectors": dict(query_vectors)},
            k=spec.k,
        )
        fusion_decision = provider.fuse(
            [ranking], k=spec.k, policy_id=spec.fuse_policy
        )
        if fusion_decision.selected_value_ids:
            values[sample_id] = tuple(fusion_decision.selected_value_ids)
        if spec.expose_facets and fusion_decision.supporting_facet_ids:
            facets[sample_id] = tuple(fusion_decision.supporting_facet_ids)
    return facets, values


def phase_supply_receipt(
    specs: Mapping[str, PhaseSupplySpec],
    query_rows_by_phase: Mapping[str, int],
    facet_rows_by_phase: Mapping[str, int],
) -> dict[str, object]:
    """A hashable identity record for what this run's phase supply IS --
    the spec plus how many sealed vector rows each side carried. Never the
    vectors themselves, and never any snapshot content."""

    phases = [
        {
            "spec": specs[phase].as_json(),
            "query_vector_rows": int(query_rows_by_phase.get(phase, 0)),
            "facet_vector_rows": int(facet_rows_by_phase.get(phase, 0)),
        }
        for phase in sorted(specs)
    ]
    return {"schema": "saea-phase-supply-v1", "phases": phases}


__all__ = [
    "EMBEDDING_SERVER_KIND",
    "SEALED_VECTORS_KIND",
    "SEED_QUERY_ID_PREFIX",
    "VECTOR_SOURCE_KINDS",
    "PhaseSupplyError",
    "PhaseSupplySpec",
    "build_bootstrap_selection",
    "build_supply_for_phase",
    "load_phase_supply_specs",
    "load_sealed_vectors",
    "phase_supply_receipt",
]
