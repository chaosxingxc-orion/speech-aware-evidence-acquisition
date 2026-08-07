"""``FrozenCoreGate`` mixin: D1-anchored media byte-identity verification (I-4).

Split out of ``gate_identity.py`` (R0 repair refactor stage 2, part C, pure
move, no behaviour change) purely for file size. See ``gate_e0.py``'s module
docstring for why ``_measure_file`` calls below go through ``_contracts_pkg``
rather than a bare/imported name.
"""

from __future__ import annotations

import math
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from ..data.carriers import resolve_media_identity_carrier
from .errors import GateClosed
from .gate_d1_lookup import _D1IdentityLookupMixin
from .identifiers import _SHA256
from .receipts import _resolve_under, _safe_relative_path


class _MediaIdentityMixin(_D1IdentityLookupMixin):
    """``verify_media_identity`` and its bitrate-plausibility helper."""

    # I-4 (external-threat-model review): a documented, generous MP3 bitrate
    # plausibility band, derived empirically from the two core carriers'
    # real, D1-frozen media -- observed 16-320 kbps across all 44 earnings21
    # and all 125 earnings22 samples (bytes from the committed D1 manifest,
    # seconds from each carrier's own metadata CSV). Widened well past that
    # observed range on both ends so genuine data never trips it, while still
    # catching the demonstrated attack by many orders of magnitude: replacing
    # a CSV's audio_length cell so 4422s of metered audio read as 0.044s
    # implies ~2.4 GILLION kbps against the file's real (D1-frozen) byte size
    # -- nowhere close to this band. This is a PLAUSIBILITY bound, not an
    # exact duration re-derivation (decoding MP3 frames to prove the exact
    # second count is out of scope here -- see the docstring below and
    # docs/owner-decisions-pending.md for the residue this leaves).
    _MIN_PLAUSIBLE_KBPS = 4.0
    _MAX_PLAUSIBLE_KBPS = 512.0

    def _assert_plausible_audio_seconds(
        self, sample_id: str, audio_seconds: object, media_bytes: int
    ) -> None:
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
        ):
            raise GateClosed(
                f"sample {sample_id!r} audio_seconds must be a finite positive number, "
                f"got {audio_seconds!r}"
            )
        implied_kbps = (media_bytes * 8 / 1000.0) / float(audio_seconds)
        if not (self._MIN_PLAUSIBLE_KBPS <= implied_kbps <= self._MAX_PLAUSIBLE_KBPS):
            raise GateClosed(
                f"sample {sample_id!r}: CSV-derived audio_seconds={audio_seconds!r} implies "
                f"{implied_kbps:.1f} kbps against the D1-recorded media size ({media_bytes} "
                f"bytes) -- outside the plausible MP3 bitrate band "
                f"[{self._MIN_PLAUSIBLE_KBPS}, {self._MAX_PLAUSIBLE_KBPS}] kbps (observed "
                "16-320 kbps across both core carriers' real media); a metadata CSV cell "
                "cannot silently inflate or deflate the metered audio budget (I-4); model "
                "touch refused"
            )

    def verify_media_identity(
        self, carrier_lock_key: str, media_facts: Mapping[str, tuple[str, float]]
    ) -> None:
        """I-4 (external-threat-model review): verify, AT MODEL-TOUCH TIME, that
        the media this run is actually about to send is the same bytes D1
        closed over -- as a re-measured FILE, never merely as a receipt's
        claim about a file.

        PRECISE SCOPE (round-2 external-threat-model review, IMPORTANT A):
        this method only ever re-hashes what ``media_facts`` NAMES -- i.e.
        what the caller's ``PayloadBindingContext.media_relpaths`` says the
        verified split bound for each sample id. It was previously possible
        for the actual outbound payload's own ``media_relpath`` to name a
        DIFFERENT file than the one this method verified (confined under the
        same carrier root, but never compared) -- so this docstring's claim
        that the media "this run is actually about to send" is checked was
        true only once ``core.model.FrozenCoreAdapter._enforce_payload_
        binding`` also enforces, as a precondition of ever reaching the
        transport, that the payload's ``media_relpath`` for a sample EXACTLY
        equals ``binding.media_relpaths[sample_id]`` -- the same value this
        method is handed. With that binding in place the two checks compose
        into the claim above; on its own, re-hashing the binding's claimed
        path is a check about what the BINDING names, not yet a check on the
        literal bytes leaving the process.

        ``media_facts`` maps each sample id the run's VERIFIED SPLIT will touch
        to ``(media_relpath, audio_seconds)`` -- exactly, and only, the samples
        this specific run can send (never the whole ~770 MB carrier). Cost was
        measured, not assumed: re-hashing a full carrier on every gate open was
        rejected as needlessly slow for what a bounded first-slice run can ever
        touch (dev/discovery splits here are 10-44 samples, a few hundred MB at
        most -- seconds, not minutes); re-hashing exactly the run's split scales
        with what the run can actually touch instead. See
        docs/owner-decisions-pending.md for the exact measurement and the
        residue this leaves unclosed.

        Two things are checked per sample, both against D1's OWN frozen
        per-file facts (``docs/receipts/artifacts/d1-identity.json``, itself
        already byte-verified against the E0 closure receipt by
        ``_validate_e0``):

        1. **Byte identity** — the live file's re-measured (size, SHA-256) must
           equal D1's recorded (size, SHA-256) for that sample id. This closes
           the demonstrated defect that an ``.mp3``'s bytes could be replaced
           on disk and the loader/adapter would proceed without complaint: D1
           recorded the fact once at closure time, but nothing ever compared
           it to disk again before this.
        2. **Audio-seconds plausibility** — the CSV-derived ``audio_seconds``
           the loader reports (the figure this run's own plan and its
           pre-registered exposure-ledger row are cross-checked against -- no
           numeric ceiling since the 2026-08-06 owner amendment retired the
           first-slice caps) must imply a plausible MP3 bitrate against that
           SAME frozen byte size (:meth:`_assert_plausible_audio_seconds`). D1
           does not record durations at all (only per-file byte/hash identity
           and the set of sample ids each metadata CSV names -- never the numeric field
           values inside it), so an exact re-derivation of "the real duration"
           is not possible from what D1 already closed over without decoding
           audio; this is a deliberately-scoped plausibility bound, not an
           exact one -- stated plainly, not silently narrowed. It still
           catches the demonstrated attack (4422s edited to 0.044s) by many
           orders of magnitude of margin.

        ``carrier_lock_key`` of ``conec`` resolves to ``earnings21-original``'s
        D1 media layer: ConEC carries no media of its own (D1:
        ``conec.canonical_identity == "earnings21-original media"``).
        MINOR 2 (external-threat-model review round 4): this aliasing is now
        expressed registry-side (``data.carriers.CarrierDescriptor.media_
        identity_aliases`` / :func:`data.carriers.resolve_media_identity_carrier`)
        rather than hand-coded here -- see that function's own docstring for
        why this is layer-specific and never applied to the reference layer.
        """

        if not isinstance(media_facts, Mapping) or not media_facts:
            raise GateClosed(
                "verify_media_identity requires a non-empty sample_id -> "
                "(media_relpath, audio_seconds) mapping"
            )
        identity_carrier = resolve_media_identity_carrier(carrier_lock_key)
        document = self._load(self._d1_identity_artifact_path(), "D1 identity artifact")
        carriers = document.get("carriers")
        carrier_doc = carriers.get(identity_carrier) if isinstance(carriers, Mapping) else None
        if not isinstance(carrier_doc, Mapping):
            raise GateClosed(
                f"D1 identity artifact has no per-sample media identity for carrier "
                f"{identity_carrier!r} (plan carrier {carrier_lock_key!r}); model touch refused"
            )
        layers = carrier_doc.get("layers")
        media_layer = layers.get("media") if isinstance(layers, Mapping) else None
        manifest_entries = media_layer.get("manifest") if isinstance(media_layer, Mapping) else None
        if not isinstance(manifest_entries, list) or not manifest_entries:
            raise GateClosed(
                f"D1 identity artifact carrier {identity_carrier!r} lacks a media manifest; "
                "model touch refused"
            )
        recorded: dict[str, tuple[int, str]] = {}
        for entry in manifest_entries:
            if not isinstance(entry, Mapping):
                raise GateClosed("D1 media manifest entry is not an object")
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
                raise GateClosed(f"D1 media manifest entry is malformed: {entry!r}")
            recorded[sample_id] = (rec_bytes, rec_sha)

        for sample_id, fact in media_facts.items():
            if (
                not isinstance(sample_id, str)
                or not isinstance(fact, tuple)
                or len(fact) != 2
            ):
                raise GateClosed(
                    f"media_facts[{sample_id!r}] must be a (media_relpath, audio_seconds) pair"
                )
            relpath, audio_seconds = fact
            d1_fact = recorded.get(sample_id)
            if d1_fact is None:
                raise GateClosed(
                    f"sample {sample_id!r} (carrier {carrier_lock_key!r}) has no D1-recorded "
                    "media identity; a sample outside D1's identity closure can never be "
                    "sent to the frozen core"
                )
            rec_bytes, rec_sha = d1_fact
            relative = _safe_relative_path(relpath, f"media_facts[{sample_id!r}] media relpath")
            resolved = _resolve_under(self.data_root, relative, f"media for sample {sample_id!r}")
            actual_bytes, actual_sha = _contracts_pkg._measure_file(
                resolved, f"media for sample {sample_id!r}"
            )
            if actual_bytes != rec_bytes or actual_sha != rec_sha:
                raise GateClosed(
                    f"media identity drift for sample {sample_id!r}: D1 recorded "
                    f"{rec_bytes} bytes / {rec_sha[:12]}..., the live file is now "
                    f"{actual_bytes} bytes / {actual_sha[:12]}...; model touch refused (I-4)"
                )
            self._assert_plausible_audio_seconds(sample_id, audio_seconds, rec_bytes)
