#!/usr/bin/env python3
"""Build the ``tail-silence-2s`` (``@ts2``) media variant of the three
cross-carrier silence-tail rosters (model-free, CPU only).

Exposure rows, one per carrier, each registered before the first byte of that
carrier is written:

===============  =========================================================
carrier          row
===============  =========================================================
``slurp``        ``SAEA-SN-MF-SLURP-DEV1000-TS2-MEDIA-V1``
``audio2tool``   ``SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1``
``earnings21``   ``SAEA-SN-MF-E21-BUF90-TS2-MEDIA-V1``
===============  =========================================================

Why one script and not three
----------------------------
The rule is the same rule on all three carriers -- exactly 2.0 SECONDS of
digital silence appended, nothing removed, nothing re-decoded from a parent
container the sealed comparator did not already decode. The Earnings-22
dev1500 builder is still the one definition of it: that file is imported and
pinned by SHA-256 below, and this build's own seconds-based ``append_tail`` is
PROVED byte-identical to its ``transform('tail-silence-2s', ...)`` on synthetic
samples before any carrier is touched. The proof is needed because the pinned
transform hard-codes ``2 * 16000`` samples, which is 2.0 s only at 16 kHz --
SLURP's FLAC and Earnings-21's slices are 16 kHz, but every Audio2Tool release
wav is **24 kHz** mono, where that same integer would append 1.333 s and
quietly change the factor under test.

What differs per carrier is only the population's own identity: which sealed
receipt is pinned, which container and rate the sealed bytes carry, which
derived root the variant lands in, and which receipts it lands beside. Those
differences live in ``CARRIERS`` and nowhere else.

What is READ, and what is never opened
--------------------------------------
**Media bytes only.** Per carrier the inputs are one or two committed,
hash-pinned receipts (identifiers, media paths, measured media identity) and
the sealed audio files those receipts name, each re-hashed against its record
before it is read. **No gold label, no reference transcript, no evaluation
query text, no tool name, no sealed output, no hypothesis and no score is
opened**, and each build receipt records those as zero. No parent container is
re-decoded that the sealed comparator did not itself send: SLURP reads the
sealed FLAC, Audio2Tool the sealed WAV, Earnings-21 the sealed 90-second
window slices the direct baseline itself wrote. ``librosa`` never runs and the
pinned absence of ``ffmpeg`` is preserved.

Building the media is not a model contact and is not a flight. Each carrier's
cell needs its own preregistration, its own owner GO and its own exposure row;
SLURP additionally needs a packet promotion, whose plan this build emits but
does not execute.

Usage (WSL2)::

    python scripts/build_cross_carrier_tail2s_media.py --carrier slurp
    python scripts/build_cross_carrier_tail2s_media.py --carrier all --write
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import sys
import wave
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e21_window_pairing import (  # noqa: E402
    window_id,
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

#: The tail is 2.0 SECONDS, and the sample count follows the file's own rate.
#: The pinned Earnings-22 transform hard-codes ``2 * 16000`` because every
#: Earnings clip is 16 kHz; Audio2Tool's release wavs are 24 kHz mono, so
#: reusing that integer there would append 1.333 s and quietly change the
#: factor under test. ``append_tail`` below is therefore written in seconds and
#: is PROVED byte-identical to the pinned transform at 16 kHz before any
#: carrier is built.
TAIL_SILENCE_SECONDS = 2.0
REFERENCE_SAMPLE_RATE_HZ = 16000
VARIANT = "tail-silence-2s"
ID_SUFFIX = "ts2"
SUPPLEMENT_SCHEMA = "saea-d1-media-supplement-v1"
BUILD_RECEIPT_SCHEMA = "saea-cross-carrier-ts2-media-build-receipt-v1"
PROBE_VIEW_SCHEMA = "saea-cross-carrier-ts2-probe-view-v1"
SPEECH_NATIVE_VIEW_SCHEMA = "saea-speech-native-runtime-view-v1"

#: Freezing an ALREADY complete population, not drawing from it: every
#: stratum's quota equals that stratum's own candidate count, so the seed
#: cannot change the membership. Recorded for reproducibility only.
FREEZE_SEED = 20260907

#: The Earnings-22 dev1500 builder is the ONE implementation of the rule. It is
#: pinned by content: if that file changes, this build refuses rather than
#: quietly producing bytes some other rule wrote.
DEV_BUILDER_RELPATH = "scripts/build_e22_dev1500_media_variants.py"
DEV_BUILDER_SHA256 = "49e5d91095c061d167688bd4dea35fc7503d3a09caa3066db68fde9807d196e6"

RULE = (
    "exactly 2.0 s of digital silence appended to the sealed clip -- "
    "2.0 x the file's OWN sample rate in zero samples; nothing is removed, no "
    "sealed sample is altered, the sample rate is never changed and no parent "
    "container is re-decoded that the sealed comparator did not itself send"
)


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


def load_pinned(relpath: str, expected: str, label: str) -> Mapping[str, Any]:
    path = REPO / relpath
    measured = sha256_file(path)
    if measured != expected:
        raise BuildError(
            f"{label} identity drift: pinned {expected[:12]}..., {path} now hashes "
            f"to {measured[:12]}..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def load_dev_builder() -> Any:
    """The Earnings-22 dev builder module, pinned by content, for its rule."""

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
    if module.VARIANTS[VARIANT]["suffix"] != ID_SUFFIX:
        raise BuildError("the pinned builder's tail-silence-2s suffix is not 'ts2'")
    if module.TAIL_SILENCE_SAMPLES != int(
        TAIL_SILENCE_SECONDS * REFERENCE_SAMPLE_RATE_HZ
    ):
        raise BuildError("the pinned builder's tail length is not 2.0 s at 16 kHz")
    assert_rule_equivalence(module)
    return module


def append_tail(samples: array, sample_rate_hz: int) -> array:
    """The rule, in seconds: 2.0 s of digital silence after the sealed samples."""

    if (
        isinstance(sample_rate_hz, bool)
        or not isinstance(sample_rate_hz, int)
        or sample_rate_hz <= 0
    ):
        raise BuildError(f"sample_rate_hz must be a positive integer, got {sample_rate_hz!r}")
    tail = int(TAIL_SILENCE_SECONDS * sample_rate_hz)
    return samples + array("h", bytes(2 * tail))


def assert_rule_equivalence(dev: Any) -> None:
    """Prove, not assert, that ``append_tail`` IS the pinned rule at 16 kHz.

    The pinned Earnings-22 transform is the one implementation of
    ``tail-silence-2s``. This build cannot call it on a 24 kHz carrier without
    changing the tail's duration, so it carries its own seconds-based rule --
    and then shows on synthetic bytes that the two produce identical output at
    the rate where both are defined. A divergence stops the build.
    """

    probe = array("h", [0, 1, -1, 32767, -32768, 7, -7])
    pinned = dev.transform(VARIANT, probe, {"sample_id": "equivalence-probe"}, None)
    local = append_tail(probe, REFERENCE_SAMPLE_RATE_HZ)
    if pinned != local:
        raise BuildError(
            "the seconds-based tail rule does not reproduce the pinned 16 kHz "
            "transform; the rule has drifted and this build refuses"
        )


# ---------------------------------------------------------------------------
# Containers: read the sealed bytes, write the variant in the SAME container
# ---------------------------------------------------------------------------


def read_wav(path: Path, sample_rate_hz: int) -> array:
    """The sealed clip's int16 samples. Mono/int16/rate are asserted, not assumed."""

    with wave.open(str(path), "rb") as handle:
        if (handle.getframerate(), handle.getnchannels(), handle.getsampwidth()) != (
            sample_rate_hz,
            1,
            2,
        ):
            raise BuildError(f"{path} is not {sample_rate_hz} Hz mono int16")
        payload = handle.readframes(handle.getnframes())
    return array("h", payload)


def read_flac(path: Path, sample_rate_hz: int) -> array:
    """The sealed FLAC's int16 samples. FLAC is lossless, so this is exact."""

    import soundfile as sf  # noqa: PLC0415 (soundfile stays a function-local import)

    info = sf.info(str(path))
    if (info.samplerate, info.channels, info.subtype, info.format) != (
        sample_rate_hz,
        1,
        "PCM_16",
        "FLAC",
    ):
        raise BuildError(
            f"{path} is not {sample_rate_hz} Hz mono PCM_16 FLAC "
            f"({info.samplerate}/{info.channels}/{info.subtype}/{info.format})"
        )
    data, rate = sf.read(str(path), dtype="int16", always_2d=False)
    if rate != sample_rate_hz or data.ndim != 1:
        raise BuildError(f"{path} did not decode to a mono int16 vector at {rate} Hz")
    return array("h", data.tobytes())


def write_flac_bytes(samples: Sequence[int], sample_rate_hz: int) -> bytes:
    """Encode int16 samples as 16 kHz mono PCM_16 FLAC, and prove it is lossless.

    FLAC is a lossless codec, but "lossless" is a property of the encoder that
    actually ran, so the encoded bytes are decoded back here and compared
    sample for sample before they are ever returned.
    """

    import numpy as np  # noqa: PLC4515,PLC0415
    import soundfile as sf  # noqa: PLC0415

    buffer = io.BytesIO()
    sf.write(
        buffer,
        np.frombuffer(array("h", samples).tobytes(), dtype="<i2"),
        sample_rate_hz,
        format="FLAC",
        subtype="PCM_16",
    )
    payload = buffer.getvalue()
    decoded, rate = sf.read(io.BytesIO(payload), dtype="int16", always_2d=False)
    if rate != sample_rate_hz:
        raise BuildError("the FLAC round trip changed the sample rate")
    if array("h", decoded.tobytes()) != array("h", samples):
        raise BuildError("the FLAC round trip is not lossless")
    return payload


CONTAINERS: dict[str, dict[str, Any]] = {
    "wav": {"read": read_wav, "write": write_wav_bytes, "suffix": ".wav"},
    "flac": {"read": read_flac, "write": write_flac_bytes, "suffix": ".flac"},
}


# ---------------------------------------------------------------------------
# Source enumeration, one function per carrier
# ---------------------------------------------------------------------------


def _slurp_sources(pinned: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    view = pinned["runtime_view"]
    if str(view["schema"]) != SPEECH_NATIVE_VIEW_SCHEMA:
        raise BuildError("the pinned SLURP source is not a speech-native runtime view")
    if str(view["split_name"]) != "DEV-1000" or int(view["count"]) != 1000:
        raise BuildError("the pinned SLURP source is not the 1,000-row DEV-1000 view")
    rows = []
    for item in view["items"]:
        sample_id = str(item["sample_id"])
        rows.append(
            {
                "source_sample_id": sample_id,
                "sample_id": f"{sample_id}@{ID_SUFFIX}",
                "stratum": "devel",
                "source_media_relpath": str(item["media_relpath"]),
                "source_audio_sha256": str(item["audio_sha256"]),
                "source_audio_seconds": float(item["audio_seconds"]),
                "media_basename": Path(str(item["media_relpath"])).stem
                + f"@{ID_SUFFIX}",
                "media_subdir": "",
                "extra": {
                    "source_packet_id": str(item["packet_id"]),
                    "packet_id": f"{item['packet_id']}@{ID_SUFFIX}",
                },
            }
        )
    return rows


def _a2t_sources(pinned: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    receipt = pinned["roster_receipt"]
    if str(receipt["split_name"]) != "A2T-CALIBRATION-400" or int(receipt["count"]) != 400:
        raise BuildError("the pinned Audio2Tool source is not the frozen 400 roster")
    rows = []
    for item in receipt["items"]:
        sample_id = str(item["sample_id"])
        tier = str(item["tier"])
        rows.append(
            {
                "source_sample_id": sample_id,
                "sample_id": f"{sample_id}@{ID_SUFFIX}",
                "stratum": tier,
                "source_media_relpath": str(item["media_relpath"]),
                "source_audio_sha256": str(item["audio_sha256"]),
                "source_audio_seconds": float(item["audio_seconds"]),
                "media_basename": sample_id.replace(":", "_") + f"@{ID_SUFFIX}",
                "media_subdir": tier,
                "extra": {
                    "source_key": str(item["key"]),
                    "tier": tier,
                    "parent_media_relpath": str(item["media_relpath"]),
                },
            }
        )
    return rows


E21_SOURCE_RUN_ID = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"


def _e21_sources(pinned: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The 1,593 sealed 90-second window slices the direct baseline itself wrote.

    The slices are runtime derivations of a sealed flight, so they are not in
    any committed D1 layer; their identity is the flight's own per-call
    ``obs-derivation`` receipts, whose ``sha256`` records every source file is
    re-verified against below. The attempt id is not typed here either: it is
    read from the committed window-pairing receipt, which is pinned by content.
    """

    roster = pinned["roster_receipt"]
    pairing = pinned["window_pairing"]
    attempt_id = str(pairing["source_attempt_id"])
    if str(pairing.get("run_id", E21_SOURCE_RUN_ID)) != E21_SOURCE_RUN_ID:
        raise BuildError("the pinned window-pairing receipt names a different run")
    attempt_dir = Path(data_root()) / "runs" / E21_SOURCE_RUN_ID / attempt_id
    if not attempt_dir.is_dir():
        raise BuildError(f"sealed attempt directory {attempt_dir} does not exist")

    rows = []
    for call in roster["calls"]:
        sample_id = str(call["sample_id"])
        derivation_path = (
            attempt_dir / f"{E21_SOURCE_RUN_ID}.obs-derivation.{sample_id}.json"
        )
        derivation = json.loads(derivation_path.read_text(encoding="utf-8"))
        if str(derivation.get("boundary_mode")) != "fixed":
            raise BuildError(f"call {sample_id} was not sliced in fixed-window mode")
        slices = sorted(derivation["slices"], key=lambda row: int(row["iteration"]))
        if [int(row["iteration"]) for row in slices] != list(range(len(slices))):
            raise BuildError(f"call {sample_id} has a gapped slice iteration sequence")
        for entry in slices:
            iteration = int(entry["iteration"])
            wid = window_id(sample_id, iteration + 1)
            rows.append(
                {
                    "source_sample_id": wid,
                    "sample_id": f"{wid}@{ID_SUFFIX}",
                    "stratum": sample_id,
                    "source_media_relpath": str(entry["media_relpath"]),
                    "source_audio_sha256": str(entry["sha256"]),
                    "source_audio_seconds": float(entry["audio_seconds"]),
                    "media_basename": f"i{iteration:04d}@{ID_SUFFIX}",
                    "media_subdir": sample_id,
                    "extra": {
                        "call_sample_id": sample_id,
                        "window_index": iteration + 1,
                        "obs_iteration": iteration,
                        "window_start_seconds": float(entry["start_seconds"]),
                        "window_end_seconds": float(entry["end_seconds"]),
                        "source_attempt_id": attempt_id,
                        "source_run_id": E21_SOURCE_RUN_ID,
                    },
                }
            )
    if len(rows) != 1593:
        raise BuildError(f"expected 1,593 sealed windows, enumerated {len(rows)}")
    return rows


# ---------------------------------------------------------------------------
# The three carrier descriptors -- the ONLY place a carrier differs
# ---------------------------------------------------------------------------

CARRIERS: dict[str, dict[str, Any]] = {
    "slurp": {
        "carrier_lock_key": "slurp",
        "exposure_row": "SAEA-SN-MF-SLURP-DEV1000-TS2-MEDIA-V1",
        "container": "flac",
        "sample_rate_hz": 16000,
        "pins": {
            "runtime_view": (
                "configs/dataset/slurp-speech-native-dev1000.json",
                "f92846760b3657ba50009e52f98fcec96df27c16ac66ea57467b4f8fa42f288d",
            ),
        },
        "sources": _slurp_sources,
        "subdir": "derived/slurp-dev1000-tail2s-v1",
        "roster_id": "SLURP-DEV-1000-TS2-V1",
        "split_name": "DEV-1000-TAIL2S",
        "split_role": "dev",
        "roster_receipt": "docs/receipts/rosters/slurp-dev-1000-ts2-v1.json",
        "supplement": "docs/receipts/artifacts/d1-slurp-dev1000-tail2s.json",
        "out_dir": "2026-09-07-slurp-dev1000-tail2s-media",
        "comparator": {
            "run_id": "SAEA-SLURP-DEV1000-CLOSED-LIST-DIRECT-V1",
            "attempt_id": "attempt-20260905T060424Z-2c5596",
            "split_identity_hash": (
                "8580d199bffc95a51ad6d8c5b2a2e9e39faa2c551dd095f8afcd78174a1e3c84"
            ),
            "paper_facing_scorer": "slurp-slu-official-projected-v2",
            "serving_path": (
                "mmproj-free decode over pre-materialized SpeechFeaturePacketV1 "
                "packets, -c 65536 -np 8"
            ),
        },
        "split_role_basis": (
            "The SAME 1,000 SLURP devel recordings the sealed DEV-1000 closed-list "
            "direct comparator flew, re-encoded by one deterministic rule from the "
            "sealed FLAC bytes. DEV-1000 is a dev-tier optimization population and "
            "stays one; nothing about this build promotes it to a reporting split, "
            "and no SLURP gold label, devel sentence, scenario, action, intent or "
            "entity is opened here."
        ),
    },
    "audio2tool": {
        "carrier_lock_key": "audio2tool",
        "exposure_row": "SAEA-SN-MF-A2T-CAL400-TS2-MEDIA-V1",
        "container": "wav",
        # Measured, not assumed: every one of the 400 release wavs is 24 kHz
        # mono 16-bit, so 2.0 s is 48,000 zero samples here and llama.cpp's
        # miniaudio front end resamples the whole file to 16 kHz exactly as it
        # already does for the sealed comparator.
        "sample_rate_hz": 24000,
        "pins": {
            "roster_receipt": (
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-04-a2t-calibration-400-roster/flight-roster-receipt.json",
                "6f352ea583d0bb91f77aad62e07bdad4d3210d066440fbfaee8e2af504853fe7",
            ),
        },
        "sources": _a2t_sources,
        "subdir": "derived/a2t-calibration-400-tail2s-v1",
        "roster_id": "A2T-CALIBRATION-400-TS2-V1",
        "split_name": "A2T-CALIBRATION-400-TAIL2S",
        "split_role": "discovery",
        "roster_receipt": "docs/receipts/rosters/a2t-calibration-400-ts2-v1.json",
        "supplement": "docs/receipts/artifacts/d1-a2t-calibration-400-tail2s.json",
        "out_dir": "2026-09-07-a2t-calibration-400-tail2s-media",
        "comparator": {
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
        },
        "split_role_basis": (
            "The SAME frozen 400-row Audio2Tool discovery split (50 per tier over "
            "all eight tiers) the sealed official-protocol replication flew, "
            "re-encoded by one deterministic rule from the sealed WAV bytes. The "
            "split was already exposed by A0 and stays discovery. No evaluation "
            "query text, gold tool name, argument or tool registry row is opened "
            "here."
        ),
    },
    "earnings21": {
        "carrier_lock_key": "earnings21-original",
        "exposure_row": "SAEA-SN-MF-E21-BUF90-TS2-MEDIA-V1",
        "container": "wav",
        "sample_rate_hz": 16000,
        "pins": {
            "roster_receipt": (
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-04-e21-full44-roster/flight-roster-receipt.json",
                "e870ada137c85e01fa9c52e6234341f867f8dbc87127806bd819aa467f969d5b",
            ),
            "window_pairing": (
                "docs/checks/speech-aware-evidence-acquisition/"
                "2026-09-06-e21-window-pairing/reaggregation.json",
                "42e0e1ccf71e9ca7b2a3aec3174588150e1752b82e2fc1bc2ab85b4ebd6281ef",
            ),
        },
        "sources": _e21_sources,
        "subdir": "derived/e21-buf90-tail2s-v1",
        "roster_id": "E21-BUF90-1593-TS2-V1",
        "split_name": "E21-BUF90-WINDOWS-1593-TAIL2S",
        "split_role": "discovery",
        "roster_receipt": "docs/receipts/rosters/e21-buf90-1593-ts2-v1.json",
        "supplement": "docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json",
        "out_dir": "2026-09-07-e21-buf90-tail2s-media",
        "comparator": {
            "run_id": E21_SOURCE_RUN_ID,
            "attempt_id": "attempt-20260904T233816Z-bcd338",
            "split_identity_hash": (
                "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
            ),
            "paper_facing_scorer": "asr-wer-whisper",
            "serving_path": "raw audio through the bf16 mmproj, -c 36864 -np 6",
        },
        "split_role_basis": (
            "The 1,593 fixed 90-second windows of the 44 Earnings-21 DISCOVERY "
            "calls, as the sealed full-44 direct baseline itself cut them, "
            "re-encoded by one deterministic rule from those sealed slice bytes. "
            "Earnings-21 is the study's discovery carrier and stays one. No "
            "reference transcript, ConEC annotation or sealed hypothesis is "
            "opened here."
        ),
    },
}


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------


def build_one(
    dev: Any,
    row: Mapping[str, Any],
    carrier: Mapping[str, Any],
    root: Path,
    *,
    write: bool,
) -> dict[str, Any]:
    """One clip, through the pinned transform and this carrier's container."""

    container = CONTAINERS[str(carrier["container"])]
    read: Callable[[Path, int], array] = container["read"]
    encode: Callable[[Sequence[int], int], bytes] = container["write"]
    rate = int(carrier["sample_rate_hz"])

    source_relpath = str(row["source_media_relpath"])
    source_path = root / source_relpath
    measured = sha256_file(source_path)
    if measured != str(row["source_audio_sha256"]):
        raise BuildError(
            f"source media drift on {row['source_sample_id']}: the pinned receipt "
            f"records {str(row['source_audio_sha256'])[:12]}..., disk hashes to "
            f"{measured[:12]}..."
        )
    samples = read(source_path, rate)
    # The pinned receipts record durations rounded to the millisecond, so the
    # duration check is stated at that resolution rather than pretending to an
    # exactness the receipt does not carry.
    if round(len(samples) / rate, 3) != round(float(row["source_audio_seconds"]), 3):
        raise BuildError(
            f"{row['source_sample_id']}: sealed clip is {len(samples) / rate:.6f} s, "
            f"the pinned receipt records {float(row['source_audio_seconds']):.6f} s"
        )

    produced = append_tail(samples, rate)
    if len(produced) != len(samples) + int(TAIL_SILENCE_SECONDS * rate):
        raise BuildError(f"{row['source_sample_id']}: the tail is not exactly 2.0 s")
    if produced[: len(samples)] != samples:
        raise BuildError(f"{row['source_sample_id']}: the sealed samples were altered")
    if any(produced[len(samples) :]):
        raise BuildError(f"{row['source_sample_id']}: the tail is not digital silence")

    payload = encode(produced, rate)
    # Determinism is checked rather than assumed: the same inputs go through the
    # same encoder twice and the bytes must agree.
    if encode(append_tail(samples, rate), rate) != payload:
        raise BuildError(f"{row['source_sample_id']}: the encoder is not deterministic")

    parts = [str(carrier["subdir"])]
    if row["media_subdir"]:
        parts.append(str(row["media_subdir"]))
    parts.append(str(row["media_basename"]) + str(container["suffix"]))
    relpath = "/".join(parts)
    target = root / relpath
    if write:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        if sha256_file(target) != hashlib.sha256(payload).hexdigest():
            raise BuildError(f"{row['sample_id']}: written bytes do not match the payload")

    margins = energy_margins(samples, rate)
    entry: dict[str, Any] = {
        "sample_id": str(row["sample_id"]),
        "source_sample_id": str(row["source_sample_id"]),
        "stratum": str(row["stratum"]),
        "source_media_relpath": source_relpath,
        "source_audio_sha256": measured,
        "source_audio_seconds": round(len(samples) / rate, 9),
        "media_relpath": relpath,
        "audio_sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "audio_seconds": round(len(produced) / rate, 9),
        "n_samples": len(produced),
        "sample_rate_hz": rate,
        "samples_added": len(produced) - len(samples),
        "samples_removed": 0,
        # The measurement the cross-carrier prediction rests on: how much
        # silence the SEALED clip already had after its last active frame.
        "source_trailing_silence_seconds": round(margins.trailing_seconds, 6),
        "source_leading_silence_seconds": round(margins.leading_seconds, 6),
        "source_peak_dbfs": round(margins.peak_dbfs, 4),
        "source_active_share": round(margins.active_share, 6),
    }
    entry.update({key: value for key, value in dict(row["extra"]).items()})
    return entry


def _trailing_summary(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = sorted(float(entry["source_trailing_silence_seconds"]) for entry in entries)
    n = len(values)

    def pct(fraction: float) -> float:
        return values[min(n - 1, int(fraction * (n - 1)))]

    return {
        "n": n,
        "min": values[0],
        "p10": round(pct(0.10), 6),
        "median": round(pct(0.50), 6),
        "p90": round(pct(0.90), 6),
        "max": values[-1],
        "mean": round(sum(values) / n, 6),
        "ends_exactly_at_an_active_frame": sum(1 for value in values if value == 0.0),
        "trailing_silence_at_most_0_02_s": sum(1 for value in values if value <= 0.02),
        "trailing_silence_at_most_0_10_s": sum(1 for value in values if value <= 0.10),
        "trailing_silence_at_least_2_00_s": sum(1 for value in values if value >= 2.0),
        "measured_by": (
            "analysis.e22_clip_boundary.energy_margins at its committed version, on "
            "the SEALED samples (not the variant): 20 ms frames, active = frame RMS "
            "within 35 dB of the clip peak and above the absolute floor"
        ),
    }


def probe_view(
    carrier: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    ids = [str(entry["sample_id"]) for entry in entries]
    if ids != sorted(ids):
        raise BuildError("the variant items are not in sample-id order")
    strata = sorted({str(entry["stratum"]) for entry in entries})
    view: dict[str, Any] = {
        "schema": PROBE_VIEW_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "carrier": str(carrier["carrier_lock_key"]),
        "split_name": str(carrier["split_name"]),
        "split_role": str(carrier["split_role"]),
        "split_role_basis": str(carrier["split_role_basis"]),
        "variant": VARIANT,
        "rule": RULE,
        "rule_implementation": {
            "module": DEV_BUILDER_RELPATH,
            "sha256": DEV_BUILDER_SHA256,
            "function": "transform('tail-silence-2s', ...)",
            "note": (
                "the Earnings-22 dev1500 builder's own transform, imported and pinned "
                "by content, so all four carriers' variant bytes are produced by the "
                "same rule and the same code"
            ),
        },
        "id_rule": (
            f"<sealed id>@{ID_SUFFIX}; the sealed key is recovered by splitting on "
            "'@', so the paired join against the sealed comparator is exact and no "
            "id collides with the comparator population's"
        ),
        "container": str(carrier["container"]),
        "sample_rate_hz": int(carrier["sample_rate_hz"]),
        "tail_silence_seconds": TAIL_SILENCE_SECONDS,
        "tail_silence_samples": int(TAIL_SILENCE_SECONDS * int(carrier["sample_rate_hz"])),
        "comparator": dict(carrier["comparator"]),
        "derived_from": {
            name: {"path": relpath, "sha256": digest}
            for name, (relpath, digest) in dict(carrier["pins"]).items()
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
        "sealed_clip_trailing_silence": _trailing_summary(entries),
        "ids_sha256": ids_sha256(ids),
        "items": list(entries),
    }
    view["items_sha256"] = canonical_sha256(list(entries))
    return view


def supplement(
    carrier: Mapping[str, Any],
    entries: Sequence[Mapping[str, Any]],
    *,
    view_sha256: str,
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
        "carrier_lock_key": str(carrier["carrier_lock_key"]),
        "parent_d1_sha256": sha256_file(REPO / "docs/receipts/artifacts/d1-identity.json"),
        "source_binding_sha256": view_sha256,
        "count": len(manifest),
        "ids_sha256": ids_sha256([str(row["id"]) for row in manifest]),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(row["bytes"]) for row in manifest),
    }


def packet_promotion_plan(
    carrier: Mapping[str, Any], entries: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """SLURP only: what it costs to give this media its own encoder packets.

    The DEV-1000 comparator does NOT serve raw audio. It serves
    ``SpeechFeaturePacketV1`` packets -- encoder features materialized once by a
    CPU-only llama sidecar and then decoded mmproj-free. The legacy feature-cache
    key is the FNV-1a hash of the ORIGINAL MEDIA BYTES
    (``core.model.speech_features.legacy_audio_feature_cache_key``), so a
    ``@ts2`` file is a cache miss by construction and the variant needs its own
    encode pass and its own promoted packet root before any flight can use it.
    That pass is a model contact -- one per row, CPU only, zero GPU -- and it
    needs its own ``bounded-discovery-probe`` exposure row.
    """

    audio_seconds = sum(float(entry["audio_seconds"]) for entry in entries)
    # The measured precedent: SAEA-SN-DEV1000-PREPROCESS spent 11.0 min of wall
    # on 1,462.712 metered audio seconds through the same CPU-only sidecar.
    minutes = 11.0 * audio_seconds / 1462.712
    return {
        "why_a_promotion_is_needed": (
            "the sealed comparator serves mmproj-free over promoted packets; the "
            "legacy feature-cache key is FNV-1a over the ORIGINAL media bytes, so a "
            "@ts2 file can never hit the comparator's cache and needs its own encode"
        ),
        "encode_pass": {
            "exposure_row": "SAEA-SN-SLURP-DEV1000-TS2-PREPROCESS-V1 (NOT registered here)",
            "execution_profile": "bounded-discovery-probe",
            "model_fragment": "q4km-preprocess-featcache-cpu-sidecar",
            "server": "CPU-only llama-server on port 8081, -ngl 0 --no-mmproj-offload",
            "contacts": len(entries),
            "max_tokens": 1,
            "prompt": "the fixed minimal preprocessing prompt; no response is read semantically",
            "audio_seconds": round(audio_seconds, 3),
            "gpu_hours": 0.0,
            "projected_wall_minutes": round(minutes, 1),
            "projection_basis": (
                "SAEA-SN-DEV1000-PREPROCESS: 11.0 min of wall for 1,462.712 metered "
                "audio seconds through this same CPU-only sidecar, scaled by audio "
                "seconds"
            ),
            "legacy_cache_dir": "/home/chao/feat-cache/slurp-ts2-q4km",
        },
        "promotion": {
            "primitive": (
                "core.model.speech_features."
                "materialize_legacy_cached_speech_feature_packets"
            ),
            "contacts": 0,
            "packet_root": "/home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a",
            "promotion_receipt": (
                "/home/chao/feat-cache/slurp-dev1000-ts2-packets-04ccc72a/"
                "DEV-1000-TAIL2S-promotion.json"
            ),
            "packet_id_convention": (
                "the comparator's own convention with the variant suffix carried on "
                "the leaf: slurp/devel/<group>/<audio-id>@ts2"
            ),
        },
        "what_this_buys": (
            "the cell then flies on the comparator's OWN serving path -- mmproj-free "
            "decode over packets at -c 65536 -np 8 -- so the contrast against the "
            "sealed DEV-1000 rows is single-factor in the media and nothing else"
        ),
        "what_it_does_not_prove": (
            "that the CPU sidecar and the GPU mmproj produce identical features. They "
            "are the same graph and the same weights, and the comparator's own packets "
            "were produced by this same sidecar, so the two arms are encoded by the "
            "same instrument -- but no bit-exactness claim is made or needed."
        ),
        "gate_before_1000_contacts": (
            "a 4-row dry run of the encode pass, proving the libsndfile-written FLAC "
            "decodes in llama.cpp's miniaudio front end and that the promoted packet's "
            "token count equals the sealed packet's plus the tail's blocks"
        ),
    }


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(
    name: str, *, write: bool, workers: int, attempts_count: int
) -> dict[str, Any]:
    carrier = CARRIERS[name]
    dev = load_dev_builder()
    root = Path(data_root())
    pinned = {
        key: load_pinned(relpath, digest, f"{name} {key}")
        for key, (relpath, digest) in dict(carrier["pins"]).items()
    }
    rows = carrier["sources"](pinned)

    def one(row: Mapping[str, Any]) -> dict[str, Any]:
        return build_one(dev, row, carrier, root, write=write)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        entries = list(pool.map(one, rows))
    entries.sort(key=lambda entry: str(entry["sample_id"]))

    per_stratum = {
        stratum: sum(1 for entry in entries if str(entry["stratum"]) == stratum)
        for stratum in {str(entry["stratum"]) for entry in entries}
    }
    receipt = freeze_roster(
        carrier_lock_key=str(carrier["carrier_lock_key"]),
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
        split_role=str(carrier["split_role"]),
        roster_id=str(carrier["roster_id"]),
        roster_role=EVALUATION_ROSTER_ROLE,
    )
    if len(receipt["items"]) != len(entries):
        raise BuildError("freezing the variant roster dropped rows")

    view = probe_view(carrier, entries)
    view_bytes = (
        json.dumps(view, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    view_sha256 = hashlib.sha256(view_bytes).hexdigest()
    media = supplement(carrier, entries, view_sha256=view_sha256)
    media_bytes = (
        json.dumps(media, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")

    out_dir = (
        REPO / "docs/checks/speech-aware-evidence-acquisition" / str(carrier["out_dir"])
    )
    build_receipt: dict[str, Any] = {
        "schema": BUILD_RECEIPT_SCHEMA,
        "carrier": name,
        "carrier_lock_key": str(carrier["carrier_lock_key"]),
        "exposure_row": str(carrier["exposure_row"]),
        "execution_profile": "model-free-check",
        "variant": VARIANT,
        "rule": RULE,
        "rule_implementation": {
            "module": DEV_BUILDER_RELPATH,
            "sha256": DEV_BUILDER_SHA256,
            "function": "transform('tail-silence-2s', ...)",
        },
        "id_suffix": ID_SUFFIX,
        "container": str(carrier["container"]),
        "media_root": str(carrier["subdir"]),
        "roster_id": str(carrier["roster_id"]),
        "split_name": str(carrier["split_name"]),
        "split_role": str(carrier["split_role"]),
        "split_identity_hash": receipt["split_identity_hash"],
        "comparator": dict(carrier["comparator"]),
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
            "samples_added_total": sum(int(entry["samples_added"]) for entry in entries),
            "samples_removed_total": 0,
            "clips_left_unchanged": 0,
        },
        "sealed_clip_trailing_silence": view["sealed_clip_trailing_silence"],
        "source_population": {
            name_: {"path": relpath, "sha256": digest}
            for name_, (relpath, digest) in dict(carrier["pins"]).items()
        }
        | {
            "files_rehashed_before_reading": len(entries),
            "all_source_digests_matched": True,
        },
        "outputs": {
            "roster_receipt": str(carrier["roster_receipt"]),
            "roster_receipt_sha256": hashlib.sha256(
                canonical_receipt_bytes(receipt)
            ).hexdigest(),
            "probe_view": (out_dir / "roster" / "flight-roster-receipt.json")
            .relative_to(REPO)
            .as_posix(),
            "probe_view_sha256": view_sha256,
            "d1_media_supplement": str(carrier["supplement"]),
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
            "librosa_calls": 0,
            "ffmpeg_calls": 0,
            "outbound_connection_attempts": attempts_count,
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
                "MEDIA BYTES ONLY. The build reads the pinned receipts (identifiers, "
                "media paths, measured media identity, window spans) and the audio "
                "samples of the sealed files those receipts name. No gold label, "
                "reference sentence, evaluation query, tool name, sealed output, "
                "hypothesis or score is opened, and none is reachable from this "
                "process."
            ),
        },
        "test_split_read": False,
        "authorizes": (
            "nothing beyond writing this media and these receipts. No cell is flown, "
            "no request is built, no server is started, no packet is promoted and no "
            "scorer runs."
        ),
    }
    if name == "slurp":
        build_receipt["packet_promotion_plan"] = packet_promotion_plan(carrier, entries)

    if write:
        (REPO / str(carrier["roster_receipt"])).parent.mkdir(parents=True, exist_ok=True)
        write_roster(receipt, REPO / str(carrier["roster_receipt"]))
        (out_dir / "roster").mkdir(parents=True, exist_ok=True)
        (out_dir / "roster" / "flight-roster-receipt.json").write_bytes(view_bytes)
        (REPO / str(carrier["supplement"])).parent.mkdir(parents=True, exist_ok=True)
        (REPO / str(carrier["supplement"])).write_bytes(media_bytes)
        write_json_artifact(out_dir / "build-receipt.json", build_receipt)
        write_manifest(out_dir)
        write_manifest(out_dir / "roster")
    return build_receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--carrier",
        choices=[*sorted(CARRIERS), "all"],
        required=True,
        help="which carrier's @ts2 media to build",
    )
    parser.add_argument("--write", action="store_true", help="write media and receipts")
    parser.add_argument(
        "--workers", type=int, default=8, help="CPU workers (campaign cap is 8)"
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("workers must be between 1 and 8 (the campaign cap)")

    attempts = arm_offline_guard()
    names = sorted(CARRIERS) if args.carrier == "all" else [args.carrier]
    for name in names:
        receipt = build(
            name, write=args.write, workers=args.workers, attempts_count=attempts.count
        )
        media = receipt["measured_media"]
        trailing = receipt["sealed_clip_trailing_silence"]
        print(
            "%s %s: %d clips, %.3f s (%.4f h), longest %.6f s, identity %s"
            % (
                name,
                receipt["variant"],
                receipt["count"],
                media["audio_seconds_total"],
                media["audio_hours_total"],
                media["audio_seconds_longest_item"],
                receipt["split_identity_hash"],
            )
        )
        print(
            "  +%d samples, -%d, %d bytes on disk, %d strata"
            % (
                media["samples_added_total"],
                media["samples_removed_total"],
                media["total_bytes"],
                len(receipt["strata_counts"]),
            )
        )
        print(
            "  sealed trailing silence: median %.3f s, mean %.3f s, %d of %d end on an "
            "active frame, %d already carry >= 2.0 s"
            % (
                trailing["median"],
                trailing["mean"],
                trailing["ends_exactly_at_an_active_frame"],
                trailing["n"],
                trailing["trailing_silence_at_least_2_00_s"],
            )
        )
    if not args.write:
        print("(print only; pass --write to land the media and the receipts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
