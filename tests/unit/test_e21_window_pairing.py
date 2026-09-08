"""``analysis.e21_window_pairing``: the 90-second window as the paired unit.

The module's whole claim is that decomposing a sealed call into its windows LOSES
NOTHING -- per-window rows re-aggregate to the call's own numbers exactly. These
tests pin that as a property on synthetic calls (the 44 real ones are proven in
``docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-window-pairing/``),
plus the two constructions the property rests on: the stitch recovery, and the
prefix-normalization boundary that survives a normalizer merging tokens across a
window boundary.
"""

from __future__ import annotations

import json
import random

import pytest

from speech_aware_evidence_acquisition.analysis.e21_window_pairing import (
    WindowPairingError,
    WindowSpan,
    aggregate_entity_buckets,
    aggregate_window_rows,
    call_of,
    charge_operations_to_windows,
    hypothesis_indices,
    hypothesis_window_boundaries,
    reference_indices,
    stitched_text,
    stitched_windows_from_trace,
    window_id,
    window_of_hypothesis_index,
    assert_stitch_reproduces_outputs,
)
from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec


# ---------------------------------------------------------------------------
# Window identity.
# ---------------------------------------------------------------------------


def test_window_ids_round_trip_to_their_call():
    identifier = window_id("4320211", 37)
    assert identifier == "4320211#w0037"
    assert call_of(identifier) == "4320211"


def test_a_sample_id_that_already_carries_the_separator_refuses():
    with pytest.raises(WindowPairingError, match="cannot carry a window suffix"):
        window_id("4320211#w0001", 1)


def test_call_of_refuses_a_bare_sample_id():
    with pytest.raises(WindowPairingError, match="not a window id"):
        call_of("4320211")


# ---------------------------------------------------------------------------
# Recovering the per-window hypothesis from a sealed trace.
# ---------------------------------------------------------------------------


def _trace_lines(
    sample_id: str,
    spans,
    *,
    skipped: str | None = None,
    saturated: str | None = None,
    raw_saturated_text: str = "",
) -> list[str]:
    """A trace shaped exactly like ``reproduction.obs_loop`` emits: per-slice
    request / OBS / response records, then the per-call stitch pair.

    ``saturated`` names one request id whose ``OBS`` record carries
    ``obs_saturated: true`` -- exactly what ``obs_loop`` writes for a slice whose
    decode hit the token cap (module comment above ``_slice_saturated``). Its
    ``MODEL_RESPONSE`` is still written in full (``raw_saturated_text``, standing
    in for the raw runaway-repetition text obs_loop fully traces for audit) so a
    reader that ignores ``obs_saturated`` would recover the wrong window text; the
    slice stays in ``stitched_request_ids`` because only a skip removes one.
    """

    lines: list[dict] = []
    request_ids = []
    for index, (text, start, end) in enumerate(spans, start=1):
        request_id = f"req-0001-i{index:04d}"
        request_ids.append(request_id)
        is_saturated = request_id == saturated
        lines.append(
            {
                "channel": "MODEL_REQUEST",
                "record_id": f"{request_id}/request",
                "payload": {
                    "arm": "bare-core",
                    "payload": {
                        "sample_id": sample_id,
                        "audio_seconds": end - start,
                    },
                },
            }
        )
        lines.append(
            {
                "channel": "OBS",
                "record_id": f"{request_id}/obs",
                "payload": {
                    "obs_iteration": index,
                    "obs_window_start_seconds": start,
                    "obs_window_end_seconds": end,
                    "obs_saturated": is_saturated,
                },
            }
        )
        lines.append(
            {
                "channel": "MODEL_RESPONSE",
                "record_id": f"{request_id}/response",
                "payload": {"text": raw_saturated_text if is_saturated else text},
            }
        )
    contributing = [rid for rid in request_ids if rid != skipped]
    lines.append(
        {
            "channel": "MODEL_REQUEST",
            "record_id": "req-0001/request",
            "payload": {"stitch": True, "stitched_request_ids": contributing},
        }
    )
    lines.append(
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "req-0001/response",
            "payload": {"stitch": True, "text": "ignored"},
        }
    )
    return [json.dumps(line) for line in lines]


def _write_trace(tmp_path, lines):
    path = tmp_path / "trace.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


SPANS = [("hello there", 0.0, 90.0), ("second window", 90.0, 180.0), ("tail", 180.0, 205.0)]


def test_the_trace_recovers_every_window_in_stitch_order(tmp_path):
    path = _write_trace(tmp_path, _trace_lines("4320211", SPANS))
    windows = stitched_windows_from_trace(path)
    assert set(windows) == {"4320211"}
    spans = windows["4320211"]
    assert [span.text for span in spans] == ["hello there", "second window", "tail"]
    assert [span.window_index for span in spans] == [1, 2, 3]
    assert spans[-1].audio_seconds == pytest.approx(25.0)
    assert spans[0].identifier == "4320211#w0001"
    assert [span.saturated for span in spans] == [False, False, False]


def test_a_slice_the_stitch_never_used_is_not_a_window(tmp_path):
    """``obs_loop`` keeps ``stitched_request_ids`` in lockstep with the slices that
    actually contributed: a skipped slice has a request and a response in the
    trace and contributes nothing to the hypothesis, so it is not a paired unit."""

    path = _write_trace(tmp_path, _trace_lines("4320211", SPANS, skipped="req-0001-i0002"))
    spans = stitched_windows_from_trace(path)["4320211"]
    assert [span.text for span in spans] == ["hello there", "tail"]


# ---------------------------------------------------------------------------
# The KC-E1 defect: a saturated slice's raw MODEL_RESPONSE must never be
# re-admitted as the window's text -- obs_loop dropped it from the stitch, and
# the recovery has to follow the join, not the raw trace (module docstring).
# ---------------------------------------------------------------------------


def test_a_saturated_slice_contributes_no_text_and_stays_a_window(tmp_path):
    huge_raw_text = "the the the the the " * 400  # stands in for a runaway decode
    path = _write_trace(
        tmp_path,
        _trace_lines(
            "4320211",
            SPANS,
            saturated="req-0001-i0002",
            raw_saturated_text=huge_raw_text,
        ),
    )
    spans = stitched_windows_from_trace(path)["4320211"]
    # Still three windows -- unlike a skip, a saturation never removes the
    # slice from stitched_request_ids -- but the middle one's text is empty,
    # never the raw response, and it alone carries the flag.
    assert [span.window_index for span in spans] == [1, 2, 3]
    assert [span.text for span in spans] == ["hello there", "", "tail"]
    assert [span.saturated for span in spans] == [False, True, False]


def test_a_saturated_window_still_rebuilds_the_sealed_hypothesis_byte_for_byte(tmp_path):
    """The whole exactness proof (module docstring, ``assert_stitch_reproduces_
    outputs``) has to hold on a call that saturated: the sealed hypothesis
    ``obs_loop`` actually emitted already dropped the saturated slice's text, so
    the recovered spans -- text forced empty, not re-admitted -- must rebuild it
    exactly, the same rule ``stitched_text`` states (empty spans join to nothing,
    module docstring above)."""

    huge_raw_text = "the the the the the " * 400
    path = _write_trace(
        tmp_path,
        _trace_lines(
            "4320211",
            SPANS,
            saturated="req-0001-i0002",
            raw_saturated_text=huge_raw_text,
        ),
    )
    windows = stitched_windows_from_trace(path)
    sealed_hypothesis = "hello there tail"  # what obs_loop actually stitched
    assert_stitch_reproduces_outputs(windows, {"4320211": sealed_hypothesis})


def test_a_stitch_naming_a_request_with_no_response_refuses(tmp_path):
    lines = _trace_lines("4320211", SPANS)
    lines = [line for line in lines if '"req-0001-i0002/response"' not in line]
    with pytest.raises(WindowPairingError, match="has no response or no OBS record"):
        stitched_windows_from_trace(_write_trace(tmp_path, lines))


def test_a_trace_with_no_stitch_record_refuses(tmp_path):
    lines = [line for line in _trace_lines("4320211", SPANS) if '"stitch": true' not in line]
    with pytest.raises(WindowPairingError, match="no stitch records"):
        stitched_windows_from_trace(_write_trace(tmp_path, lines))


def _spans(texts):
    return tuple(
        WindowSpan(
            sample_id="s",
            window_index=index,
            request_id=f"r{index}",
            start_seconds=90.0 * (index - 1),
            end_seconds=90.0 * index,
            audio_seconds=90.0,
            text=text,
        )
        for index, text in enumerate(texts, start=1)
    )


def test_the_stitch_rule_drops_empty_spans_exactly_as_obs_loop_does():
    assert stitched_text(_spans(["a", "", "b"])) == "a b"


def test_the_recovery_must_rebuild_the_sealed_hypothesis_byte_for_byte():
    windows = {"s": _spans(["a", "b"])}
    assert_stitch_reproduces_outputs(windows, {"s": "a b"})
    with pytest.raises(WindowPairingError, match="do not rebuild the sealed hypothesis"):
        assert_stitch_reproduces_outputs(windows, {"s": "a  b"})


def test_a_sample_present_on_only_one_side_refuses():
    with pytest.raises(WindowPairingError, match="differ"):
        assert_stitch_reproduces_outputs({"s": _spans(["a"])}, {"s": "a", "t": "b"})


# ---------------------------------------------------------------------------
# The prefix-normalization boundary -- the construction the whole partition
# rests on, tested against a normalizer that MERGES across a boundary exactly
# the way the Whisper normalizer does on 13 of the 44 sealed calls.
# ---------------------------------------------------------------------------


def _merging_normalizer(text: str) -> str:
    """Joins a trailing ``one`` to a following ``.14`` -- the shape of the real
    merge (``... to one`` + ``.14 to ...`` -> ``... to one.14 to ...``)."""

    return text.replace("one .14", "one.14")


def test_boundaries_are_monotone_and_total_even_when_the_normalizer_merges():
    spans = _spans(["alpha beta one", ".14 gamma"])
    boundaries = hypothesis_window_boundaries(spans, _merging_normalizer)
    whole = _merging_normalizer(stitched_text(spans)).split()
    assert whole == ["alpha", "beta", "one.14", "gamma"]
    # window 1 alone normalizes to three words; the merge then FUSES its last
    # word with the next window's first, so the cumulative count does not grow
    # by the naive span length -- and never shrinks.
    assert boundaries == (3, 4)
    assert boundaries[-1] == len(whole)


def test_a_merged_boundary_token_is_charged_to_the_earlier_window():
    spans = _spans(["alpha beta one", ".14 gamma"])
    boundaries = hypothesis_window_boundaries(spans, _merging_normalizer)
    # index 2 is the merged "one.14"
    assert window_of_hypothesis_index(boundaries, 2) == 0
    assert window_of_hypothesis_index(boundaries, 3) == 1


def test_a_non_monotone_normalizer_refuses():
    def shrinking(text: str) -> str:
        return "" if "b" in text else text

    with pytest.raises(WindowPairingError, match="not monotone"):
        hypothesis_window_boundaries(_spans(["a", "b"]), shrinking)


# ---------------------------------------------------------------------------
# Charging operations to windows: a partition, never a filter.
# ---------------------------------------------------------------------------


def test_charging_partitions_every_operation():
    ref = "the quick brown fox jumps over the lazy dog".split()
    hyp = "the quick brown fox leaps over lazy dog now".split()
    operations = conec.aligned_operations(ref, hyp)
    boundaries = (4, 7, len(hyp))
    charged = charge_operations_to_windows(operations, boundaries, len(hyp))
    assert sum(len(bucket) for bucket in charged) == len(operations)
    assert [op for bucket in charged for op in bucket] == list(operations)


def test_charging_refuses_boundaries_that_disagree_with_the_alignment():
    with pytest.raises(WindowPairingError, match="account for"):
        charge_operations_to_windows(((conec.OP_HIT, 0, 0),), (5,), 1)


def test_a_trailing_deletion_lands_in_the_last_window():
    ref = "a b c d".split()
    hyp = "a b".split()
    operations = conec.aligned_operations(ref, hyp)
    boundaries = (1, 2)
    charged = charge_operations_to_windows(operations, boundaries, len(hyp))
    kinds = [[kind for kind, _r, _h in bucket] for bucket in charged]
    assert kinds[0] == [conec.OP_HIT]
    assert kinds[1] == [conec.OP_HIT, conec.OP_DELETION, conec.OP_DELETION]


def test_reference_and_hypothesis_indices_are_the_windows_own_positions():
    operations = (
        (conec.OP_HIT, 0, 0),
        (conec.OP_SUBSTITUTION, 1, 1),
        (conec.OP_DELETION, 2, None),
        (conec.OP_INSERTION, None, 2),
    )
    assert reference_indices(operations) == (0, 1, 2)
    assert hypothesis_indices(operations) == (0, 1, 2)


# ---------------------------------------------------------------------------
# The property the whole module exists for.
# ---------------------------------------------------------------------------


def _random_call(seed: int, *, windows: int, words_per_window: int):
    rng = random.Random(seed)
    vocabulary = [f"w{index}" for index in range(30)]
    hyp_windows = [
        [rng.choice(vocabulary) for _ in range(words_per_window)] for _ in range(windows)
    ]
    hyp = [word for window in hyp_windows for word in window]
    ref = []
    for word in hyp:
        roll = rng.random()
        if roll < 0.70:
            ref.append(word)
        elif roll < 0.85:
            ref.append(rng.choice(vocabulary))
        elif roll < 0.93:
            ref.extend([rng.choice(vocabulary), word])
        # else: the word is an insertion -- no reference token at all
    boundaries = tuple(
        sum(len(window) for window in hyp_windows[: index + 1]) for index in range(windows)
    )
    return ref, hyp, boundaries


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_per_window_rows_reaggregate_to_the_calls_own_numbers(seed):
    ref, hyp, boundaries = _random_call(seed, windows=5, words_per_window=40)
    operations = conec.aligned_operations(ref, hyp)
    whole = conec.operation_counts(operations, len(ref), len(hyp))
    charged = charge_operations_to_windows(operations, boundaries, len(hyp))

    owners = [(("e1",) if index % 7 == 0 else ()) for index in range(len(ref))]
    entity_types = {"e1": "PERSON"}
    whole_buckets = conec.entity_wer_buckets(operations, owners, entity_types)

    rows = []
    window_buckets = []
    for bucket_operations in charged:
        buckets = conec.entity_wer_buckets(bucket_operations, owners, entity_types)
        window_buckets.append(buckets)
        overall = buckets[conec.OVERALL_BUCKET]
        rows.append(
            {
                "substitutions": overall["substitutions"],
                "deletions": overall["deletions"],
                "insertions": overall["insertions"],
                "reference_words": overall["reference_words"],
            }
        )

    aggregate = aggregate_window_rows(rows)
    assert aggregate["substitutions"] == whole[conec.OP_SUBSTITUTION]
    assert aggregate["deletions"] == whole[conec.OP_DELETION]
    assert aggregate["insertions"] == whole[conec.OP_INSERTION]
    assert aggregate["reference_words"] == len(ref)
    assert aggregate["corpus_wer"] == pytest.approx(
        whole["errors"] / len(ref)
    )

    merged = aggregate_entity_buckets(window_buckets)
    assert set(merged) == set(whole_buckets)
    for name, values in whole_buckets.items():
        for key in ("substitutions", "deletions", "insertions", "reference_words"):
            assert merged[name][key] == values[key], (name, key)
        assert merged[name]["wer"] == pytest.approx(values["wer"])


def test_aggregate_pools_rather_than_averaging_per_window_rates():
    """Two windows, one error each: 1/100 and 1/1 pool to 2/101, never to the
    mean of 0.01 and 1.0."""

    rows = [
        {"substitutions": 1, "deletions": 0, "insertions": 0, "reference_words": 100},
        {"substitutions": 1, "deletions": 0, "insertions": 0, "reference_words": 1},
    ]
    assert aggregate_window_rows(rows)["corpus_wer"] == pytest.approx(2.0 / 101.0)
