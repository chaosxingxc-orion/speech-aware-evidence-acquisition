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
          "embedded_signal": "speech+state: <what was embedded, in English>"
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

The query must carry speech (owner rule, 2026-09-06)
-----------------------------------------------------

A QUERY vector must contain the speech signal -- speech alone, or speech
plus an agent intermediate state (speech + the row's own draft answer, for
instance) -- and may never be text-only. The rule is enforced, not merely
written down: a ``query_source``'s ``embedded_signal`` must DECLARE its
modality as its first token, from :data:`QUERY_SIGNAL_MODALITIES`, followed
by ``:`` and the free English description. :func:`load_phase_supply_specs`
refuses anything else before a file is opened, and
:func:`assert_phase_supply_queries_carry_speech` applies the same rule to a
raw fragment inside ``core.flight.FlightRuntime``'s own preflight. The KEY
(facet) side is unconstrained: a key is knowledge text by construction.

No inference is attempted over the prose -- no regex can decide whether a
vector file carries speech. The fragment declares it, and the declaration
rides the config hash, which is part of the cell's identity.

The vector file is one JSON object per line::

    {"id": "<sample id or facet id>", "vectors": {"content": [0.1, ...]}}

read from ``SPEECHRL_DATA_DIR``; no vectors are ever committed to Git.
"""

from __future__ import annotations

import codecs
import hashlib
import io
import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Mapping, Sequence

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
    EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
    FuseKnobs,
    RankWeights,
    _argmax_labels,
    _blend_scores,
    _fused_label_scores,
    _label_identities,
    default_label_normalizer,
    multidim_recall,
    multidim_segment_recall,
)

#: The one query/facet vector source kind this module implements: a
#: receipt-pinned JSONL file under ``SPEECHRL_DATA_DIR``, produced BEFORE
#: the flight under its own tool-contact ledger row (module docstring).
SEALED_VECTORS_KIND = "sealed-vectors"

SEALED_SEGMENT_VECTORS_KIND = "sealed-segment-vectors"

#: Named and REFUSED (module docstring): an in-flight embedding-server
#: contact. Declaring it keeps the refusal specific instead of generic.
EMBEDDING_SERVER_KIND = "embedding-server"

#: A pre-computed, receipt-pinned per-row AGREEMENT table -- the same
#: bootstrap shape as :data:`SEALED_VECTORS_KIND`: a JSONL file under
#: ``SPEECHRL_DATA_DIR``, produced BEFORE the flight under its own
#: tool-contact ledger row, hash-verified by its reader. It is legal on
#: ``agreement_source`` only, never on a query or a facet source, because it
#: carries no vector: see :func:`load_sealed_agreement`.
SEALED_AGREEMENT_KIND = "sealed-agreement"

VECTOR_SOURCE_KINDS = frozenset(
    {SEALED_VECTORS_KIND, SEALED_SEGMENT_VECTORS_KIND, EMBEDDING_SERVER_KIND}
)

#: The kinds :func:`_validated_source` accepts at all. ``sealed-agreement``
#: is gated to the agreement slot inside that function.
SOURCE_KINDS = VECTOR_SOURCE_KINDS | {SEALED_AGREEMENT_KIND}

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
        "agreement_source",
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
_SOURCE_AUDIO_BINDING_KEYS = frozenset(
    {"packet_id", "packet_sha256", "source_audio_sha256"}
)

#: How far a row's agreement shares may drift from 1.0 before
#: :func:`load_sealed_agreement` refuses the file. A share set is a vote count
#: divided by its own total, so the only legal drift is IEEE-754 accumulation
#: over at most a few dozen terms.
_AGREEMENT_SUM_TOLERANCE = 1e-9

_SHA256_CHARS = frozenset("0123456789abcdef")

#: OWNER RULE, 2026-09-06 (binding): **the retrieval QUERY must contain the
#: speech signal.** It may be speech alone, or speech plus an agent
#: intermediate state (speech + the draft answer, say); it can never be
#: text-only. A text-only query vector makes the retrieval a text-retrieval
#: experiment wearing a speech carrier's clothes, and this study's object is
#: speech-aware evidence acquisition.
#:
#: The rule is machine-enforced rather than left to prose: a ``query_source``
#: DECLARES its modality as the first token of ``embedded_signal``, in the
#: fixed vocabulary below, followed by ``:`` and the free English description
#: the key already carried. So::
#:
#:     "embedded_signal": "speech+state: the 90 s speech packet of the row
#:                         fused with that row's own phase-1 draft answer, ..."
#:
#: The KEY (facet) side is deliberately UNCONSTRAINED: a key is knowledge
#: text and always has been (``KeyFacet.representation``); the rule is about
#: what the QUERY carries.
QUERY_SIGNAL_MODALITIES: tuple[str, ...] = ("speech", "speech+state")

#: The single character separating the declared modality from the prose.
QUERY_SIGNAL_SEPARATOR = ":"


class PhaseSupplyError(RailsError):
    """A ``phase_supply`` config fragment, or the binding built from it, is
    invalid."""


@dataclass(frozen=True)
class SealedSegmentQuery:
    """One hash-pinned speech query with vectors for contiguous audio spans."""

    audio_sha256: str
    segments: tuple[Mapping[str, tuple[float, ...]], ...]


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


def _validate_source_audio_bindings(
    bindings: Mapping[str, Mapping[str, object]] | None,
) -> Mapping[str, Mapping[str, str]] | None:
    """Validate the optional source-audio to derived-packet authority."""

    if bindings is None:
        return None
    if not isinstance(bindings, Mapping) or not bindings:
        raise PhaseSupplyError("source-audio bindings must be a non-empty mapping")
    validated: dict[str, Mapping[str, str]] = {}
    for sample_id, raw in bindings.items():
        _require_text(sample_id, field="source-audio binding sample id")
        if not isinstance(raw, Mapping) or set(raw) != _SOURCE_AUDIO_BINDING_KEYS:
            raise PhaseSupplyError(
                "source-audio binding entries must carry exactly packet_id, "
                "packet_sha256, and source_audio_sha256"
            )
        validated[sample_id] = {
            "packet_id": _require_text(
                raw["packet_id"], field=f"source-audio binding {sample_id} packet id"
            ),
            "packet_sha256": _require_sha256(
                raw["packet_sha256"],
                field=f"source-audio binding {sample_id} packet SHA",
            ),
            "source_audio_sha256": _require_sha256(
                raw["source_audio_sha256"],
                field=f"source-audio binding {sample_id} source audio SHA",
            ),
        }
    return validated


def _assert_segment_query_binding(
    *,
    sample_id: str,
    query_state: QueryState,
    query_record: SealedSegmentQuery,
    source_audio_bindings: Mapping[str, Mapping[str, str]] | None,
) -> None:
    if query_state.query_sample_id != sample_id:
        raise PhaseSupplyError(
            "segmented query context sample and QueryState sample differ"
        )
    if source_audio_bindings is None:
        if query_state.query_source != "speech_audio":
            raise PhaseSupplyError(
                "sealed-segment-vectors requires QueryState.query_source='speech_audio'"
            )
        if query_record.audio_sha256 != query_state.speech_packet_sha256:
            raise PhaseSupplyError(
                "sealed-segment-vectors row audio_sha256 does not match "
                "QueryState.speech_packet_sha256"
            )
        return

    binding = source_audio_bindings.get(sample_id)
    if binding is None:
        raise PhaseSupplyError(
            f"segmented query sample {sample_id!r} has no source-audio binding"
        )
    if query_state.speech_packet_id != binding["packet_id"]:
        raise PhaseSupplyError(
            "segmented query QueryState packet id differs from its source-audio binding"
        )
    if query_state.speech_packet_sha256 != binding["packet_sha256"]:
        raise PhaseSupplyError(
            "segmented query QueryState packet SHA differs from its source-audio binding"
        )
    if query_record.audio_sha256 != binding["source_audio_sha256"]:
        raise PhaseSupplyError(
            "segmented query row source audio SHA differs from its source-audio binding"
        )


def assert_segment_query_bindings(
    query_records: Mapping[str, SealedSegmentQuery],
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    source_audio_bindings: Mapping[str, Mapping[str, object]] | None,
) -> None:
    """Bind segmented source audio independently from derived packet bytes."""

    validated = _validate_source_audio_bindings(source_audio_bindings)
    if validated is None:
        raise PhaseSupplyError(
            "segmented packet execution requires explicit source-audio bindings"
        )
    if set(query_records) != set(speech_packet_bindings):
        raise PhaseSupplyError(
            "segmented query roster differs from speech packet bindings"
        )
    for sample_id, query_record in query_records.items():
        descriptor = speech_packet_bindings[sample_id]
        if (
            not isinstance(descriptor, Mapping)
            or set(descriptor) != {"packet_id", "sha256"}
        ):
            raise PhaseSupplyError(
                "speech packet binding must carry exactly packet_id and sha256"
            )
        binding = validated.get(sample_id)
        if binding is None:
            raise PhaseSupplyError(
                f"segmented query sample {sample_id!r} has no source-audio binding"
            )
        if descriptor["packet_id"] != binding["packet_id"]:
            raise PhaseSupplyError(
                "segmented query packet id differs from its source-audio binding"
            )
        if descriptor["sha256"] != binding["packet_sha256"]:
            raise PhaseSupplyError(
                "segmented query packet SHA differs from its source-audio binding"
            )
        if query_record.audio_sha256 != binding["source_audio_sha256"]:
            raise PhaseSupplyError(
                "segmented query source audio SHA differs from its source-audio binding"
            )


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


def assert_query_signal_declares_speech(embedded_signal: object, *, field: str) -> str:
    """Return the declared query modality, or refuse (owner rule 2026-09-06).

    ``embedded_signal`` of a QUERY source must begin with one of
    :data:`QUERY_SIGNAL_MODALITIES` followed by
    :data:`QUERY_SIGNAL_SEPARATOR` and a non-empty English description of
    what was actually embedded. Anything else -- including the honest
    text-only descriptions this seam accepted before the rule -- is refused
    before any file is opened and before any contact.

    This is deliberately a declaration, not an inference: no regex over
    prose can decide whether a vector carries speech, so the fragment says
    so in a fixed vocabulary and the claim rides the config hash, which is
    part of the cell's identity.
    """

    text = _require_text(embedded_signal, field=field)
    for modality in QUERY_SIGNAL_MODALITIES:
        prefix = f"{modality}{QUERY_SIGNAL_SEPARATOR}"
        if text.startswith(prefix):
            if not text[len(prefix) :].strip():
                raise PhaseSupplyError(
                    f"{field} declares modality {modality!r} but carries no "
                    "description after it"
                )
            return modality
    raise PhaseSupplyError(
        f"{field} must DECLARE the query signal's modality as its first token, one "
        f"of {list(QUERY_SIGNAL_MODALITIES)} followed by "
        f"{QUERY_SIGNAL_SEPARATOR!r} (owner rule 2026-09-06: the retrieval query "
        "must contain the speech signal; it may be speech plus an agent "
        "intermediate state, but never text-only). Got: "
        f"{text[:80]!r}"
    )


def query_signal_modality(source: Mapping[str, object], *, field: str) -> str:
    """The declared modality of a resolved ``query_source`` mapping."""

    return assert_query_signal_declares_speech(
        source.get("embedded_signal"), field=f"{field}.embedded_signal"
    )


def assert_phase_supply_queries_carry_speech(values: Mapping[str, object]) -> None:
    """Apply the owner rule to a RAW baseline fragment, before the phase
    program is even resolved.

    ``core.flight.FlightRuntime`` calls this from its own preflight so a
    text-only query source is refused at the earliest possible point rather
    than at vector-load time. Fragments that declare no ``phase_supply``, and
    ``embedding-server`` sources (already refused by name elsewhere), pass
    through untouched.
    """

    declared = values.get("phase_supply")
    if not isinstance(declared, Mapping):
        return
    for phase in sorted(declared):
        entry = declared[phase]
        if not isinstance(entry, Mapping):
            continue
        source = entry.get("query_source")
        if not isinstance(source, Mapping):
            continue
        if source.get("kind") not in (
            SEALED_VECTORS_KIND,
            SEALED_SEGMENT_VECTORS_KIND,
        ):
            continue
        assert_query_signal_declares_speech(
            source.get("embedded_signal"),
            field=f"phase_supply[{phase!r}].query_source.embedded_signal",
        )


def _validated_source(
    source: object,
    *,
    field: str,
    required: bool,
    is_query: bool = False,
    is_agreement: bool = False,
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
    if kind not in SOURCE_KINDS:
        raise PhaseSupplyError(
            f"{field}.kind must be one of {sorted(SOURCE_KINDS)}, got {kind!r}"
        )
    # ``sealed-agreement`` carries shares, not vectors, so it is legal in the
    # agreement slot ONLY -- and that slot takes nothing else, because every
    # other kind would have to be recalled against and this one is merged.
    if is_agreement and kind != SEALED_AGREEMENT_KIND:
        raise PhaseSupplyError(
            f"{field}.kind must be {SEALED_AGREEMENT_KIND!r}, got {kind!r}"
        )
    if kind == SEALED_AGREEMENT_KIND and not is_agreement:
        raise PhaseSupplyError(
            f"{field}.kind={SEALED_AGREEMENT_KIND!r} is agreement-only; a query or "
            "facet source must carry a vector kind"
        )
    if kind == EMBEDDING_SERVER_KIND:
        # Structurally legal to DECLARE so the refusal below can name it, but
        # never resolvable here: an in-flight embedding contact needs its own
        # serving geometry, its own ExecutionPlan clause and a per-row
        # tool-contact ledger row, none of which this seam owns.
        return dict(source)
    if kind == SEALED_SEGMENT_VECTORS_KIND and not is_query:
        raise PhaseSupplyError(
            f"{field}.kind={SEALED_SEGMENT_VECTORS_KIND!r} is query-only; "
            "facet_source must use sealed-vectors"
        )
    _require_relpath(source.get("relpath"), field=f"{field}.relpath")
    _require_sha256(source.get("sha256"), field=f"{field}.sha256")
    _require_text(
        source.get("tool_contact_ledger_row"),
        field=f"{field}.tool_contact_ledger_row",
    )
    _require_text(source.get("embedded_signal"), field=f"{field}.embedded_signal")
    if is_query:
        # Owner rule 2026-09-06: a QUERY vector must carry speech. The KEY
        # side is unconstrained -- a key is knowledge text by construction.
        assert_query_signal_declares_speech(
            source.get("embedded_signal"), field=f"{field}.embedded_signal"
        )
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
    #: A pre-computed per-row AGREEMENT table, pinned exactly the way
    #: ``facet_source`` pins the key vectors: ``kind``
    #: :data:`SEALED_AGREEMENT_KIND`, ``relpath``, ``sha256``,
    #: ``tool_contact_ledger_row``, ``embedded_signal``. When present, the
    #: provider merges this row's shares into the recall under
    #: ``rails.kb_policy.EXEMPLAR_INTENT_AGREEMENT_DIMENSION``, so the
    #: registered ranker's own ``w_agree`` reads it. The flown default declares
    #: nothing here and is byte-unchanged.
    agreement_source: Mapping[str, object] | None = None
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
            is_query=True,
        )
        _validated_source(
            self.facet_source,
            field=f"phase_supply[{self.phase!r}].facet_source",
            required=False,
        )
        _validated_source(
            self.agreement_source,
            field=f"phase_supply[{self.phase!r}].agreement_source",
            required=False,
            is_agreement=True,
        )
        if self.agreement_source is not None and self.rank_weights is None:
            # A supplied agreement signal that no weight reads is dead config,
            # and the flown default's w_agree is 0.0, so the weights must be
            # explicit for the declaration to mean anything.
            raise PhaseSupplyError(
                f"phase_supply[{self.phase!r}].agreement_source requires explicit "
                "rank_weights; the agreement signal is read only through w_agree"
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
        """The identity view every prepared artifact binds
        (``core.flight.FlightRuntime._phase_seed_inputs``, key ``supply_spec``).

        ``agreement_source`` is emitted ONLY when declared, unlike the other
        optional keys, which emit ``None``. That asymmetry is deliberate and is
        the narrower of the two honest options: a cell that declares no
        agreement signal keeps a byte-identical ``supply_spec``, so the only
        thing that moves its prepared-artifact identity is the ``implementation``
        hash every edit to this module moves anyway. Emitting ``None`` here
        would additionally perturb the identity of every cell in the repository
        for no information gain.
        """

        self.validate()
        document: dict[str, object] = {
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
        if self.agreement_source is not None:
            document["agreement_source"] = dict(self.agreement_source)
        return document

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
            agreement_source=entry.get("agreement_source"),
            rank_weights=entry.get("rank_weights"),
            fuse_coverage=entry.get("fuse_coverage"),
            alpha=entry.get("alpha"),
            expose_facets=bool(entry.get("expose_facets", False)),
        ).validate()
    return specs


#: The JSONL schema :func:`load_sealed_agreement` accepts, stamped on every
#: line by its producer so a file of another shape is refused by name.
SEALED_AGREEMENT_SCHEMA = "saea-phase-agreement-v1"

#: The exact key set one ``saea-phase-agreement-v1`` line carries.
_AGREEMENT_LINE_KEYS = frozenset(
    {"schema", "id", "dimension", "scores", "vote_total", "self_excluded"}
)


def load_sealed_agreement(
    path: Path,
    *,
    expected_sha256: str,
    dimension: str,
    facet_ids: Sequence[str] | None = None,
) -> Mapping[str, Mapping[str, float]]:
    """``{sample_id: {facet_id: share}}`` from a receipt-pinned JSONL file.

    The AGREEMENT half of the boundary channel's own pre-flight bootstrap:
    the key vectors are pinned by ``facet_source`` and read by
    :func:`load_sealed_vectors`; this table is pinned by ``agreement_source``
    and read here, under the same discipline -- the file exists, its bytes
    hash to the configured digest, every line is well-formed, and nothing is
    defaulted.

    Fail-closed on: a missing file; a sha256 that is not the configured one; a
    malformed or unexpectedly-keyed line; a line stamped with another schema or
    another dimension; a duplicate sample id; a share that is not a finite
    number in ``[0, 1]``; a vote total or self-exclusion count that is not a
    non-negative integer; a row whose shares do not sum to 1 (within
    :data:`_AGREEMENT_SUM_TOLERANCE`) while it claims a positive vote total;
    and -- when ``facet_ids`` is given -- a facet id absent from the target
    snapshot, which would be a share the ranker can never reach.
    """

    resolved = Path(path)
    if not resolved.is_file():
        raise PhaseSupplyError(f"sealed agreement file {resolved} does not exist")
    raw = resolved.read_bytes()
    measured = hashlib.sha256(raw).hexdigest()
    if measured != _require_sha256(expected_sha256, field="expected_sha256"):
        raise PhaseSupplyError(
            f"sealed agreement file {resolved} hashes to {measured}, not the configured "
            f"{expected_sha256}"
        )
    _require_text(dimension, field="load_sealed_agreement dimension")
    allowed_facets = None if facet_ids is None else set(facet_ids)
    table: dict[str, Mapping[str, float]] = {}
    for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PhaseSupplyError(
                f"{resolved} line {number} is not valid JSON: {error}"
            ) from None
        if not isinstance(document, Mapping) or set(document) != _AGREEMENT_LINE_KEYS:
            raise PhaseSupplyError(
                f"{resolved} line {number} must be an object with exactly "
                f"{sorted(_AGREEMENT_LINE_KEYS)}"
            )
        if document["schema"] != SEALED_AGREEMENT_SCHEMA:
            raise PhaseSupplyError(
                f"{resolved} line {number} declares schema {document['schema']!r}, not "
                f"{SEALED_AGREEMENT_SCHEMA!r}"
            )
        if document["dimension"] != dimension:
            raise PhaseSupplyError(
                f"{resolved} line {number} declares dimension "
                f"{document['dimension']!r}, not the configured {dimension!r}"
            )
        entry_id = _require_text(document["id"], field=f"{resolved} line {number} id")
        if entry_id in table:
            raise PhaseSupplyError(f"{resolved} has a duplicate id {entry_id!r}")
        for name in ("vote_total", "self_excluded"):
            count = document[name]
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise PhaseSupplyError(
                    f"{resolved} line {number} {name!r} must be a non-negative integer"
                )
        scores = document["scores"]
        if not isinstance(scores, Mapping):
            raise PhaseSupplyError(
                f"{resolved} line {number} 'scores' must be an object"
            )
        row: dict[str, float] = {}
        for facet_id, share in scores.items():
            if not isinstance(facet_id, str) or not facet_id:
                raise PhaseSupplyError(
                    f"{resolved} line {number} 'scores' keys must be facet ids"
                )
            if allowed_facets is not None and facet_id not in allowed_facets:
                raise PhaseSupplyError(
                    f"{resolved} line {number} scores a facet id the target snapshot "
                    "does not declare"
                )
            if (
                isinstance(share, bool)
                or not isinstance(share, (int, float))
                or not math.isfinite(float(share))
                or not 0.0 <= float(share) <= 1.0
            ):
                raise PhaseSupplyError(
                    f"{resolved} line {number} carries a share that is not a finite "
                    "number within [0, 1]"
                )
            row[facet_id] = float(share)
        total = sum(row.values())
        if document["vote_total"] > 0:
            if abs(total - 1.0) > _AGREEMENT_SUM_TOLERANCE:
                raise PhaseSupplyError(
                    f"{resolved} line {number} claims {document['vote_total']} votes but "
                    f"its shares sum to {total!r}, not 1.0"
                )
        elif row:
            raise PhaseSupplyError(
                f"{resolved} line {number} claims no votes yet carries shares"
            )
        table[entry_id] = row
    if not table:
        raise PhaseSupplyError(f"{resolved} carries no agreement rows")
    return table


def _sealed_vector_lines(
    resolved: Path, *, expected_sha256: str, label: str
) -> Iterator[str]:
    """Verify the whole source before parsing, then decode bounded records.

    Retain the full validated table at the callers, but never a whole-file
    bytes buffer or decoded line list. Match ``str.splitlines`` separators,
    including CRLF and Unicode boundaries across I/O chunks. Recheck the
    second pass before a caller can return a table from changed source bytes.
    """

    line_endings = (
        "\n", "\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"
    )
    with resolved.open("rb") as stream:
        digest = hashlib.sha256()
        decoder = codecs.getincrementaldecoder("utf-8")()
        decode_error: UnicodeDecodeError | None = None
        while chunk := stream.read(io.DEFAULT_BUFFER_SIZE):
            digest.update(chunk)
            if decode_error is None:
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError as error:
                    decode_error = error
        if decode_error is None:
            try:
                decoder.decode(b"", final=True)
            except UnicodeDecodeError as error:
                decode_error = error
        measured = digest.hexdigest()
        expected = _require_sha256(expected_sha256, field="expected_sha256")
        if measured != expected:
            raise PhaseSupplyError(
                f"{label} {resolved} hashes to {measured}, not the configured "
                f"{expected_sha256}"
            )
        # The original loader hashes before decoding the entire UTF-8 source.
        # Keep that refusal precedence, even for invalid UTF-8 late in a file.
        if decode_error is not None:
            raise decode_error

        stream.seek(0)
        digest = hashlib.sha256()
        decoder = codecs.getincrementaldecoder("utf-8")()
        pending = ""
        while True:
            chunk = stream.read(io.DEFAULT_BUFFER_SIZE)
            digest.update(chunk)
            pending += decoder.decode(chunk, final=not chunk)
            parts = pending.splitlines(keepends=True)
            pending = parts.pop() if parts else ""
            for line in parts:
                yield line[:-2] if line.endswith("\r\n") else line[:-1]
            if pending.endswith(line_endings) and (
                not pending.endswith("\r") or not chunk
            ):
                yield pending[:-2] if pending.endswith("\r\n") else pending[:-1]
                pending = ""
            if not chunk:
                if pending:
                    yield pending
                break
        measured = digest.hexdigest()
        if measured != expected:
            raise PhaseSupplyError(
                f"{label} {resolved} changed during decoding: hashes to {measured}, "
                f"not the configured {expected_sha256}"
            )


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
    allowed = set(dimensions)
    widths: dict[str, int] = {}
    table: dict[str, Mapping[str, tuple[float, ...]]] = {}
    for number, line in enumerate(
        _sealed_vector_lines(resolved, expected_sha256=expected_sha256, label="sealed vector file"),
        start=1,
    ):
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


def load_sealed_segment_vectors(
    path: Path, *, expected_sha256: str, dimensions: Sequence[str]
) -> Mapping[str, SealedSegmentQuery]:
    """Load query-only vectors for ordered, gap-free spans of one packet.

    Adjacent ranges and overlap are both lawful. Every subsequent range must
    extend the covered end, which refuses duplicate, reversed, and contained
    ranges while accepting the registered 120 s / 8 s-overlap protocol.
    """

    resolved = Path(path)
    if not resolved.is_file():
        raise PhaseSupplyError(f"sealed segment vector file {resolved} does not exist")
    allowed = set(dimensions)
    widths: dict[str, int] = {}
    table: dict[str, SealedSegmentQuery] = {}
    required_keys = {
        "id", "audio_sha256", "source_frames", "source_sample_rate_hz", "segments"
    }
    segment_keys = {"id", "start_frame", "end_frame", "vectors"}
    for number, line in enumerate(
        _sealed_vector_lines(resolved, expected_sha256=expected_sha256, label="sealed segment vector file"),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PhaseSupplyError(
                f"{resolved} line {number} is not valid JSON: {error}"
            ) from None
        if not isinstance(document, Mapping) or set(document) != required_keys:
            raise PhaseSupplyError(
                f"{resolved} line {number} must carry exactly {sorted(required_keys)}"
            )
        entry_id = _require_text(document["id"], field=f"{resolved} line {number} id")
        if entry_id in table:
            raise PhaseSupplyError(f"{resolved} has a duplicate id {entry_id!r}")
        audio_sha256 = _require_sha256(
            document["audio_sha256"], field=f"{resolved} line {number} audio_sha256"
        )
        source_frames = _require_positive_int(
            document["source_frames"], field=f"{resolved} line {number} source_frames"
        )
        _require_positive_int(
            document["source_sample_rate_hz"],
            field=f"{resolved} line {number} source_sample_rate_hz",
        )
        raw_segments = document["segments"]
        if not isinstance(raw_segments, list) or not raw_segments:
            raise PhaseSupplyError(f"{resolved} line {number} segments must be non-empty")
        covered_end = 0
        previous_start: int | None = None
        segment_ids: set[str] = set()
        segments: list[Mapping[str, tuple[float, ...]]] = []
        for segment_number, segment in enumerate(raw_segments, start=1):
            field = f"{resolved} line {number} segment {segment_number}"
            if not isinstance(segment, Mapping) or set(segment) != segment_keys:
                raise PhaseSupplyError(f"{field} must carry exactly {sorted(segment_keys)}")
            segment_id = _require_text(segment["id"], field=f"{field} id")
            if segment_id in segment_ids:
                raise PhaseSupplyError(f"{field} has duplicate segment id {segment_id!r}")
            segment_ids.add(segment_id)
            start = segment["start_frame"]
            end = segment["end_frame"]
            if (
                isinstance(start, bool) or not isinstance(start, int)
                or isinstance(end, bool) or not isinstance(end, int)
                or start < 0 or end > source_frames
                or (previous_start is None and start != 0)
                or (previous_start is not None and start <= previous_start)
                or start > covered_end or end <= covered_end
            ):
                raise PhaseSupplyError(
                    f"{field} does not provide ordered, gap-free extending frame coverage"
                )
            previous_start = start
            covered_end = end
            vectors = segment["vectors"]
            if not isinstance(vectors, Mapping) or set(vectors) != allowed:
                raise PhaseSupplyError(
                    f"{field} vectors must carry exactly declared dimensions {sorted(allowed)}"
                )
            parsed: dict[str, tuple[float, ...]] = {}
            for dimension in sorted(vectors):
                vector = vectors[dimension]
                if not isinstance(vector, list) or not vector:
                    raise PhaseSupplyError(
                        f"{field} dimension {dimension!r} must be a non-empty list"
                    )
                if any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(float(value))
                    for value in vector
                ):
                    raise PhaseSupplyError(
                        f"{field} dimension {dimension!r} must be finite numbers"
                    )
                parsed_vector = tuple(float(value) for value in vector)
                if not any(value != 0.0 for value in parsed_vector):
                    raise PhaseSupplyError(
                        f"{field} dimension {dimension!r} must be nonzero"
                    )
                width = widths.setdefault(dimension, len(parsed_vector))
                if len(parsed_vector) != width:
                    raise PhaseSupplyError(
                        f"{resolved} dimension {dimension!r} mixes widths {width} and "
                        f"{len(parsed_vector)}; one file is one embedding model"
                    )
                parsed[dimension] = parsed_vector
            segments.append(parsed)
        if covered_end != source_frames:
            raise PhaseSupplyError(
                f"{resolved} line {number} segments do not provide exact frame coverage "
                f"[0, {source_frames}]"
            )
        table[entry_id] = SealedSegmentQuery(audio_sha256=audio_sha256, segments=tuple(segments))
    if not table:
        raise PhaseSupplyError(f"sealed segment vector file {resolved} carries no rows")
    return table


def _load_query_source(
    spec: PhaseSupplySpec,
    source: Mapping[str, object],
    data_root: Path,
    *,
    label: str,
) -> Mapping[str, Mapping[str, tuple[float, ...]]] | Mapping[str, SealedSegmentQuery]:
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
    if kind == SEALED_SEGMENT_VECTORS_KIND:
        if label != "query_source":
            raise PhaseSupplyError("sealed-segment-vectors is query-only")
        return load_sealed_segment_vectors(
            data_root / str(source["relpath"]),
            expected_sha256=str(source["sha256"]),
            dimensions=spec.dimensions,
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
    prepared_recall_by_phase: Mapping[str, Mapping[str, Mapping[str, Mapping[str, float]]]] | None = None,
    source_audio_bindings: Mapping[str, Mapping[str, object]] | None = None,
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

    validated_source_bindings = _validate_source_audio_bindings(
        source_audio_bindings
    )
    query_tables: dict[
        str, Mapping[str, Mapping[str, tuple[float, ...]]] | Mapping[str, SealedSegmentQuery]
    ] = {}
    facet_tables: dict[str, Mapping[str, Mapping[str, tuple[float, ...]]]] = {}
    agreement_tables: dict[str, Mapping[str, Mapping[str, float]] | None] = {}
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
        # The AGREEMENT table is loaded exactly where and when the key vectors
        # are: from the same ``data_root``, against the same config-pinned
        # sha256, before the first decision. Absent declaration, absent load,
        # absent signal -- so the flown default reaches the provider with
        # ``agreement_scores=None`` and the recall it ranks is byte-identical.
        agreement_tables[phase] = (
            None
            if spec.agreement_source is None
            else load_sealed_agreement(
                data_root / str(spec.agreement_source["relpath"]),
                expected_sha256=str(spec.agreement_source["sha256"]),
                dimension=EXEMPLAR_INTENT_AGREEMENT_DIMENSION,
                facet_ids=sorted(facet.facet_id for facet in snapshot.facets),
            )
        )
        provider_factories[phase] = _provider_factory(
            spec,
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            facet_vectors=facet_tables[phase],
            provider_for_phase=provider_for_phase,
            prepared_recall=(None if prepared_recall_by_phase is None else prepared_recall_by_phase.get(phase)),
            agreement_scores=agreement_tables[phase],
        )

    seeded = set(seed_phases)
    # Owner decision 159 (``rails.dispatch_slot_fill``, ``recall_prefetch``):
    # the Perception-independent recall a later phase's decision will make,
    # computed ahead on a caller-supplied worker. Empty -- and every branch
    # below that reads it unreachable -- unless ``prefetch_recall`` is called,
    # which only an armed ``dispatch`` block does.
    recall_prefetches: dict[tuple[str, str], object] = {}
    prefetch_lock = threading.Lock()
    prefetchable = {
        phase: spec
        for phase, spec in specs.items()
        if phase not in seeded
        and provider_for_phase is None
        and spec.provider == "kb-facet-v1"
        and (prepared_recall_by_phase is None or prepared_recall_by_phase.get(phase) is None)
    }

    def _recall_now(phase: str, query_record: object) -> dict[str, dict[str, float]]:
        """EXACTLY the recall ``KbFacetProvider.candidates`` makes for this
        phase and row: the same function, the same snapshot object, the same
        key-vector lookup and the same ``top_k_per_dimension`` (the spec's
        ``k``, as ``_provider_factory`` passes it)."""

        table = facet_tables[phase]

        def lookup(facet_id: str) -> Mapping[str, Sequence[float]]:
            return table.get(facet_id, {})

        if isinstance(query_record, SealedSegmentQuery):
            return multidim_segment_recall(
                snapshot, query_record.segments, lookup, specs[phase].k
            )
        return multidim_recall(snapshot, dict(query_record), lookup, specs[phase].k)

    def prefetch_recall(sample_id: str, submit: Callable[..., object]) -> int:
        """Submit this row's later-phase recall(s) through ``submit``
        (``Executor.submit``-shaped). Returns how many were submitted."""

        submitted = 0
        for phase in sorted(prefetchable):
            query_record = query_tables[phase].get(sample_id)
            if not query_record:
                continue
            key = (phase, sample_id)
            with prefetch_lock:
                if key in recall_prefetches:
                    continue
                recall_prefetches[key] = submit(_recall_now, phase, query_record)
            submitted += 1
        return submitted

    def _take_prefetched(phase: str, sample_id: str, query_state: QueryState):
        if not recall_prefetches:
            return None
        with prefetch_lock:
            future = recall_prefetches.pop((phase, sample_id), None)
        if future is None:
            return None
        recall = future.result()
        # The provider keys prepared recall by the QueryState's own query
        # sample; a row whose query sample differs recomputes live.
        if getattr(query_state, "query_sample_id", None) != sample_id:
            return None
        return _provider_factory(
            specs[phase],
            snapshot=snapshot,
            snapshot_sha256=snapshot_sha256,
            facet_vectors=facet_tables[phase],
            provider_for_phase=None,
            prepared_recall={sample_id: recall},
            agreement_scores=agreement_tables[phase],
        )()

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
        if (
            validated_source_bindings is not None
            and sample_id not in validated_source_bindings
        ):
            raise PhaseSupplyError(
                f"segmented query sample {sample_id!r} has no source-audio binding"
            )
        query_record = query_tables[phase_name].get(sample_id)
        if not query_record:
            return None
        if isinstance(query_record, SealedSegmentQuery):
            _assert_segment_query_binding(
                sample_id=sample_id,
                query_state=query_state,
                query_record=query_record,
                source_audio_bindings=validated_source_bindings,
            )
            provider_query = {
                "query_state": query_state,
                "query_segments": query_record.segments,
            }
        else:
            provider_query = {
                "query_state": query_state,
                "query_vectors": dict(query_record),
            }
        # A FRESH provider per decision: KbFacetProvider carries the
        # last-candidates() rank result on the instance, and
        # rails.runner runs trajectories concurrently, so one shared
        # instance would let two samples interleave their decisions.
        provider = _take_prefetched(phase_name, sample_id, query_state)
        if provider is None:
            provider = provider_factories[phase_name]()
        ranking = provider.candidates(provider_query, k=spec.k)
        fusion_decision = provider.fuse(
            [ranking], k=spec.k, policy_id=spec.fuse_policy
        )
        rank_result = provider.last_rank_result()
        if rank_result is None:
            raise PhaseSupplyError(
                f"provider {spec.provider!r} produced no RankResult for phase "
                f"{phase_name!r}; an acquire transition cannot be traced without one"
            )
        # Item E21w (the knowledge INDEX, not the Earnings-21 carrier):
        # the exemplar retrieval RANK, recorded where it is computed and
        # nowhere else. ``rails.kb_policy._fuse_supply_filter`` tags every
        # candidate value with the score of its best admitted supporting
        # facet and then returns ``tuple(sorted(set(...)))``, so today's
        # exemplar block renders in lexicographic evidence-id order and
        # carries no rank at all (M1 analysis section 4.2). This records the
        # number the decision already made; it changes no selection, no
        # order and no request byte, and it runs ONLY when a caller has
        # armed the record by setting the attribute to a dict -- which is
        # exactly when ``native_episode.knowledge_index`` is armed.
        ranks = getattr(supply_for_phase, "retrieval_ranks", None)
        if ranks is not None:
            from .knowledge_index import (  # noqa: PLC0415
                retrieval_similarity, value_retrieval_ranks,
            )

            recorded = value_retrieval_ranks(
                rank_result=rank_result,
                fusion_decision=fusion_decision,
                values=snapshot.values,
            )
            if recorded:
                ranks.setdefault(sample_id, {}).update(recorded)
                similarity = getattr(
                    supply_for_phase, "retrieval_similarity", None
                )
                if similarity is not None and not similarity:
                    similarity.update(
                        retrieval_similarity(
                            rank_result=rank_result,
                            fusion_decision=fusion_decision,
                        )
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
    # E21w: ``None`` -- and therefore no rank recording at all -- unless a
    # caller arms it with a dict before the first contact.
    supply_for_phase.retrieval_ranks = None  # type: ignore[attr-defined]
    supply_for_phase.retrieval_similarity = None  # type: ignore[attr-defined]
    supply_for_phase.snapshot_sha256 = snapshot_sha256  # type: ignore[attr-defined]
    supply_for_phase.provider_factories = provider_factories  # type: ignore[attr-defined]
    supply_for_phase.query_tables = query_tables  # type: ignore[attr-defined]
    supply_for_phase.query_vector_rows = {  # type: ignore[attr-defined]
        phase: len(table) for phase, table in query_tables.items()
    }
    supply_for_phase.facet_vector_rows = {  # type: ignore[attr-defined]
        phase: len(table) for phase, table in facet_tables.items()
    }
    # Only the phases that DECLARED an agreement signal appear, so a receipt
    # never claims a table a cell does not carry.
    supply_for_phase.agreement_rows = {  # type: ignore[attr-defined]
        phase: len(table)
        for phase, table in agreement_tables.items()
        if table is not None
    }
    supply_for_phase.source_audio_bindings = (  # type: ignore[attr-defined]
        validated_source_bindings
    )
    supply_for_phase.prefetch_recall = prefetch_recall  # type: ignore[attr-defined]
    return supply_for_phase


def _provider_factory(
    spec: PhaseSupplySpec,
    *,
    snapshot: KnowledgeSnapshot,
    snapshot_sha256: str,
    facet_vectors: Mapping[str, Mapping[str, tuple[float, ...]]],
    provider_for_phase: ProviderForPhase | None,
    prepared_recall: Mapping[str, Mapping[str, Mapping[str, float]]] | None = None,
    agreement_scores: Mapping[str, Mapping[str, float]] | None = None,
) -> Callable[[], object]:
    """A zero-argument factory producing a provider ready for ONE decision.

    ``kb-facet-v1`` is rebuilt per decision because its recall/rank state
    lives on the instance and trajectories run concurrently. An INJECTED
    provider is returned as the same object every time -- the caller that
    built it owns its concurrency, and says so at
    ``core.flight.FlightRuntime.bind_phase_supply_providers``.
    """

    if prepared_recall is not None and (provider_for_phase is not None or spec.provider != "kb-facet-v1"):
        raise PhaseSupplyError("prepared recall requires the shared kb-facet-v1 provider")
    if agreement_scores is not None and (
        provider_for_phase is not None or spec.provider != "kb-facet-v1"
    ):
        # An INJECTED provider owns its own ranking, so handing it an agreement
        # table would silently drop the signal the config declared. Refused by
        # name rather than ignored.
        raise PhaseSupplyError(
            "an agreement signal requires the shared kb-facet-v1 provider"
        )
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
            prepared_recall=prepared_recall,
            agreement_scores=agreement_scores,
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



_BOOTSTRAP_WORKER_STATE = None


def _bootstrap_worker_init(state):
    global _BOOTSTRAP_WORKER_STATE
    _BOOTSTRAP_WORKER_STATE = state


def _bootstrap_one(task):
    if _BOOTSTRAP_WORKER_STATE is None:
        raise RuntimeError("bootstrap worker state was not initialized")
    return _bootstrap_select(task, _BOOTSTRAP_WORKER_STATE)


def _bootstrap_select(task, state):
    sample_id, query_record, descriptor, source_audio_binding = task
    spec, provider, split_identity_hash = state
    if (
        not isinstance(descriptor, Mapping)
        or set(descriptor) != {"packet_id", "sha256"}
    ):
        raise PhaseSupplyError(
            "speech packet binding must carry exactly packet_id and sha256"
        )
    seed_state = QueryState(
        query_id=f"{SEED_QUERY_ID_PREFIX}:{spec.phase}:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=str(descriptor["packet_id"]),
        speech_packet_sha256=str(descriptor["sha256"]),
        use_split_identity_hash=split_identity_hash,
        query_source=(
            "speech_audio"
            if isinstance(query_record, SealedSegmentQuery)
            and source_audio_binding is None
            else "speech_features"
        ),
    ).validate()
    if isinstance(query_record, SealedSegmentQuery):
        _assert_segment_query_binding(
            sample_id=sample_id,
            query_state=seed_state,
            query_record=query_record,
            source_audio_bindings=(
                None
                if source_audio_binding is None
                else {sample_id: source_audio_binding}
            ),
        )
        provider_query = {"query_state": seed_state, "query_segments": query_record.segments}
    else:
        provider_query = {"query_state": seed_state, "query_vectors": dict(query_record)}
    ranking = provider.candidates(provider_query, k=spec.k)
    fusion_decision = provider.fuse([ranking], k=spec.k, policy_id=spec.fuse_policy)
    return (
        sample_id,
        tuple(fusion_decision.supporting_facet_ids)
        if spec.expose_facets
        else (),
        tuple(fusion_decision.selected_value_ids),
    )


def _validate_bootstrap_workers(workers: int, *, lease_metadata_present: bool = False) -> int:
    if isinstance(workers, bool) or not isinstance(workers, int) or not 1 <= workers <= 20:
        raise PhaseSupplyError("workers must be an integer from 1 through 20")
    if workers > 8 and lease_metadata_present:
        return 8
    return workers



def build_bootstrap_selection(
    spec: PhaseSupplySpec,
    *,
    provider: object,
    query_vectors_by_sample: Mapping[
        str, Mapping[str, tuple[float, ...]] | SealedSegmentQuery
    ],
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    split_identity_hash: str,
    source_audio_bindings: Mapping[str, Mapping[str, object]] | None = None,
    workers: int = 1,
    lease_metadata_present: bool = False,
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
    
    Use explicit workers for Linux fork preparation without changing retrieval
    arithmetic. The parent never installs worker-global provider state, so
    independent calls cannot leak providers or select from another job.
    """
    workers = _validate_bootstrap_workers(workers, lease_metadata_present=lease_metadata_present)
    validated_source_bindings = _validate_source_audio_bindings(
        source_audio_bindings
    )
    tasks = [
        (
            sample_id,
            query_vectors_by_sample[sample_id],
            speech_packet_bindings[sample_id],
            (
                None
                if validated_source_bindings is None
                else validated_source_bindings.get(sample_id)
            ),
        )
        for sample_id in sorted(speech_packet_bindings)
        if query_vectors_by_sample.get(sample_id)
    ]
    if not tasks:
        return {}, {}

    state = (spec, provider, split_identity_hash)
    if workers == 1:
        rows = [_bootstrap_select(task, state) for task in tasks]
    else:
        import sys
        if sys.platform != "linux":
            raise PhaseSupplyError(
                "parallel bootstrap selection requires Linux/WSL fork semantics"
            )
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor

        context = multiprocessing.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_bootstrap_worker_init,
            initargs=(state,),
        ) as pool:
            rows = list(pool.map(_bootstrap_one, tasks))

    facets: dict[str, tuple[str, ...]] = {}
    values: dict[str, tuple[str, ...]] = {}
    for sample_id, facet_ids, value_ids in sorted(rows, key=lambda row: row[0]):
        if value_ids:
            values[sample_id] = value_ids
        if spec.expose_facets and facet_ids:
            facets[sample_id] = facet_ids
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
            # Owner rule 2026-09-06, recorded per phase so a receipt says out
            # loud which modality this run's query vectors declared.
            "query_signal_modality": query_signal_modality(
                specs[phase].query_source,
                field=f"phase_supply[{phase!r}].query_source",
            ),
        }
        for phase in sorted(specs)
    ]
    return {
        "schema": "saea-phase-supply-v2",
        "query_signal_vocabulary": list(QUERY_SIGNAL_MODALITIES),
        "phases": phases,
    }


__all__ = [
    "EMBEDDING_SERVER_KIND",
    "QUERY_SIGNAL_MODALITIES",
    "QUERY_SIGNAL_SEPARATOR",
    "SEALED_AGREEMENT_KIND",
    "SEALED_AGREEMENT_SCHEMA",
    "SEALED_SEGMENT_VECTORS_KIND",
    "SEALED_VECTORS_KIND",
    "SEED_QUERY_ID_PREFIX",
    "SOURCE_KINDS",
    "VECTOR_SOURCE_KINDS",
    "load_sealed_agreement",
    "PhaseSupplyError",
    "PhaseSupplySpec",
    "SealedSegmentQuery",
    "assert_phase_supply_queries_carry_speech",
    "assert_query_signal_declares_speech",
    "assert_segment_query_bindings",
    "build_bootstrap_selection",
    "build_supply_for_phase",
    "load_phase_supply_specs",
    "load_sealed_vectors",
    "load_sealed_segment_vectors",
    "phase_supply_receipt",
    "query_signal_modality",
]


_RECALL_WORKER_STATE = None


def _recall_worker_init(snapshot, facets, k):
    global _RECALL_WORKER_STATE
    _RECALL_WORKER_STATE = (snapshot, facets, k)


def _recall_one(task):
    from .kb_policy import multidim_recall, multidim_segment_recall

    sample_id, query = task
    snapshot, facets, k = _RECALL_WORKER_STATE
    recall = (
        multidim_segment_recall(snapshot, query.segments, lambda fid: facets.get(fid, {}), k)
        if isinstance(query, SealedSegmentQuery)
        else multidim_recall(snapshot, query, lambda fid: facets.get(fid, {}), k)
    )
    return sample_id, recall


def prepare_recall_rows(snapshot, queries, facets, k, *, workers=1):
    """Compute only state-independent recall using the existing deterministic rule."""
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context

    workers = _validate_bootstrap_workers(workers)
    tasks = tuple(sorted(queries.items()))
    if workers == 1:
        global _RECALL_WORKER_STATE
        _recall_worker_init(snapshot, facets, k)
        try:
            return dict(map(_recall_one, tasks))
        finally:
            _RECALL_WORKER_STATE = None
    with ProcessPoolExecutor(
        max_workers=workers, mp_context=get_context("fork"),
        initializer=_recall_worker_init, initargs=(snapshot, facets, k),
    ) as executor:
        return dict(executor.map(_recall_one, tasks, chunksize=8))
