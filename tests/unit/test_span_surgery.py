"""core.span_surgery: a thin torchaudio/soundfile wrapper for MMS_FA forced
alignment and deterministic waveform slicing (SCORE stage span selection
for the future listen-score-replay policy).

``cut_span`` is exercised end-to-end against a small generated sine-wave
WAV (written via ``soundfile`` in a tmpdir, matching the module's own
soundfile-based I/O -- see ``core.span_surgery`` module docstring) -- no
model touch. ``align_words`` is exercised ONLY for its fail-closed argument
validation (missing file, empty transcript); the real MMS_FA alignment
path is a genuine model touch and is covered by the separate registered
tool-smoke (``SAEA-SMOKE-align``, ``docs/exposure-ledger.md`` 2026-08-13),
never by this repo's unit tests."""

import math

import pytest

from speech_aware_evidence_acquisition.core.span_surgery import (
    SpanSurgeryError,
    align_words,
    cut_span,
)

RATE = 16000


def _sine_wav(tmp_path, seconds: float = 1.0, freq: float = 440.0, name: str = "tone.wav"):
    sf = pytest.importorskip("soundfile")
    numpy = pytest.importorskip("numpy")
    n = int(seconds * RATE)
    t = numpy.arange(n, dtype="float32") / RATE
    waveform = (0.5 * numpy.sin(2 * math.pi * freq * t)).astype("float32")
    path = tmp_path / name
    sf.write(str(path), waveform, RATE)
    return path


class TestCutSpan:
    def test_slices_the_requested_span(self, tmp_path):
        sf = pytest.importorskip("soundfile")
        src = _sine_wav(tmp_path, seconds=2.0)
        out = cut_span(src, start_s=0.5, end_s=1.0, pad_s=0.0, out_path=tmp_path / "cut.wav")
        assert out == tmp_path / "cut.wav"
        assert out.is_file()
        data, rate = sf.read(str(out))
        assert rate == RATE
        assert len(data) == pytest.approx(0.5 * RATE, abs=1)

    def test_padding_extends_the_span(self, tmp_path):
        sf = pytest.importorskip("soundfile")
        src = _sine_wav(tmp_path, seconds=2.0)
        out = cut_span(src, start_s=1.0, end_s=1.2, pad_s=0.1, out_path=tmp_path / "cut.wav")
        data, rate = sf.read(str(out))
        # [1.0-0.1, 1.2+0.1] = [0.9, 1.3] -> 0.4s
        assert len(data) == pytest.approx(0.4 * RATE, abs=1)

    def test_padding_clamped_to_file_bounds(self, tmp_path):
        sf = pytest.importorskip("soundfile")
        src = _sine_wav(tmp_path, seconds=1.0)
        out = cut_span(src, start_s=0.0, end_s=1.0, pad_s=5.0, out_path=tmp_path / "cut.wav")
        data, rate = sf.read(str(out))
        # padded span clamps to the full [0, 1.0] duration, not beyond it.
        assert len(data) == pytest.approx(1.0 * RATE, abs=1)

    def test_deterministic_output_bytes(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=1.0)
        out_a = cut_span(src, start_s=0.2, end_s=0.6, pad_s=0.0, out_path=tmp_path / "a.wav")
        out_b = cut_span(src, start_s=0.2, end_s=0.6, pad_s=0.0, out_path=tmp_path / "b.wav")
        assert out_a.read_bytes() == out_b.read_bytes()

    def test_creates_missing_output_directory(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=1.0)
        out_path = tmp_path / "nested" / "dir" / "cut.wav"
        out = cut_span(src, start_s=0.0, end_s=0.5, pad_s=0.0, out_path=out_path)
        assert out.is_file()

    def test_refuses_missing_audio_file(self, tmp_path):
        with pytest.raises(SpanSurgeryError, match="audio file missing"):
            cut_span(
                tmp_path / "does-not-exist.wav",
                start_s=0.0,
                end_s=1.0,
                pad_s=0.0,
                out_path=tmp_path / "cut.wav",
            )

    def test_refuses_negative_start(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=1.0)
        with pytest.raises(SpanSurgeryError, match="start_s"):
            cut_span(src, start_s=-0.1, end_s=0.5, pad_s=0.0, out_path=tmp_path / "cut.wav")

    def test_refuses_negative_pad(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=1.0)
        with pytest.raises(SpanSurgeryError, match="pad_s"):
            cut_span(src, start_s=0.0, end_s=0.5, pad_s=-0.1, out_path=tmp_path / "cut.wav")

    def test_refuses_inverted_bounds(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=1.0)
        with pytest.raises(SpanSurgeryError, match="end_s"):
            cut_span(src, start_s=0.5, end_s=0.5, pad_s=0.0, out_path=tmp_path / "cut.wav")
        with pytest.raises(SpanSurgeryError, match="end_s"):
            cut_span(src, start_s=0.8, end_s=0.2, pad_s=0.0, out_path=tmp_path / "cut.wav")


class TestAlignWords:
    """Fail-closed argument validation only -- see module docstring."""

    def test_refuses_missing_audio_file(self, tmp_path):
        with pytest.raises(SpanSurgeryError, match="audio file missing"):
            align_words(tmp_path / "does-not-exist.wav", ["hello", "world"])

    def test_refuses_empty_transcript(self, tmp_path):
        src = _sine_wav(tmp_path, seconds=0.5)
        with pytest.raises(SpanSurgeryError, match="transcript_words"):
            align_words(src, [])

    def test_missing_file_is_checked_before_empty_transcript(self, tmp_path):
        # both inputs are invalid; the file-existence check fires first,
        # before any transcript validation or model/waveform I/O.
        with pytest.raises(SpanSurgeryError, match="audio file missing"):
            align_words(tmp_path / "does-not-exist.wav", [])


def test_mms_word_normalizes_to_the_aligner_alphabet():
    """MMS_FA's tokenizer dictionary is lowercase a-z plus apostrophe; raw
    transcript words (capitals, digits, punctuation) crashed the aligner in
    production (SAEA-MM3-replay, 2026-08-14, KeyError 'L'). The normalizer
    maps every word into that alphabet, possibly to empty."""
    from speech_aware_evidence_acquisition.core.span_surgery import _mms_word

    assert _mms_word("Louise") == "louise"
    assert _mms_word("RASp,") == "rasp"
    assert _mms_word("company's") == "company's"
    assert _mms_word("2020") == ""
    assert _mms_word("$1.5") == ""
    assert _mms_word("Co-Chairman") == "cochairman"
