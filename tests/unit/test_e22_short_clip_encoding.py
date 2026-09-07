"""Unit tests for the model-free short-clip encoding arithmetic.

Every expectation here is derived by hand from the pinned sources named in
``analysis/e22_short_clip_encoding.py`` -- llama.cpp-featcache at
``04ccc72a2207347ca76161b93fd9d846dd0a8675`` and transformers 5.12.1 -- and not
from the module's own output.
"""

from __future__ import annotations

import math

import pytest

from speech_aware_evidence_acquisition.analysis.e22_short_clip_encoding import (
    QWEN3A,
    describe_clip,
    hf_audio_tokens,
    hf_mel_frames,
    llamacpp_audio_tokens,
    llamacpp_mel_frames,
    llamacpp_windows,
    samples_for_seconds,
    summarize,
)


def test_front_end_constants_match_the_pinned_sources():
    assert QWEN3A.sample_rate_hz == 16000
    assert QWEN3A.n_fft == 400
    assert QWEN3A.window_len == 400
    assert QWEN3A.hop_len == 160
    assert QWEN3A.reflect_pad_samples == 200
    assert QWEN3A.chunk_frames == 100
    assert QWEN3A.window_frames == 800
    assert QWEN3A.tokens_per_chunk == 13
    assert QWEN3A.chunk_seconds == pytest.approx(1.0)
    assert QWEN3A.window_seconds == pytest.approx(8.0)


def test_our_frame_count_is_exactly_one_more_than_the_published_one():
    for n_samples in (1, 159, 160, 161, 48000, 48001, 528000, 1_254_000):
        assert llamacpp_mel_frames(n_samples) == hf_mel_frames(n_samples) + 1


def test_three_second_clip_walkthrough():
    n_samples = samples_for_seconds(3.0)
    assert n_samples == 48000
    encoding = describe_clip(n_samples)
    # 48000 // 160 + 1
    assert encoding.llamacpp_frames == 301
    assert encoding.hf_frames == 300
    # One window: 301 effective frames rounded up to 400 with 99 zero frames.
    assert len(encoding.windows) == 1
    window = encoding.windows[0]
    assert (window.offset_frames, window.effective_frames, window.padded_frames) == (
        0,
        301,
        400,
    )
    assert window.zero_pad_frames == 99
    assert window.tokens == 52
    assert encoding.llamacpp_tokens == 52
    # 13 * 3 full blocks + ceil(0/8) for the remainder
    assert encoding.hf_tokens == 39
    assert encoding.extra_tokens == 13
    assert encoding.zero_pad_frames == 99
    assert encoding.zero_pad_seconds == pytest.approx(0.99)
    assert encoding.tail_block_speech_frames == 1
    assert encoding.extra_token_share == pytest.approx(13 / 52)


def test_thirty_three_second_clip_walkthrough():
    n_samples = samples_for_seconds(33.0)
    assert n_samples == 528000
    encoding = describe_clip(n_samples)
    assert encoding.llamacpp_frames == 3301
    assert encoding.hf_frames == 3300
    # Four full 800-frame windows plus a 101-frame tail window padded to 200.
    assert [window.effective_frames for window in encoding.windows] == [
        800,
        800,
        800,
        800,
        101,
    ]
    assert [window.padded_frames for window in encoding.windows] == [
        800,
        800,
        800,
        800,
        200,
    ]
    assert [window.tokens for window in encoding.windows] == [104, 104, 104, 104, 26]
    assert encoding.llamacpp_tokens == 442
    assert encoding.hf_tokens == 429
    assert encoding.extra_tokens == 13
    assert encoding.zero_pad_frames == 99
    # No fixed 30-second window: a 33 s clip is five encoder invocations, not one.
    assert len(encoding.windows) == 5


def test_the_extra_token_count_is_thirteen_minus_ceil_remainder_over_eight():
    for frames in range(1, 1200):
        n_samples = frames * QWEN3A.hop_len
        assert hf_mel_frames(n_samples) == frames
        remainder = frames % QWEN3A.chunk_frames
        expected = 13 - (math.ceil(remainder / 8) if remainder else 0)
        assert describe_clip(n_samples).extra_tokens == expected


def test_zero_pad_frames_are_ninety_nine_minus_the_remainder():
    for frames in range(1, 600):
        n_samples = frames * QWEN3A.hop_len
        remainder = frames % QWEN3A.chunk_frames
        expected = 0 if remainder == 99 else 99 - remainder
        assert describe_clip(n_samples).zero_pad_frames == expected


def test_a_clip_whose_frames_end_at_ninety_nine_pays_nothing_extra():
    # 99 mel frames -> n_eff 100 -> exactly one block, no padding, and the
    # published path also spends 13 tokens (ceil(99/8) == 13).
    n_samples = 99 * QWEN3A.hop_len
    encoding = describe_clip(n_samples)
    assert encoding.llamacpp_frames == 100
    assert encoding.zero_pad_frames == 0
    assert encoding.llamacpp_tokens == 13
    assert encoding.hf_tokens == 13
    assert encoding.extra_tokens == 0


def test_windows_split_at_eight_hundred_frames_not_at_thirty_seconds():
    twenty = describe_clip(samples_for_seconds(20.0))
    assert [w.effective_frames for w in twenty.windows] == [800, 800, 401]
    assert [w.padded_frames for w in twenty.windows] == [800, 800, 500]
    assert twenty.llamacpp_tokens == 13 * (8 + 8 + 5)
    # A clip padded to exactly 30.0 s is four encoder invocations, not one
    # 30-second window: the `pad-30s` probe variant's own cost.
    thirty = describe_clip(samples_for_seconds(30.0))
    assert [w.effective_frames for w in thirty.windows] == [800, 800, 800, 601]
    assert [w.padded_frames for w in thirty.windows] == [800, 800, 800, 700]
    assert thirty.llamacpp_tokens == 13 * (8 + 8 + 8 + 7) == 403


def test_the_repositorys_thirteen_times_ceil_seconds_rule_and_where_it_breaks():
    # The rule recorded in configs/model/q4km-e22-dev-esb-*.json reproduces the
    # sealed COST records; it is exact except at whole-second durations, where
    # the extra frame opens one more block.
    for seconds in (0.219938, 2.38, 5.32, 6.5, 32.88, 78.36):
        n_samples = samples_for_seconds(seconds)
        assert llamacpp_audio_tokens(n_samples) == 13 * math.ceil(seconds)
    for seconds in (1.0, 3.0, 6.0, 30.0):
        n_samples = samples_for_seconds(seconds)
        assert llamacpp_audio_tokens(n_samples) == 13 * (int(seconds) + 1)


def test_summarize_aggregates_a_population():
    counts = [samples_for_seconds(value) for value in (0.5, 3.0, 8.0, 33.0)]
    summary = summarize(counts)
    assert summary["clips"] == 4
    assert summary["llamacpp_audio_tokens_total"] == sum(
        llamacpp_audio_tokens(count) for count in counts
    )
    assert summary["hf_audio_tokens_total"] == sum(
        hf_audio_tokens(count) for count in counts
    )
    assert (
        summary["extra_audio_tokens_total"]
        == summary["llamacpp_audio_tokens_total"] - summary["hf_audio_tokens_total"]
    )
    assert summary["extra_audio_tokens_max"] <= 13
    assert sum(summary["extra_audio_tokens_histogram"].values()) == 4


def test_empty_and_negative_inputs_fail_closed():
    with pytest.raises(ValueError):
        llamacpp_mel_frames(0)
    with pytest.raises(ValueError):
        hf_mel_frames(-1)
    with pytest.raises(ValueError):
        llamacpp_windows(0)
    with pytest.raises(ValueError):
        summarize([])
