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
from .paths import _normalized_relative_path, _resolve_confined


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
        relative = _normalized_relative_path(payload["media_relpath"], "payload media_relpath")
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
        _resolve_confined(
            binding.data_root,
            relative,
            binding.carrier_root,
            "payload media_relpath",
            strict=True,
        )
