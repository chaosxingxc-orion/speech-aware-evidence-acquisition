"""``FrozenCoreAdapter`` mixin: payload<->plan<->split binding enforcement (I3/I4).

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). A plain mixin (method only, no
``__init__``/fields) combined into ``FrozenCoreAdapter`` via multiple
inheritance in ``adapter.py`` -- this changes nothing about the class's
runtime behaviour, only which file the method's source lives in.
"""

from __future__ import annotations

from typing import Mapping

from . import FrozenCoreError
from .paths import _normalized_relative_path, _resolve_confined, _resolve_confined_any


class _PayloadBindingMixin:
    """``_enforce_payload_binding``: the payload's own claimed values must
    agree with what the driver actually verified for this run."""

    def _enforce_payload_binding(self, payload: Mapping[str, object], audio_seconds: object) -> None:
        """I3/I4: the payload's own claimed values must agree with what the
        driver actually verified for this run (the T1 split + carrier loader
        facts bound at construction), not merely be well-typed. A payload can
        name any carrier, sample, path or audio fact it likes; only what
        ``self._binding`` says was loaded is ever trusted."""

        binding = self._binding
        carrier_lock_key = payload["carrier_lock_key"]
        if carrier_lock_key != self._plan.carrier_lock_key:
            raise FrozenCoreError(
                f"payload carrier_lock_key {carrier_lock_key!r} does not match the "
                f"execution plan carrier_lock_key {self._plan.carrier_lock_key!r}"
            )
        sample_id = payload["sample_id"]
        if not isinstance(sample_id, str) or sample_id not in binding.allowed_sample_ids:
            raise FrozenCoreError(
                f"payload sample_id {sample_id!r} is not in the verified split bound "
                "to this run"
            )
        expected_speech_ref = f"{self._plan.carrier_lock_key}/{sample_id}"
        if payload["speech_ref"] != expected_speech_ref:
            raise FrozenCoreError(
                f"payload speech_ref {payload['speech_ref']!r} does not match the "
                f"expected {expected_speech_ref!r} for carrier_lock_key/sample_id"
            )
        relative = _normalized_relative_path(payload["media_relpath"], "payload media_relpath")
        # Slice-rail extension (obs-agent-loop, owner directive 2026-08-08): a
        # payload naming something OTHER than the sample's registered parent
        # media is admitted ONLY as a derivation-chained runtime slice --
        # exactly the (sample_id, media_relpath) pair a core.model.SliceRegistry
        # verified chains to the registered media (parent-bytes hash, offsets
        # inside the parent's verified duration, run-local slice tree, slice
        # byte identity re-checked per send). Its metered audio_seconds /
        # sample_rate_hz then bind to the SLICE record, so a slice request is
        # charged exactly the seconds actually sent -- never the parent's
        # whole duration, and never a payload-claimed number the rail cannot
        # vouch for. With no registry (every pre-existing caller) or no
        # matching record, the original exact-relpath refusal below fires
        # unchanged.
        if binding.media_relpaths and relative != binding.media_relpaths.get(sample_id):
            self._enforce_slice_payload_binding(payload, audio_seconds, sample_id, relative)
            return
        fact_audio_seconds, fact_sample_rate_hz = binding.sample_facts[sample_id]
        if float(audio_seconds) != float(fact_audio_seconds):
            raise FrozenCoreError(
                f"payload audio_seconds {audio_seconds!r} disagrees with the loader "
                f"fact {fact_audio_seconds!r} for sample {sample_id!r}"
            )
        sample_rate_hz = payload["sample_rate_hz"]
        if (
            isinstance(sample_rate_hz, bool)
            or not isinstance(sample_rate_hz, int)
            or sample_rate_hz != fact_sample_rate_hz
        ):
            raise FrozenCoreError(
                f"payload sample_rate_hz {sample_rate_hz!r} disagrees with the loader "
                f"fact {fact_sample_rate_hz!r} for sample {sample_id!r}"
            )
        # IMPORTANT A (round-2 external-threat-model review): confinement alone
        # only proved the payload's media_relpath stays INSIDE the carrier
        # root -- it never compared it to what this run's verified split
        # actually names for THIS sample (``binding.media_relpaths``, the same
        # per-sample mapping ``core.driver.run_experiment`` builds from the
        # loader and the gate's ``verify_media_identity`` re-hashes). A
        # payload could therefore name any OTHER file confined under the same
        # carrier root -- e.g. a decoy media file -- and it sailed straight
        # through: the gate re-hashed the BINDING's claimed path, but the
        # transport read and sent whatever path the payload itself carried.
        # Demonstrated: a gate verified {'s1': ('carrier/s1.mp3', 10.0)}; a
        # payload naming media_relpath="carrier/decoy.mp3" was accepted, the
        # decoy's bytes were sent, and only 10.0s (the BOUND sample's
        # duration) was metered against this run's own planned audio-seconds
        # budget regardless of the decoy's real length. Requiring an EXACT
        # match after
        # normalization closes this: the only media_relpath a payload for
        # ``sample_id`` may ever carry is the one the verified split/loader
        # bound for that exact sample id.
        if binding.media_relpaths:
            expected_relpath = binding.media_relpaths.get(sample_id)
            if expected_relpath is None:
                raise FrozenCoreError(
                    f"payload binding has no verified media_relpath for sample "
                    f"{sample_id!r}; a sample the binding cannot vouch for can never "
                    "be sent"
                )
            if relative != expected_relpath:
                raise FrozenCoreError(
                    f"payload media_relpath {relative!r} does not match the verified "
                    f"split's own media_relpath {expected_relpath!r} for sample "
                    f"{sample_id!r} -- confinement under the carrier root is necessary "
                    "but not sufficient; the payload must name EXACTLY the file the "
                    "binding (and, at the gate, verify_media_identity) vouches for, "
                    "never merely some other file that happens to live under the same "
                    "root (I4 exact media-relpath binding)"
                )
        # DERIVED-MEDIA CONFINEMENT (2026-09-07). The carrier root is not always
        # the only place this run's OWN verified media lives: a derived media
        # variant of the carrier (the ``@ts2`` silence-tail populations, the
        # 16 kHz input-rate populations, the ESB utterance cuts) is written under
        # its own ``<data_root>/derived/<variant>/`` root, and its dataset
        # fragment declares that root plus the hash-pinned D1 media supplement
        # that vouches for every file under it. Confining to ``carrier_root``
        # ALONE therefore refused every such row the moment a real request was
        # built, on every construction site that had no per-script workaround:
        # ``core.driver.run_experiment``, the speech-native profile (what packet
        # preprocessing runs through -- where the SLURP ``@ts2`` promotion lost
        # 4/4 contacts on 2026-09-07 with nothing reaching the wire), and
        # ``core.flight.FlightRuntime``'s default ``asset_dir`` resolver. The
        # preflights and the zero-socket wire checks passed throughout, because
        # neither ever builds a payload.
        #
        # Accepting those declared roots does NOT re-open the decoy hole
        # IMPORTANT A above closes, for one reason: this widening happens
        # strictly AFTER the I4 exact-relpath check. By the time control reaches
        # here the payload's media_relpath has already been proven EQUAL to the
        # one string this run's verified split holds for this exact sample id --
        # so the set of files a payload can name is unchanged at exactly one
        # (its own), whatever roots are legal. Confinement's remaining job is
        # what it always was: prove that one string cannot resolve, through
        # symlinks and all, outside the controlled trees this run is bound to.
        # A root only enters that set through ``core.base.
        # declared_derived_media_roots``, which refuses anything that is not a
        # named variant directory strictly beneath ``<data_root>/derived/`` and
        # anything a fragment declares without its paired, hash-pinned D1 media
        # supplement -- so the widening is per-fragment, hash-anchored and, for
        # every fragment that declares no such key, empty.
        _resolve_confined_any(
            binding.data_root,
            relative,
            (binding.carrier_root, *binding.derived_media_roots),
            "payload media_relpath",
            strict=True,
        )

    def _enforce_slice_payload_binding(
        self, payload: Mapping[str, object], audio_seconds: object, sample_id: str, relative: str
    ) -> None:
        """Admit-or-refuse a non-parent media_relpath as a derivation-chained
        runtime slice (see the call-site comment in
        :meth:`_enforce_payload_binding` for the contract; fail-closed)."""

        registry = getattr(self, "_slice_registry", None)
        record = registry.lookup(sample_id, relative) if registry is not None else None
        if record is None:
            expected_relpath = self._binding.media_relpaths.get(sample_id)
            if expected_relpath is None:
                raise FrozenCoreError(
                    f"payload binding has no verified media_relpath for sample "
                    f"{sample_id!r}; a sample the binding cannot vouch for can never "
                    "be sent"
                )
            raise FrozenCoreError(
                f"payload media_relpath {relative!r} does not match the verified "
                f"split's own media_relpath {expected_relpath!r} for sample "
                f"{sample_id!r} -- confinement under the carrier root is necessary "
                "but not sufficient; the payload must name EXACTLY the file the "
                "binding (and, at the gate, verify_media_identity) vouches for, "
                "never merely some other file that happens to live under the same "
                "root (I4 exact media-relpath binding; a runtime slice is admitted "
                "only through a registered core.model.SliceRecord derivation chain)"
            )
        if abs(float(audio_seconds) - float(record.audio_seconds)) > 1e-6:
            raise FrozenCoreError(
                f"payload audio_seconds {audio_seconds!r} disagrees with the slice "
                f"derivation record's {record.audio_seconds!r} for {relative!r} -- a "
                "slice request is metered by exactly the seconds its derivation "
                "record proves were cut"
            )
        sample_rate_hz = payload["sample_rate_hz"]
        if (
            isinstance(sample_rate_hz, bool)
            or not isinstance(sample_rate_hz, int)
            or sample_rate_hz != record.sample_rate_hz
        ):
            raise FrozenCoreError(
                f"payload sample_rate_hz {sample_rate_hz!r} disagrees with the slice "
                f"derivation record's {record.sample_rate_hz!r} for {relative!r}"
            )
        # Byte identity re-checked on EVERY send, not merely at registration --
        # a slice swapped between the two is caught before its bytes leave the
        # process (mirrors the registration-time check; same registry code).
        registry.verify_slice_bytes(record)
        _resolve_confined(
            self._binding.data_root,
            relative,
            registry.slice_root(),
            "payload media_relpath (runtime slice)",
            strict=True,
        )
