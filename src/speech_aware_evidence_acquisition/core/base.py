"""Foundation seams: ONE registry mechanism + shared value types (R0).

Anti-fragmentation contract (owner direction 2026-08-05): every pluggable
dimension of a Stage-2 experiment — carrier, evidence source, transport,
policy, scorer — registers here through the same Registry class, and every
run flows through core.driver.run_experiment(). A new experiment is config
plus at most one newly registered component, never new wiring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from ..contracts import assert_information_boundary


class CoreError(RuntimeError):
    """A foundation seam refuses: unknown/duplicate registration or wiring misuse."""


class Registry:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._entries: dict[str, object] = {}

    def register(self, name: str, entry: object) -> object:
        if not isinstance(name, str) or not name.strip():
            raise CoreError(f"{self._kind} registry: blank name")
        if name in self._entries:
            raise CoreError(f"{self._kind} registry: duplicate name {name!r}")
        self._entries[name] = entry
        return entry

    def resolve(self, name: str) -> object:
        try:
            return self._entries[name]
        except KeyError:
            raise CoreError(
                f"unknown {self._kind} {name!r}; registered: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._entries)


CARRIERS = Registry("carrier")
EVIDENCE_SOURCES = Registry("evidence source")
TRANSPORTS = Registry("transport")
POLICIES = Registry("policy")
SCORERS = Registry("scorer")
# P1 scaffold: named fills for the ONE supported task-instruction template
# placeholder ("{tool_schemas}" -- see core.instructions). A fill is a
# callable (lock, root) -> str rendering pinned carrier data (e.g. the
# Audio2Tool tools_registry.csv) into the frozen prompt template at run time,
# so registry-sized prompt material is never committed into a config
# fragment. Same one-Registry discipline as every other seam above.
INSTRUCTION_FILLS = Registry("instruction fill")

_REQUIRED_PROVENANCE = ("lock_key", "relpath", "sha256")


class EvidenceError(RuntimeError):
    """An evidence item is malformed or an evidence source is unavailable."""


@dataclass(frozen=True)
class DerivedEvidenceRecord:
    """One evidence item's derivation chain (2026-08-09, ``docs/readiness/
    2026-08-09-conec-evidence-shape.md`` "Blocking gap"): the evidence-layer
    counterpart to ``core.model.slices.SliceRecord`` for runtime audio
    slices. ``core.driver.run_experiment`` used to bind evidence identity by
    hashing the carrier's RAW per-sample file and checking that hash against
    whatever content an evidence source actually returned -- correct for a
    verbatim passthrough (``conec-contexts``), but it fails closed on every
    source that TRANSFORMS that content (a capped bias list, reconstructed
    phrases, a carrier-independent distractor list, ...), because the
    transformed bytes never equal the raw file's D1-frozen hash.

    The fix extends the chain rather than weakening the rail (exactly the
    audio precedent): a transforming evidence source builds one of these
    records alongside its :class:`EvidenceItem`, naming the untransformed
    SOURCE it read, the PINNED transform (name+version) it applied, a hash of
    the params that governed the transform, and the resulting derived
    content's own hash. ``core.evidence_derivation.DerivedEvidenceRegistry``
    re-derives every one of those links independently before the content is
    trusted to reach a prompt -- see that module's docstring for the exact
    four conditions and which refusal names which broken link.

    ``carrier_bound`` (default ``True``): ``source_relpath``/``source_sha256``
    name a SINGLE per-sample carrier file (the SAME relative-path convention
    ``core.evidence.evidence_file_relpath`` already uses), whose identity the
    EXISTING, UNCHANGED D1 evidence rail
    (``contracts.gate_evidence_identity``) independently re-verifies via
    ``core.driver.run_experiment``'s ``binding.evidence_relpaths``/
    ``evidence_contents`` -- now scoped to the SOURCE bytes, never the
    derived ones. ``carrier_bound=False`` is the HONEST alternative for
    evidence built from files that carry no D1-recorded per-sample identity
    at all (e.g. the shared ``bias_lists/`` corpus): ``source_relpath``/
    ``source_sha256`` then name a COMBINED, canonically-ordered manifest of
    those files, identity rests SOLELY on this record's own re-derived chain
    (weaker than the D1-anchored case), and the record says so plainly
    instead of fabricating a per-sample carrier binding it cannot back up.
    """

    sample_id: str
    source_relpath: str
    source_sha256: str
    transform_name: str
    transform_version: str
    params_hash: str
    derived_sha256: str
    carrier_bound: bool = True

    def trace_view(self) -> dict[str, object]:
        """The record as a JSON-safe mapping for trace/derivation artifacts."""

        return {
            "sample_id": self.sample_id,
            "source_relpath": self.source_relpath,
            "source_sha256": self.source_sha256,
            "transform_name": self.transform_name,
            "transform_version": self.transform_version,
            "params_hash": self.params_hash,
            "derived_sha256": self.derived_sha256,
            "carrier_bound": self.carrier_bound,
        }


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_uri: str
    content: str
    provenance: Mapping[str, str]
    # Derivation-chain rail (2026-08-09): optional, defaulted so every
    # pre-existing direct construction (this module's own "none" source, unit
    # tests building a bare EvidenceItem) is unaffected. A transforming
    # evidence source (core.evidence's conec-bias-list/distractor-only-
    # bias-list) sets both: `derivation` is the claim, `derivation_source_
    # bytes` is the untransformed source bytes the source function actually
    # read (kept OFF the runtime/provenance views below -- never crosses the
    # information boundary, it exists purely for
    # core.evidence_derivation.DerivedEvidenceRegistry to re-verify against,
    # zero extra I/O, mirroring verify_evidence_content_identity's own
    # "check the bytes already read" discipline).
    derivation: DerivedEvidenceRecord | None = None
    derivation_source_bytes: bytes | None = None

    def validate(self) -> "EvidenceItem":
        for label, value in (
            ("evidence_id", self.evidence_id),
            ("source_uri", self.source_uri),
            ("content", self.content),
        ):
            if not isinstance(value, str) or not value:
                raise EvidenceError(f"evidence {label} must be a non-empty string")
        if not isinstance(self.provenance, Mapping):
            raise EvidenceError("evidence provenance must be a mapping")
        missing = [key for key in _REQUIRED_PROVENANCE if key not in self.provenance]
        if missing:
            raise EvidenceError(f"evidence provenance lacks required keys {missing}")
        assert_information_boundary(self.runtime_view())
        assert_information_boundary(dict(self.provenance))
        return self

    def runtime_view(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source_uri": self.source_uri,
            "content": self.content,
        }

    def provenance_view(self) -> dict[str, object]:
        return dict(self.provenance)


@dataclass(frozen=True)
class SampleOutcome:
    sample_id: str
    request_ids: tuple[str, ...]
    text: str
    admitted: bool
    request_sha256: str
    response_sha256: str
    # R0 repair T6 (I7): sha256 of ``text`` alone (UTF-8 bytes), independent of
    # ``response_sha256``'s raw-transport-bytes hash (whose exact bytes --
    # dict key order of a server-controlled ``usage`` mapping included -- are
    # not reproducible from ``text`` alone). This is the field
    # ``core.bundle.verify_bundle`` recomputes to catch an outputs row whose
    # ``text`` was mutated after the fact while ``response_sha256`` was left
    # untouched (see ``core.model.CoreResponse.response_text_sha256`` for
    # where it is first computed, at the one true model-request choke point).
    response_text_sha256: str


@dataclass(frozen=True)
class RunResult:
    run_id: str
    arm: str
    outputs_path: Path
    trace_manifest_hash: str
    cost: Mapping[str, object]


@dataclass(frozen=True)
class PayloadBindingContext:
    """Immutable payload<->plan<->split binding facts (R0 repair T3, invariants I3/I4).

    Built by the driver from the T1 :class:`~.split_receipt.VerifiedSplit` (the
    frozen, live-recomputed sample id set actually authorized for this run) and
    the same carrier loader's per-sample facts, plus the controlled data root
    and the specific carrier's own subdirectory beneath it. This is the object
    a :class:`~.model.FrozenCoreAdapter` must be constructed with: a payload can
    name any sample id, carrier or path string it likes, but the adapter only
    ever trusts what this context says was actually loaded for this run.
    """

    carrier_lock_key: str
    allowed_sample_ids: frozenset[str]
    sample_facts: Mapping[str, tuple[float, int]]
    data_root: Path
    carrier_root: Path
    # I-4 (external-threat-model review): the same carrier loader's per-sample
    # media_relpath, keyed exactly like sample_facts. Optional/defaulted (not a
    # constructor-breaking addition) so every pre-existing caller in this
    # module's own test suite -- unit tests isolating I3 payload-binding or I4
    # path-confinement behavior, which never touch D1 identity at all -- keeps
    # working unchanged; the one true production call site
    # (core.driver.run_experiment) always supplies it, and
    # core.model.FrozenCoreAdapter only attempts the D1 media-identity check
    # (gate.verify_media_identity) when it is present and non-empty.
    media_relpaths: Mapping[str, str] = field(default_factory=dict)
    # IMPORTANT 1 (external-threat-model review round 4): the sample ids THIS
    # run's evidence source supplied non-empty evidence for, mapped to that
    # evidence file's path (core.evidence.evidence_file_relpath), so
    # core.model.FrozenCoreAdapter can ask the gate to re-verify it against
    # D1's frozen evidence-layer identity -- the evidence-layer counterpart to
    # media_relpaths above. Optional/defaulted (not every sample necessarily
    # carries evidence -- evidence_source "none" supplies an empty mapping)
    # and, unlike media_relpaths, deliberately NOT required to cover every
    # allowed_sample_id: only samples with actual evidence appear here.
    evidence_relpaths: Mapping[str, str] = field(default_factory=dict)
    # IMPROVEMENT (fifth external-threat-model review): the same sample ids as
    # evidence_relpaths, mapped instead to the exact UTF-8 bytes of the
    # evidence content this run's evidence source ALREADY READ into memory --
    # so core.model.FrozenCoreAdapter can ask the gate to bind the D1
    # evidence-identity check to the bytes actually consumed, never merely a
    # second read of the file at gate-check time (see
    # contracts.gate_evidence_identity's own module docstring for the
    # check<->send race this closes). Optional/defaulted like
    # evidence_relpaths, for the same reason: not every binding built in this
    # module's own test suite constructs a real evidence corpus.
    evidence_contents: Mapping[str, bytes] = field(default_factory=dict)

    def validate(self) -> "PayloadBindingContext":
        """Structural self-check, no filesystem access: a malformed binding
        context (wrong shape, sample_facts that don't exactly cover
        allowed_sample_ids, a carrier_root outside data_root) refuses rather
        than silently under-checking payloads later."""

        if not isinstance(self.carrier_lock_key, str) or not self.carrier_lock_key.strip():
            raise CoreError("binding context carrier_lock_key must be a non-empty string")
        if not isinstance(self.allowed_sample_ids, frozenset) or not self.allowed_sample_ids:
            raise CoreError("binding context allowed_sample_ids must be a non-empty frozenset")
        if not all(
            isinstance(sample_id, str) and sample_id for sample_id in self.allowed_sample_ids
        ):
            raise CoreError("binding context allowed_sample_ids must contain non-empty strings")
        if not isinstance(self.sample_facts, Mapping) or set(self.sample_facts) != set(
            self.allowed_sample_ids
        ):
            raise CoreError(
                "binding context sample_facts keys must exactly match allowed_sample_ids"
            )
        for sample_id, fact in self.sample_facts.items():
            if not isinstance(fact, tuple) or len(fact) != 2:
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] must be an "
                    "(audio_seconds, sample_rate_hz) tuple"
                )
            audio_seconds, sample_rate_hz = fact
            if (
                isinstance(audio_seconds, bool)
                or not isinstance(audio_seconds, (int, float))
                or not math.isfinite(audio_seconds)
                or audio_seconds <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] audio_seconds must be "
                    "a finite positive number"
                )
            if (
                isinstance(sample_rate_hz, bool)
                or not isinstance(sample_rate_hz, int)
                or sample_rate_hz <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] sample_rate_hz must be "
                    "a positive integer"
                )
        if not isinstance(self.data_root, Path) or not isinstance(self.carrier_root, Path):
            raise CoreError("binding context data_root/carrier_root must be Path objects")
        if not self.carrier_root.is_relative_to(self.data_root):
            raise CoreError("binding context carrier_root must be beneath data_root")
        if not isinstance(self.media_relpaths, Mapping):
            raise CoreError("binding context media_relpaths must be a mapping")
        # I-4: optional (empty is allowed -- see the field's own docstring), but
        # if ANY entry is supplied it must exactly cover allowed_sample_ids: a
        # partial media_relpaths mapping would let some samples silently skip
        # the D1 media-identity check entirely.
        if self.media_relpaths and set(self.media_relpaths) != set(self.allowed_sample_ids):
            raise CoreError(
                "binding context media_relpaths keys must exactly match allowed_sample_ids "
                "when supplied"
            )
        for sample_id, relpath in self.media_relpaths.items():
            if not isinstance(relpath, str) or not relpath:
                raise CoreError(
                    f"binding context media_relpaths[{sample_id!r}] must be a non-empty string"
                )
        if not isinstance(self.evidence_relpaths, Mapping):
            raise CoreError("binding context evidence_relpaths must be a mapping")
        # IMPORTANT 1: unlike media_relpaths, evidence is legitimately sparse
        # (not every sample carries evidence -- evidence_source "none" yields
        # none at all), so only a SUBSET check applies: every key must still
        # name an actually-allowed sample id, never one outside this run's own
        # verified split.
        if not set(self.evidence_relpaths) <= set(self.allowed_sample_ids):
            raise CoreError(
                "binding context evidence_relpaths keys must be a subset of "
                "allowed_sample_ids"
            )
        for sample_id, relpath in self.evidence_relpaths.items():
            if not isinstance(relpath, str) or not relpath:
                raise CoreError(
                    f"binding context evidence_relpaths[{sample_id!r}] must be a "
                    "non-empty string"
                )
        if not isinstance(self.evidence_contents, Mapping):
            raise CoreError("binding context evidence_contents must be a mapping")
        # IMPROVEMENT: same sparse-subset discipline as evidence_relpaths above
        # -- not every allowed sample id necessarily carries evidence content.
        if not set(self.evidence_contents) <= set(self.allowed_sample_ids):
            raise CoreError(
                "binding context evidence_contents keys must be a subset of "
                "allowed_sample_ids"
            )
        for sample_id, content_bytes in self.evidence_contents.items():
            if not isinstance(content_bytes, (bytes, bytearray)) or not content_bytes:
                raise CoreError(
                    f"binding context evidence_contents[{sample_id!r}] must be "
                    "non-empty bytes"
                )
        return self


@dataclass
class SampleContext:
    sample: object
    evidence: list[EvidenceItem]
    adapter: object
    sink: object
    arm: str
    task_instruction: str
    decoding_params: Mapping[str, object]
    request_id_base: str
    retrieval_query: str | None = None
    extras: dict[str, object] = field(default_factory=dict)
