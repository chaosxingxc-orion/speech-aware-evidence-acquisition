"""``FrozenCoreGate`` mixin: D1-anchored reference byte-identity verification
(IMPORTANT 2, external-threat-model review round 3).

Split out of ``gate_identity.py`` (R0 repair refactor stage 2, part C, pure
move, no behaviour change) purely for file size. See ``gate_e0.py``'s module
docstring for why ``_measure_file`` calls below go through ``_contracts_pkg``
rather than a bare/imported name.
"""

from __future__ import annotations

from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from ..data.carriers import reference_scoped_carrier_lock_keys
from .errors import GateClosed
from .gate_d1_lookup import _D1IdentityLookupMixin
from .identifiers import _SHA256
from .receipts import _resolve_under, _safe_relative_path

# IMPORTANT 2 (external-threat-model review round 3): the D1 identity
# artifact layer key holding per-file (id, bytes, sha256) reference-file
# identity -- ``FrozenCoreGate.verify_reference_identity`` reads this the
# same way ``verify_media_identity`` reads the ``media`` layer key.
_NLP_REFERENCE_D1_LAYER_KEY = "nlp_references"
# R0 repair refactor stage 2 (part B): derived from the SAME
# ``data.carriers.CarrierDescriptor`` registry ``data.references`` reads,
# instead of its own hand-maintained frozenset kept in sync BY CONVENTION
# with ``data.references``'s (then) independent ``_NLP_SUBDIR`` mapping --
# exactly the kind of duplicated carrier-layout knowledge the owner flagged;
# the two can no longer silently drift apart. ``conec`` is deliberately
# absent: it has no reference layer of its own that ``reference_tokens``
# resolves (its D1 identity layer is named ``e21_nlp_references``, a
# DIFFERENT key with DIFFERENT bytes than earnings21-original's own
# ``nlp_references`` -- scoring conec was never reachable through
# ``reference_tokens`` and this gate correctly refuses it too rather than
# silently reusing earnings21's facts for a key that names a distinct file
# set). See docs/owner-decisions-pending.md item 5. Snapshotted once at
# import time: every carrier this study actually registers a descriptor for
# does so unconditionally at ``data.carriers`` import time (its own module
# docstring), so this is equivalent to a live lookup for every carrier this
# gate can ever be asked about in practice.
_REFERENCE_SCOPED_CARRIER_LOCK_KEYS = reference_scoped_carrier_lock_keys()


class _ReferenceIdentityMixin(_D1IdentityLookupMixin):
    """``verify_reference_identity``: the reference-layer counterpart to
    ``gate_media_identity._MediaIdentityMixin.verify_media_identity``."""

    def verify_reference_identity(
        self, carrier_lock_key: str, reference_facts: Mapping[str, str]
    ) -> None:
        """IMPORTANT 2 (external-threat-model review round 3): the reference-
        layer counterpart to :meth:`verify_media_identity`, re-verified AS
        FILES, never merely trusted as a bare ``read_text()`` claim.

        Every formal WER is ``f(frozen scoring code, hypothesis text,
        reference bytes)``. Before this, only the first two were pinned: the
        D3 freeze binds the scoring SOURCE (``_validate_scoring_freeze``),
        and I7's ``response_text_sha256`` re-derivation binds the hypothesis
        -- but ``data.references.reference_tokens`` did a bare
        ``read_text()`` on ``<data_root>/<carrier>/transcripts/
        nlp_references/<sample_id>.nlp`` with no hash/size check at all,
        even though D1 already recorded byte size + SHA-256 for every one of
        these files (the same ``{count, ids_sha256, manifest,
        manifest_sha256, total_bytes}`` shape :meth:`verify_media_identity`
        already reads for ``media``, here under the ``nlp_references`` layer
        key instead). An interrupted asset fetch or a wrong
        ``SPEECHRL_DATA_DIR`` silently produces the identical symptom as a
        deliberate substitution: a WER computed against the wrong bytes with
        every other check green.

        ``reference_facts`` maps each sample id THIS bundle's own verified
        split touches to its reference file's path, relative to
        ``self.data_root`` -- computed by the caller (``core.scorers``, via
        ``data.references.reference_file_relpath``, the SAME relative-path
        convention ``reference_tokens`` itself resolves) rather than
        re-derived here: this module stays independent of ``data.lock``/
        ``data.references`` (the filesystem-touching, umbrella-lock-resolving
        modules) -- module docstring; it does read the layout FACTS a
        ``data.carriers.CarrierDescriptor`` declares (``_REFERENCE_SCOPED_
        CARRIER_LOCK_KEYS`` above), which is pure stdlib/dataclasses with no
        filesystem access of its own. Scoped to exactly the bundle's own
        split -- never the whole ~169-file corpus -- mirroring
        :meth:`verify_media_identity`'s cost discipline (a dev/discovery
        split here is 10-125 samples).

        A carrier lock key with no D1-recorded reference-layer identity this
        gate can re-verify fails closed rather than silently skipping the
        check -- see ``_REFERENCE_SCOPED_CARRIER_LOCK_KEYS`` (today:
        ``earnings21-original`` and ``earnings22-original`` only --
        ``conec`` has no reference layer ``reference_tokens`` can read at
        all, so scoring it was never possible and this method correctly
        refuses it too) and ``docs/owner-decisions-pending.md`` item 5 for
        the residue this leaves if that set ever needs to grow.
        """

        if not isinstance(reference_facts, Mapping) or not reference_facts:
            raise GateClosed(
                "verify_reference_identity requires a non-empty sample_id -> "
                "reference_relpath mapping"
            )
        if carrier_lock_key not in _REFERENCE_SCOPED_CARRIER_LOCK_KEYS:
            raise GateClosed(
                f"carrier lock key {carrier_lock_key!r} has no D1-recorded reference-layer "
                "identity this gate can re-verify; scoring against an unverified reference "
                "layer is refused rather than silently trusted (IMPORTANT 2 fail-closed; "
                "see docs/owner-decisions-pending.md item 5)"
            )
        document = self._load(self._d1_identity_artifact_path(), "D1 identity artifact")
        carriers = document.get("carriers")
        carrier_doc = carriers.get(carrier_lock_key) if isinstance(carriers, Mapping) else None
        if not isinstance(carrier_doc, Mapping):
            raise GateClosed(
                f"D1 identity artifact has no per-sample identity for carrier "
                f"{carrier_lock_key!r}; model touch refused"
            )
        layers = carrier_doc.get("layers")
        ref_layer = (
            layers.get(_NLP_REFERENCE_D1_LAYER_KEY) if isinstance(layers, Mapping) else None
        )
        manifest_entries = ref_layer.get("manifest") if isinstance(ref_layer, Mapping) else None
        if not isinstance(manifest_entries, list) or not manifest_entries:
            raise GateClosed(
                f"D1 identity artifact carrier {carrier_lock_key!r} lacks a "
                f"{_NLP_REFERENCE_D1_LAYER_KEY!r} manifest; model touch refused"
            )
        recorded: dict[str, tuple[int, str]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, Mapping):
                raise GateClosed("D1 reference manifest entry is not an object")
            sample_id = entry.get("id")
            rec_bytes = entry.get("bytes")
            rec_sha = entry.get("sha256")
            if (
                not isinstance(sample_id, str)
                or not sample_id
                or isinstance(rec_bytes, bool)
                or not isinstance(rec_bytes, int)
                or rec_bytes <= 0
                or not isinstance(rec_sha, str)
                or _SHA256.fullmatch(rec_sha) is None
            ):
                raise GateClosed(f"D1 reference manifest entry is malformed: {entry!r}")
            recorded[sample_id] = (rec_bytes, rec_sha)

        for sample_id, relpath in reference_facts.items():
            if not isinstance(sample_id, str) or not isinstance(relpath, str):
                raise GateClosed(
                    f"reference_facts[{sample_id!r}] must be a string reference relpath"
                )
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no D1-recorded "
                    "reference identity; a sample outside D1's identity closure can never be "
                    "scored against"
                )
            rec_bytes, rec_sha = d1_fact
            relative = _safe_relative_path(relpath, f"reference_facts[{sample_id!r}] relpath")
            resolved = _resolve_under(
                self.data_root, relative, f"reference for sample {sample_id!r}"
            )
            actual_bytes, actual_sha = _contracts_pkg._measure_file(
                resolved, f"reference for sample {sample_id!r}"
            )
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"reference identity drift for sample {sample_id!r}: D1 recorded "
                    f"{rec_bytes} bytes / {rec_sha[:12]}..., the live file is now "
                    f"{actual_bytes} bytes / {actual_sha[:12]}...; scoring refused "
                    "(IMPORTANT 2)"
                )
