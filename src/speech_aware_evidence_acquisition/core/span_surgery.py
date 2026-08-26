"""Thin, testable wrapper around torchaudio's MMS_FA forced aligner and a
deterministic waveform slicer -- the span-selection primitives the future
listen-score-replay policy's SCORE stage will use to turn a low-confidence
word span (``core.replay_signals.flag_spans``) back into audio to re-listen
to (``core.model.transport`` module docstring, 2026-08-12: "prep
infrastructure for the future listen-score-replay policy"). No policy
integration yet.

``torch``/``torchaudio``/``soundfile`` imports stay function-local (repo
convention -- see ``reproduction.obs_loop.decode_parent_pcm``'s
librosa/soundfile imports): this module must import cleanly with zero
heavy dependencies installed, so importing it never pulls torch into a
pure-Python test run.

Audio I/O uses ``soundfile``, NOT ``torchaudio.load``/``torchaudio.save``:
on this machine torchaudio 2.9's ``load``/``save`` route through
torchcodec, whose FFmpeg system libraries are not installed, while
``soundfile`` has no such dependency and is already this repo's WAV-I/O
fallback (``reproduction.obs_loop.decode_parent_pcm``). ``torchaudio`` is
still used for ``torchaudio.functional.resample`` (pure tensor math, no
torchcodec/FFmpeg involved) inside :func:`align_words`.

MMS_FA is a locked tool-model (``docs/datasets.lock.json``
``mms-fa-torchaudio``, checkpoint sha256 20ef12963ab4924bef49ac4fc7f58ad5
da2ee43b2c11bc8c853c9b90ecdbc680): ``torchaudio.pipelines.MMS_FA.get_model()``
downloads/caches its weights via ``torch.hub`` under ``$TORCH_HOME`` on
first use. Callers MUST set ``TORCH_HOME`` to the locked tool dir before
calling :func:`align_words` -- ``$SPEECHRL_DATA_DIR/models/speech-tools/
torch-hub`` -- so the aligner loads the pinned, already-verified checkpoint
instead of silently re-downloading an unpinned one. A real model touch
through this module additionally requires its own exposure-ledger row and
gate closure (see the tool-smoke row ``SAEA-SMOKE-align``,
``docs/exposure-ledger.md`` 2026-08-13) -- this module only wraps the call,
it does not gate or log it.
"""

from __future__ import annotations

import re as _re
from pathlib import Path


class SpanSurgeryError(RuntimeError):
    """A span-surgery function was given unusable inputs, or the aligner/
    waveform I/O it wraps failed."""


_MMS_STRIP = _re.compile(r"[^a-z']")


def _mms_word(word: str) -> str:
    """Normalize one transcript word to MMS_FA's tokenizer alphabet
    (lowercase a-z plus apostrophe); may normalize to empty (digits,
    symbols), which align_words maps to a zero-width interpolated span."""
    return _MMS_STRIP.sub("", word.lower())


def _read_mono(audio_path: Path):
    """Read ``audio_path`` as float32 mono via ``soundfile`` -- module
    docstring: NOT ``torchaudio.load`` (torchcodec/FFmpeg unavailable on
    this machine). Multi-channel input is mono-ized by averaging channels.
    Returns ``(numpy.ndarray shape (n_samples,), sample_rate_hz)``."""

    import soundfile as sf  # noqa: PLC0415 (heavy import stays function-local)

    data, sample_rate = sf.read(str(audio_path), dtype="float32", always_2d=True)
    return data.mean(axis=1), sample_rate


def align_words(
    audio_path: str | Path, transcript_words: list[str], device: str = "cpu"
) -> list[dict[str, object]]:
    """Word-level forced alignment of ``transcript_words`` against
    ``audio_path`` via ``torchaudio.pipelines.MMS_FA``. Returns one
    ``{"word": str, "start_s": float, "end_s": float}`` per input word, in
    input order.

    NOT unit-tested here beyond the fail-closed argument validation below:
    the real-alignment path (model load, resample, emission, aligner) is a
    genuine model touch and is exercised only by the registered tool-smoke
    (``SAEA-SMOKE-align``, ``docs/exposure-ledger.md`` 2026-08-13) -- a
    plain ``pytest`` run of this repo must never download or run MMS_FA.

    Fails closed on a missing/non-file ``audio_path`` or an empty
    ``transcript_words``, before any model or waveform I/O."""

    audio_path = Path(audio_path)
    if not audio_path.is_file():
        raise SpanSurgeryError(f"audio file missing: {audio_path}")
    if not transcript_words:
        raise SpanSurgeryError("transcript_words must be a non-empty list")

    import torch  # noqa: PLC0415 (heavy import stays function-local)
    import torchaudio  # noqa: PLC0415 (functional.resample only -- module docstring)
    from torchaudio.pipelines import MMS_FA  # noqa: PLC0415

    bundle = MMS_FA
    model = bundle.get_model().to(device)
    tokenizer = bundle.get_tokenizer()
    aligner = bundle.get_aligner()

    mono, sample_rate = _read_mono(audio_path)
    waveform = torch.from_numpy(mono).unsqueeze(0)
    if sample_rate != bundle.sample_rate:
        waveform = torchaudio.functional.resample(waveform, sample_rate, bundle.sample_rate)
    waveform = waveform.to(device)

    with torch.inference_mode():
        emission, _ = model(waveform)

    # MMS_FA's tokenizer dictionary is lowercase a-z (plus apostrophe): raw
    # model transcripts carry capitals, digits and punctuation and crash it
    # with a KeyError (first hit: SAEA-MM3-replay, 2026-08-14, "Louise").
    # Align only the MMS-compatible normalized words, then map timestamps
    # back to ALL input positions -- unalignable words (pure digits, symbols)
    # get a zero-width span interpolated at the preceding aligned boundary,
    # keeping the one-entry-per-input-word contract flag_spans depends on.
    normalized = [_mms_word(word) for word in transcript_words]
    alignable = [(i, n) for i, n in enumerate(normalized) if n]
    if not alignable:
        raise SpanSurgeryError(
            "no MMS-alignable word in transcript_words (all normalized to empty)"
        )
    tokens = tokenizer([n for _, n in alignable])
    token_spans = aligner(emission[0], tokens)

    num_frames = emission.size(1)
    seconds_per_frame = waveform.size(1) / num_frames / bundle.sample_rate
    aligned: dict[int, tuple[float, float]] = {}
    for (i, _n), spans in zip(alignable, token_spans):
        aligned[i] = (spans[0].start * seconds_per_frame, spans[-1].end * seconds_per_frame)
    results: list[dict[str, object]] = []
    last_end = 0.0
    for i, word in enumerate(transcript_words):
        if i in aligned:
            start_s, end_s = aligned[i]
            last_end = end_s
        else:
            start_s = end_s = last_end
        results.append({"word": word, "start_s": start_s, "end_s": end_s})
    return results


def cut_span(
    audio_path: str | Path,
    start_s: float,
    end_s: float,
    pad_s: float,
    out_path: str | Path,
) -> Path:
    """Slice ``audio_path`` to ``[start_s - pad_s, end_s + pad_s]`` (clamped
    to ``[0, duration]``) and write it to ``out_path`` via ``soundfile``
    (module docstring -- not ``torchaudio.save``). Deterministic: the same
    inputs always produce the same output bytes -- a straight sample-index
    slice of the loaded (mono-ized) waveform, no resampling, no dithering.

    Fails closed on a negative ``start_s``/``pad_s``, on ``end_s <=
    start_s`` (inverted or zero-width bounds), or when clamping the padded
    span to the file's own duration leaves nothing to cut -- a caller-side
    bug in span selection, never silently "fixed" here."""

    if start_s < 0:
        raise SpanSurgeryError(f"start_s must be non-negative, got {start_s!r}")
    if pad_s < 0:
        raise SpanSurgeryError(f"pad_s must be non-negative, got {pad_s!r}")
    if end_s <= start_s:
        raise SpanSurgeryError(
            f"end_s ({end_s!r}) must be greater than start_s ({start_s!r})"
        )
    audio_path = Path(audio_path)
    if not audio_path.is_file():
        raise SpanSurgeryError(f"audio file missing: {audio_path}")

    mono, sample_rate = _read_mono(audio_path)
    duration_s = len(mono) / sample_rate
    padded_start = max(0.0, start_s - pad_s)
    padded_end = min(duration_s, end_s + pad_s)
    if padded_end <= padded_start:
        raise SpanSurgeryError(
            f"padded span [{padded_start}, {padded_end}] is empty after clamping to "
            f"[0, {duration_s}] audio duration"
        )
    start_sample = int(round(padded_start * sample_rate))
    end_sample = int(round(padded_end * sample_rate))
    sliced = mono[start_sample:end_sample]

    import soundfile as sf  # noqa: PLC0415 (heavy import stays function-local)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), sliced, sample_rate)
    return out_path
