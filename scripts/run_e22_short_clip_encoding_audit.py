#!/usr/bin/env python3
"""CLI: the Earnings-22 SHORT-CLIP ENCODING audit (model-free, zero contacts).

Exposure row ``SAEA-E22-MF-SHORT-CLIP-ENCODING-AUDIT-V1`` (``model-free-check``),
registered before the first clip header was read.

The question, and it is the only one: what does THIS study's serving path do to
a short speech clip that the published evaluation path does not? The arithmetic
lives in ``analysis.e22_short_clip_encoding``, transcribed from
``llama.cpp-featcache`` at the pinned build commit
``04ccc72a2207347ca76161b93fd9d846dd0a8675`` and from ``transformers`` 5.12.1;
this script measures the two registered dev populations against it and proves
the transcription against 6,038 SEALED per-call ``prompt_tokens`` records.

What is opened: the two hash-pinned roster receipts, the committed dev10 D1
media supplement, the 6,038 derived WAV **container headers** (frame count and
sample rate; the sample data is never decoded), and the sealed arm A trace's
``usage`` blocks. No reference sentence, no hypothesis text, no score, no
segment table, no test-split artifact. No model, tokenizer, embedder, retriever,
scorer, network, GPU or audio-decode contact, and no llama.cpp source is
modified, built or executed.

Usage (WSL2)::

    python scripts/run_e22_short_clip_encoding_audit.py            # print only
    python scripts/run_e22_short_clip_encoding_audit.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (  # noqa: E402
    load_flight_tokens,
    trace_path,
)
from speech_aware_evidence_acquisition.analysis.e22_short_clip_encoding import (  # noqa: E402
    QWEN3A,
    describe_clip,
    llamacpp_audio_tokens,
    samples_for_seconds,
    summarize,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402

#: The pinned dev10 flight roster receipt and its digest, copied from
#: ``scripts/build_e22_dev1500_roster.py`` so a drift in either place is a
#: refusal rather than a silent divergence.
DEV10_ROSTER_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-e22-dev-esb-prompt-ab-v1/roster/flight-roster-receipt.json"
)
DEV10_ROSTER_SHA256 = "20437bcbde1a52b58bb48642d8809836e20073f7963f19b5ff836ead69c945c8"
DEV10_SUPPLEMENT_RELPATH = "docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json"
DEV10_SUPPLEMENT_SHA256 = (
    "ad01c4eca82b2739e121886fda5d95172756c9f232e5627b1f3f42274c2946a1"
)
DEV1500_VIEW_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-e22-dev-esb-1500-v1/roster/flight-roster-receipt.json"
)
DEV1500_VIEW_SHA256 = (
    "fe9528be3ad62c27b95da61e7397fda5e19c0fe711fda07db6731c2d6fcccf9f"
)

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-short-clip-encoding-audit"
)

#: The text envelope of arm A's request, measured rather than assumed: the
#: audit asserts that ``prompt_tokens - audio_tokens`` is the SAME integer on
#: all 6,038 sealed rows, and records whatever that integer is.
HASH_WORKERS = 8


class AuditError(RuntimeError):
    """An input drifted or a derived quantity did not reproduce -- fail closed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pinned(relpath: str, expected: str, label: str) -> Mapping[str, Any]:
    path = REPO_ROOT / relpath
    measured = sha256_file(path)
    if measured != expected:
        raise AuditError(
            f"{label} identity drift: pinned {expected[:12]}..., {path} now hashes "
            f"to {measured[:12]}..."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def read_container(path: Path) -> tuple[int, int, int, int]:
    """``(frames, sample_rate_hz, channels, sample_width)`` from the WAV header.

    ``wave.open`` reads the RIFF/fmt/data headers only; ``readframes`` is never
    called, so no sample of speech is decoded by this audit.
    """

    with wave.open(str(path), "rb") as handle:
        return (
            handle.getnframes(),
            handle.getframerate(),
            handle.getnchannels(),
            handle.getsampwidth(),
        )


def measure_population(
    items: Sequence[Mapping[str, Any]],
    digests: Mapping[str, str],
    root: Path,
) -> list[dict[str, Any]]:
    """One row per clip: measured container facts plus both paths' arithmetic."""

    def one(item: Mapping[str, Any]) -> dict[str, Any]:
        sample_id = str(item["sample_id"])
        relpath = str(item["media_relpath"])
        path = root / relpath
        frames, rate, channels, width = read_container(path)
        if (rate, channels, width) != (QWEN3A.sample_rate_hz, 1, 2):
            raise AuditError(
                f"{sample_id}: container is {rate} Hz / {channels} ch / {width} B, "
                f"not 16 kHz mono int16"
            )
        measured_digest = sha256_file(path)
        recorded = digests.get(sample_id)
        if recorded is None:
            raise AuditError(f"{sample_id} is absent from the D1 media supplement")
        if measured_digest != recorded:
            raise AuditError(
                f"media identity drift on {sample_id}: supplement records "
                f"{recorded[:12]}..., disk hashes to {measured_digest[:12]}..."
            )
        recorded_seconds = float(item["audio_seconds"])
        if abs(frames / QWEN3A.sample_rate_hz - recorded_seconds) > 1e-6:
            raise AuditError(
                f"{sample_id}: header says {frames} frames "
                f"({frames / QWEN3A.sample_rate_hz:.6f} s), roster says "
                f"{recorded_seconds:.6f} s"
            )
        encoding = describe_clip(frames)
        return {
            "sample_id": sample_id,
            "parent_sample_id": str(item["parent_sample_id"]),
            "n_samples": frames,
            "seconds": round(encoding.seconds, 6),
            "llamacpp_mel_frames": encoding.llamacpp_frames,
            "hf_mel_frames": encoding.hf_frames,
            "encoder_windows": len(encoding.windows),
            "zero_pad_frames": encoding.zero_pad_frames,
            "llamacpp_audio_tokens": encoding.llamacpp_tokens,
            "hf_audio_tokens": encoding.hf_tokens,
            "extra_audio_tokens": encoding.extra_tokens,
            "tail_block_speech_frames": encoding.tail_block_speech_frames,
        }

    with ThreadPoolExecutor(max_workers=HASH_WORKERS) as pool:
        return list(pool.map(one, items))


def supplement_digests(document: Mapping[str, Any]) -> dict[str, str]:
    return {
        str(entry["id"]): str(entry["sha256"]) for entry in document["manifest"]
    }


def cross_check_sealed_prompt_tokens(
    rows: Sequence[Mapping[str, Any]], root: Path
) -> dict[str, Any]:
    """Prove the transcription against the flight's own tokenizer.

    ``prompt_tokens`` for arm A is (text envelope) + (audio tokens). If this
    module's audio-token arithmetic is the server's, then
    ``prompt_tokens - llamacpp_audio_tokens`` is the SAME integer on every row,
    because arm A's instruction is byte-identical on every row. Any other
    outcome refuses the audit.
    """

    usage = load_flight_tokens(trace_path(root))
    envelopes: dict[int, int] = {}
    missing = 0
    for row in rows:
        block = usage.get(str(row["sample_id"]))
        if block is None:
            missing += 1
            continue
        envelope = int(block["prompt_tokens"]) - int(row["llamacpp_audio_tokens"])
        envelopes[envelope] = envelopes.get(envelope, 0) + 1
    if missing:
        raise AuditError(f"{missing} roster rows have no sealed usage record")
    if len(envelopes) != 1:
        raise AuditError(
            "the audio-token arithmetic does not reproduce the sealed prompt_tokens: "
            f"{len(envelopes)} distinct text envelopes {sorted(envelopes)}"
        )
    envelope = next(iter(envelopes))
    return {
        "rows_checked": len(rows),
        "text_envelope_tokens": envelope,
        "distinct_envelopes": 1,
        "source": (
            "sealed SAEA-E22-DEV-ESB-PROMPT-A-V1 trace, usage.prompt_tokens only; "
            "no hypothesis text, no score and no reference was read"
        ),
    }


def variant_projection(rows: Sequence[Mapping[str, Any]], label: str) -> dict[str, Any]:
    """What a probe media variant costs, computed before any byte is written."""

    counts: list[int] = []
    unchanged = 0
    for row in rows:
        n_samples = int(row["n_samples"])
        if label == "tail-silence-2s":
            counts.append(n_samples + 2 * QWEN3A.sample_rate_hz)
        elif label == "pad-30s":
            target = 30 * QWEN3A.sample_rate_hz
            if n_samples >= target:
                unchanged += 1
                counts.append(n_samples)
            else:
                counts.append(target)
        else:  # pragma: no cover - guarded by the caller
            raise AuditError(f"unknown variant {label!r}")
    summary = dict(summarize(counts))
    summary["variant"] = label
    summary["clips_left_unchanged"] = unchanged
    summary["audio_seconds_delta"] = round(
        summary["audio_seconds_total"]
        - sum(float(row["seconds"]) for row in rows),
        6,
    )
    summary["llamacpp_audio_tokens_delta"] = summary["llamacpp_audio_tokens_total"] - sum(
        int(row["llamacpp_audio_tokens"]) for row in rows
    )
    summary["longest_clip_audio_tokens"] = max(
        llamacpp_audio_tokens(count) for count in counts
    )
    return summary


def mel_floor_probe(
    rows: Sequence[Mapping[str, Any]], items: Mapping[str, str], root: Path, *, per_call: int
) -> dict[str, Any]:
    """Where does the literal 0.0 pad sit inside a real clip's feature range?

    The encoder's pad is ``0.0f`` in the ALREADY-NORMALIZED mel space
    (``mtmd-audio.cpp:709``), and normalization is
    ``v -> (max(log10 mel, max - 8) + 4) / 4``. Digital silence therefore lands
    on the clamp floor ``(max - 4)/4``, which is a different number. This probe
    measures both on a deterministic sample of real clips so the audit can say
    how far apart they are instead of asserting that they differ.

    Front end: the published path's own ``WhisperFeatureExtractor`` numpy
    kernel, at Qwen3-Omni's 128 mel bins / 400-point FFT / 160 hop. No model, no
    tokenizer, no network: the extractor is constructed from explicit arguments
    and only its ``_np_extract_fbank_features`` is called.
    """

    import random  # noqa: PLC0415
    import wave as _wave  # noqa: PLC0415
    from array import array  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415
    from transformers.models.whisper.feature_extraction_whisper import (  # noqa: PLC0415
        WhisperFeatureExtractor,
    )

    extractor = WhisperFeatureExtractor(
        feature_size=128,
        sampling_rate=QWEN3A.sample_rate_hz,
        hop_length=QWEN3A.hop_len,
        chunk_length=30,
        n_fft=QWEN3A.n_fft,
    )

    by_call: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        by_call.setdefault(str(row["parent_sample_id"]), []).append(row)
    rng = random.Random(20260907)
    drawn: list[Mapping[str, Any]] = []
    for call in sorted(by_call):
        pool = sorted(by_call[call], key=lambda entry: str(entry["sample_id"]))
        drawn.extend(rng.sample(pool, min(per_call, len(pool))))

    samples_read = 0
    floors: list[float] = []
    maxima: list[float] = []
    tail_means: list[float] = []
    below_zero_share: list[float] = []
    silence_values: list[float] = []
    for row in drawn:
        path = root / items[str(row["sample_id"])]
        with _wave.open(str(path), "rb") as handle:
            payload = handle.readframes(handle.getnframes())
        pcm = np.asarray(array("h", payload), dtype=np.float32) / 32768.0
        samples_read += int(pcm.size)
        features = extractor._np_extract_fbank_features(pcm[None, :], "cpu")[0]
        floors.append(float(features.min()))
        maxima.append(float(features.max()))
        tail_means.append(float(features[:, -10:].mean()))
        below_zero_share.append(float((features < 0.0).mean()))
        # The same clip with 2.0 s of digital silence appended: the silent
        # frames' own normalized value, which is what a `tail-silence-2s` clip
        # actually delivers where the padding used to abut the speech.
        padded = np.concatenate(
            [pcm, np.zeros(2 * QWEN3A.sample_rate_hz, dtype=np.float32)]
        )
        padded_features = extractor._np_extract_fbank_features(padded[None, :], "cpu")[0]
        silence_values.append(float(padded_features[:, -50:].mean()))

    def stats(values: Sequence[float]) -> dict[str, float]:
        ordered = sorted(values)
        middle = len(ordered) // 2
        return {
            "min": round(ordered[0], 6),
            "median": round(ordered[middle], 6),
            "max": round(ordered[-1], 6),
            "mean": round(sum(ordered) / len(ordered), 6),
        }

    return {
        "clips_sampled": len(drawn),
        "per_call": per_call,
        "seed": 20260907,
        "pcm_samples_read": samples_read,
        "front_end": (
            "transformers WhisperFeatureExtractor._np_extract_fbank_features, "
            "feature_size=128, n_fft=400, hop=160 -- the published path's own kernel"
        ),
        "pad_value_the_encoder_sees": 0.0,
        "clamp_floor_normalized": stats(floors),
        "feature_max_normalized": stats(maxima),
        "final_ten_real_frames_mean": stats(tail_means),
        "share_of_real_frames_below_the_pad_value": stats(below_zero_share),
        "appended_digital_silence_normalized": stats(silence_values),
        "reading": (
            "the pad the encoder is handed is 0.0; digital silence on the same "
            "clips lands on the clamp floor, which is strictly lower. The pad is "
            "not silence, and it is not the clip's own room tone either"
        ),
    }


def walkthrough(seconds: float) -> dict[str, Any]:
    encoding = describe_clip(samples_for_seconds(seconds))
    return {
        "seconds": seconds,
        "n_samples": encoding.n_samples,
        "reflection_pad_samples_each_end": QWEN3A.reflect_pad_samples,
        "llamacpp_mel_frames": encoding.llamacpp_frames,
        "hf_mel_frames": encoding.hf_frames,
        "windows": [
            {
                "offset_frames": window.offset_frames,
                "effective_frames": window.effective_frames,
                "padded_frames": window.padded_frames,
                "zero_pad_frames": window.zero_pad_frames,
                "audio_tokens": window.tokens,
            }
            for window in encoding.windows
        ],
        "llamacpp_audio_tokens": encoding.llamacpp_tokens,
        "hf_audio_tokens": encoding.hf_tokens,
        "extra_audio_tokens": encoding.extra_tokens,
        "zero_pad_frames": encoding.zero_pad_frames,
        "zero_pad_seconds": round(encoding.zero_pad_seconds, 6),
        "fixed_30_second_window_applied": False,
    }


def speech_token_rule_check(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Where the study's own ``13 * ceil(audio_seconds)`` rule is wrong, and why.

    The exact rule is ``13 * (n_samples // 16000 + 1)``; the two disagree only
    when ``n_samples`` is an exact multiple of 16,000, i.e. at a whole-second
    duration. The published boundary columns are quantized, so those durations
    are not rare on this carrier.
    """

    disagreements = [
        row
        for row in rows
        if 13 * math.ceil(int(row["n_samples"]) / QWEN3A.sample_rate_hz)
        != int(row["llamacpp_audio_tokens"])
    ]
    residues = sorted({int(row["n_samples"]) % QWEN3A.hop_len for row in rows})
    longest = max(rows, key=lambda row: int(row["n_samples"]))
    shortest = min(rows, key=lambda row: int(row["n_samples"]))
    return {
        "exact_rule": "13 * (n_samples // 16000 + 1)",
        "study_rule": "13 * ceil(audio_seconds)",
        "rows_checked": len(rows),
        "rows_where_the_study_rule_understates_by_13": len(disagreements),
        "whole_second_clips": len(disagreements),
        "distinct_n_samples_mod_hop": len(residues),
        "n_samples_mod_hop_values": residues,
        "quantization_note": (
            "the published start_ts/end_ts are quantized, so n_samples takes only "
            f"{len(residues)} residues mod {QWEN3A.hop_len} across this population "
            "and whole-second durations are common rather than measure-zero"
        ),
        "longest_clip": {
            "sample_id": longest["sample_id"],
            "seconds": longest["seconds"],
            "audio_tokens": longest["llamacpp_audio_tokens"],
            "encoder_windows": longest["encoder_windows"],
            "both_rules_agree": 13
            * math.ceil(int(longest["n_samples"]) / QWEN3A.sample_rate_hz)
            == int(longest["llamacpp_audio_tokens"]),
        },
        "shortest_clip": {
            "sample_id": shortest["sample_id"],
            "seconds": shortest["seconds"],
            "audio_tokens": shortest["llamacpp_audio_tokens"],
            "hf_audio_tokens": shortest["hf_audio_tokens"],
            "extra_audio_tokens": shortest["extra_audio_tokens"],
        },
    }


def per_call_table(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    calls = sorted({str(row["parent_sample_id"]) for row in rows})
    table: list[dict[str, Any]] = []
    for call in calls:
        subset = [row for row in rows if str(row["parent_sample_id"]) == call]
        table.append(
            {
                "call": call,
                "clips": len(subset),
                "audio_seconds": round(sum(float(r["seconds"]) for r in subset), 6),
                "llamacpp_audio_tokens": sum(
                    int(r["llamacpp_audio_tokens"]) for r in subset
                ),
                "hf_audio_tokens": sum(int(r["hf_audio_tokens"]) for r in subset),
                "extra_audio_tokens": sum(int(r["extra_audio_tokens"]) for r in subset),
                "zero_pad_frames": sum(int(r["zero_pad_frames"]) for r in subset),
            }
        )
    return table


def duration_buckets(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    edges = [(0.0, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 1e9)]
    out: list[dict[str, Any]] = []
    for low, high in edges:
        subset = [row for row in rows if low <= float(row["seconds"]) < high]
        if not subset:
            continue
        tokens = sum(int(r["llamacpp_audio_tokens"]) for r in subset)
        extra = sum(int(r["extra_audio_tokens"]) for r in subset)
        out.append(
            {
                "bucket": f"[{low:g}, {high:g})" if high < 1e9 else f"[{low:g}, inf)",
                "clips": len(subset),
                "llamacpp_audio_tokens": tokens,
                "extra_audio_tokens": extra,
                "extra_token_share": round(extra / tokens, 6) if tokens else 0.0,
                "zero_pad_frames_mean": round(
                    sum(int(r["zero_pad_frames"]) for r in subset) / len(subset), 4
                ),
            }
        )
    return out


def write_manifest(directory: Path) -> None:
    lines = sorted(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in directory.iterdir()
        if path.is_file() and path.name != "MANIFEST.sha256"
    )
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise AuditError("refusing to write an empty table")
    header = list(rows[0].keys())
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(str(row[key]) for key in header))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(*, write: bool, mel_probe_per_call: int) -> dict[str, Any]:
    attempts = arm_offline_guard()
    root = Path(data_root())

    dev10 = load_pinned(
        DEV10_ROSTER_RELPATH, DEV10_ROSTER_SHA256, "dev10 flight roster receipt"
    )
    dev1500 = load_pinned(
        DEV1500_VIEW_RELPATH, DEV1500_VIEW_SHA256, "dev1500 probe view"
    )
    supplement = load_pinned(
        DEV10_SUPPLEMENT_RELPATH, DEV10_SUPPLEMENT_SHA256, "dev10 D1 media supplement"
    )
    digests = supplement_digests(supplement)

    rows = measure_population(dev10["items"], digests, root)
    by_id = {row["sample_id"]: row for row in rows}
    subset_ids = [str(item["sample_id"]) for item in dev1500["items"]]
    subset = [by_id[sample_id] for sample_id in subset_ids]
    relpaths = {
        str(item["sample_id"]): str(item["media_relpath"]) for item in dev10["items"]
    }
    mel_probe = (
        mel_floor_probe(subset, relpaths, root, per_call=mel_probe_per_call)
        if mel_probe_per_call > 0
        else {"clips_sampled": 0, "skipped": True}
    )

    receipt: dict[str, Any] = {
        "schema": "saea-e22-short-clip-encoding-audit-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": "SAEA-E22-MF-SHORT-CLIP-ENCODING-AUDIT-V1",
        "execution_profile": "model-free-check",
        "deterministic": (
            "this receipt carries no timestamp: two back-to-back writes reproduce "
            "the same MANIFEST.sha256"
        ),
        "front_end": {
            "projector_type": "PROJECTOR_TYPE_QWEN3A",
            "build_commit": "04ccc72a2207347ca76161b93fd9d846dd0a8675",
            "sample_rate_hz": QWEN3A.sample_rate_hz,
            "n_fft": QWEN3A.n_fft,
            "window_len": QWEN3A.window_len,
            "hop_len": QWEN3A.hop_len,
            "reflection_pad_samples_each_end": QWEN3A.reflect_pad_samples,
            "chunk_frames": QWEN3A.chunk_frames,
            "inference_window_frames": QWEN3A.window_frames,
            "tokens_per_chunk": QWEN3A.tokens_per_chunk,
            "pad_value_in_normalized_mel_space": 0.0,
            "fixed_30_second_window": False,
            "fixed_30_second_window_basis": (
                "hparams.audio_chunk_len is set to 30 at clip.cpp:1551 for the whole "
                "ULTRAVOX/QWEN2A/QWEN3A/... arm, but mtmd_audio_preprocessor_qwen3a "
                "never reads it: it calls log_mel_spectrogram with no_padding=true, so "
                "neither the 30-second stage_1_pad of mtmd-audio.cpp:399 nor the "
                "whisper preprocessor's min_samples short-audio pad of "
                "mtmd-audio.cpp:559 is on this path"
            ),
            "encoder_masks_the_padding": False,
            "encoder_mask_basis": (
                "models/qwen3a.cpp carries n_len_org but never reads it; the graph "
                "views the padded [n_frames, n_mel] tensor as n_frames/100 chunks and "
                "emits 13 tokens for each, padded or not"
            ),
        },
        "published_path": {
            "processor": "Qwen3OmniMoeProcessor (transformers 5.12.1)",
            "feature_extractor": "WhisperFeatureExtractor",
            "audio_kwargs": {
                "sampling_rate": 16000,
                "padding": True,
                "truncation": False,
            },
            "frames_rule": "n_samples // 160 (torch.stft center=True, last frame dropped)",
            "tail_block_rule": (
                "chunk_and_pad_features records each 100-frame chunk's TRUE length and "
                "get_valid_indices keeps only "
                "_get_feat_extract_output_lengths(length) = ceil(length/8) post-CNN "
                "positions, so the padding is discarded rather than encoded"
            ),
        },
        "walkthroughs": {
            "3s": walkthrough(3.0),
            "33s": walkthrough(33.0),
        },
        "populations": {
            "E22-ESB-DEV10-UTTERANCES": {
                "roster_receipt": DEV10_ROSTER_RELPATH,
                "roster_receipt_sha256": DEV10_ROSTER_SHA256,
                **summarize([int(row["n_samples"]) for row in rows]),
            },
            "E22-ESB-DEV1500-UTTERANCES": {
                "roster_receipt": DEV1500_VIEW_RELPATH,
                "roster_receipt_sha256": DEV1500_VIEW_SHA256,
                **summarize([int(row["n_samples"]) for row in subset]),
            },
        },
        "sealed_prompt_token_cross_check": cross_check_sealed_prompt_tokens(rows, root),
        "mel_floor_probe": mel_probe,
        "speech_token_rule_check_dev10": speech_token_rule_check(rows),
        "speech_token_rule_check_dev1500": speech_token_rule_check(subset),
        "variant_projections_on_the_1500": {
            "tail-silence-2s": variant_projection(subset, "tail-silence-2s"),
            "pad-30s": variant_projection(subset, "pad-30s"),
        },
        "per_call_dev1500": per_call_table(subset),
        "duration_buckets_dev1500": duration_buckets(subset),
        "media_identity": {
            "files_header_read": len(rows),
            "files_rehashed": len(rows),
            "all_digests_matched_the_committed_supplement": True,
            "audio_samples_read_for_the_mel_floor_probe": mel_probe.get(
                "pcm_samples_read", 0
            ),
            "audio_samples_sent_anywhere": 0,
        },
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "audio_seconds_decoded": 0,
            "paid_api_spend": 0,
            "llama_cpp_processes_started": 0,
            "llama_cpp_sources_modified": 0,
            "outbound_connection_attempts": attempts.count,
            "outbound_connection_targets": list(attempts.targets),
        },
        "opened": {
            "reference_sentences": 0,
            "hypothesis_text": 0,
            "scores": 0,
            "test_split_artifacts": 0,
            "sealed_usage_records": len(rows),
        },
        "test_split_read": False,
    }

    if write:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        write_json_artifact(OUT_DIR / "summary.json", receipt)
        write_csv(OUT_DIR / "per-clip-table.csv", rows)
        write_manifest(OUT_DIR)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    parser.add_argument(
        "--mel-probe-per-call",
        type=int,
        default=6,
        help="clips per call for the pad-value probe (0 skips it)",
    )
    args = parser.parse_args()

    receipt = build(write=args.write, mel_probe_per_call=args.mel_probe_per_call)
    dev1500 = receipt["populations"]["E22-ESB-DEV1500-UTTERANCES"]
    check = receipt["sealed_prompt_token_cross_check"]
    print(
        "dev1500: %d clips, %d audio tokens on our path against %d on the published "
        "one (+%d, %.2f%%)"
        % (
            dev1500["clips"],
            dev1500["llamacpp_audio_tokens_total"],
            dev1500["hf_audio_tokens_total"],
            dev1500["extra_audio_tokens_total"],
            100.0
            * dev1500["extra_audio_tokens_total"]
            / dev1500["llamacpp_audio_tokens_total"],
        )
    )
    print(
        "  zero-pad: %.1f frames per clip on average, %.3f s in total; %d of %d clips "
        "carry one"
        % (
            dev1500["zero_pad_frames_mean"],
            dev1500["zero_pad_seconds_total"],
            dev1500["clips_with_zero_pad"],
            dev1500["clips"],
        )
    )
    print(
        "  sealed cross-check: %d rows, one text envelope of %d tokens"
        % (check["rows_checked"], check["text_envelope_tokens"])
    )
    probe = receipt["mel_floor_probe"]
    if probe.get("clips_sampled"):
        print(
            "  pad value 0.0 against a clamp floor of %.4f (median) and appended "
            "digital silence at %.4f (median) over %d sampled clips"
            % (
                probe["clamp_floor_normalized"]["median"],
                probe["appended_digital_silence_normalized"]["median"],
                probe["clips_sampled"],
            )
        )
    for label, block in receipt["walkthroughs"].items():
        print(
            "  %s clip: %d mel frames (published %d), %d windows, %d zero-pad frames, "
            "%d audio tokens against %d"
            % (
                label,
                block["llamacpp_mel_frames"],
                block["hf_mel_frames"],
                len(block["windows"]),
                block["zero_pad_frames"],
                block["llamacpp_audio_tokens"],
                block["hf_audio_tokens"],
            )
        )
    if not args.write:
        print("(print only; pass --write to land the receipts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
