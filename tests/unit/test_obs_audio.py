"""Pure OBS audio/boundary functions (obs-agent-loop v1, owner directive
2026-08-08): energy VAD, VAD transitions/non-speech spans, RMS normalization,
boundary-response parsing, sentence-cut acceptance, and the three-tier
boundary resolution (model estimate -> VAD snap -> clamp, with fixed-advance
fallback).

Synthetic waveforms only: silence, tones, and speech-like AM noise. Every
function under test is deterministic pure Python (stdlib ``array``/``math``)
-- no numpy, no soundfile, no model.
"""

import io
import math
import random
import wave
from array import array

import pytest

from speech_aware_evidence_acquisition.reproduction.obs_audio import (
    ObsAudioError,
    accept_up_to_boundary,
    energy_vad_flags,
    frame_rms,
    nearest_transition,
    nonspeech_spans,
    parse_boundary_response,
    resolve_advance,
    rms_normalize,
    vad_transitions,
    write_wav_bytes,
)

RATE = 16000


def _silence(seconds: float) -> array:
    return array("h", [0] * int(seconds * RATE))


def _am_noise(seconds: float, amplitude: int = 8000, seed: int = 7) -> array:
    """Speech-like amplitude-modulated noise (deterministic)."""

    rng = random.Random(seed)
    n = int(seconds * RATE)
    samples = array("h")
    for index in range(n):
        envelope = 0.55 + 0.45 * math.sin(2 * math.pi * 3.0 * index / RATE)
        samples.append(int(amplitude * envelope * (2 * rng.random() - 1)))
    return samples


def _concat(*chunks: array) -> array:
    out = array("h")
    for chunk in chunks:
        out.extend(chunk)
    return out


class TestFrameRms:
    def test_constant_signal(self):
        rms = frame_rms(array("h", [1000] * 300), 100)
        assert rms == [1000.0, 1000.0, 1000.0]

    def test_partial_last_frame_included(self):
        assert len(frame_rms(array("h", [0] * 250), 100)) == 3

    def test_refuses_nonpositive_frame(self):
        with pytest.raises(ObsAudioError):
            frame_rms(array("h", [0] * 10), 0)


class TestEnergyVad:
    def test_silence_is_nonspeech_and_noise_is_speech(self):
        signal = _concat(_silence(1.0), _am_noise(1.0), _silence(1.0))
        flags = energy_vad_flags(signal, RATE)
        third = len(flags) // 3
        assert not any(flags[: third - 2])
        assert any(flags[third + 1 : 2 * third])
        assert not any(flags[2 * third + 8 :])  # hangover (5 frames) may extend a little

    def test_deterministic(self):
        signal = _concat(_silence(0.5), _am_noise(0.7))
        assert energy_vad_flags(signal, RATE) == energy_vad_flags(signal, RATE)

    def test_all_silence_yields_no_speech(self):
        assert not any(energy_vad_flags(_silence(2.0), RATE))


class TestSpansAndTransitions:
    def test_nonspeech_spans_finds_the_long_gap(self):
        signal = _concat(_am_noise(1.0), _silence(6.0), _am_noise(1.0))
        flags = energy_vad_flags(signal, RATE)
        spans = nonspeech_spans(flags, 0.03, min_seconds=5.0)
        assert len(spans) == 1
        start, end = spans[0]
        assert start == pytest.approx(1.0, abs=0.35)
        assert end == pytest.approx(7.0, abs=0.35)

    def test_short_gaps_are_not_reported(self):
        signal = _concat(_am_noise(1.0), _silence(1.0), _am_noise(1.0))
        flags = energy_vad_flags(signal, RATE)
        assert nonspeech_spans(flags, 0.03, min_seconds=5.0) == []

    def test_transitions_bracket_the_speech_burst(self):
        signal = _concat(_silence(2.0), _am_noise(1.0), _silence(2.0))
        flags = energy_vad_flags(signal, RATE)
        transitions = vad_transitions(flags, 0.03)
        assert any(abs(t - 2.0) < 0.35 for t in transitions)
        assert any(abs(t - 3.0) < 0.35 for t in transitions)

    def test_nearest_transition(self):
        transitions = [10.0, 20.0, 30.0]
        assert nearest_transition(transitions, 19.2, 2.0) == 20.0
        assert nearest_transition(transitions, 24.9, 2.0) is None
        assert nearest_transition([], 5.0, 2.0) is None


class TestRmsNormalize:
    def test_scales_toward_target(self):
        quiet = array("h", [100, -100] * 1000)
        louder = rms_normalize(quiet, target_dbfs=-20.0)
        in_rms = frame_rms(quiet, len(quiet))[0]
        out_rms = frame_rms(louder, len(louder))[0]
        assert out_rms > in_rms
        target = 32768 * (10 ** (-20 / 20))
        assert out_rms == pytest.approx(target, rel=0.05)

    def test_pure_silence_is_unchanged(self):
        silent = _silence(0.1)
        assert rms_normalize(silent, target_dbfs=-20.0) == silent

    def test_clipping_is_bounded_not_wrapped(self):
        loud = array("h", [30000, -30000] * 100)
        result = rms_normalize(loud, target_dbfs=0.0)
        assert max(result) <= 32767 and min(result) >= -32768

    def test_deterministic(self):
        signal = _am_noise(0.2)
        assert rms_normalize(signal, -20.0) == rms_normalize(signal, -20.0)


class TestWavBytes:
    def test_roundtrip_header_and_samples(self):
        samples = _am_noise(0.05)
        raw = write_wav_bytes(samples, RATE)
        with wave.open(io.BytesIO(raw), "rb") as handle:
            assert handle.getframerate() == RATE
            assert handle.getnchannels() == 1
            assert handle.getsampwidth() == 2
            assert handle.getnframes() == len(samples)

    def test_deterministic_bytes(self):
        samples = _am_noise(0.05)
        assert write_wav_bytes(samples, RATE) == write_wav_bytes(samples, RATE)


class TestParseBoundaryResponse:
    def test_strict_format(self):
        text = "TRANSCRIPT:\nhello world. second sentence.\nBOUNDARY_SECONDS: 47.5\n"
        transcript, boundary = parse_boundary_response(text)
        assert transcript == "hello world. second sentence."
        assert boundary == 47.5

    def test_integer_boundary_and_no_label(self):
        transcript, boundary = parse_boundary_response("just text\nBOUNDARY_SECONDS: 30")
        assert transcript == "just text"
        assert boundary == 30.0

    def test_missing_boundary_line_returns_none(self):
        transcript, boundary = parse_boundary_response("TRANSCRIPT:\nonly text here")
        assert transcript == "only text here"
        assert boundary is None

    def test_unparseable_boundary_returns_none(self):
        transcript, boundary = parse_boundary_response("words\nBOUNDARY_SECONDS: soonish")
        assert boundary is None
        assert "words" in transcript

    def test_last_boundary_line_wins_and_trailing_junk_is_dropped(self):
        text = "a.\nBOUNDARY_SECONDS: 10\nb.\nBOUNDARY_SECONDS: 20\ntrailing junk"
        transcript, boundary = parse_boundary_response(text)
        assert boundary == 20.0
        assert transcript == "a.\nBOUNDARY_SECONDS: 10\nb."


class TestAcceptUpToBoundary:
    TEXT = "First sentence. Second sentence goes on. Third trails off without end"

    def test_cuts_at_last_sentence_final_punctuation_before_the_share(self):
        accepted, dropped = accept_up_to_boundary(self.TEXT, 0.8)
        assert accepted == "First sentence. Second sentence goes on."
        assert dropped == self.TEXT[len(accepted):]

    def test_full_fraction_accepts_everything(self):
        accepted, dropped = accept_up_to_boundary(self.TEXT, 1.0)
        assert accepted == self.TEXT and dropped == ""

    def test_no_punctuation_in_window_falls_back_to_the_raw_cut(self):
        text = "no punctuation anywhere in this stretch of text"
        accepted, dropped = accept_up_to_boundary(text, 0.5)
        assert accepted == text[: int(round(len(text) * 0.5))]
        assert accepted + dropped == text

    def test_zero_fraction_accepts_nothing(self):
        accepted, dropped = accept_up_to_boundary(self.TEXT, 0.0)
        assert accepted == "" and dropped == self.TEXT


class TestResolveAdvance:
    KW = dict(
        snap_window=2.0,
        min_advance=20.0,
        max_advance=55.0,
        fallback_advance=50.0,
        buffer_seconds=60.0,
    )

    def test_estimate_snaps_to_nearby_transition(self):
        result = resolve_advance(47.0, transitions=[45.6, 52.0], **self.KW)
        assert result["advance"] == 45.6
        assert result["snapped"] == 45.6
        assert result["fallback"] is False

    def test_no_transition_within_window_keeps_the_estimate(self):
        result = resolve_advance(30.0, transitions=[45.6], **self.KW)
        assert result["advance"] == 30.0
        assert result["snapped"] is None

    def test_clamped_to_min_and_max(self):
        low = resolve_advance(5.0, transitions=[], **self.KW)
        assert low["advance"] == 20.0 and low["clamped"] is True
        high = resolve_advance(59.0, transitions=[], **self.KW)
        assert high["advance"] == 55.0 and high["clamped"] is True

    def test_unparseable_estimate_falls_back(self):
        result = resolve_advance(None, transitions=[30.0], **self.KW)
        assert result["advance"] == 50.0
        assert result["fallback"] is True
        assert result["snapped"] is None

    def test_out_of_range_estimate_falls_back(self):
        for estimate in (-3.0, 0.0, 400.0):
            result = resolve_advance(estimate, transitions=[], **self.KW)
            assert result["fallback"] is True
            assert result["advance"] == 50.0
