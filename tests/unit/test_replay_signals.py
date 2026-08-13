"""Pure signal-extraction functions for the future listen-score-replay
policy's SCORE stage (core.replay_signals): per-slice logprob summary
stats, the D-1-measured words/speech-second catastrophe detector, and
contiguous low-scoring-word span flagging. No policy integration, no
model, no filesystem -- deterministic pure Python only."""

import pytest

from speech_aware_evidence_acquisition.core.replay_signals import (
    CATASTROPHIC_WPS_THRESHOLD,
    ReplaySignalsError,
    flag_spans,
    is_catastrophic,
    slice_logprob_stats,
    words_per_second,
)


class TestSliceLogprobStats:
    def test_exact_arithmetic(self):
        result = slice_logprob_stats([-5.0, -4.0, -3.0, -2.0, -1.0], below_threshold=-2.5)
        assert result["mean"] == pytest.approx(-3.0)
        assert result["min"] == -5.0
        assert result["p10"] == -5.0  # count=5 -> p10_index = max(0, 5//10 - 1) = 0
        assert result["count"] == 5
        assert result["below_threshold_count"] == 3  # -5, -4, -3

    def test_p10_index_matches_obs_audio_noise_floor_convention(self):
        # 20 ascending values -1..-20 (already sorted); p10_index = 20//10-1 = 1
        values = [-float(index) for index in range(1, 21)]
        result = slice_logprob_stats(values, below_threshold=0.0)
        assert result["p10"] == -19.0
        assert result["min"] == -20.0
        assert result["count"] == 20

    def test_single_value(self):
        result = slice_logprob_stats([-7.5], below_threshold=-1.0)
        assert result == {
            "mean": -7.5,
            "min": -7.5,
            "p10": -7.5,
            "count": 1,
            "below_threshold_count": 1,
        }

    def test_unsorted_input_is_handled(self):
        result = slice_logprob_stats([-1.0, -9.0, -3.0], below_threshold=-2.0)
        assert result["min"] == -9.0
        assert result["mean"] == pytest.approx(-13.0 / 3.0)
        assert result["below_threshold_count"] == 2  # -9.0, -3.0

    def test_no_tokens_below_threshold(self):
        result = slice_logprob_stats([-0.1, -0.2, -0.3], below_threshold=-10.0)
        assert result["below_threshold_count"] == 0

    def test_refuses_empty(self):
        with pytest.raises(ReplaySignalsError, match="non-empty"):
            slice_logprob_stats([], below_threshold=-1.0)

    @pytest.mark.parametrize("bad", [None, "-1.0", [1.0], True, False, float("nan"), float("inf")])
    def test_refuses_non_numeric_or_non_finite_entries(self, bad):
        with pytest.raises(ReplaySignalsError):
            slice_logprob_stats([-1.0, bad], below_threshold=-1.0)

    def test_refuses_non_finite_threshold(self):
        with pytest.raises(ReplaySignalsError, match="below_threshold"):
            slice_logprob_stats([-1.0, -2.0], below_threshold=float("nan"))

    def test_deterministic(self):
        values = [-3.0, -1.0, -4.0, -1.0, -5.0]
        first = slice_logprob_stats(values, below_threshold=-2.0)
        second = slice_logprob_stats(values, below_threshold=-2.0)
        assert first == second


class TestWordsPerSecond:
    def test_exact_arithmetic(self):
        assert words_per_second(100, 50.0) == 2.0
        assert words_per_second(0, 10.0) == 0.0

    def test_matches_d1_measured_regimes(self):
        healthy = words_per_second(10335, 4307.0)
        collapsed = words_per_second(16, 4307.0)
        assert healthy == pytest.approx(2.40, abs=0.01)
        assert collapsed == pytest.approx(0.004, abs=0.0005)

    @pytest.mark.parametrize("bad", [-1, 1.5, "10", True, False, None])
    def test_refuses_bad_word_count(self, bad):
        with pytest.raises(ReplaySignalsError, match="word_count"):
            words_per_second(bad, 10.0)

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf"), "10", None, True])
    def test_refuses_bad_audio_seconds(self, bad):
        with pytest.raises(ReplaySignalsError, match="audio_seconds"):
            words_per_second(10, bad)

    def test_deterministic(self):
        assert words_per_second(42, 21.0) == words_per_second(42, 21.0)


class TestIsCatastrophic:
    def test_collapsed_regime_is_catastrophic(self):
        assert is_catastrophic(0.004) is True

    def test_healthy_regime_is_not_catastrophic(self):
        assert is_catastrophic(2.40) is False

    def test_boundary_is_exclusive(self):
        assert is_catastrophic(CATASTROPHIC_WPS_THRESHOLD) is False
        assert is_catastrophic(CATASTROPHIC_WPS_THRESHOLD - 1e-9) is True

    def test_custom_threshold(self):
        assert is_catastrophic(1.0, threshold=2.0) is True
        assert is_catastrophic(3.0, threshold=2.0) is False

    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), None, "0.1", True, False])
    def test_refuses_non_finite_or_non_numeric(self, bad):
        with pytest.raises(ReplaySignalsError, match="wps"):
            is_catastrophic(bad)


class TestFlagSpans:
    def test_single_contiguous_run(self):
        words = ["a", "b", "c", "d", "e"]
        scores = [0.9, 0.9, 0.1, 0.1, 0.9]
        assert flag_spans(words, scores, low_threshold=0.5, min_run=1) == [(2, 4)]

    def test_multiple_runs_in_ascending_order(self):
        words = list("abcdefg")
        scores = [0.1, 0.9, 0.1, 0.1, 0.9, 0.1, 0.9]
        assert flag_spans(words, scores, low_threshold=0.5, min_run=1) == [
            (0, 1),
            (2, 4),
            (5, 6),
        ]

    def test_run_exactly_at_min_run_is_kept(self):
        words = ["a", "b", "c"]
        scores = [0.9, 0.1, 0.9]
        assert flag_spans(words, scores, low_threshold=0.5, min_run=1) == [(1, 2)]

    def test_run_shorter_than_min_run_is_dropped(self):
        words = ["a", "b", "c", "d"]
        scores = [0.9, 0.1, 0.1, 0.9]
        assert flag_spans(words, scores, low_threshold=0.5, min_run=3) == []
        assert flag_spans(words, scores, low_threshold=0.5, min_run=2) == [(1, 3)]

    def test_run_touching_the_start_and_end_of_the_list(self):
        words = ["a", "b", "c"]
        scores = [0.1, 0.9, 0.1]
        assert flag_spans(words, scores, low_threshold=0.5, min_run=1) == [(0, 1), (2, 3)]

    def test_no_low_scores_yields_no_spans(self):
        assert flag_spans(["a", "b"], [0.9, 0.9], low_threshold=0.5, min_run=1) == []

    def test_empty_input_yields_no_spans(self):
        assert flag_spans([], [], low_threshold=0.5, min_run=1) == []

    def test_boundary_equal_to_threshold_is_not_low(self):
        # word_scores[i] < low_threshold is strict; equal is NOT low.
        assert flag_spans(["a"], [0.5], low_threshold=0.5, min_run=1) == []

    def test_refuses_length_mismatch(self):
        with pytest.raises(ReplaySignalsError, match="length mismatch"):
            flag_spans(["a", "b"], [0.1], low_threshold=0.5, min_run=1)

    @pytest.mark.parametrize("bad", [0, -1, 1.5, True, False])
    def test_refuses_bad_min_run(self, bad):
        with pytest.raises(ReplaySignalsError, match="min_run"):
            flag_spans(["a"], [0.1], low_threshold=0.5, min_run=bad)

    @pytest.mark.parametrize("bad", [None, "0.1", float("nan"), float("inf")])
    def test_refuses_bad_word_scores_entry(self, bad):
        with pytest.raises(ReplaySignalsError, match="word_scores"):
            flag_spans(["a", "b"], [0.1, bad], low_threshold=0.5, min_run=1)

    def test_refuses_non_finite_low_threshold(self):
        with pytest.raises(ReplaySignalsError, match="low_threshold"):
            flag_spans(["a"], [0.1], low_threshold=float("nan"), min_run=1)

    def test_deterministic(self):
        words = list("abcdef")
        scores = [0.9, 0.1, 0.1, 0.9, 0.1, 0.1]
        first = flag_spans(words, scores, low_threshold=0.5, min_run=2)
        second = flag_spans(words, scores, low_threshold=0.5, min_run=2)
        assert first == second == [(1, 3), (4, 6)]
