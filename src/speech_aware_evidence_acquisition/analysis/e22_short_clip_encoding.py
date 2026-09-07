"""What the llama.cpp mtmd audio front end does to ONE short speech clip.

Model-free arithmetic only. Every constant and every branch below is a
transcription of source this study does not own and does not modify:
``llama.cpp-featcache`` at the pinned build commit
``04ccc72a2207347ca76161b93fd9d846dd0a8675`` (the commit the E22 dev arms were
served from, recorded in ``docs/receipts/runtime-q4km-featcache-04ccc72a.json``),
and ``transformers`` 5.12.1 as installed in the shared WSL environment. Nothing
here imports torch, numpy, librosa or the package's own heavy modules, nothing
here opens a socket, and nothing here is a measurement of a model.

The two paths, stated once so the functions below are readable
-------------------------------------------------------------

**Our path** (`raw-audio-mmproj`): the WAV bytes go to ``llama-server`` as an
``input_audio`` content part; ``mtmd_helper_bitmap_init_from_buf``
(``tools/mtmd/mtmd-helper.cpp``) decodes them with miniaudio to mono float32 at
``mtmd_get_audio_sample_rate`` = 16 kHz, and — because this study's clips are
already 16 kHz mono int16 — that conversion is a format cast with no resample.
The Qwen3-Omni mmproj declares ``PROJECTOR_TYPE_QWEN3A``
(``tools/mtmd/clip-impl.h:347``), so ``mtmd.cpp:685`` selects
``mtmd_audio_preprocessor_qwen3a`` (``tools/mtmd/mtmd-audio.cpp:640``), which:

1. reflection-pads ``n_fft/2 = 200`` samples at each end (``mtmd-audio.cpp:653``),
   matching ``torch.stft(center=True, pad_mode="reflect")``;
2. computes the log10 mel spectrogram with ``no_padding = true`` — so the
   30-second ``stage_1_pad`` of ``log_mel_spectrogram``
   (``mtmd-audio.cpp:399``) is NOT taken, and neither is the whisper
   preprocessor's ``min_samples = sample_rate * (audio_chunk_len + 1)``
   short-audio zero-pad (``mtmd-audio.cpp:559``). **There is no fixed 30-second
   window anywhere on this path**, even though ``hparams.audio_chunk_len`` is
   still set to 30 at ``clip.cpp:1551``;
3. normalizes whisper-style over the WHOLE clip: ``v -> (max(v, max-8) + 4)/4``
   (``mtmd-audio.cpp:679``);
4. keeps ``n_eff = n_samples // hop + 1`` frames (``mtmd-audio.cpp:689``);
5. splits into inference windows of ``window_size = 800`` frames and pads the
   LAST window of each split up to a multiple of ``chunk_size = 100`` frames
   **with the literal float 0.0** (``mtmd-audio.cpp:709``, ``out.data.assign(...,
   0.0f)``);
6. hands every window to the encoder as its own ``MTMD_INPUT_CHUNK_TYPE_AUDIO``
   chunk (``mtmd.cpp:1300``) worth ``(n_frames / 100) * 13`` tokens
   (``clip.cpp:3398``). ``models/qwen3a.cpp`` applies **no mask** over the
   padded frames: ``n_len_org`` is carried but never read by the graph.

**The published path** (HF ``Qwen3OmniMoeProcessor``, transformers 5.12.1):
``WhisperFeatureExtractor`` with the processor's own audio defaults
``{"sampling_rate": 16000, "padding": True, "truncation": False}``
(``processing_qwen3_omni_moe.py:98``). ``torch.stft`` then
``magnitudes = stft[..., :-1]`` (``feature_extraction_whisper.py:150``) — the
last STFT frame is DROPPED — so the frame count is ``n_samples // hop``,
exactly one less than ours. The processor keeps a ``feature_attention_mask``
and the model's ``chunk_and_pad_features`` / ``get_valid_indices``
(``modeling_qwen3_omni_moe.py:643`` and ``:678``) record each 100-frame chunk's
TRUE length, so the tail chunk yields
``_get_feat_extract_output_lengths(r) = ceil(r/8)`` tokens for a remainder of
``r`` frames and the padding is discarded rather than encoded.

Consequence, and it is the whole point of this module: for the same waveform
our path emits ``13 - ceil(r/8)`` MORE audio tokens than the published path,
where ``r = (n_samples // 160) % 100``, and the extra tokens are computed from a
block that is ``99 - r`` frames of literal zero. On a 3-second clip that is 13
of 52 tokens (25 %); on a 33-second clip it is 13 of 442 (2.9 %).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

__all__ = [
    "QWEN3A",
    "FrontEnd",
    "Window",
    "ClipEncoding",
    "describe_clip",
    "hf_audio_tokens",
    "hf_mel_frames",
    "llamacpp_audio_tokens",
    "llamacpp_mel_frames",
    "llamacpp_windows",
    "samples_for_seconds",
    "summarize",
]


@dataclass(frozen=True)
class FrontEnd:
    """The audio hyper-parameters a ``PROJECTOR_TYPE_QWEN3A`` mmproj forces.

    ``sample_rate_hz`` / ``n_fft`` / ``window_len`` / ``hop_len`` are hard-coded
    at ``tools/mtmd/clip.cpp:1551-1555`` for the whole
    ULTRAVOX/QWEN2A/QWEN3A/GLMA/VOXTRAL/MERALION/MUSIC_FLAMINGO arm, i.e. they
    are NOT read from the GGUF; ``chunk_frames`` (100), ``window_frames`` (800)
    and ``tokens_per_chunk`` (13) are hard-coded in the qwen3a preprocessor and
    graph (``mtmd-audio.cpp:706-708``, ``clip.cpp:3398-3403``,
    ``models/qwen3a.cpp:11``).
    """

    sample_rate_hz: int = 16000
    n_fft: int = 400
    window_len: int = 400
    hop_len: int = 160
    chunk_frames: int = 100
    window_frames: int = 800
    tokens_per_chunk: int = 13

    @property
    def reflect_pad_samples(self) -> int:
        """``const int pad = hparams.audio_n_fft / 2`` (``mtmd-audio.cpp:653``)."""

        return self.n_fft // 2

    @property
    def chunk_seconds(self) -> float:
        return self.chunk_frames * self.hop_len / self.sample_rate_hz

    @property
    def window_seconds(self) -> float:
        return self.window_frames * self.hop_len / self.sample_rate_hz


#: The only front end this study serves. Named so every caller can see which
#: constants it is reasoning about rather than inlining 100 / 800 / 13.
QWEN3A = FrontEnd()


@dataclass(frozen=True)
class Window:
    """One ``mtmd`` audio chunk: a separate encoder invocation and its tokens."""

    offset_frames: int
    effective_frames: int
    padded_frames: int
    tokens: int

    @property
    def zero_pad_frames(self) -> int:
        return self.padded_frames - self.effective_frames


@dataclass(frozen=True)
class ClipEncoding:
    """Everything both paths do to one clip, side by side."""

    n_samples: int
    seconds: float
    #: ``mtmd-audio.cpp:689`` -- ``n_samples // hop + 1``.
    llamacpp_frames: int
    #: ``feature_extraction_whisper.py:150`` -- ``n_samples // hop``.
    hf_frames: int
    windows: tuple[Window, ...]
    llamacpp_tokens: int
    hf_tokens: int
    zero_pad_frames: int

    @property
    def extra_tokens(self) -> int:
        """Audio tokens our path charges that the published path does not."""

        return self.llamacpp_tokens - self.hf_tokens

    @property
    def zero_pad_seconds(self) -> float:
        return self.zero_pad_frames * QWEN3A.hop_len / QWEN3A.sample_rate_hz

    @property
    def extra_token_share(self) -> float:
        """The extra tokens as a share of what our path actually sends."""

        return self.extra_tokens / self.llamacpp_tokens if self.llamacpp_tokens else 0.0

    @property
    def tail_block_speech_frames(self) -> int:
        """Real mel frames inside the padded tail block (0 when it is exact)."""

        if self.zero_pad_frames == 0:
            return 0
        return QWEN3A.chunk_frames - self.zero_pad_frames


def samples_for_seconds(seconds: float, front_end: FrontEnd = QWEN3A) -> int:
    """Sample count for a duration, by this study's own slicer convention.

    ``scripts/build_e22_esb_utterance_roster.py::_cut_one_call`` cuts on
    ``int(round(t * 16000))``, so a duration maps to samples by rounding, never
    by truncation.
    """

    return int(round(seconds * front_end.sample_rate_hz))


def llamacpp_mel_frames(n_samples: int, front_end: FrontEnd = QWEN3A) -> int:
    """``n_eff`` from ``mtmd_audio_preprocessor_qwen3a::preprocess``.

    The preprocessor reflection-pads to ``n_samples + 2 * (n_fft/2)`` and calls
    ``log_mel_spectrogram`` with ``no_padding = true``, which yields
    ``(N - frame_size)/hop + 1 = n_samples/hop + 1`` frames; ``n_eff`` then
    clamps to ``n_samples/hop + 1``, which is the same number. So the clamp is
    inert and the frame count is exactly one more than the published path's.
    """

    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    return n_samples // front_end.hop_len + 1


def hf_mel_frames(n_samples: int, front_end: FrontEnd = QWEN3A) -> int:
    """Frames the HF ``WhisperFeatureExtractor`` keeps for the same waveform.

    ``torch.stft(center=True)`` returns ``1 + n_samples // hop`` frames and
    ``_torch_extract_fbank_features`` drops the last one
    (``magnitudes = stft[..., :-1].abs() ** 2``).
    """

    if n_samples <= 0:
        raise ValueError("n_samples must be positive")
    return n_samples // front_end.hop_len


def llamacpp_windows(n_eff: int, front_end: FrontEnd = QWEN3A) -> tuple[Window, ...]:
    """The loop at ``mtmd-audio.cpp:706-727``, frame for frame.

    ``for (off = 0; off < n_eff; off += 800)``: each window takes at most 800
    effective frames, rounds them UP to a multiple of 100 with zeros, and is
    charged 13 tokens per 100-frame block.
    """

    if n_eff <= 0:
        raise ValueError("n_eff must be positive")
    windows: list[Window] = []
    offset = 0
    while offset < n_eff:
        effective = min(front_end.window_frames, n_eff - offset)
        blocks = -(-effective // front_end.chunk_frames)  # ceil
        padded = blocks * front_end.chunk_frames
        windows.append(
            Window(
                offset_frames=offset,
                effective_frames=effective,
                padded_frames=padded,
                tokens=blocks * front_end.tokens_per_chunk,
            )
        )
        offset += front_end.window_frames
    return tuple(windows)


def llamacpp_audio_tokens(n_samples: int, front_end: FrontEnd = QWEN3A) -> int:
    """Audio tokens our path sends for one clip."""

    frames = llamacpp_mel_frames(n_samples, front_end)
    return sum(window.tokens for window in llamacpp_windows(frames, front_end))


def _hf_feat_extract_output_lengths(frames: int, front_end: FrontEnd = QWEN3A) -> int:
    """``_get_feat_extract_output_lengths`` (``processing_qwen3_omni_moe.py:107``).

    Transcribed with the same integer arithmetic (Python ``//`` and torch's
    floor division agree, including on the negative intermediate a remainder of
    0 produces). Algebraically it is ``13 * (frames // 100) + ceil(r / 8)`` for
    ``r = frames % 100``, and the assertion below states that identity rather
    than trusting it.
    """

    leave = frames % front_end.chunk_frames
    feat = (leave - 1) // 2 + 1
    tail = ((feat - 1) // 2 + 1 - 1) // 2 + 1
    total = tail + (frames // front_end.chunk_frames) * front_end.tokens_per_chunk
    return total


def hf_audio_tokens(n_samples: int, front_end: FrontEnd = QWEN3A) -> int:
    """Audio tokens the published path would send for the same waveform."""

    return _hf_feat_extract_output_lengths(hf_mel_frames(n_samples, front_end), front_end)


def describe_clip(n_samples: int, front_end: FrontEnd = QWEN3A) -> ClipEncoding:
    """The complete side-by-side account of one clip."""

    frames = llamacpp_mel_frames(n_samples, front_end)
    windows = llamacpp_windows(frames, front_end)
    return ClipEncoding(
        n_samples=n_samples,
        seconds=n_samples / front_end.sample_rate_hz,
        llamacpp_frames=frames,
        hf_frames=hf_mel_frames(n_samples, front_end),
        windows=windows,
        llamacpp_tokens=sum(window.tokens for window in windows),
        hf_tokens=hf_audio_tokens(n_samples, front_end),
        zero_pad_frames=sum(window.zero_pad_frames for window in windows),
    )


def summarize(
    sample_counts: Sequence[int], front_end: FrontEnd = QWEN3A
) -> dict[str, object]:
    """Population aggregates over a roster's measured sample counts."""

    if not sample_counts:
        raise ValueError("no clips to summarize")
    encodings = [describe_clip(int(count), front_end) for count in sample_counts]
    n = len(encodings)
    extra = [enc.extra_tokens for enc in encodings]
    pad = [enc.zero_pad_frames for enc in encodings]
    shares = [enc.extra_token_share for enc in encodings]
    histogram: dict[str, int] = {}
    for enc in encodings:
        key = str(enc.extra_tokens)
        histogram[key] = histogram.get(key, 0) + 1
    return {
        "clips": n,
        "audio_seconds_total": round(sum(enc.seconds for enc in encodings), 6),
        "llamacpp_audio_tokens_total": sum(enc.llamacpp_tokens for enc in encodings),
        "hf_audio_tokens_total": sum(enc.hf_tokens for enc in encodings),
        "extra_audio_tokens_total": sum(extra),
        "extra_audio_tokens_mean": round(sum(extra) / n, 6),
        "extra_audio_tokens_max": max(extra),
        "extra_audio_tokens_min": min(extra),
        "extra_token_share_mean": round(sum(shares) / n, 6),
        "extra_token_share_max": round(max(shares), 6),
        "zero_pad_frames_total": sum(pad),
        "zero_pad_frames_mean": round(sum(pad) / n, 6),
        "zero_pad_seconds_total": round(
            sum(pad) * front_end.hop_len / front_end.sample_rate_hz, 6
        ),
        "clips_with_zero_pad": sum(1 for value in pad if value > 0),
        "clips_with_no_extra_token": sum(1 for value in extra if value == 0),
        "clips_spanning_multiple_windows": sum(
            1 for enc in encodings if len(enc.windows) > 1
        ),
        "extra_audio_tokens_histogram": {
            key: histogram[key] for key in sorted(histogram, key=int)
        },
    }


def _self_check() -> None:
    """The algebraic identities the docstrings assert, checked at import time.

    Cheap (a few hundred integer operations) and it makes a transcription slip
    in ``_hf_feat_extract_output_lengths`` impossible to land silently.
    """

    for frames in range(1, 400):
        leave = frames % QWEN3A.chunk_frames
        expected = 13 * (frames // QWEN3A.chunk_frames) + (
            math.ceil(leave / 8) if leave else 0
        )
        if _hf_feat_extract_output_lengths(frames) != expected:
            raise AssertionError(
                f"HF token identity broken at {frames} frames: "
                f"{_hf_feat_extract_output_lengths(frames)} != {expected}"
            )


_self_check()
