"""Per-carrier layout knowledge, in ONE place (R0 repair refactor stage 2, part B).

Owner-identified abstraction gap: before this module existed, knowing "where
Earnings21/Earnings22 keep their media / metadata / references / ConEC
evidence contexts" was spread, independently, across four modules --
``data/loader.py`` (media subdir+extension, metadata filename, and the
metadata COLUMN NAMES per carrier, duplicated across two near-identical
loader functions), ``data/references.py`` (a carrier -> reference-subdir
mapping), ``core/evidence.py`` (a hardcoded ``earnings21/contexts/<id>.txt``
ConEC path regardless of which carrier the run's split actually named --
"exactly what made three config fragments non-runnable in an earlier
round"), and ``contracts/gate_identity.py`` (a hand-maintained
reference-scoped carrier set that had to be kept in sync with
``data/references.py``'s own mapping by convention, not by construction).

A :class:`CarrierDescriptor` now holds every one of those layout facts for
one carrier lock key. Adding a future carrier means registering ONE new
descriptor (:func:`register_carrier_descriptor`) plus its loader
(``core.carriers``) -- never editing four modules' internals. Every one of
the four consumers above now reads a descriptor rather than carrying its own
copy of this knowledge; see each module's own docstring for exactly how.

Stdlib-only, pure dataclasses -- no filesystem access, no dependency on
``core.*``/``contracts.*`` at module scope. This is deliberate: it is what
lets ``contracts/gate_identity.py`` consult a descriptor's reference-layer
facts (module docstring there) without importing anything heavier than plain
data, and it means every descriptor here is fully testable before any
dataset asset, umbrella lock, or ML dependency exists.
"""

from __future__ import annotations

from dataclasses import dataclass


class CarrierDescriptorError(RuntimeError):
    """An unknown carrier lock key was asked for layout facts, or a descriptor
    was itself malformed at registration time."""


@dataclass(frozen=True)
class MetadataColumns:
    """The column names a carrier's metadata CSV uses (these differ per
    carrier today: Earnings21 uses ``file_id``/``audio_length``/
    ``sample_rate``; Earnings22 uses ``File ID``/``File Length (seconds)``/
    ``Sampling Rate (Hz)``)."""

    id_column: str
    duration_column: str
    sample_rate_column: str


@dataclass(frozen=True)
class ReferenceLayout:
    """Where a carrier's ``.nlp``-style reference-transcript layer lives,
    relative to the carrier's own materialized root."""

    subdir: str
    extension: str


@dataclass(frozen=True)
class EvidenceLayout:
    """Where a carrier's evidence-source layer lives -- NOT necessarily under
    the carrier's own asset root: ConEC evidence for Earnings21 lives under
    the separate ``conec`` lock key's own materialized root
    (``<conec root>/earnings21/contexts/<id>.txt``), so ``lock_key`` names
    which asset the evidence bytes actually live under.

    ``d1_layer_key`` (IMPORTANT 1, external-threat-model review round 4)
    names the layer key this evidence lives under in D1's own identity
    artifact (``docs/receipts/artifacts/d1-identity.json``,
    ``carriers[lock_key].layers[d1_layer_key]``) -- e.g. ConEC's context
    layer is D1-recorded as ``e21_contexts``, not derivable from ``subdir``
    (``earnings21/contexts``) by any fixed rule, so it is its own explicit
    fact rather than a hand-coded string at the gate call site. This is what
    lets ``contracts.FrozenCoreGate.verify_evidence_identity`` re-hash
    exactly the D1-frozen evidence bytes a carrier's evidence source is
    about to read, the same way ``ReferenceLayout``'s own subdir already
    lets :meth:`verify_reference_identity` do for references (that method's
    D1 layer key, ``nlp_references``, happens to equal its subdir's last
    path segment for both registered carriers today -- evidence's does not,
    which is exactly why this field exists instead of reusing that
    coincidence)."""

    lock_key: str
    subdir: str
    extension: str
    d1_layer_key: str


@dataclass(frozen=True)
class EntityLayout:
    """Where a carrier's entity-annotation sidecar layer lives (owner decision
    D-3, entity-class WER scorer admission): one JSON file per sample,
    ``<sample_id><extension>`` under ``subdir``, relative to the carrier's own
    materialized root -- the SAME root :class:`ReferenceLayout` resolves
    under, via the SAME ``data.lock.asset_dir`` convention.

    This sidecar (Earnings21's ``transcripts/wer_tags/<id>.wer_tag.json``)
    maps an entity ID to its ``entity_type`` label; the entity ID -> reference
    TOKEN membership itself lives in the carrier's OWN ``.nlp`` reference
    file's ``wer_tags`` column (:class:`ReferenceLayout`, read by
    :func:`speech_aware_evidence_acquisition.data.references.reference_tokens`'s
    sibling, ``reference_entity_mentions``) -- an entity layer is therefore
    only usable for a carrier that ALSO declares a ``reference`` layout;
    ``reference_entity_mentions`` fails closed otherwise.
    """

    subdir: str
    extension: str


@dataclass(frozen=True)
class TaskLayout:
    """Consolidation slice C1 ("one carrier registry"): the paper-facing task
    facts a carrier's own data layer cannot express on its own -- which task
    family this carrier probes, which registered ``core.base.SCORERS`` name
    is the OFFICIAL scorer for it, which short key names its knowledge layer
    (if any), and which field a stratified read groups its samples by (if
    any).

    ``official_scorer_id`` names a ``core.base.SCORERS`` registry key as a
    plain string, not a live lookup -- this module stays stdlib-only (module
    docstring) and must not import ``core.*`` at module scope, and a scorer
    (e.g. ``slurp-slu``) may legitimately not exist yet at the point its
    carrier's descriptor is registered (this slice registers the STRING only;
    building the scorer itself is a different slice's job, exactly as this
    field's own admission note says).

    ``knowledge_layer``/``stratum_key`` are short, free-text description
    keys (not layout paths -- those still live in ``reference``/``evidence``/
    ``entity`` below), deliberately optional: a carrier with no knowledge
    layer of its own (earnings22-original) or no stratified read axis
    (earnings21-original/earnings22-original, whose D1 closure is a flat
    per-file split) declares that honestly as ``None``, the same "declare
    absence, never guess" discipline ``CarrierDescriptor.reference``/
    ``evidence`` already apply.
    """

    task_kind: str
    official_scorer_id: str
    knowledge_layer: str | None = None
    stratum_key: str | None = None


@dataclass(frozen=True)
class CarrierDescriptor:
    """Every per-carrier layout fact this study's data-access layer needs.

    ``reference``/``evidence`` are optional: a carrier with no reference
    layer of its own, or no evidence-source layer at all, declares that
    honestly as ``None`` rather than a caller guessing wrong and silently
    reading nothing (or the wrong carrier's files) -- see
    ``data.references``/``core.evidence`` for the two fail-closed refusals
    this makes possible.

    ``metadata_filename``/``metadata_columns`` are ALSO optional (consolidation
    slice C1): a carrier whose sample universe is authorized by its own
    receipt or governed metadata rather than a single per-carrier metadata
    CSV (Audio2Tool's frozen probe-sample receipt, SLURP's governed jsonl
    splits -- see ``AUDIO2TOOL``/``SLURP`` below) declares both ``None``
    rather than naming a CSV that does not exist. This is safe for every
    EXISTING consumer: ``data.loader.load_carrier`` is the only reader of
    either field (verified by repository-wide search, C1 slice) and now fails
    closed with a clear ``LoaderError`` for a descriptor with no metadata
    layer, instead of a bare ``TypeError`` from ``Path / None``; both
    earnings descriptors keep declaring both fields exactly as before, so
    ``load_carrier``'s existing behaviour for them is completely unchanged.

    ``task`` (consolidation slice C1) is optional for the same "declare
    absence honestly" reason: a carrier's paper-facing task family, official
    scorer, knowledge layer and stratum key are facts a CONSUMER (e.g. a
    future cross-task roster/report builder) may need to derive without
    hand-maintaining its own carrier->task table; see :class:`TaskLayout` and
    :func:`task_scoped_carrier_lock_keys`/:func:`carrier_task_layout` below.
    Both earnings descriptors currently declare no ``task`` layer (their own
    ``asr-wer`` scoring is not yet expressed this way) -- adding one for them
    is left to whichever slice actually needs it, not invented speculatively
    here.

    ``media_identity_aliases`` (MINOR 2, external-threat-model review round
    4): the set of OTHER lock keys whose D1 media identity this carrier's
    OWN media layer also supplies -- e.g. ``earnings21-original`` declares
    ``{"conec"}`` because D1 records ``conec.canonical_identity ==
    "earnings21-original media"`` (ConEC carries no media of its own).
    Registry-driven so ``contracts.gate_media_identity.verify_media_identity``
    never hand-codes this equivalence (MINOR 2's own fix): see
    :func:`resolve_media_identity_carrier`. Layer-specific and deliberately
    NOT reused for the reference layer (``reference_scoped_carrier_lock_
    keys`` above): conec's own D1 reference layer, ``e21_nlp_references``,
    is a DIFFERENT, differently-hashed file set than earnings21-original's
    own ``nlp_references`` -- aliasing conec to earnings21-original for
    references would score against the wrong bytes.
    """

    lock_key: str
    media_subdir: str
    media_extension: str
    metadata_filename: str | None = None
    metadata_columns: MetadataColumns | None = None
    reference: ReferenceLayout | None = None
    evidence: EvidenceLayout | None = None
    media_identity_aliases: frozenset[str] = frozenset()
    entity: EntityLayout | None = None
    task: TaskLayout | None = None


_REGISTRY: dict[str, CarrierDescriptor] = {}
_MEDIA_IDENTITY_ALIAS_INDEX: dict[str, str] = {}


def register_carrier_descriptor(descriptor: CarrierDescriptor) -> CarrierDescriptor:
    """Register one carrier's layout facts. Refuses a duplicate lock key --
    a descriptor is registered exactly once, the same "one true definition"
    discipline ``core.base.Registry`` applies to loaders/evidence
    sources/scorers (this module stays independent of that registry, and of
    ``core.*`` generally, so it can be imported from ``contracts.*`` and
    ``data.*`` alike without a cycle -- module docstring).

    Also registers every one of ``descriptor.media_identity_aliases`` into
    the module-level alias index (MINOR 2): refuses an alias that collides
    with an already-registered carrier lock key or an already-registered
    alias, the same duplicate discipline the primary registry itself
    applies -- and, symmetrically (MINOR, fifth external-threat-model
    review), refuses registering a descriptor whose OWN ``lock_key`` was
    already declared as someone else's alias. Before this direction was
    checked too, a real carrier could register itself under a lock key an
    earlier descriptor had claimed as an alias, and
    :func:`resolve_media_identity_carrier` would then silently redirect that
    new carrier's own media-identity rail to the ALIASING carrier's D1 media
    layer instead of its own -- with no signal, exactly the collision this
    docstring's "same duplicate discipline" claim was previously only half
    true for."""

    if not isinstance(descriptor, CarrierDescriptor):
        raise CarrierDescriptorError(
            f"register_carrier_descriptor requires a CarrierDescriptor, got "
            f"{type(descriptor).__name__}"
        )
    if descriptor.lock_key in _REGISTRY:
        raise CarrierDescriptorError(
            f"a carrier descriptor is already registered for {descriptor.lock_key!r}"
        )
    if descriptor.lock_key in _MEDIA_IDENTITY_ALIAS_INDEX:
        raise CarrierDescriptorError(
            f"carrier lock key {descriptor.lock_key!r} collides with an already-"
            f"registered media identity alias (declared by "
            f"{_MEDIA_IDENTITY_ALIAS_INDEX[descriptor.lock_key]!r})"
        )
    for alias in descriptor.media_identity_aliases:
        if not isinstance(alias, str) or not alias.strip():
            raise CarrierDescriptorError(
                f"{descriptor.lock_key!r} media_identity_aliases must contain only "
                "non-empty strings"
            )
        if alias in _REGISTRY or alias in _MEDIA_IDENTITY_ALIAS_INDEX:
            raise CarrierDescriptorError(
                f"media identity alias {alias!r} (declared by {descriptor.lock_key!r}) "
                "collides with an already-registered carrier lock key or alias"
            )
    _REGISTRY[descriptor.lock_key] = descriptor
    for alias in descriptor.media_identity_aliases:
        _MEDIA_IDENTITY_ALIAS_INDEX[alias] = descriptor.lock_key
    return descriptor


def resolve_media_identity_carrier(carrier_lock_key: str) -> str:
    """MINOR 2 (external-threat-model review round 4): which carrier's D1
    media layer supplies identity for ``carrier_lock_key`` -- itself, unless
    some OTHER registered carrier declares it as one of its own
    ``media_identity_aliases``. Today only ``earnings21-original`` declares
    ``conec`` as an alias; a lock key that is neither a registered carrier
    nor a declared alias is returned unchanged (the caller, e.g.
    ``verify_media_identity``, is responsible for refusing an unresolvable
    result -- this function itself never raises)."""

    return _MEDIA_IDENTITY_ALIAS_INDEX.get(carrier_lock_key, carrier_lock_key)


def get_carrier_descriptor(lock_key: str) -> CarrierDescriptor:
    try:
        return _REGISTRY[lock_key]
    except KeyError:
        raise CarrierDescriptorError(
            f"no carrier descriptor registered for {lock_key!r}; registered: "
            f"{sorted(_REGISTRY)}"
        ) from None


def registered_carrier_lock_keys() -> frozenset[str]:
    return frozenset(_REGISTRY)


def reference_scoped_carrier_lock_keys() -> frozenset[str]:
    """Every registered carrier whose descriptor declares its own reference
    layer -- the set ``contracts.gate_identity._REFERENCE_SCOPED_CARRIER_
    LOCK_KEYS`` is now derived from, rather than separately hand-maintained
    to agree with :func:`data.references.reference_file_relpath`'s own
    per-carrier lookup."""

    return frozenset(key for key, entry in _REGISTRY.items() if entry.reference is not None)


def entity_scoped_carrier_lock_keys() -> frozenset[str]:
    """Every registered carrier whose descriptor declares its own entity
    layer (owner decision D-3) -- the ``entity-wer`` scorer's fail-closed
    scope check derives from this, exactly the way ``asr-wer`` already
    derives its own scope from :func:`reference_scoped_carrier_lock_keys`.
    Today: ``earnings21-original`` only -- ``earnings22-original`` has no
    ``wer_tags`` layer at all (E0 D1, ``data/identity.py::earnings22_layers``)."""

    return frozenset(key for key, entry in _REGISTRY.items() if entry.entity is not None)


def task_scoped_carrier_lock_keys() -> frozenset[str]:
    """Every registered carrier whose descriptor declares its own
    :class:`TaskLayout` (consolidation slice C1) -- ``audio2tool`` and
    ``slurp`` from that slice, plus ``earnings21-original`` since item E35
    (owner decision 89, 2026-09-21: the contextual-ASR task layer, so the
    Earnings21+ConEC carrier can fly the same native six-node episode SLURP
    flies through the shared harness). ``earnings22-original`` still
    declares no ``task`` layer at all (``CarrierDescriptor.task``'s own
    docstring) -- it is not in scope for E35 and has no ConEC evidence layer
    of its own (``EARNINGS22_ORIGINAL.evidence is None`` above)."""

    return frozenset(key for key, entry in _REGISTRY.items() if entry.task is not None)


def carrier_task_layout(lock_key: str) -> TaskLayout:
    """``lock_key``'s :class:`TaskLayout`, fail-closed for an unregistered
    carrier (:func:`get_carrier_descriptor`'s own refusal) or a registered
    one that declares no task layer at all -- the same "declare absence,
    refuse a guess" discipline :func:`data.references._reference_layout`/
    :func:`core.evidence._evidence_layout` already apply for their own
    optional layers."""

    descriptor = get_carrier_descriptor(lock_key)
    if descriptor.task is None:
        raise CarrierDescriptorError(
            f"carrier {lock_key!r} declares no task layer "
            "(data.carriers.CarrierDescriptor.task is None)"
        )
    return descriptor.task


# ---------------------------------------------------------------------------
# The two built-in carriers this study actually scores today. Registered
# unconditionally at import time (not lazily), so importing this module
# alone is always enough to make both descriptors available to every
# consumer -- no separate "register the built-ins" step to remember to run
# first (unlike ``core.carriers``, which registers LOADERS into
# ``core.base.CARRIERS`` and is imported explicitly by whatever needs
# runtime loading; this module is imported directly by ``data.loader``/
# ``data.references``/``contracts.gate_identity`` themselves).
# ---------------------------------------------------------------------------

EARNINGS21_ORIGINAL = register_carrier_descriptor(
    CarrierDescriptor(
        lock_key="earnings21-original",
        media_subdir="media",
        media_extension=".mp3",
        metadata_filename="earnings21-file-metadata.csv",
        metadata_columns=MetadataColumns(
            id_column="file_id",
            duration_column="audio_length",
            sample_rate_column="sample_rate",
        ),
        reference=ReferenceLayout(subdir="transcripts/nlp_references", extension=".nlp"),
        evidence=EvidenceLayout(
            lock_key="conec",
            subdir="earnings21/contexts",
            extension=".txt",
            d1_layer_key="e21_contexts",
        ),
        # MINOR 2: D1 records conec.canonical_identity == "earnings21-original
        # media" (ConEC carries no media of its own) -- see CarrierDescriptor's
        # own docstring for why this is layer-specific (never applied to
        # references).
        media_identity_aliases=frozenset({"conec"}),
        # Owner decision D-3 (entity-class WER scorer admission): the ONLY
        # carrier whose `.nlp` reference file's `wer_tags` column has a
        # matching `<id>.wer_tag.json` entity-type sidecar registered here at
        # all (E0 D1, `data/identity.py::earnings21_layers`'s own "wer_tags"
        # layer). `earnings22-original` below declares no `entity` layout --
        # `earnings22_layers` has no `wer_tags` layer -- so `entity-wer`
        # fails closed for it via `entity_scoped_carrier_lock_keys`.
        entity=EntityLayout(subdir="transcripts/wer_tags", extension=".wer_tag.json"),
        # Item E35 (owner decision 89, 2026-09-21): the Earnings21+ConEC
        # carrier is a "contextual-asr" task -- the program's standard
        # Earnings number is the Whisper-normalised corpus WER
        # (``asr-wer-whisper``, beside ``saea-scoring-v1``); its knowledge
        # layer is the ConEC evidence layer this descriptor already declares
        # above (``evidence.d1_layer_key == "e21_contexts"``); its natural
        # stratified-read axis is the per-call id
        # (``metadata_columns.id_column == "file_id"``), the same field the
        # native-window six-node episode's readiness package strata on.
        task=TaskLayout(
            task_kind="contextual-asr",
            official_scorer_id="asr-wer-whisper",
            knowledge_layer="conec-contexts",
            stratum_key="file_id",
        ),
    )
)

EARNINGS22_ORIGINAL = register_carrier_descriptor(
    CarrierDescriptor(
        lock_key="earnings22-original",
        media_subdir="media",
        media_extension=".mp3",
        metadata_filename="metadata.csv",
        metadata_columns=MetadataColumns(
            id_column="File ID",
            duration_column="File Length (seconds)",
            sample_rate_column="Sampling Rate (Hz)",
        ),
        reference=ReferenceLayout(subdir="transcripts/nlp_references", extension=".nlp"),
        # Earnings22's ConEC evidence layer is a fundamentally different shape
        # (per-call PDF packets under conec/earnings22/contexts/pdfs/, not
        # one-.txt-per-sample) that `core.evidence._conec_contexts` has never
        # read -- declared absent here so a config naming this carrier with
        # `evidence_source=conec-contexts` fails closed with a clear message
        # instead of silently reading earnings21-original's contexts for an
        # earnings22 sample id (the exact defect this refactor closes).
        evidence=None,
    )
)


# ---------------------------------------------------------------------------
# The two bounded-discovery-probe carriers (2026-08-15 owner amendment,
# module docstring of ``data/identity.py``). Neither carries a per-carrier
# metadata CSV -- their sample universe is authorized by their OWN receipt or
# governed metadata (Audio2Tool's frozen probe-sample receipt, SLURP's
# governed jsonl splits), never a ``file_id,...`` table this module could
# read generically -- so both declare ``metadata_filename``/
# ``metadata_columns`` as ``None`` (``CarrierDescriptor``'s own docstring) and
# neither is loadable through ``data.loader.load_carrier``; each has its own
# dedicated loader (``data.audio2tool.load_audio2tool`` /
# ``core.carriers.SlurpEngineeringCarrier``) that ``core.carriers`` registers
# by lock key (consolidation slice C1).
# ---------------------------------------------------------------------------

# Lock key strings below are quoted literally (not imported) to keep this
# module stdlib-only (module docstring: "no dependency on core.*/contracts.*
# at module scope") -- the canonical constants they must match are
# ``data.audio2tool.AUDIO2TOOL_LOCK_KEY`` ("audio2tool") and
# ``data.slurp.SLURP_LOCK_KEY`` ("slurp"); the C1 unification tests pin both
# literals against those constants directly so the two can never silently
# drift apart.

AUDIO2TOOL = register_carrier_descriptor(
    CarrierDescriptor(
        lock_key="audio2tool",
        # ``data/audio2tool.py`` module docstring: "``<asset root>/
        # tools_registry.csv`` plus ``<asset root>/public/`` holding one
        # ``tier{N}_{name}_data/tier{N}_{name}.json`` manifest ... and one
        # ``tier{N}_{name}_audios/query_{id:05d}/*.wav`` directory tree per
        # tier"; ``load_audio2tool`` builds every sample's own
        # ``media_relpath`` as ``f"{subdir}/public/{item.audio_relpath_in_
        # public}"`` (``data/audio2tool.py::load_audio2tool``) -- "public" is
        # the one fixed top-level subdir every tier's media tree sits under,
        # relative to the carrier's own asset root.
        media_subdir="public",
        media_extension=".wav",
        # No metadata CSV (module docstring above); no reference/evidence/
        # entity layer either -- the receipt is this carrier's ONLY sample
        # authority (``data/audio2tool.py`` module docstring: "pre-
        # registration means no run may ever resolve Audio2Tool items outside
        # it") and it never names a gold reference-transcript or evidence
        # file this study's generic reference/evidence machinery could read.
        task=TaskLayout(
            task_kind="speech-tool-use",
            official_scorer_id="a2t-toolcall",
            knowledge_layer="tool-registry",
            stratum_key="tier",
        ),
    )
)

SLURP = register_carrier_descriptor(
    CarrierDescriptor(
        lock_key="slurp",
        # ``data/slurp.py``'s own ``_governed_roots`` resolves the governed
        # audio ROOT dynamically from the lock, never a fixed subdir off a
        # carrier asset root the way earnings21/22 do: "the umbrella lock's
        # own ``slurp`` entry names two DISTINCT trees ... ``annotations.
        # governed_copy`` (``datasets/slurp/metadata`` ...)" (module
        # docstring), and ``audio_root_relpath = governed_copy[:
        # -len("/metadata")]`` (``_governed_roots``) -- i.e. the audio root is
        # the metadata directory's own sibling, not a literal constant this
        # descriptor can name. Split-specific media then sits one level
        # below that root: ``_AUDIO_SUBDIR_FOR_SPLIT: Mapping[str, str] =
        # {"devel": "slurp_real", "test": "slurp_real", "train": "slurp_real",
        # "train_synthetic": "slurp_synth"}`` (``data/slurp.py``). This field
        # therefore names the concrete subdir the study's own discovery split
        # resolves under -- ``devel``, the ``split_id`` default in
        # ``data.identity.slurp_layers`` and the only split this study's own
        # CLAUDE.md research boundary makes addressable without an explicit
        # ``allow_heldout``/``allow_synthetic`` opt-in -- for descriptive/
        # registry purposes ONLY: SLURP's real loader
        # (``core.carriers.SlurpEngineeringCarrier`` /
        # ``data.slurp._governed_roots``) resolves its own root straight from
        # the lock and never reads this descriptor field at all.
        media_subdir="slurp_real",
        media_extension=".flac",
        # No metadata CSV (governed jsonl splits, not a CSV table); no
        # reference/evidence/entity layer -- SLURP's own SLU gold
        # (scenario/action/entities) lives in ``data.slurp.SlurpRecord``, read
        # through ``data.slurp.load_slurp_split`` directly, never through this
        # study's generic ``.nlp``-reference/entity-sidecar machinery.
        task=TaskLayout(
            task_kind="slot-slu",
            official_scorer_id="slurp-slu",
            knowledge_layer="train-ontology",
            stratum_key="scenario",
        ),
    )
)
