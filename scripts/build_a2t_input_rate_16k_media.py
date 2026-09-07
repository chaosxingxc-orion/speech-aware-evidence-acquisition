#!/usr/bin/env python3
"""Build the INPUT-RATE STANDARDIZED media variants of the Audio2Tool frozen 400
(model-free, CPU only).

One exposure row covers both variants, registered before the first byte is
written:

    ``SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1``

==============  ==========================================================
variant         what it is
==============  ==========================================================
``16k``         every sealed 24 kHz release wav resampled to 16 kHz mono
                int16 through the study's OWN pinned decoder
                (``reproduction.obs_loop.decode_parent_pcm`` -> librosa
                ``soxr_hq``), and nothing else
``16k+ts2``     the ``16k`` samples with exactly 2.0 s of digital silence
                appended, through the PINNED Earnings-22 transform
==============  ==========================================================

Why this build exists
---------------------
Every Audio2Tool release wav is **24 kHz mono 16-bit**, and the frozen core's
front end wants 16 kHz. Today nobody converts: the study's transport base64s the
sealed bytes verbatim and llama.cpp's miniaudio front end resamples them inside
the decoder, with ITS resampler and ITS filter. The owner rule of 2026-09-07 is
to standardize the input rate ourselves, with librosa, before the bytes ever
reach the wire. This build produces that media and measures what the conversion
moves; it decides nothing and flies nothing.

``docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md`` is the read of the
resampler that is running today; ``docs/readiness/2026-09-07-a2t-input-rate-
standardization-v1-preregistration.md`` is the cell this media enables. Neither
is authorized by this row.

Why the tail variant rides along
--------------------------------
The cross-carrier preregistration's Audio2Tool ``@ts2`` cell appended 2.0 s
(48,000 samples) to the **24 kHz** bytes. If the 16 kHz standardization is
admitted, that cell's media is superseded: the tail must sit on the standardized
bytes instead. ``16k+ts2`` is that replacement, built here so the two cells are
one preparation and not two, and so the tail's own rule can be the PINNED one
rather than a second implementation -- at 16 kHz the Earnings-22 transform's
hard-coded ``2 * 16000`` is exactly 2.0 s, so it is called directly.

What is READ, and what is never opened
--------------------------------------
**Media bytes only.** The inputs are one committed, hash-pinned roster receipt
(identifiers, media paths, measured media identity) and the 400 sealed wavs it
names, each re-hashed against its record before it is read. **No evaluation
query text, gold tool name, argument, tool-registry row, sealed output,
hypothesis or score is opened**, and the build receipt records each as zero.

What is PINNED, and what makes the build refuse
-----------------------------------------------
A resample is not a rearrangement of bytes: a different decoder, a different
``res_type`` or a different library version produces different samples. So the
decoder is pinned three ways and any drift stops the build before a clip is
touched:

1. ``reproduction.obs_loop.decode_parent_pcm`` -- the study's ONE decode-and-
   resample path, already the definition of "16 kHz mono int16" for every
   Earnings parent -- is pinned by the SHA-256 of its own source text, not by
   the file it lives in, so an unrelated edit to ``obs_loop.py`` does not
   invalidate the pin and an edit to the decoder does.
2. ``librosa`` and ``soxr`` versions, and ``librosa.load``'s default
   ``res_type``, read from the running interpreter and compared to the pins.
3. ``ffmpeg`` must be ABSENT. ``decode_parent_pcm`` prefers ffmpeg when it is on
   PATH, so an ffmpeg that appeared on this machine would silently change every
   produced byte. Its absence is a pinned property of this program and is
   asserted here rather than assumed.

Building the media is not a model contact and is not a flight. The cell needs
its own preregistration, its own owner GO and its own exposure row.

Usage (WSL2)::

    python scripts/build_a2t_input_rate_16k_media.py --variant all
    python scripts/build_a2t_input_rate_16k_media.py --variant all --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import shutil
import sys
import tempfile
import wave
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_clip_boundary import (  # noqa: E402
    energy_margins,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    EVALUATION_ROSTER_ROLE,
    RosterItem,
    canonical_receipt_bytes,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    write_wav_bytes,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: E402
    decode_parent_pcm,
)

#: The rate everything is standardized TO. It is the rate llama.cpp's mtmd front
#: end asks its decoder for (``mtmd_get_audio_sample_rate``) and the rate the
#: Qwen3-Omni mel front end hard-codes (``clip.cpp`` ``audio_sample_rate``).
TARGET_SAMPLE_RATE_HZ = 16000

#: The rate every Audio2Tool release wav actually carries -- measured across all
#: 400 by the 2026-09-07 cross-carrier media build, and re-asserted per file by
#: ``read_wav_header`` below.
SOURCE_SAMPLE_RATE_HZ = 24000

TAIL_SILENCE_SECONDS = 2.0
SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
BUILD_RECEIPT_SCHEMA = "saea-a2t-input-rate-16k-media-build-receipt-v1"
PROBE_VIEW_SCHEMA = "saea-a2t-input-rate-16k-probe-view-v1"

#: Freezing an ALREADY complete population, not drawing from it: every stratum's
#: quota equals that stratum's own candidate count, so the seed cannot change
#: the membership. Recorded for reproducibility only.
FREEZE_SEED = 20260907

#: The frozen 400 roster, pinned exactly as the cross-carrier ``@ts2`` build
#: pins it, so both variants of this population descend from the same receipt.
ROSTER_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json"
)
ROSTER_SHA256 = "6f352ea583d0bb91f77aad62e07bdad4d3210d066440fbfaee8e2af504853fe7"

#: The Earnings-22 dev1500 builder is the ONE implementation of the 2.0 s tail.
#: At 16 kHz its hard-coded ``2 * 16000`` IS 2.0 s, so ``16k+ts2`` calls it
#: directly rather than re-deriving the rule.
DEV_BUILDER_RELPATH = "scripts/build_e22_dev1500_media_variants.py"
DEV_BUILDER_SHA256 = "49e5d91095c061d167688bd4dea35fc7503d3a09caa3066db68fde9807d196e6"
TAIL_VARIANT = "tail-silence-2s"

#: The decoder, pinned by the SHA-256 of its own source text.
DECODER_QUALNAME = "reproduction.obs_loop.decode_parent_pcm"
DECODER_SOURCE_SHA256 = (
    "32450decda3101b6d78fa01cb5bb1c105ea1a7c18666105cb4e5597b8963de1a"
)
PINNED_LIBROSA_VERSION = "0.11.0"
PINNED_SOXR_VERSION = "1.1.0"
PINNED_RES_TYPE = "soxr_hq"

RESAMPLE_RULE = (
    "every sealed 24 kHz mono int16 release wav decoded to 16 kHz mono int16 "
    "through reproduction.obs_loop.decode_parent_pcm -- librosa.load(sr=16000, "
    f"mono=True) at res_type '{PINNED_RES_TYPE}' (librosa "
    f"{PINNED_LIBROSA_VERSION} / soxr {PINNED_SOXR_VERSION}), then "
    "clip(rint(float32 * 32767), -32768, 32767) to int16; nothing is trimmed, "
    "nothing is normalized, no channel is dropped and the sample count is the "
    "exact 2/3 the rate ratio requires"
)
TAIL_RULE = (
    "exactly 2.0 s of digital silence appended to the 16 kHz standardized clip "
    "-- 32,000 zero samples through the PINNED Earnings-22 "
    "transform('tail-silence-2s', ...); nothing is removed, no standardized "
    "sample is altered and the sample rate is never changed"
)

#: The probe tones the frequency-response summary is measured on. One second
#: each, synthesized at 24 kHz and pushed through the SAME pinned decode path,
#: so the summary describes the resampler this build actually ran.
PROBE_FREQUENCIES_HZ: tuple[int, ...] = (
    100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500, 7800,
    7900, 8000, 8100, 8200, 8500, 9000, 10000, 11000, 11900,
)
PROBE_TONE_SECONDS = 1.0
PROBE_TONE_AMPLITUDE = 0.5


class BuildError(RuntimeError):
    """An input drifted, a property failed, or a written byte did not reproduce."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def ids_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def load_roster() -> Mapping[str, Any]:
    path = REPO / ROSTER_RELPATH
    measured = sha256_file(path)
    if measured != ROSTER_SHA256:
        raise BuildError(
            f"frozen 400 roster identity drift: pinned {ROSTER_SHA256[:12]}..., "
            f"{path} now hashes to {measured[:12]}..."
        )
    receipt = json.loads(path.read_text(encoding="utf-8"))
    if str(receipt["split_name"]) != "A2T-CALIBRATION-400" or int(receipt["count"]) != 400:
        raise BuildError("the pinned Audio2Tool source is not the frozen 400 roster")
    return receipt


def load_dev_builder() -> Any:
    """The Earnings-22 dev builder module, pinned by content, for its tail rule."""

    path = REPO / DEV_BUILDER_RELPATH
    measured = sha256_file(path)
    if measured != DEV_BUILDER_SHA256:
        raise BuildError(
            "the pinned variant builder drifted: expected "
            f"{DEV_BUILDER_SHA256[:12]}..., {path} now hashes to {measured[:12]}.... "
            "This build reuses that file's transform, so a changed rule must be an "
            "explicit re-pin, never a silent inheritance."
        )
    spec = importlib.util.spec_from_file_location("e22_dev1500_media_variants", path)
    if spec is None or spec.loader is None:
        raise BuildError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.VARIANTS[TAIL_VARIANT]["suffix"] != "ts2":
        raise BuildError("the pinned builder's tail-silence-2s suffix is not 'ts2'")
    if module.TAIL_SILENCE_SAMPLES != int(TAIL_SILENCE_SECONDS * TARGET_SAMPLE_RATE_HZ):
        raise BuildError(
            "the pinned builder appends "
            f"{module.TAIL_SILENCE_SAMPLES} samples, which is not 2.0 s at "
            f"{TARGET_SAMPLE_RATE_HZ} Hz"
        )
    return module


def pin_decoder() -> dict[str, Any]:
    """Refuse unless the decoder that will run IS the pinned one.

    Three independent facts, all read from the running interpreter: the
    decoder's own source text, the resampler library versions, and the absence
    of ffmpeg (which ``decode_parent_pcm`` would prefer over librosa and which
    would therefore produce different bytes without changing a line of code).
    """

    import importlib.metadata as metadata  # noqa: PLC0415
    import librosa  # noqa: PLC0415

    source = inspect.getsource(decode_parent_pcm)
    measured = hashlib.sha256(source.encode("utf-8")).hexdigest()
    if measured != DECODER_SOURCE_SHA256:
        raise BuildError(
            f"{DECODER_QUALNAME} drifted: pinned {DECODER_SOURCE_SHA256[:12]}..., "
            f"its source now hashes to {measured[:12]}.... A resample is not a "
            "rearrangement of bytes; a changed decoder must be an explicit re-pin."
        )
    librosa_version = metadata.version("librosa")
    soxr_version = metadata.version("soxr")
    if librosa_version != PINNED_LIBROSA_VERSION:
        raise BuildError(
            f"librosa {librosa_version} is installed, this build pins "
            f"{PINNED_LIBROSA_VERSION}"
        )
    if soxr_version != PINNED_SOXR_VERSION:
        raise BuildError(
            f"soxr {soxr_version} is installed, this build pins {PINNED_SOXR_VERSION}"
        )
    res_type = inspect.signature(librosa.load).parameters["res_type"].default
    if res_type != PINNED_RES_TYPE:
        raise BuildError(
            f"librosa.load's default res_type is {res_type!r}, this build pins "
            f"{PINNED_RES_TYPE!r}; decode_parent_pcm does not pass res_type, so the "
            "default IS the filter that runs"
        )
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is not None:
        raise BuildError(
            f"ffmpeg is on PATH at {ffmpeg}. decode_parent_pcm prefers ffmpeg over "
            "librosa, so every byte this build produces would come from a different "
            "resampler than the pinned one. ffmpeg's absence is a pinned property of "
            "this program (docs: all buf90 slices were cut via the librosa fallback)."
        )
    return {
        "decoder": DECODER_QUALNAME,
        "decoder_source_sha256": measured,
        "resampler": f"librosa.load(res_type={PINNED_RES_TYPE!r}) -> soxr",
        "res_type": PINNED_RES_TYPE,
        "librosa_version": librosa_version,
        "soxr_version": soxr_version,
        "numpy_version": metadata.version("numpy"),
        "soundfile_version": metadata.version("soundfile"),
        "ffmpeg_on_path": False,
        "int16_quantization": "clip(rint(float32 * 32767.0), -32768, 32767)",
        "note": (
            "decode_parent_pcm is the study's ONE decode-and-resample path and is "
            "already the definition of 16 kHz mono int16 for every Earnings parent; "
            "this build calls it rather than writing a second resampler"
        ),
    }


# ---------------------------------------------------------------------------
# The two rules
# ---------------------------------------------------------------------------


def resample_to_target(path: Path) -> array:
    """The rule: one sealed 24 kHz wav as 16 kHz mono int16, pinned decoder."""

    return decode_parent_pcm(Path(path), TARGET_SAMPLE_RATE_HZ)


def expected_output_samples(n_input: int) -> int:
    """librosa's own output length for a rate change, stated rather than trusted.

    ``librosa.resample(..., fix=True)`` returns ``ceil(n * target / orig)``
    frames, which for 24 kHz -> 16 kHz is ``ceil(2n/3)``. Nothing is truncated:
    the last input sample is inside the last output frame's support.
    """

    return -((-n_input * TARGET_SAMPLE_RATE_HZ) // SOURCE_SAMPLE_RATE_HZ)


def append_tail(dev: Any, samples: array, sample_id: str) -> array:
    """The tail rule, through the PINNED Earnings-22 transform at 16 kHz."""

    produced = dev.transform(TAIL_VARIANT, samples, {"sample_id": sample_id}, None)
    if len(produced) != len(samples) + int(TAIL_SILENCE_SECONDS * TARGET_SAMPLE_RATE_HZ):
        raise BuildError(f"{sample_id}: the pinned tail is not exactly 2.0 s at 16 kHz")
    return produced


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------


def read_wav_header(path: Path) -> tuple[int, int]:
    """(sample_rate, n_frames) of a mono int16 wav. Asserted, never assumed."""

    with wave.open(str(path), "rb") as handle:
        if (handle.getnchannels(), handle.getsampwidth()) != (1, 2):
            raise BuildError(f"{path} is not mono int16")
        return handle.getframerate(), handle.getnframes()


def read_wav_samples(path: Path) -> array:
    with wave.open(str(path), "rb") as handle:
        payload = handle.readframes(handle.getnframes())
    return array("h", payload)


# ---------------------------------------------------------------------------
# The two variant descriptors -- the ONLY place a variant differs
# ---------------------------------------------------------------------------

VARIANTS: dict[str, dict[str, Any]] = {
    "16k": {
        "id_suffix": "16k",
        "variant": "input-rate-16k",
        "rule": RESAMPLE_RULE,
        "tail": False,
        "subdir": "derived/a2t-calibration-400-16k-v1",
        "roster_id": "A2T-CALIBRATION-400-16K-V1",
        "split_name": "A2T-CALIBRATION-400-16K",
        "roster_receipt": "docs/receipts/rosters/a2t-calibration-400-16k-v1.json",
        "supplement": "docs/receipts/artifacts/d1-a2t-calibration-400-16k.json",
        "out_dir": "2026-09-07-a2t-calibration-400-16k-media",
        "what_it_is_for": (
            "cell (a) of the input-rate standardization preregistration: the ONLY "
            "difference from the sealed official-protocol comparator is which "
            "resampler converted 24 kHz to 16 kHz -- librosa soxr_hq here, "
            "miniaudio's linear interpolator inside llama.cpp there"
        ),
    },
    "16k+ts2": {
        "id_suffix": "16k+ts2",
        "variant": "input-rate-16k+tail-silence-2s",
        "rule": f"{RESAMPLE_RULE}; then {TAIL_RULE}",
        "tail": True,
        "subdir": "derived/a2t-calibration-400-16k-tail2s-v1",
        "roster_id": "A2T-CALIBRATION-400-16K-TS2-V1",
        "split_name": "A2T-CALIBRATION-400-16K-TAIL2S",
        "roster_receipt": "docs/receipts/rosters/a2t-calibration-400-16k-ts2-v1.json",
        "supplement": "docs/receipts/artifacts/d1-a2t-calibration-400-16k-tail2s.json",
        "out_dir": "2026-09-07-a2t-calibration-400-16k-tail2s-media",
        "what_it_is_for": (
            "cell (b): the silence tail on STANDARDIZED bytes, which replaces the "
            "cross-carrier preregistration's 24 kHz-based @ts2 Audio2Tool cell if "
            "and only if cell (a) admits the standardization"
        ),
    },
}

COMPARATOR: dict[str, Any] = {
    "run_id": "SAEA-A2T-OFFICIAL-PROTOCOL-REPLICATION-V1",
    "attempt_id": "attempt-20260904T135250Z-rofficialraw",
    "cell_id": "R-official-raw",
    "split_identity_hash": (
        "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
    ),
    "flight_split_identity_hash": (
        "11091b38ae9d53530952af632636d7e79a614350213e10c6c26583c37f85846b"
    ),
    "paper_facing_scorer": "a2t-toolcall-official",
    "serving_path": "raw audio through the bf16 mmproj, -c 49152 -np 3",
    "what_the_comparator_sends": (
        "the sealed 24 kHz bytes verbatim (core/model/transport.py base64s the file "
        "and declares format 'wav'); the 24 -> 16 kHz conversion happens inside "
        "llama.cpp's miniaudio decoder, not in this study"
    ),
}

SPLIT_ROLE = "discovery"
SPLIT_ROLE_BASIS = (
    "The SAME frozen 400-row Audio2Tool discovery split (50 per tier over all eight "
    "tiers) the sealed official-protocol replication flew, re-encoded by one "
    "deterministic rule from the sealed WAV bytes. The split was already exposed by "
    "A0 and stays discovery. No evaluation query text, gold tool name, argument or "
    "tool registry row is opened here."
)


# ---------------------------------------------------------------------------
# Per-clip build
# ---------------------------------------------------------------------------


#: The band edges the clip's spectrum is split at, in one FFT pass. 8 kHz is the
#: output Nyquist -- energy above it is what a rate conversion must DISCARD and
#: what a poor low-pass folds back into the speech band. 6 and 7 kHz price the
#: OTHER difference between the two resamplers: miniaudio's 4th-order Butterworth
#: is already 1.3 dB down at 6 kHz and 2.1 dB down at 7 kHz, where soxr_hq is
#: flat, so a corpus with no energy up there cannot show either effect.
BAND_EDGES_HZ: tuple[int, ...] = (4000, 6000, 7000, 8000)


def band_energy_shares(samples: array, sample_rate_hz: int) -> dict[str, float]:
    """Share of the clip's spectral energy above each of :data:`BAND_EDGES_HZ`.

    Measured on the SEALED samples, once, in float64.
    """

    import numpy as np  # noqa: PLC0415

    zero = {f"source_energy_above_{edge // 1000}k_share": 0.0 for edge in BAND_EDGES_HZ}
    if not samples:
        return zero
    vector = np.frombuffer(array("h", samples).tobytes(), dtype="<i2").astype(np.float64)
    vector = vector - vector.mean()
    spectrum = np.fft.rfft(vector)
    power = (spectrum.real**2) + (spectrum.imag**2)
    total = float(power.sum())
    if total <= 0.0:
        return zero
    freqs = np.fft.rfftfreq(vector.size, d=1.0 / sample_rate_hz)
    return {
        f"source_energy_above_{edge // 1000}k_share": round(
            float(power[freqs > edge].sum() / total), 9
        )
        for edge in BAND_EDGES_HZ
    }


def build_one(
    dev: Any,
    item: Mapping[str, Any],
    variant: Mapping[str, Any],
    root: Path,
    *,
    write: bool,
) -> dict[str, Any]:
    """One clip: verify the sealed bytes, standardize, optionally tail, encode."""

    sample_id = str(item["sample_id"])
    tier = str(item["tier"])
    suffix = str(variant["id_suffix"])
    variant_id = f"{sample_id}@{suffix}"

    source_relpath = str(item["media_relpath"])
    source_path = root / source_relpath
    measured = sha256_file(source_path)
    if measured != str(item["audio_sha256"]):
        raise BuildError(
            f"source media drift on {sample_id}: the pinned receipt records "
            f"{str(item['audio_sha256'])[:12]}..., disk hashes to {measured[:12]}..."
        )
    rate, n_source = read_wav_header(source_path)
    if rate != SOURCE_SAMPLE_RATE_HZ:
        raise BuildError(
            f"{source_path} is {rate} Hz, this build pins the release's "
            f"{SOURCE_SAMPLE_RATE_HZ} Hz"
        )
    source_seconds = n_source / rate
    # The pinned receipt records durations to the millisecond, so the duration
    # check is stated at that resolution rather than pretending to an exactness
    # the receipt does not carry.
    if round(source_seconds, 3) != round(float(item["audio_seconds"]), 3):
        raise BuildError(
            f"{sample_id}: sealed clip is {source_seconds:.6f} s, the pinned receipt "
            f"records {float(item['audio_seconds']):.6f} s"
        )

    standardized = resample_to_target(source_path)
    expected = expected_output_samples(n_source)
    if len(standardized) != expected:
        raise BuildError(
            f"{sample_id}: the resampler returned {len(standardized)} samples, the "
            f"rate ratio requires exactly {expected}"
        )
    target_seconds = len(standardized) / TARGET_SAMPLE_RATE_HZ
    # "Within one sample" at the TARGET rate: the ceil above can add at most one
    # output frame, and nothing may ever be dropped.
    if not -1e-12 <= (target_seconds - source_seconds) < 1.0 / TARGET_SAMPLE_RATE_HZ:
        raise BuildError(
            f"{sample_id}: standardized duration {target_seconds:.9f} s is not the "
            f"sealed {source_seconds:.9f} s within one 16 kHz sample"
        )
    # Determinism is checked rather than assumed: the same file through the same
    # pinned decoder twice, and the samples must agree.
    if resample_to_target(source_path) != standardized:
        raise BuildError(f"{sample_id}: the pinned decoder is not deterministic")

    produced = append_tail(dev, standardized, variant_id) if variant["tail"] else standardized
    if produced[: len(standardized)] != standardized:
        raise BuildError(f"{sample_id}: the standardized samples were altered")
    if variant["tail"] and any(produced[len(standardized) :]):
        raise BuildError(f"{sample_id}: the tail is not digital silence")

    payload = write_wav_bytes(produced, TARGET_SAMPLE_RATE_HZ)
    if write_wav_bytes(produced, TARGET_SAMPLE_RATE_HZ) != payload:
        raise BuildError(f"{sample_id}: the encoder is not deterministic")

    relpath = "/".join(
        [str(variant["subdir"]), tier, f"{sample_id.replace(':', '_')}@{suffix}.wav"]
    )
    target = root / relpath
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        if sha256_file(target) != hashlib.sha256(payload).hexdigest():
            raise BuildError(f"{variant_id}: written bytes do not match the payload")

    sealed_samples = read_wav_samples(source_path)
    margins = energy_margins(sealed_samples, rate)
    peak_source = max((abs(value) for value in sealed_samples), default=0)
    peak_standardized = max((abs(value) for value in standardized), default=0)
    clipped = sum(1 for value in standardized if value in (-32768, 32767))
    source_clipped = sum(1 for value in sealed_samples if value in (-32768, 32767))
    entry: dict[str, Any] = {
        "sample_id": variant_id,
        "source_sample_id": sample_id,
        "stratum": tier,
        "tier": tier,
        "source_key": str(item["key"]),
        "source_media_relpath": source_relpath,
        "source_audio_sha256": measured,
        "source_sample_rate_hz": rate,
        "source_n_samples": n_source,
        "source_audio_seconds": round(source_seconds, 9),
        "media_relpath": relpath,
        "audio_sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
        "n_samples": len(produced),
        "audio_seconds": round(len(produced) / TARGET_SAMPLE_RATE_HZ, 9),
        "standardized_n_samples": len(standardized),
        "standardized_audio_seconds": round(target_seconds, 9),
        "duration_delta_seconds": round(target_seconds - source_seconds, 9),
        "samples_added_by_tail": len(produced) - len(standardized),
        "samples_removed": 0,
        # What the rate conversion has to throw away, and what it did to the peak.
        "source_peak_abs": peak_source,
        "source_clipped_samples": source_clipped,
        "standardized_peak_abs": peak_standardized,
        "standardized_clipped_samples": clipped,
        # Carried forward from the @ts2 build so the two preparations describe the
        # same population in the same terms.
        "source_trailing_silence_seconds": round(margins.trailing_seconds, 6),
        "source_leading_silence_seconds": round(margins.leading_seconds, 6),
        "source_peak_dbfs": round(margins.peak_dbfs, 4),
        "source_active_share": round(margins.active_share, 6),
    }
    entry.update(band_energy_shares(sealed_samples, rate))
    return entry


# ---------------------------------------------------------------------------
# The resampler's frequency response, measured on the path that actually ran
# ---------------------------------------------------------------------------


def frequency_response() -> dict[str, Any]:
    """Push pure tones through the PINNED decode path and report what survives.

    Cheap and deterministic: one second per probe frequency, synthesized at
    24 kHz, written as a mono int16 wav and read back through
    ``decode_parent_pcm``. For each tone the output's energy is split into the
    bin at the tone's own frequency and everything else -- so a resampler that
    folds an 11 kHz tone down to 5 kHz shows up as ALIAS, not as attenuation.
    """

    import numpy as np  # noqa: PLC0415

    n_in = int(PROBE_TONE_SECONDS * SOURCE_SAMPLE_RATE_HZ)
    times = np.arange(n_in) / float(SOURCE_SAMPLE_RATE_HZ)
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory() as tmp:
        probe_path = Path(tmp) / "tone.wav"
        for freq in PROBE_FREQUENCIES_HZ:
            tone = PROBE_TONE_AMPLITUDE * np.sin(2.0 * np.pi * freq * times)
            pcm = np.clip(np.rint(tone * 32767.0), -32768, 32767).astype("<i2")
            probe_path.write_bytes(write_wav_bytes(array("h", pcm.tolist()), SOURCE_SAMPLE_RATE_HZ))
            out = decode_parent_pcm(probe_path, TARGET_SAMPLE_RATE_HZ)
            vector = np.frombuffer(array("h", out).tobytes(), dtype="<i2").astype(np.float64)
            # Drop 50 ms of edge on each side: the ceil() output frame and the
            # filter's own transient are not part of its steady-state response.
            edge = int(0.05 * TARGET_SAMPLE_RATE_HZ)
            vector = vector[edge:-edge] if vector.size > 2 * edge else vector
            vector = vector - vector.mean()
            spectrum = np.fft.rfft(vector)
            power = (spectrum.real**2) + (spectrum.imag**2)
            freqs = np.fft.rfftfreq(vector.size, d=1.0 / TARGET_SAMPLE_RATE_HZ)
            total = float(power.sum())
            in_band = float(power[np.abs(freqs - freq) <= 25.0].sum()) if freq < 8000 else 0.0
            alias = total - in_band
            reference = float(
                np.sum((PROBE_TONE_AMPLITUDE * 32767.0 / 2.0) ** 2)
                * vector.size
                * vector.size
                / 2.0
            )
            rows.append(
                {
                    "frequency_hz": freq,
                    "passband": freq < 8000,
                    "retained_share": round(in_band / total, 9) if total > 0 else 0.0,
                    "alias_share": round(alias / total, 9) if total > 0 else 0.0,
                    "output_rms": round(float(np.sqrt(np.mean(vector**2))), 6),
                    "output_rms_dbfs": round(
                        20.0 * np.log10(max(float(np.sqrt(np.mean(vector**2))), 1e-12) / 32767.0),
                        4,
                    ),
                    "reference_rms_dbfs": round(
                        20.0 * np.log10(PROBE_TONE_AMPLITUDE / np.sqrt(2.0)), 4
                    ),
                }
            )
            del reference
    passband = [row for row in rows if row["passband"]]
    stopband = [row for row in rows if not row["passband"]]
    return {
        "measured_on": (
            f"{DECODER_QUALNAME} (librosa {PINNED_LIBROSA_VERSION} / soxr "
            f"{PINNED_SOXR_VERSION}, res_type {PINNED_RES_TYPE!r}), "
            f"{SOURCE_SAMPLE_RATE_HZ} -> {TARGET_SAMPLE_RATE_HZ} Hz"
        ),
        "method": (
            f"one {PROBE_TONE_SECONDS:.1f} s pure tone per frequency at amplitude "
            f"{PROBE_TONE_AMPLITUDE}, synthesized at {SOURCE_SAMPLE_RATE_HZ} Hz, "
            "written as mono int16 wav, decoded through the pinned path, 50 ms of "
            "each edge dropped, energy split into a +/-25 Hz bin at the tone and "
            "everything else (= alias + noise)"
        ),
        "output_nyquist_hz": TARGET_SAMPLE_RATE_HZ // 2,
        "passband_min_retained_share": round(
            min((row["retained_share"] for row in passband), default=0.0), 9
        ),
        "passband_max_rms_dbfs_deviation": round(
            max(
                (abs(row["output_rms_dbfs"] - row["reference_rms_dbfs"]) for row in passband),
                default=0.0,
            ),
            4,
        ),
        "stopband_max_output_rms_dbfs": round(
            max((row["output_rms_dbfs"] for row in stopband), default=-999.0), 4
        ),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Views and receipts
# ---------------------------------------------------------------------------


def _summary(entries: Sequence[Mapping[str, Any]], key: str) -> dict[str, Any]:
    values = sorted(float(entry[key]) for entry in entries)
    n = len(values)

    def pct(fraction: float) -> float:
        return values[min(n - 1, int(fraction * (n - 1)))]

    return {
        "n": n,
        "min": round(values[0], 9),
        "p10": round(pct(0.10), 9),
        "median": round(pct(0.50), 9),
        "p90": round(pct(0.90), 9),
        "max": round(values[-1], 9),
        "mean": round(sum(values) / n, 9),
    }


def probe_view(
    variant: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    ids = [str(entry["sample_id"]) for entry in entries]
    if ids != sorted(ids):
        raise BuildError("the variant items are not in sample-id order")
    strata = sorted({str(entry["stratum"]) for entry in entries})
    view: dict[str, Any] = {
        "schema": PROBE_VIEW_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": "audio2tool",
        "split_name": str(variant["split_name"]),
        "split_role": SPLIT_ROLE,
        "split_role_basis": SPLIT_ROLE_BASIS,
        "variant": str(variant["variant"]),
        "rule": str(variant["rule"]),
        "what_it_is_for": str(variant["what_it_is_for"]),
        "id_rule": (
            f"<sealed id>@{variant['id_suffix']}; the sealed key is recovered by "
            "splitting on the FIRST '@' (reproduction.esb_reference."
            "published_segment_key), so the paired join against the sealed "
            "comparator is exact and no id collides with the comparator "
            "population's"
        ),
        "container": "wav",
        "source_sample_rate_hz": SOURCE_SAMPLE_RATE_HZ,
        "sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
        "tail_silence_seconds": TAIL_SILENCE_SECONDS if variant["tail"] else 0.0,
        "tail_silence_samples": (
            int(TAIL_SILENCE_SECONDS * TARGET_SAMPLE_RATE_HZ) if variant["tail"] else 0
        ),
        "comparator": dict(COMPARATOR),
        "derived_from": {
            "roster_receipt": {"path": ROSTER_RELPATH, "sha256": ROSTER_SHA256}
        },
        "count": len(entries),
        "audio_seconds_total": round(
            sum(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_seconds_longest_item": round(
            max(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "audio_seconds_shortest_item": round(
            min(float(entry["audio_seconds"]) for entry in entries), 6
        ),
        "source_audio_seconds_total": round(
            sum(float(entry["source_audio_seconds"]) for entry in entries), 6
        ),
        "per_stratum": {
            stratum: {
                "count": sum(1 for entry in entries if str(entry["stratum"]) == stratum),
                "audio_seconds": round(
                    sum(
                        float(entry["audio_seconds"])
                        for entry in entries
                        if str(entry["stratum"]) == stratum
                    ),
                    6,
                ),
            }
            for stratum in strata
        },
        "source_band_energy": {
            f"above_{edge // 1000}k_share": _summary(
                entries, f"source_energy_above_{edge // 1000}k_share"
            )
            for edge in BAND_EDGES_HZ
        },
        "duration_delta_seconds": _summary(entries, "duration_delta_seconds"),
        "ids_sha256": ids_sha256(ids),
        "items": list(entries),
    }
    view["items_sha256"] = canonical_sha256(list(entries))
    return view


def supplement(
    entries: Sequence[Mapping[str, Any]], *, view_sha256: str
) -> dict[str, Any]:
    manifest = [
        {
            "id": str(entry["sample_id"]),
            "media_relpath": str(entry["media_relpath"]),
            "sha256": str(entry["audio_sha256"]),
            "bytes": int(entry["bytes"]),
            "audio_seconds": round(float(entry["audio_seconds"]), 6),
            "sample_rate_hz": int(entry["sample_rate_hz"]),
            "roles": ["query"],
        }
        for entry in entries
    ]
    return {
        "schema": SUPPLEMENT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": "audio2tool",
        "parent_d1_sha256": sha256_file(REPO / "docs/receipts/artifacts/d1-identity.json"),
        "source_binding_sha256": view_sha256,
        "count": len(manifest),
        "ids_sha256": ids_sha256([str(row["id"]) for row in manifest]),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(row["bytes"]) for row in manifest),
    }


def union_rebuild_price(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """What it costs to standardize the ORG-1 union 4,000 the same way.

    An admitted 16 kHz standardization re-locks the Audio2Tool comparator, and
    every later Audio2Tool cell that pairs against the sealed official-protocol
    populations has to fly on standardized media too. The union roster is 4,000
    rows and 23,418.083083 audio seconds
    (``configs/dataset/audio2tool-org1-union-4000.json``), so the price is
    scaled from THIS build's own measured population rather than guessed.

    **Wall time is deliberately not in here.** It is not reproducible, and this
    receipt promises that two back-to-back writes produce the same
    ``MANIFEST.sha256``. The runner prints the measured wall; the
    preregistration quotes it as an observation, not as a sealed figure.
    """

    measured_seconds = sum(float(entry["source_audio_seconds"]) for entry in entries)
    measured_bytes = sum(int(entry["bytes"]) for entry in entries)
    union_seconds = 23418.083083
    union_rows = 4000
    scale = union_seconds / measured_seconds if measured_seconds else 0.0
    return {
        "why": (
            "an admitted 16 kHz media re-locks the A2T frozen-400 comparator, and no "
            "further Audio2Tool cell can mix standardized and unstandardized media -- "
            "so the ORG-1 union 4,000, which every sealed official-population pairing "
            "runs on, must be rebuilt by this same rule before it is used again"
        ),
        "population": "A2T-ORG1-UNION-4000 (configs/dataset/audio2tool-org1-union-4000.json)",
        "rows": union_rows,
        "source_audio_seconds": union_seconds,
        "measured_basis": {
            "rows": len(entries),
            "source_audio_seconds": round(measured_seconds, 6),
            "output_bytes": measured_bytes,
            "scale": round(scale, 9),
            "wall_time": (
                "NOT SEALED HERE -- wall time is not reproducible and this receipt is. "
                "The runner prints it."
            ),
        },
        "projected_output_bytes": int(round(measured_bytes * scale)),
        "projected_output_gib": round(measured_bytes * scale / (1024.0**3), 4),
        "contacts": {
            "frozen_core": 0,
            "gpu_hours": 0.0,
            "note": (
                "the rebuild is model-free: it is a decode and a re-encode, at most 8 "
                "CPU workers, and it opens no text of any kind. What it is NOT free of "
                "is the D1 supplement and roster work -- the union's supplement covers "
                "3,932 ids and would need a standardized twin -- and the sealed "
                "official-population outputs it pairs against were produced on "
                "UNSTANDARDIZED media, so those pairings become cross-media and stop "
                "being single-factor"
            ),
        },
        "the_real_cost": (
            "not the CPU minutes. Re-standardizing the union invalidates the paired "
            "comparator: the 4,000 sealed official-protocol outputs were produced from "
            "24 kHz bytes, so after a rebuild every one of them would have to be "
            "RE-FLOWN to stay a like-for-like baseline -- 4,000 contacts and roughly "
            "23,418 audio seconds of GPU work, which is the price this preregistration "
            "puts on cell (a) admitting"
        ),
    }


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------


def build(
    name: str,
    *,
    write: bool,
    workers: int,
    attempts_count: int,
    response: Mapping[str, Any],
    pins: Mapping[str, Any],
) -> dict[str, Any]:
    import time  # noqa: PLC0415

    variant = VARIANTS[name]
    dev = load_dev_builder()
    roster = load_roster()
    root = Path(data_root())

    def one(item: Mapping[str, Any]) -> dict[str, Any]:
        return build_one(dev, item, variant, root, write=write)

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        entries = list(pool.map(one, roster["items"]))
    wall_seconds = time.monotonic() - started
    entries.sort(key=lambda entry: str(entry["sample_id"]))

    per_stratum = {
        stratum: sum(1 for entry in entries if str(entry["stratum"]) == stratum)
        for stratum in {str(entry["stratum"]) for entry in entries}
    }
    receipt = freeze_roster(
        carrier_lock_key="audio2tool",
        candidates=[
            RosterItem(
                sample_id=str(entry["sample_id"]),
                stratum=str(entry["stratum"]),
                extra={
                    "audio_seconds": float(entry["audio_seconds"]),
                    "media_relpath": str(entry["media_relpath"]),
                },
            )
            for entry in entries
        ],
        per_stratum=per_stratum,
        seed=FREEZE_SEED,
        split_role=SPLIT_ROLE,
        roster_id=str(variant["roster_id"]),
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    if len(receipt["items"]) != len(entries):
        raise BuildError("freezing the variant roster dropped rows")

    view = probe_view(variant, entries)
    view_bytes = (
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    view_sha256 = hashlib.sha256(view_bytes).hexdigest()
    media = supplement(entries, view_sha256=view_sha256)
    media_bytes = (
        json.dumps(media, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    out_dir = REPO / "docs/checks/speech-aware-evidence-acquisition" / str(variant["out_dir"])
    build_receipt: dict[str, Any] = {
        "schema": BUILD_RECEIPT_SCHEMA,
        "carrier": "audio2tool",
        "carrier_lock_key": "audio2tool",
        "exposure_row": "SAEA-SN-MF-A2T-CAL400-16K-MEDIA-V1",
        "execution_profile": "model-free-check",
        "variant": str(variant["variant"]),
        "rule": str(variant["rule"]),
        "what_it_is_for": str(variant["what_it_is_for"]),
        "id_suffix": str(variant["id_suffix"]),
        "container": "wav",
        "source_sample_rate_hz": SOURCE_SAMPLE_RATE_HZ,
        "sample_rate_hz": TARGET_SAMPLE_RATE_HZ,
        "media_root": str(variant["subdir"]),
        "roster_id": str(variant["roster_id"]),
        "split_name": str(variant["split_name"]),
        "split_role": SPLIT_ROLE,
        "split_identity_hash": receipt["split_identity_hash"],
        "comparator": dict(COMPARATOR),
        "decoder_pins": dict(pins),
        "tail_rule_implementation": (
            {
                "module": DEV_BUILDER_RELPATH,
                "sha256": DEV_BUILDER_SHA256,
                "function": f"transform({TAIL_VARIANT!r}, ...)",
                "note": (
                    "called DIRECTLY, not re-derived: the pinned transform's hard-coded "
                    "2 * 16000 samples IS 2.0 s on standardized media, which is the "
                    "whole point of standardizing first"
                ),
            }
            if variant["tail"]
            else None
        ),
        "count": len(entries),
        "strata_counts": receipt["strata_counts"],
        "deterministic": (
            "this receipt carries no timestamp: two back-to-back writes reproduce the "
            "same MANIFEST.sha256"
        ),
        "measured_media": {
            "audio_seconds_total": view["audio_seconds_total"],
            "audio_hours_total": round(view["audio_seconds_total"] / 3600.0, 6),
            "audio_seconds_longest_item": view["audio_seconds_longest_item"],
            "audio_seconds_shortest_item": view["audio_seconds_shortest_item"],
            "source_audio_seconds_total": view["source_audio_seconds_total"],
            "total_bytes": media["total_bytes"],
            "n_samples_total": sum(int(entry["n_samples"]) for entry in entries),
            "source_n_samples_total": sum(int(entry["source_n_samples"]) for entry in entries),
            "samples_added_by_tail_total": sum(
                int(entry["samples_added_by_tail"]) for entry in entries
            ),
            "samples_removed_total": 0,
            "clips_left_unchanged": 0,
            "max_abs_duration_delta_seconds": round(
                max(abs(float(entry["duration_delta_seconds"])) for entry in entries), 9
            ),
            "one_sample_at_16k_seconds": round(1.0 / TARGET_SAMPLE_RATE_HZ, 9),
            "clips_with_a_clipped_standardized_sample": sum(
                1 for entry in entries if int(entry["standardized_clipped_samples"]) > 0
            ),
            "standardized_clipped_samples_total": sum(
                int(entry["standardized_clipped_samples"]) for entry in entries
            ),
        },
        "source_band_energy": view["source_band_energy"],
        "source_band_energy_note": (
            "the mechanism budget, measured on the SEALED 24 kHz samples. Energy "
            "above 8 kHz is what a rate conversion must discard and what miniaudio's "
            "4th-order Butterworth folds back into the speech band; energy above 6 "
            "and 7 kHz is where that same filter's passband droop (-1.3 dB and "
            "-2.1 dB, measured) differs from soxr_hq's flat response. A corpus with "
            "no energy in those bands cannot show either effect, whatever the "
            "resamplers do."
        ),
        "clips_above_share": {
            f"above_{edge // 1000}k_more_than_{threshold}": sum(
                1
                for entry in entries
                if float(entry[f"source_energy_above_{edge // 1000}k_share"]) > threshold
            )
            for edge in BAND_EDGES_HZ
            for threshold in (0.001, 0.01)
        },
        "resampler_frequency_response": dict(response),
        "union_rebuild_price": union_rebuild_price(entries),
        "source_population": {
            "roster_receipt": {"path": ROSTER_RELPATH, "sha256": ROSTER_SHA256},
            "files_rehashed_before_reading": len(entries),
            "all_source_digests_matched": True,
            "all_sources_measured_24k_mono_int16": True,
        },
        "outputs": {
            "roster_receipt": str(variant["roster_receipt"]),
            "roster_receipt_sha256": hashlib.sha256(
                canonical_receipt_bytes(receipt)
            ).hexdigest(),
            "probe_view": (out_dir / "roster" / "flight-roster-receipt.json")
            .relative_to(REPO)
            .as_posix(),
            "probe_view_sha256": view_sha256,
            "d1_media_supplement": str(variant["supplement"]),
            "d1_media_supplement_sha256": hashlib.sha256(media_bytes).hexdigest(),
        },
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
            "parent_container_decodes": 0,
            "sealed_wav_decodes": len(entries),
            "librosa_calls": 2 * len(entries) + len(PROBE_FREQUENCIES_HZ),
            "ffmpeg_calls": 0,
            "outbound_connection_attempts": attempts_count,
            "note": (
                "unlike the @ts2 build, this one RUNS librosa -- that is the factor "
                "under test. Each clip is decoded twice (the determinism check) and "
                "the frequency-response probe decodes one synthetic tone per "
                "frequency. No parent container is opened: the input is the sealed wav "
                "the comparator itself sends."
            ),
        },
        "opened": {
            "gold_labels": 0,
            "reference_transcripts": 0,
            "evaluation_query_text": 0,
            "tool_registry_rows": 0,
            "sealed_outputs": 0,
            "hypothesis_text": 0,
            "scores": 0,
            "note": (
                "MEDIA BYTES ONLY. The build reads the pinned roster receipt "
                "(identifiers, media paths, measured media identity) and the audio "
                "samples of the sealed files it names. No gold tool name, argument, "
                "evaluation query, tool-registry row, sealed output, hypothesis or "
                "score is opened, and none is reachable from this process."
            ),
        },
        "test_split_read": False,
        "authorizes": (
            "nothing beyond writing this media and these receipts. No cell is flown, "
            "no request is built, no server is started and no scorer runs."
        ),
    }

    if write:
        (REPO / str(variant["roster_receipt"])).parent.mkdir(parents=True, exist_ok=True)
        write_roster(receipt, REPO / str(variant["roster_receipt"]))
        (out_dir / "roster").mkdir(parents=True, exist_ok=True)
        (out_dir / "roster" / "flight-roster-receipt.json").write_bytes(view_bytes)
        (REPO / str(variant["supplement"])).parent.mkdir(parents=True, exist_ok=True)
        (REPO / str(variant["supplement"])).write_bytes(media_bytes)
        write_json_artifact(out_dir / "build-receipt.json", build_receipt)
        write_manifest(out_dir)
        write_manifest(out_dir / "roster")
    # Returned for the runner to print, never written: wall time is not
    # reproducible and every receipt this build lands is.
    return {**build_receipt, "wall_seconds_not_sealed": round(wall_seconds, 3)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--variant",
        choices=[*VARIANTS, "all"],
        required=True,
        help="which input-rate standardized media to build",
    )
    parser.add_argument("--write", action="store_true", help="write media and receipts")
    parser.add_argument(
        "--workers", type=int, default=8, help="CPU workers (campaign cap is 8)"
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("workers must be between 1 and 8 (the campaign cap)")

    attempts = arm_offline_guard()
    pins = pin_decoder()
    response = frequency_response()
    print(
        "resampler: %s, passband keeps >= %.6f of a tone's energy, stopband tops out "
        "at %.2f dBFS"
        % (
            pins["resampler"],
            response["passband_min_retained_share"],
            response["stopband_max_output_rms_dbfs"],
        )
    )
    names = list(VARIANTS) if args.variant == "all" else [args.variant]
    for name in names:
        receipt = build(
            name,
            write=args.write,
            workers=args.workers,
            attempts_count=attempts.count,
            response=response,
            pins=pins,
        )
        media = receipt["measured_media"]
        band = receipt["source_band_energy"]["above_8k_share"]
        print(
            "%s: %d clips, %.3f s (%.4f h) from a sealed %.3f s, identity %s"
            % (
                receipt["variant"],
                receipt["count"],
                media["audio_seconds_total"],
                media["audio_hours_total"],
                media["source_audio_seconds_total"],
                receipt["split_identity_hash"],
            )
        )
        print(
            "  %d bytes on disk, %d strata, max |duration delta| %.9f s (one 16 kHz "
            "sample is %.9f s), %d clips clipped"
            % (
                media["total_bytes"],
                len(receipt["strata_counts"]),
                media["max_abs_duration_delta_seconds"],
                media["one_sample_at_16k_seconds"],
                media["clips_with_a_clipped_standardized_sample"],
            )
        )
        print(
            "  sealed energy above 8 kHz: median %.9f, mean %.9f, max %.9f; %d clips "
            "above 1 %%, %d above 0.1 %%"
            % (
                band["median"],
                band["mean"],
                band["max"],
                receipt["clips_above_share"]["above_8k_more_than_0.01"],
                receipt["clips_above_share"]["above_8k_more_than_0.001"],
            )
        )
        seven = receipt["source_band_energy"]["above_7k_share"]
        print(
            "  sealed energy above 7 kHz: median %.9f, mean %.9f, max %.9f"
            % (seven["median"], seven["mean"], seven["max"])
        )
        price = receipt["union_rebuild_price"]
        wall = float(receipt["wall_seconds_not_sealed"])
        print(
            "  %.1f s of wall for %.3f source seconds at %d workers (NOT sealed in the "
            "receipt); union 4,000 rebuild projects to %.2f CPU-min and %.4f GiB"
            % (
                wall,
                price["measured_basis"]["source_audio_seconds"],
                args.workers,
                wall * float(price["measured_basis"]["scale"]) / 60.0,
                price["projected_output_gib"],
            )
        )
    if not args.write:
        print("(print only; pass --write to land the media and the receipts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
