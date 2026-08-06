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
    which asset the evidence bytes actually live under."""

    lock_key: str
    subdir: str
    extension: str


@dataclass(frozen=True)
class CarrierDescriptor:
    """Every per-carrier layout fact this study's data-access layer needs.

    ``reference``/``evidence`` are optional: a carrier with no reference
    layer of its own, or no evidence-source layer at all, declares that
    honestly as ``None`` rather than a caller guessing wrong and silently
    reading nothing (or the wrong carrier's files) -- see
    ``data.references``/``core.evidence`` for the two fail-closed refusals
    this makes possible.
    """

    lock_key: str
    media_subdir: str
    media_extension: str
    metadata_filename: str
    metadata_columns: MetadataColumns
    reference: ReferenceLayout | None = None
    evidence: EvidenceLayout | None = None


_REGISTRY: dict[str, CarrierDescriptor] = {}


def register_carrier_descriptor(descriptor: CarrierDescriptor) -> CarrierDescriptor:
    """Register one carrier's layout facts. Refuses a duplicate lock key --
    a descriptor is registered exactly once, the same "one true definition"
    discipline ``core.base.Registry`` applies to loaders/evidence
    sources/scorers (this module stays independent of that registry, and of
    ``core.*`` generally, so it can be imported from ``contracts.*`` and
    ``data.*`` alike without a cycle -- module docstring)."""

    if not isinstance(descriptor, CarrierDescriptor):
        raise CarrierDescriptorError(
            f"register_carrier_descriptor requires a CarrierDescriptor, got "
            f"{type(descriptor).__name__}"
        )
    if descriptor.lock_key in _REGISTRY:
        raise CarrierDescriptorError(
            f"a carrier descriptor is already registered for {descriptor.lock_key!r}"
        )
    _REGISTRY[descriptor.lock_key] = descriptor
    return descriptor


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
        evidence=EvidenceLayout(lock_key="conec", subdir="earnings21/contexts", extension=".txt"),
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
