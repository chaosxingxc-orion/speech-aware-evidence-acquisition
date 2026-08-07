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
class CarrierDescriptor:
    """Every per-carrier layout fact this study's data-access layer needs.

    ``reference``/``evidence`` are optional: a carrier with no reference
    layer of its own, or no evidence-source layer at all, declares that
    honestly as ``None`` rather than a caller guessing wrong and silently
    reading nothing (or the wrong carrier's files) -- see
    ``data.references``/``core.evidence`` for the two fail-closed refusals
    this makes possible.

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
    metadata_filename: str
    metadata_columns: MetadataColumns
    reference: ReferenceLayout | None = None
    evidence: EvidenceLayout | None = None
    media_identity_aliases: frozenset[str] = frozenset()


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
