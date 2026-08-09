"""The evidence-derivation chain: pinned/versioned transforms + the registry
that re-verifies a :class:`~.base.DerivedEvidenceRecord` before its content is
trusted (2026-08-09, ``docs/readiness/2026-08-09-conec-evidence-shape.md``
"Blocking gap"). The evidence-layer counterpart to
``core.model.slices`` (runtime audio slices): same idea -- admit a DERIVED
artefact only when it demonstrably chains to something already verified,
never merely trust a self-computed hash -- applied to evidence text instead
of audio bytes.

Before this module, ``core.driver.run_experiment`` bound evidence identity by
hashing the carrier's RAW per-sample file and checking that hash against
whatever content an evidence source actually returned
(``contracts.gate_evidence_identity.verify_evidence_identity``/
``verify_evidence_content_identity``). That is exactly right for a verbatim
passthrough (``conec-contexts``) and exactly wrong for anything that
TRANSFORMS the source (a capped bias list, reconstructed phrases, a
carrier-independent distractor list, ...): the transformed bytes never equal
the raw file's D1-frozen hash, so every such source failed closed on a real
gated run.

The fix extends the chain instead of weakening the rail. A transforming
evidence source builds a :class:`~.base.DerivedEvidenceRecord` alongside its
``EvidenceItem`` naming: the untransformed SOURCE it read, the PINNED
transform (name+version) it applied, a hash of the params that governed the
transform, and the resulting derived content's own hash.
:meth:`DerivedEvidenceRegistry.register` re-derives every one of those links
independently -- never merely re-hashes the record's own numbers -- and
refuses, naming exactly which link broke, unless ALL of:

  1. the untransformed SOURCE bytes this run actually read hash to
     ``record.source_sha256`` (a self-check performed here; for a
     ``carrier_bound`` record the SEPARATE, UNCHANGED D1 evidence rail --
     ``contracts.gate_evidence_identity`` -- independently re-verifies those
     SAME source bytes against D1's frozen per-sample identity, wired by
     ``core.driver.run_experiment`` to the SOURCE, never the derived output;
     a ``carrier_bound=False`` record has no such D1 anchor at all -- see
     ``DerivedEvidenceRecord``'s own docstring for why that is an HONEST
     limitation, not a bypass);
  2. ``transform_name`` is a REGISTERED transform in :data:`TRANSFORMS` whose
     PINNED version equals ``record.transform_version`` (an unregistered
     name, or a registered name at the WRONG version, both refuse -- never
     silently resolves to "whatever the code happens to do today");
  3. ``record.params_hash`` equals :func:`canonical_params_hash` of the
     params THIS RUN's config actually declares for that transform (an
     independently supplied value from the caller, never merely re-read off
     the record itself -- a source that lied about which params it used is
     caught here);
  4. re-invoking the PINNED transform on the source content with those SAME
     params reproduces bytes whose sha256 equals ``record.derived_sha256``,
     AND the content this run will actually send hashes to the same value --
     which also proves the transform is deterministic (same input + same
     params -> identical output) as a side effect of every real
     verification, never a separately-trusted claim.

No filesystem access happens anywhere in this module: every check is a pure
in-memory hash/re-derivation comparison over bytes the caller already holds
-- the same "zero extra I/O" discipline
``contracts.gate_evidence_identity.verify_evidence_content_identity`` already
established for the (unchanged) source-file rail.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Callable, Mapping

from .base import DerivedEvidenceRecord, EvidenceError

_SHA256 = re.compile(r"[0-9a-f]{64}")
_TRANSFORM_NAME = re.compile(r"[a-z][a-z0-9_-]*")
_TRANSFORM_VERSION = re.compile(r"v[0-9]+(?:\.[0-9]+)*")

TransformFn = Callable[[str, Mapping[str, object]], str]


class DerivedEvidenceError(EvidenceError):
    """A derivation-chain link failed to re-verify, or a transform was
    registered/resolved incorrectly. Subclasses :class:`~.base.EvidenceError`
    so an existing ``except EvidenceError`` catch site still catches this."""


def canonical_params_hash(params: Mapping[str, object]) -> str:
    """Deterministic hash of a transform's own parameters: sorted-key,
    separator-pinned JSON, so the SAME params always hash identically
    regardless of dict construction/insertion order (condition 3 above)."""

    if not isinstance(params, Mapping):
        raise DerivedEvidenceError(
            f"transform params must be a mapping, got {type(params).__name__}"
        )
    canonical = json.dumps(params, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class _TransformSpec:
    __slots__ = ("name", "version", "apply")

    def __init__(self, name: str, version: str, apply: TransformFn) -> None:
        self.name = name
        self.version = version
        self.apply = apply


class TransformRegistry:
    """Pinned, versioned evidence transforms.

    Deliberately NOT :class:`~.base.Registry` (that registry stores one
    object per bare name with no version concept at all): a transform here
    additionally requires an EXPLICIT, non-empty, well-shaped version at
    REGISTRATION time (:meth:`register` refuses a missing/blank/malformed
    version -- an "unversioned" transform can never even be registered, let
    alone resolved), and lookup (:meth:`resolve`) takes a ``(name, version)``
    PAIR: an unregistered name and a registered name at the WRONG version
    both refuse identically. Together this makes reaching a transform's
    ``apply`` function with anything other than the one exact pinned
    (name, version) impossible -- deliverable 5's "make an unregistered or
    unversioned transform impossible to use".
    """

    def __init__(self) -> None:
        self._entries: dict[str, _TransformSpec] = {}

    def register(self, name: str, version: str, apply: TransformFn) -> TransformFn:
        if not isinstance(name, str) or _TRANSFORM_NAME.fullmatch(name) is None:
            raise DerivedEvidenceError(
                f"transform name {name!r} must match {_TRANSFORM_NAME.pattern!r}"
            )
        if not isinstance(version, str) or _TRANSFORM_VERSION.fullmatch(version) is None:
            raise DerivedEvidenceError(
                f"transform {name!r} version {version!r} must be a non-empty "
                "'vN[.N...]' string -- an unversioned transform can never be registered"
            )
        if name in self._entries:
            raise DerivedEvidenceError(f"transform registry: duplicate name {name!r}")
        if not callable(apply):
            raise DerivedEvidenceError(f"transform {name!r} apply must be callable")
        self._entries[name] = _TransformSpec(name, version, apply)
        return apply

    def resolve(self, name: str, version: str) -> _TransformSpec:
        if not isinstance(name, str) or not name:
            raise DerivedEvidenceError(f"unregistered transform {name!r}")
        spec = self._entries.get(name)
        if spec is None:
            raise DerivedEvidenceError(
                f"unregistered transform {name!r}; registered: {self.names()}"
            )
        if not isinstance(version, str) or not version or spec.version != version:
            raise DerivedEvidenceError(
                f"transform {name!r} version {version!r} does not match the pinned "
                f"registered version {spec.version!r}; an unversioned or mismatched-"
                "version transform can never be used"
            )
        return spec

    def names(self) -> list[str]:
        return sorted(self._entries)


# One shared, permanent registry (module singleton -- mirrors core.base's
# EVIDENCE_SOURCES/CARRIERS/etc.). Individual transforms register themselves
# here at import time from the module that implements them
# (core.bias_lists), exactly like core.evidence registers its sources into
# EVIDENCE_SOURCES.
TRANSFORMS = TransformRegistry()


def _identity_transform(text: str, params: Mapping[str, object]) -> str:
    """The verbatim evidence source's own "transform": returns its input
    unchanged. Registered so ``conec-contexts`` can carry a genuine
    DerivedEvidenceRecord too (deliverable 4) instead of being a special
    case the registry has to know about."""

    return text


TRANSFORMS.register("identity", "v1", _identity_transform)


class DerivedEvidenceRegistry:
    """Per-run registry: :class:`~.base.DerivedEvidenceRecord` ->
    full independent re-derivation (module docstring, conditions 2-4; the
    D1-anchored condition 1 is the SEPARATE, unchanged
    ``contracts.gate_evidence_identity`` rail, run alongside this one by
    ``core.driver.run_experiment`` for every ``carrier_bound`` record).
    Constructed fresh per run (no shared state across runs), mirroring
    ``core.model.slices.SliceRegistry``; a record once registered is kept
    for :meth:`lookup` (audit/trace), and a duplicate registration for the
    same ``(sample_id, transform_name)`` key is refused.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], DerivedEvidenceRecord] = {}

    def register(
        self,
        record: DerivedEvidenceRecord,
        *,
        source_content: bytes,
        derived_content: bytes,
        params: Mapping[str, object],
    ) -> DerivedEvidenceRecord:
        if not isinstance(record, DerivedEvidenceRecord):
            raise DerivedEvidenceError(
                "derived-evidence registration requires a DerivedEvidenceRecord, got "
                f"{type(record).__name__}"
            )
        for label, value in (
            ("sample_id", record.sample_id),
            ("source_relpath", record.source_relpath),
            ("transform_name", record.transform_name),
            ("transform_version", record.transform_version),
        ):
            if not isinstance(value, str) or not value:
                raise DerivedEvidenceError(
                    f"derived-evidence record {label} must be a non-empty string"
                )
        for label, value in (
            ("source_sha256", record.source_sha256),
            ("params_hash", record.params_hash),
            ("derived_sha256", record.derived_sha256),
        ):
            if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
                raise DerivedEvidenceError(
                    f"derived-evidence record {label} must be a sha256 hex digest"
                )
        if not isinstance(record.carrier_bound, bool):
            raise DerivedEvidenceError("derived-evidence record carrier_bound must be a bool")

        # Condition 2: registered, pinned transform. Named FIRST -- a record
        # naming an unregistered/mismatched-version transform is refused
        # before any bytes are even inspected.
        spec = TRANSFORMS.resolve(record.transform_name, record.transform_version)

        # Self-check: the SOURCE bytes this run actually read must hash to
        # what the record claims (mirrors SliceRegistry's independent parent
        # re-measurement). For a carrier_bound record this DUPLICATES, but is
        # independent of, the D1 file/content rail run alongside it; for a
        # carrier_bound=False record it is the ONLY identity anchor there is.
        if not isinstance(source_content, (bytes, bytearray)) or not source_content:
            raise DerivedEvidenceError(
                f"derived-evidence chain for sample {record.sample_id!r}: source_content "
                "must be non-empty bytes"
            )
        actual_source_sha256 = hashlib.sha256(source_content).hexdigest()
        if actual_source_sha256 != record.source_sha256:
            raise DerivedEvidenceError(
                f"derived-evidence chain broke at SOURCE for sample {record.sample_id!r}: "
                f"record claims source_sha256 {record.source_sha256[:12]}..., the bytes "
                f"this run actually read hash to {actual_source_sha256[:12]}... -- a "
                "tampered or substituted source can never derive trusted content"
            )

        # Condition 3: params hash matches what THIS RUN's config declares
        # (params supplied by the caller, never merely re-read off the
        # record).
        expected_params_hash = canonical_params_hash(params)
        if record.params_hash != expected_params_hash:
            raise DerivedEvidenceError(
                f"derived-evidence chain broke at PARAMS for sample {record.sample_id!r} "
                f"transform {record.transform_name!r}: record declares params_hash "
                f"{record.params_hash[:12]}..., this run's config declares "
                f"{expected_params_hash[:12]}..."
            )

        # Condition 4: re-invoking the pinned transform on the (verified)
        # source with those SAME params reproduces the claimed derived hash,
        # AND the bytes this run will actually send match it too.
        try:
            source_text = source_content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise DerivedEvidenceError(
                f"derived-evidence chain for sample {record.sample_id!r}: source_content "
                f"is not valid UTF-8: {error}"
            ) from error
        re_derived = spec.apply(source_text, params)
        if not isinstance(re_derived, str) or not re_derived:
            raise DerivedEvidenceError(
                f"transform {record.transform_name!r} produced empty/non-string output "
                f"for sample {record.sample_id!r}"
            )
        re_derived_sha256 = hashlib.sha256(re_derived.encode("utf-8")).hexdigest()
        if re_derived_sha256 != record.derived_sha256:
            raise DerivedEvidenceError(
                f"derived-evidence chain broke at DERIVED CONTENT for sample "
                f"{record.sample_id!r} transform {record.transform_name!r}: "
                f"re-applying the pinned transform hashes to {re_derived_sha256[:12]}..., "
                f"record claims {record.derived_sha256[:12]}..."
            )
        if not isinstance(derived_content, (bytes, bytearray)) or not derived_content:
            raise DerivedEvidenceError(
                f"derived-evidence chain for sample {record.sample_id!r}: derived_content "
                "must be non-empty bytes"
            )
        actual_derived_sha256 = hashlib.sha256(derived_content).hexdigest()
        if actual_derived_sha256 != record.derived_sha256:
            raise DerivedEvidenceError(
                f"derived-evidence chain broke at SENT CONTENT for sample "
                f"{record.sample_id!r}: the evidence content this run will actually send "
                f"hashes to {actual_derived_sha256[:12]}..., record claims "
                f"{record.derived_sha256[:12]}..."
            )

        key = (record.sample_id, record.transform_name)
        if key in self._records:
            raise DerivedEvidenceError(
                f"derived-evidence record for sample {record.sample_id!r} transform "
                f"{record.transform_name!r} is already registered"
            )
        self._records[key] = record
        return record

    def lookup(self, sample_id: str, transform_name: str) -> DerivedEvidenceRecord | None:
        return self._records.get((str(sample_id), str(transform_name)))
