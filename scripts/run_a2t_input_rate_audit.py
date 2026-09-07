#!/usr/bin/env python3
"""Audit the resampler that converts Audio2Tool's 24 kHz wavs to the 16 kHz the
frozen core's front end wants (model-free, CPU only).

Row ``SAEA-A2T-MF-INPUT-RATE-AUDIT-V1`` (``model-free-check``). **Zero model,
tokenizer, embedder, retriever, scorer, network and GPU contacts; zero audio
seconds delivered to any service; no llama.cpp binary is built or executed and
no file in the llama.cpp checkout is written.** No dataset media is opened at
all: every sample this script measures is a synthetic tone it generates itself.

What it answers
---------------
Today nothing in this study converts the rate. ``core/model/transport.py``
base64s the sealed 24 kHz bytes verbatim and llama.cpp's mtmd front end resamples
them inside its decoder. So "which resampler is running, with which filter, and
what does it cost" is a question about *miniaudio's* defaults, not about ours.
This script answers it three ways, in increasing order of force:

1. **Pins the sources.** The cited files of the pinned featcache checkout
   (build commit ``04ccc72a``) are re-hashed and the checkout must be clean and
   detached at that commit, so every ``file:line`` in
   ``docs/readiness/2026-09-07-a2t-input-rate-audit-v1.md`` is anchored to bytes.
2. **Runs miniaudio's own decoder** on synthetic tones, through a standalone C
   harness that reproduces ``tools/mtmd/mtmd-helper.cpp``'s
   ``decode_audio_from_buf`` call sequence line for line. The harness is
   compiled in a temporary directory against the checkout's read-only vendored
   header; nothing in the checkout is modified and no llama.cpp target is built.
3. **Runs the study's own decoder** -- ``reproduction.obs_loop.
   decode_parent_pcm`` (librosa ``soxr_hq``) -- on the same tones, so the two
   candidates for the 24 -> 16 kHz conversion are measured on one instrument.

If ``gcc`` is absent the miniaudio half is recorded as ``not_measured`` with the
reason, and the source citations stand on their own; the script still succeeds.

Usage (WSL2)::

    python scripts/run_a2t_input_rate_audit.py
    python scripts/run_a2t_input_rate_audit.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from array import array
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

import speech_aware_evidence_acquisition.core as _core  # noqa: E402, F401

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.obs_audio import (  # noqa: E402
    write_wav_bytes,
)
from speech_aware_evidence_acquisition.reproduction.obs_loop import (  # noqa: E402
    decode_parent_pcm,
)

OUT_DIR = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-a2t-input-rate-audit"
)

#: The pinned build every sealed Audio2Tool arm was served from. The checkout
#: root is ``model_materialization_root`` + the runtime receipt's own
#: ``llama_cpp.binary_path`` prefix.
RUNTIME_RECEIPT = "docs/receipts/runtime-q4km-featcache-04ccc72a.json"
BUILD_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
DEFAULT_CHECKOUT = "/home/chao/llama.cpp-featcache"

#: Every file the audit note cites, pinned by content. A drift here means a
#: line number in the note may point at different bytes, so the audit refuses.
CITED_SOURCES: dict[str, str] = {
    "vendor/miniaudio/miniaudio.h": (
        "ac7af4de748b7e26b777f37e01cee313a308a7296a3eb080e2906b320cc55c89"
    ),
    "tools/mtmd/mtmd-helper.cpp": (
        "cb0bb84a55640be49a2ec5f2d6b95c97afa7775eaffc0d1ebe1e79dfb68f4064"
    ),
    "tools/mtmd/mtmd.cpp": (
        "8accbc17efb1b301e7b02fff5522376e95990f477ad4f4f0f389eceb3c2b3109"
    ),
    "tools/mtmd/clip.cpp": (
        "c7eaf112c2e067d3552af04f00fbe6cbcb6145cedf0f0f4a9040662760b87308"
    ),
    "tools/server/server-common.cpp": (
        "7d86566ac735e2c0e7a3d78719b49fdb8383786fd142c8b4df9dd303ba1f6e96"
    ),
    "tools/server/server-context.cpp": (
        "e235949a10bfa9284b8d79c735b638569e3db533e0eee8da2f3e474ca2701248"
    ),
}

SOURCE_RATE_HZ = 24000
TARGET_RATE_HZ = 16000

#: The tone grid. Dense either side of the 8 kHz output Nyquist, because that is
#: where the two candidate resamplers differ: one rolls off gently and folds the
#: rest back, the other cuts.
TONE_FREQUENCIES_HZ: tuple[int, ...] = (
    100, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 7500,
    7900, 8000, 8100, 8500, 9000, 10000, 11000, 11900,
)
TONE_SECONDS = 1.0
TONE_AMPLITUDE = 0.5
#: 50 ms of each end is dropped before the spectrum is taken: the priming frame
#: and the filter transient are not part of a steady-state response.
EDGE_SECONDS = 0.05
#: Half-width of the "did the tone stay where it was" bin.
BIN_HALF_WIDTH_HZ = 25.0

#: Input lengths for the truncation probe. Chosen so ``n % 3`` covers 0, 1 and 2
#: -- the only thing that decides whether the two resamplers' output lengths
#: agree.
LENGTH_PROBE_SAMPLES: tuple[int, ...] = (
    24000, 24001, 24002, 24003, 35931, 35932, 35933, 15984, 21697,
)

#: The C harness. It is ``decode_audio_from_buf`` (mtmd-helper.cpp:461-497)'s
#: call sequence and nothing else: same config init, same
#: ``ma_decoder_get_length_in_pcm_frames``, same single
#: ``ma_decoder_read_pcm_frames`` for exactly that many frames.
HARNESS_C = r"""
#define MA_NO_DEVICE_IO
#define MA_NO_ENGINE
#define MA_NO_GENERATION
#define MA_NO_THREADING
#define MINIAUDIO_IMPLEMENTATION
#include "miniaudio.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "usage: harness <in.wav> <target_rate>\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 2; }
    fseek(f, 0, SEEK_END); long len = ftell(f); fseek(f, 0, SEEK_SET);
    unsigned char *buf = (unsigned char *)malloc((size_t)len);
    if (fread(buf, 1, (size_t)len, f) != (size_t)len) { return 2; }
    fclose(f);

    int target = atoi(argv[2]);
    const int channels = 1;
    ma_decoder_config decoder_config = ma_decoder_config_init(ma_format_f32, channels, target);
    ma_decoder decoder;
    if (ma_decoder_init_memory(buf, (size_t)len, &decoder_config, &decoder) != MA_SUCCESS) {
        fprintf(stderr, "decoder init failed\n"); return 1;
    }
    ma_uint64 frame_count = 0, frames_read = 0;
    if (ma_decoder_get_length_in_pcm_frames(&decoder, &frame_count) != MA_SUCCESS) {
        fprintf(stderr, "length failed\n"); return 1;
    }
    float *out = (float *)calloc((size_t)frame_count, sizeof(float));
    if (ma_decoder_read_pcm_frames(&decoder, out, frame_count, &frames_read) != MA_SUCCESS) {
        fprintf(stderr, "read failed\n"); return 1;
    }
    printf("%llu %llu\n", (unsigned long long)frame_count, (unsigned long long)frames_read);
    for (ma_uint64 i = 0; i < frame_count; i++) printf("%.9g\n", out[i]);
    ma_decoder_uninit(&decoder);
    free(out); free(buf);
    return 0;
}
"""


class AuditError(RuntimeError):
    """An input drifted, or a measured property contradicted the source read."""


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


def git(checkout: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(checkout), capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def pin_checkout(checkout: Path) -> dict[str, Any]:
    """Refuse unless the checkout is the pinned commit, clean, and unmodified."""

    if not (checkout / ".git").exists():
        raise AuditError(f"{checkout} is not a git checkout")
    head = git(checkout, "rev-parse", "HEAD")
    if head != BUILD_COMMIT:
        raise AuditError(
            f"{checkout} is at {head[:12]}..., this audit pins the sealed build "
            f"{BUILD_COMMIT[:12]}..."
        )
    dirty = git(checkout, "status", "--porcelain")
    if dirty:
        raise AuditError(
            f"{checkout} has uncommitted changes; a line number cited against a dirty "
            "tree is not evidence"
        )
    files: dict[str, str] = {}
    for relpath, expected in CITED_SOURCES.items():
        measured = sha256_file(checkout / relpath)
        if measured != expected:
            raise AuditError(
                f"{relpath} drifted: pinned {expected[:12]}..., measured "
                f"{measured[:12]}..."
            )
        files[relpath] = measured
    return {
        "checkout": str(checkout),
        "build_commit": head,
        "working_tree": "clean",
        "runtime_receipt": RUNTIME_RECEIPT,
        "cited_sources": files,
        "note": (
            "read-only. No llama.cpp target is built, no binary from this checkout is "
            "executed, and no file under it is written."
        ),
    }


# ---------------------------------------------------------------------------
# The two decoders
# ---------------------------------------------------------------------------


def build_harness(checkout: Path, workdir: Path) -> tuple[Path | None, str]:
    """Compile the standalone miniaudio harness, or say why it could not be."""

    compiler = shutil.which("cc") or shutil.which("gcc")
    if compiler is None:
        return None, "no C compiler on PATH (looked for cc, gcc)"
    source = workdir / "harness.c"
    source.write_text(HARNESS_C, encoding="utf-8")
    binary = workdir / "harness"
    command = [
        compiler,
        "-O2",
        "-I",
        str(checkout / "vendor/miniaudio"),
        "-o",
        str(binary),
        str(source),
        "-lm",
        "-lpthread",
        "-ldl",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not binary.is_file():
        return None, f"compile failed: {result.stderr.strip()[:400]}"
    return binary, f"{compiler} -O2, vendored miniaudio header, read-only include"


def tone_wav(freq_hz: float, n_samples: int) -> bytes:
    import numpy as np  # noqa: PLC0415

    times = np.arange(n_samples) / float(SOURCE_RATE_HZ)
    wave = TONE_AMPLITUDE * np.sin(2.0 * np.pi * freq_hz * times)
    pcm = np.clip(np.rint(wave * 32767.0), -32768, 32767).astype("<i2")
    return write_wav_bytes(array("h", pcm.tolist()), SOURCE_RATE_HZ)


def decode_miniaudio(binary: Path, path: Path) -> tuple[int, int, Any]:
    import numpy as np  # noqa: PLC0415

    result = subprocess.run(
        [str(binary), str(path), str(TARGET_RATE_HZ)],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result.stdout.strip().splitlines()
    frame_count, frames_read = (int(value) for value in lines[0].split())
    # miniaudio hands mtmd float32 in [-1, 1]; scale to the int16 grid the study
    # side lives on so the two are compared on one axis.
    vector = np.asarray([float(value) for value in lines[1:]], dtype=np.float64) * 32767.0
    return frame_count, frames_read, vector


def decode_study(path: Path) -> Any:
    import numpy as np  # noqa: PLC0415

    samples = decode_parent_pcm(path, TARGET_RATE_HZ)
    return np.frombuffer(array("h", samples).tobytes(), dtype="<i2").astype(np.float64)


# ---------------------------------------------------------------------------
# The measurements
# ---------------------------------------------------------------------------


def folded_frequency(freq_hz: float) -> float:
    """Where a tone above the output Nyquist lands after decimation."""

    nyquist = TARGET_RATE_HZ / 2.0
    return freq_hz if freq_hz <= nyquist else TARGET_RATE_HZ - freq_hz


def band_class(freq_hz: float) -> str:
    """``passband`` / ``at_output_nyquist`` / ``stopband``.

    A tone exactly at the output Nyquist is its own class and is excluded from
    both aggregates: it is neither something a resampler should keep nor
    something it should remove, and a decoder that annihilates it is not thereby
    a decoder with a 300 dB passband droop.
    """

    nyquist = TARGET_RATE_HZ / 2.0
    if freq_hz < nyquist:
        return "passband"
    return "at_output_nyquist" if freq_hz == nyquist else "stopband"


def spectrum_row(vector: Any, freq_hz: float) -> dict[str, Any]:
    import numpy as np  # noqa: PLC0415

    edge = int(EDGE_SECONDS * TARGET_RATE_HZ)
    trimmed = vector[edge:-edge] if vector.size > 2 * edge else vector
    trimmed = trimmed - trimmed.mean()
    power = np.abs(np.fft.rfft(trimmed)) ** 2
    freqs = np.fft.rfftfreq(trimmed.size, d=1.0 / TARGET_RATE_HZ)
    total = float(power.sum())
    target = folded_frequency(freq_hz)
    in_bin = float(power[np.abs(freqs - target) <= BIN_HALF_WIDTH_HZ].sum())
    rms = float(np.sqrt(np.mean(trimmed**2)))
    return {
        "landed_at_hz": round(target, 3),
        "output_rms_dbfs": round(20.0 * math.log10(max(rms, 1e-12) / 32767.0), 4),
        "share_at_landing_bin": round(in_bin / total, 9) if total > 0 else 0.0,
    }


def reference_dbfs() -> float:
    return round(20.0 * math.log10(TONE_AMPLITUDE / math.sqrt(2.0)), 4)


def tone_table(binary: Path | None, workdir: Path) -> list[dict[str, Any]]:
    n_samples = int(TONE_SECONDS * SOURCE_RATE_HZ)
    probe = workdir / "tone.wav"
    rows: list[dict[str, Any]] = []
    for freq in TONE_FREQUENCIES_HZ:
        probe.write_bytes(tone_wav(freq, n_samples))
        row: dict[str, Any] = {
            "frequency_hz": freq,
            "band": band_class(freq),
            "study_soxr_hq": spectrum_row(decode_study(probe), freq),
        }
        if binary is not None:
            _, _, vector = decode_miniaudio(binary, probe)
            row["llama_cpp_miniaudio_linear"] = spectrum_row(vector, freq)
        rows.append(row)
    return rows


def length_table(binary: Path | None, workdir: Path) -> list[dict[str, Any]]:
    probe = workdir / "length.wav"
    rows: list[dict[str, Any]] = []
    for n_in in LENGTH_PROBE_SAMPLES:
        probe.write_bytes(tone_wav(440.0, n_in))
        study = decode_study(probe)
        row: dict[str, Any] = {
            "input_samples_24k": n_in,
            "input_samples_mod_3": n_in % 3,
            "input_seconds": round(n_in / SOURCE_RATE_HZ, 9),
            "floor_two_thirds": (2 * n_in) // 3,
            "ceil_two_thirds": -((-2 * n_in) // 3),
            "study_soxr_hq_output_samples": int(study.size),
            "study_soxr_hq_output_seconds": round(study.size / TARGET_RATE_HZ, 9),
        }
        if binary is not None:
            frame_count, frames_read, vector = decode_miniaudio(binary, probe)
            row["llama_cpp_frame_count"] = frame_count
            row["llama_cpp_frames_read"] = frames_read
            row["llama_cpp_output_seconds"] = round(frame_count / TARGET_RATE_HZ, 9)
            row["llama_cpp_short_read_zero_pad_samples"] = frame_count - frames_read
            row["llama_cpp_dropped_seconds_vs_source"] = round(
                n_in / SOURCE_RATE_HZ - frame_count / TARGET_RATE_HZ, 9
            )
            if int(vector.size) != frame_count:
                raise AuditError("the harness returned a different count than it printed")
        rows.append(row)
    return rows


def verdicts(
    tones: Sequence[Mapping[str, Any]], lengths: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Turn the two tables into the claims the audit note states."""

    reference = reference_dbfs()
    out: dict[str, Any] = {"reference_tone_dbfs": reference}
    for key, label in (
        ("study_soxr_hq", "study_soxr_hq"),
        ("llama_cpp_miniaudio_linear", "llama_cpp_miniaudio_linear"),
    ):
        rows = [row for row in tones if key in row]
        if not rows:
            continue
        passband = [row for row in rows if row["band"] == "passband"]
        stopband = [row for row in rows if row["band"] == "stopband"]
        out[label] = {
            "passband_worst_attenuation_db": round(
                max(reference - row[key]["output_rms_dbfs"] for row in passband), 4
            ),
            "passband_worst_attenuation_at_hz": max(
                passband, key=lambda row: reference - row[key]["output_rms_dbfs"]
            )["frequency_hz"],
            "passband_min_share_at_own_frequency": round(
                min(row[key]["share_at_landing_bin"] for row in passband), 9
            ),
            "stopband_worst_leakage_db_below_input": round(
                min(reference - row[key]["output_rms_dbfs"] for row in stopband), 4
            ),
            "stopband_worst_leakage_at_hz": min(
                stopband, key=lambda row: reference - row[key]["output_rms_dbfs"]
            )["frequency_hz"],
            "stopband_max_output_dbfs": round(
                max(row[key]["output_rms_dbfs"] for row in stopband), 4
            ),
            "at_output_nyquist_output_dbfs": [
                {
                    "frequency_hz": row["frequency_hz"],
                    "output_rms_dbfs": row[key]["output_rms_dbfs"],
                }
                for row in rows
                if row["band"] == "at_output_nyquist"
            ],
        }
    if any("llama_cpp_frame_count" in row for row in lengths):
        out["output_length_rule"] = {
            "llama_cpp_always_floor_two_thirds": all(
                row["llama_cpp_frame_count"] == row["floor_two_thirds"] for row in lengths
            ),
            "study_always_ceil_two_thirds": all(
                row["study_soxr_hq_output_samples"] == row["ceil_two_thirds"]
                for row in lengths
            ),
            "llama_cpp_max_dropped_seconds": round(
                max(row["llama_cpp_dropped_seconds_vs_source"] for row in lengths), 9
            ),
            "llama_cpp_short_read_zero_pad_observed": any(
                row["llama_cpp_short_read_zero_pad_samples"] > 0 for row in lengths
            ),
        }
    else:
        out["study_always_ceil_two_thirds"] = all(
            row["study_soxr_hq_output_samples"] == row["ceil_two_thirds"] for row in lengths
        )
    return out


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def tone_csv(tones: Sequence[Mapping[str, Any]]) -> str:
    header = (
        "frequency_hz,band,landed_at_hz,"
        "miniaudio_output_rms_dbfs,miniaudio_share_at_landing_bin,"
        "soxr_hq_output_rms_dbfs,soxr_hq_share_at_landing_bin\n"
    )
    lines = [header]
    for row in tones:
        mini = row.get("llama_cpp_miniaudio_linear")
        soxr = row["study_soxr_hq"]
        lines.append(
            "%d,%s,%.3f,%s,%s,%.4f,%.9f\n"
            % (
                int(row["frequency_hz"]),
                str(row["band"]),
                float(soxr["landed_at_hz"]),
                f"{mini['output_rms_dbfs']:.4f}" if mini else "",
                f"{mini['share_at_landing_bin']:.9f}" if mini else "",
                float(soxr["output_rms_dbfs"]),
                float(soxr["share_at_landing_bin"]),
            )
        )
    return "".join(lines)


def run(checkout: Path, *, write: bool, attempts_count: int) -> dict[str, Any]:
    import importlib.metadata as metadata  # noqa: PLC0415

    pinned = pin_checkout(checkout)
    with tempfile.TemporaryDirectory() as tmp:
        workdir = Path(tmp)
        binary, harness_note = build_harness(checkout, workdir)
        tones = tone_table(binary, workdir)
        lengths = length_table(binary, workdir)
    summary: dict[str, Any] = {
        "schema": "saea-a2t-input-rate-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": "SAEA-A2T-MF-INPUT-RATE-AUDIT-V1",
        "execution_profile": "model-free-check",
        "question": (
            "Audio2Tool release wavs are 24 kHz mono; the Qwen3-Omni front end wants "
            "16 kHz. Nothing in this study converts them, so WHICH resampler runs, "
            "with WHICH filter, and what does that cost against converting them "
            "ourselves with librosa first?"
        ),
        "source_rate_hz": SOURCE_RATE_HZ,
        "target_rate_hz": TARGET_RATE_HZ,
        "pinned_llama_cpp": pinned,
        "the_wire": {
            "study_sends": (
                "core/model/transport.py::_load_audio_part -- "
                "base64.b64encode(media.read_bytes()) into an input_audio part with "
                "format taken from the file suffix. The sealed bytes go out verbatim: "
                "no resample, no trim, no normalization, no re-encode."
            ),
            "server_forwards": (
                "tools/server/server-common.cpp handle_media base64-decodes the string "
                "straight into a raw_buffer and hands file.data()/file.size() to "
                "mtmd_helper_bitmap_init_from_buf. Nothing between the wire and "
                "miniaudio inspects or converts the bytes."
            ),
            "conversion_happens_in": (
                "tools/mtmd/mtmd-helper.cpp::decode_audio_from_buf -- miniaudio, "
                "ma_decoder_config_init(ma_format_f32, 1, mtmd_get_audio_sample_rate) "
                "= 16000, which for a 24 kHz file is a RESAMPLE, not a format cast"
            ),
        },
        "decoders": {
            "llama_cpp_miniaudio_linear": {
                "library": "miniaudio 0.11.25 (vendored, unmodified from upstream)",
                "algorithm": "ma_resample_algorithm_linear",
                "algorithm_note": (
                    "miniaudio's own comment on the enum: 'Fastest, lowest quality. "
                    "Optional low-pass filtering. Default.'"
                ),
                "interpolation": "two-tap linear between x0 and x1",
                "low_pass": (
                    "ma_lpf, a high-order Butterworth, order 4 by default "
                    "(MA_DEFAULT_RESAMPLER_LPF_ORDER), applied BEFORE decimation, "
                    "cutoff min(in,out)/2 = 8000 Hz"
                ),
                "step": "fixed point, 1.5 input frames per output frame (gcf-reduced 3:2)",
                "measured": binary is not None,
                "harness": harness_note,
            },
            "study_soxr_hq": {
                "library": (
                    f"librosa {metadata.version('librosa')} / soxr "
                    f"{metadata.version('soxr')}"
                ),
                "algorithm": "res_type 'soxr_hq' (librosa.load's default)",
                "entry_point": "reproduction.obs_loop.decode_parent_pcm",
                "int16_quantization": "clip(rint(float32 * 32767.0), -32768, 32767)",
                "measured": True,
            },
        },
        "tone_probe": {
            "method": (
                f"one {TONE_SECONDS:.1f} s pure tone per frequency at amplitude "
                f"{TONE_AMPLITUDE}, synthesized at {SOURCE_RATE_HZ} Hz as mono int16 "
                f"wav, decoded to {TARGET_RATE_HZ} Hz by each decoder, "
                f"{EDGE_SECONDS * 1000:.0f} ms of each edge dropped, then the output "
                f"energy split into a +/-{BIN_HALF_WIDTH_HZ:.0f} Hz bin at the "
                "frequency the tone should land on and everything else"
            ),
            "reference_tone_dbfs": reference_dbfs(),
            "rows": tones,
        },
        "length_probe": {
            "method": (
                "a 440 Hz tone at input lengths covering every n mod 3, so the two "
                "decoders' output-length rules are measured rather than derived"
            ),
            "rows": lengths,
        },
        "verdicts": verdicts(tones, lengths),
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "paid_api_spend": 0,
            "llama_cpp_targets_built": 0,
            "llama_cpp_binaries_executed": 0,
            "llama_cpp_files_written": 0,
            "dataset_media_files_opened": 0,
            "outbound_connection_attempts": attempts_count,
        },
        "opened": {
            "gold_labels": 0,
            "reference_transcripts": 0,
            "evaluation_query_text": 0,
            "tool_registry_rows": 0,
            "sealed_outputs": 0,
            "scores": 0,
            "note": (
                "NO DATASET BYTES AT ALL. Every sample measured here is a synthetic "
                "tone this script generated; the only files read from disk are the "
                "pinned llama.cpp sources, which are C and C++ text."
            ),
        },
        "test_split_read": False,
        "deterministic": (
            "this receipt carries no timestamp: two back-to-back writes reproduce the "
            "same MANIFEST.sha256"
        ),
        "authorizes": (
            "nothing. No cell is flown, no media is built, no request is made and no "
            "conclusion about Audio2Tool accuracy is licensed."
        ),
    }
    summary["summary_sha256"] = canonical_sha256(
        {key: value for key, value in summary.items() if key != "summary_sha256"}
    )
    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_json_artifact(OUT_DIR / "summary.json", summary)
        (OUT_DIR / "tone-response.csv").write_text(tone_csv(tones), encoding="utf-8")
        write_manifest(OUT_DIR)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkout",
        default=os.environ.get("SAEA_LLAMA_CPP_CHECKOUT", DEFAULT_CHECKOUT),
        help="the pinned llama.cpp-featcache checkout (read-only)",
    )
    parser.add_argument("--write", action="store_true", help="write the receipt")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    summary = run(Path(args.checkout), write=args.write, attempts_count=attempts.count)
    verdict = summary["verdicts"]
    print(
        "pinned llama.cpp %s, %d cited sources re-hashed, tree clean"
        % (
            summary["pinned_llama_cpp"]["build_commit"][:12],
            len(summary["pinned_llama_cpp"]["cited_sources"]),
        )
    )
    for key in ("llama_cpp_miniaudio_linear", "study_soxr_hq"):
        if key not in verdict:
            print(f"{key}: NOT MEASURED ({summary['decoders'][key].get('harness', '')})")
            continue
        row = verdict[key]
        print(
            "%s: passband worst -%.2f dB at %d Hz (min share at own frequency %.4f); "
            "above 8 kHz the worst leak is only %.2f dB below the input, at %d Hz"
            % (
                key,
                row["passband_worst_attenuation_db"],
                row["passband_worst_attenuation_at_hz"],
                row["passband_min_share_at_own_frequency"],
                row["stopband_worst_leakage_db_below_input"],
                row["stopband_worst_leakage_at_hz"],
            )
        )
    if "output_length_rule" in verdict:
        rule = verdict["output_length_rule"]
        print(
            "lengths: llama.cpp floor(2n/3) %s, study ceil(2n/3) %s, worst drop %.9f s, "
            "short-read zero pad observed %s"
            % (
                rule["llama_cpp_always_floor_two_thirds"],
                rule["study_always_ceil_two_thirds"],
                rule["llama_cpp_max_dropped_seconds"],
                rule["llama_cpp_short_read_zero_pad_observed"],
            )
        )
    if not args.write:
        print("(print only; pass --write to land the receipt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
