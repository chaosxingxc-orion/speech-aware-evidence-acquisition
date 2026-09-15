"""Earnings-21 window-level pairing: the 90-second window as the paired unit, the
call as the bootstrap cluster (owner ruling, 2026-09-06).

The problem this solves
-----------------------
Earnings-21 has 44 calls. The program's own rule is ``n >= 400`` paired units for
an effectiveness claim, and no amount of statistics turns 44 into 400. The units
where the model contacts actually happen are the **1,593 fixed 90-second windows**
-- each one its own request, its own audio, its own answer -- so the owner's ruling
is: pair at the window and cluster at the call, report the call-clustered interval
as the honest one and the window-level interval beside it as the optimistic bound.

Why the sealed run can be decomposed at all, and exactly
--------------------------------------------------------
``reproduction.obs_loop`` sends N slice requests per call and emits ONE stitched
hypothesis, ``" ".join(span for span in accepted_spans if span)``. Every piece of
that stitch is in the sealed trace: each slice's own ``MODEL_RESPONSE`` text, the
stitch record's ``stitched_request_ids`` in slice order, and each slice's
``OBS`` window bounds. So the per-window hypothesis is RECOVERED, never re-derived
-- and :func:`assert_stitch_reproduces_outputs` proves the recovery byte for byte
against the sealed ``outputs.jsonl`` before anything is measured. One slice class
is the exception to "each slice's own MODEL_RESPONSE text": a slice whose decode
saturated ``obs_loop``'s token cap keeps its raw ``MODEL_RESPONSE`` in the trace
for audit, but ``obs_loop`` itself replaced its contribution to ``accepted_spans``
with ``""`` before the join (its own ``obs_saturated`` flag says so). The recovery
follows the join, not the raw text: such a window's recovered ``text`` is ``""``
and ``WindowSpan.saturated`` is ``True``, which is what keeps the byte-for-byte
proof honest on a call that saturated at least one slice.

The one real difficulty is that the scorers normalize the WHOLE stitched string at
once (``reproduction.conec_entity_scoring.hypothesis_whisper_words``), and the
Whisper normalizer is not local at a span boundary: on 13 of the 44 sealed calls it
merges number tokens across a boundary, so normalizing each span separately and
concatenating yields 18 more words than normalizing the stitch. Splitting the
hypothesis per span is therefore NOT a valid decomposition of what the scorer
computed.

:func:`hypothesis_window_boundaries` uses the only construction that is: normalize
each PREFIX of the stitch and take its word count. ``c_k`` is the number of
whole-string-normalized hypothesis words the first ``k`` windows account for; the
sequence is non-decreasing and ``c_K`` equals the whole normalization's length
exactly (both asserted, on all 44 sealed calls, in the receipt this module's runner
writes), so ``[c_{k-1}, c_k)`` is a genuine PARTITION of the hypothesis indices the
scorer actually aligned. A token the normalizer merged across a boundary is charged
to the earlier window -- a stated convention, applied deterministically, and it
moves no total.

Reference words then follow the hypothesis through the alignment: every operation
in the trace ``conec-entity-wer-official`` itself computes is charged to exactly one
window (:func:`charge_operations_to_windows`), a deletion to the window its
hypothesis cursor stands in. Because the charge is a partition of the operations,
**summing the per-window rows reproduces the sealed corpus numbers exactly** --
corpus WER 8.200 %, S 13,098 / D 5,701 / I 10,700 over 359,765 reference words, and
every ConEC entity bucket. That is a proof obligation, not a hope:
:func:`aggregate_window_rows` re-derives the totals and the runner compares them to
the sealed values.

Which metrics decompose exactly, and which does not
----------------------------------------------------
``asr-wer-whisper``, ``conec-entity-wer-official`` and
``semantic-high-impact-error-rate-v1`` are all functions of the operation trace, so
the partition above is exact for all three. ``numeric-value-accuracy-v1`` is not: it
BAG-matches the call's reference numeric values against the call's hypothesis
numeric values, and a bag match inside a window is strictly stricter than one across
the call (a value spoken in window 3 and transcribed into window 4 matches at call
level and not at window level). Its per-window ``expected`` and ``hypothesis``
counts still partition exactly; only ``matched`` can fall short, and the runner
reports that shortfall as a number rather than hiding it.

What the window unit does and does not buy
-------------------------------------------
Stated plainly, because it is easy to oversell: for a POOLED statistic with the call
as the cluster, resampling calls and pooling over their windows is arithmetically
identical to resampling calls and pooling over their totals -- **the window unit
changes no digit of the call-clustered interval**. What it buys is (1) the
window-level interval as an explicitly labelled optimistic bound, (2) a paired
saves / harms / ties count at n = 1,593 instead of 44, and (3) per-window strata --
including the diarized speaker strata of ``saea-diarization-v1``, which exist only
at the window level. A verdict that quotes the window-level interval as if it were
the honest one is misreading this module.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence

#: The Earnings window pairing's frozen resampling parameters (the 2026-09-06
#: ruling; the seed is this campaign's own, reused so two reads of the same rows
#: cannot silently differ).
E21_WINDOW_SEED = 20260903
E21_WINDOW_REPLICATES = 10_000
E21_WINDOW_CI_LEVEL = 0.90

#: ``<sample_id>#w<index>`` -- a window id that a plain ``str.split`` turns back
#: into its call, so ``cluster_of`` is a one-liner everywhere.
WINDOW_ID_SEPARATOR = "#w"

RESULT_SCHEMA = "saea-e21-window-pairing-v1"


class WindowPairingError(RuntimeError):
    """A window decomposition input is malformed -- fail closed, never guess."""


def window_id(sample_id: str, window_index: int) -> str:
    if not isinstance(sample_id, str) or not sample_id or WINDOW_ID_SEPARATOR in sample_id:
        raise WindowPairingError(f"sample id {sample_id!r} cannot carry a window suffix")
    if isinstance(window_index, bool) or not isinstance(window_index, int) or window_index < 1:
        raise WindowPairingError("window_index must be a positive integer")
    return f"{sample_id}{WINDOW_ID_SEPARATOR}{window_index:04d}"


def call_of(identifier: str) -> str:
    """The cluster key of a window id -- the ``cluster_of`` callable every
    Earnings paired read passes to ``analysis.paired``."""

    head, separator, _tail = identifier.partition(WINDOW_ID_SEPARATOR)
    if not separator or not head:
        raise WindowPairingError(f"{identifier!r} is not a window id")
    return head


@dataclass(frozen=True)
class WindowSpan:
    """One delivered speech window in its sealed stitch order.

    ``saturated`` is ``True`` when this slice's decode hit ``reproduction.
    obs_loop``'s ``max_tokens`` cap (the trace's own ``obs_saturated``): such a
    slice is a runaway repetition, not a transcript, and ``obs_loop`` drops it
    from the stitched hypothesis (module comment above ``_slice_saturated``,
    "Saturation QUARANTINE"). ``text`` already reflects that -- it is forced
    empty at construction time, never the raw ``MODEL_RESPONSE`` -- and the
    flag is kept on the span so a saturated window stays a named, countable
    covariate of the pairing rather than a silently vanished one.
    """

    sample_id: str
    window_index: int
    request_id: str
    start_seconds: float
    end_seconds: float
    audio_seconds: float
    text: str
    saturated: bool = False
    execution_unit_id: str | None = None
    delivery_kind: str | None = None
    skipped: bool = False

    @property
    def identifier(self) -> str:
        return window_id(self.sample_id, self.window_index)

    def as_dict(self) -> dict[str, object]:
        return {
            "window_id": self.identifier,
            "sample_id": self.sample_id,
            "window_index": self.window_index,
            "request_id": self.request_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "audio_seconds": self.audio_seconds,
            "saturated": self.saturated,
            **({"execution_unit_id": self.execution_unit_id,
                "delivery_kind": self.delivery_kind, "skipped": self.skipped}
               if self.execution_unit_id is not None else {}),
        }


# ---------------------------------------------------------------------------
# 1. Recover the per-window hypothesis from the sealed trace.
# ---------------------------------------------------------------------------


def stitched_windows_from_trace(trace_path: Path | str) -> dict[str, tuple[WindowSpan, ...]]:
    """Every call's windows, in stitch order, out of a sealed ``trace.jsonl``.

    Reads only what the run itself recorded: the per-slice ``MODEL_REQUEST``
    payload (sample id, audio seconds), the per-slice ``OBS`` record (window
    bounds, iteration, ``obs_saturated``), the per-slice ``MODEL_RESPONSE`` text,
    and the per-call stitch ``MODEL_REQUEST``'s ``stitched_request_ids``, which is
    the authority on WHICH slices contributed and in what order (a skipped slice
    never appears in it, exactly as ``reproduction.obs_loop`` records).

    A slice whose ``obs_saturated`` is true stayed IN ``stitched_request_ids``
    (only a skip removes a slice from the stitch) but contributed nothing to the
    stitched text: ``obs_loop`` replaces its transcript with ``""`` before joining
    (module comment above, "Saturation QUARANTINE"). The raw ``MODEL_RESPONSE``
    text is still fully traced for audit, but it is never what was actually
    stitched, so this reader must not read it as the window's hypothesis -- doing
    so re-admits exactly the text ``obs_loop`` excluded. The recovered span's
    ``text`` is therefore forced to ``""`` here too, and ``saturated=True`` is
    carried on the span so the drop is a named covariate, not a silent one.

    A POLICY THAT DELIVERS SOMETHING OTHER THAN THE RAW RESPONSE (KC-E1f, 2026-
    09-07): ``reproduction.repair_loop`` stitches a substitution-only delivery,
    not the pass-2 text, and a refused window delivers its sealed pass-1
    hypothesis rather than the empty string -- including when the pass-2 decode
    saturated. Such a policy records the exact span it contributed in its own
    OBS record as ``obs_delivered_text``, and this reader PREFERS that field
    whenever a trace carries it. The rule is key-gated and strictly additive: no
    trace written before that policy existed carries the key, so every sealed
    run reads byte for byte as it did before, and ``assert_stitch_reproduces_
    outputs`` remains the proof either way.
    """

    path = Path(trace_path)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise WindowPairingError(f"cannot read trace {path}: {error}") from error

    slice_sample: dict[str, str] = {}
    slice_audio: dict[str, float] = {}
    slice_text: dict[str, str] = {}
    slice_delivered: dict[str, str] = {}
    slice_bounds: dict[str, tuple[int, float, float, bool]] = {}
    stitch_order: list[list[str]] = []

    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise WindowPairingError(f"trace line {number} malformed: {error}") from error
        channel = record.get("channel")
        payload = record.get("payload")
        record_id = record.get("record_id")
        if not isinstance(payload, Mapping) or not isinstance(record_id, str):
            raise WindowPairingError(f"trace line {number} has no usable record")
        base = record_id.split("/", 1)[0]
        if channel == "MODEL_REQUEST" and payload.get("stitch"):
            ids = payload.get("stitched_request_ids")
            if not isinstance(ids, list) or not ids:
                raise WindowPairingError(f"stitch record {record_id!r} names no requests")
            stitch_order.append([str(value) for value in ids])
        elif channel == "MODEL_REQUEST":
            inner = payload.get("payload")
            if not isinstance(inner, Mapping):
                raise WindowPairingError(f"slice request {record_id!r} has no payload")
            slice_sample[base] = str(inner["sample_id"])
            slice_audio[base] = float(inner["audio_seconds"])
        elif channel == "MODEL_RESPONSE" and not payload.get("stitch"):
            slice_text[base] = str(payload["text"])
        elif channel == "OBS" and "obs_iteration" in payload:
            slice_bounds[base] = (
                int(payload["obs_iteration"]),
                float(payload["obs_window_start_seconds"]),
                float(payload["obs_window_end_seconds"]),
                bool(payload.get("obs_saturated", False)),
            )
            if "obs_delivered_text" in payload:
                slice_delivered[base] = str(payload["obs_delivered_text"])

    windows: dict[str, tuple[WindowSpan, ...]] = {}
    for ids in stitch_order:
        spans: list[WindowSpan] = []
        sample_ids = {slice_sample.get(request_id) for request_id in ids}
        if len(sample_ids) != 1 or None in sample_ids:
            raise WindowPairingError(f"a stitch spans several samples: {sorted(sample_ids)}")
        sample_id = sample_ids.pop()
        assert sample_id is not None
        if sample_id in windows:
            raise WindowPairingError(f"sample {sample_id!r} carries two stitch records")
        for position, request_id in enumerate(ids, start=1):
            if request_id not in slice_text or request_id not in slice_bounds:
                raise WindowPairingError(
                    f"stitched request {request_id!r} has no response or no OBS record"
                )
            _iteration, start, end, saturated = slice_bounds[request_id]
            # A saturated slice's raw MODEL_RESPONSE text is fully traced for
            # audit but was never stitched (module docstring above): force the
            # recovered span empty exactly as obs_loop's own accepted_spans
            # entry is, rather than reading the raw text back in. A policy that
            # DELIVERED something else said so in its own OBS record, and that
            # is what was stitched -- saturation included.
            if request_id in slice_delivered:
                text = slice_delivered[request_id]
            else:
                text = "" if saturated else slice_text[request_id].strip()
            spans.append(
                WindowSpan(
                    sample_id=sample_id,
                    window_index=position,
                    request_id=request_id,
                    start_seconds=start,
                    end_seconds=end,
                    audio_seconds=slice_audio[request_id],
                    text=text,
                    saturated=saturated,
                )
            )
        windows[sample_id] = tuple(spans)
    if not windows:
        raise WindowPairingError(f"trace {path} carries no stitch records")
    return windows


def stitched_text(spans: Sequence[WindowSpan]) -> str:
    """``reproduction.obs_loop``'s own stitch rule, reproduced exactly: empty
    spans contribute nothing, the rest are joined by a single space."""

    return " ".join(span.text for span in spans if span.text)


def assert_stitch_reproduces_outputs(
    windows: Mapping[str, Sequence[WindowSpan]], outputs_text: Mapping[str, str]
) -> None:
    """Refuse to measure anything until the recovered spans rebuild every sealed
    hypothesis byte for byte. This is the whole basis of the decomposition."""

    if set(windows) != set(outputs_text):
        raise WindowPairingError(
            "the trace's stitched samples and the sealed outputs' samples differ: "
            f"trace-only {sorted(set(windows) - set(outputs_text))}, "
            f"outputs-only {sorted(set(outputs_text) - set(windows))}"
        )
    for sample_id, spans in windows.items():
        rebuilt = stitched_text(spans)
        if rebuilt != outputs_text[sample_id]:
            raise WindowPairingError(
                f"the recovered windows of sample {sample_id!r} do not rebuild the "
                f"sealed hypothesis ({len(rebuilt)} chars vs {len(outputs_text[sample_id])})"
            )


# ---------------------------------------------------------------------------
# 2. Partition the whole-string-normalized hypothesis by window.
# ---------------------------------------------------------------------------


def hypothesis_window_boundaries(
    spans: Sequence[WindowSpan], normalize: Callable[[str], str]
) -> tuple[int, ...]:
    """Cumulative whole-string-normalized word counts, one per window.

    ``boundaries[k]`` is the number of hypothesis words the first ``k + 1``
    windows account for, computed by normalizing the PREFIX of the stitch rather
    than the span, because the normalizer merges tokens across span boundaries
    (module docstring). Non-decreasing by construction and asserted so; the caller
    asserts ``boundaries[-1]`` equals the whole normalization's length.
    """

    boundaries: list[int] = []
    prefix = ""
    for span in spans:
        if span.text:
            prefix = f"{prefix} {span.text}" if prefix else span.text
        boundaries.append(len(normalize(prefix).split()))
    for index in range(1, len(boundaries)):
        if boundaries[index] < boundaries[index - 1]:
            raise WindowPairingError(
                "prefix normalization is not monotone at window "
                f"{index + 1}: {boundaries[index - 1]} then {boundaries[index]}"
            )
    return tuple(boundaries)


def window_of_hypothesis_index(boundaries: Sequence[int], hypothesis_index: int) -> int:
    """The 0-based window a hypothesis word belongs to: the first window whose
    cumulative count strictly exceeds the index."""

    position = bisect_right(list(boundaries), hypothesis_index)
    return min(position, len(boundaries) - 1)


def charge_operations_to_windows(
    operations: Sequence[tuple[str, int | None, int | None]],
    boundaries: Sequence[int],
    hypothesis_length: int,
) -> tuple[tuple[tuple[str, int | None, int | None], ...], ...]:
    """Charge every alignment operation to exactly one window -- a PARTITION, so
    the per-window counts sum to the call's own.

    A hit, substitution or insertion goes to the window of its hypothesis word. A
    deletion consumes no hypothesis word, so it goes to the window its hypothesis
    cursor currently stands in -- the window of the next hypothesis word due,
    clamped to the last window for the deletions that trail the final one.
    """

    if not boundaries:
        raise WindowPairingError("a call must have at least one window")
    if boundaries[-1] != hypothesis_length:
        raise WindowPairingError(
            f"the window boundaries account for {boundaries[-1]} hypothesis words but "
            f"the scorer aligned {hypothesis_length}"
        )
    buckets: list[list[tuple[str, int | None, int | None]]] = [[] for _ in boundaries]
    cursor = 0
    for operation in operations:
        _kind, _ref_index, hyp_index = operation
        if hyp_index is None:
            index = min(cursor, max(hypothesis_length - 1, 0))
        else:
            if hyp_index != cursor:
                raise WindowPairingError(
                    f"alignment trace consumed hypothesis index {hyp_index} where "
                    f"{cursor} was due"
                )
            index = hyp_index
            cursor += 1
        buckets[window_of_hypothesis_index(boundaries, index)].append(operation)
    if cursor != hypothesis_length:
        raise WindowPairingError(
            f"alignment trace consumed {cursor} hypothesis words, expected "
            f"{hypothesis_length}"
        )
    total = sum(len(bucket) for bucket in buckets)
    if total != len(operations):
        raise WindowPairingError(
            f"charging lost operations: {total} of {len(operations)}"
        )
    return tuple(tuple(bucket) for bucket in buckets)


def reference_indices(
    operations: Iterable[tuple[str, int | None, int | None]],
) -> tuple[int, ...]:
    """The reference-word positions one window's operations consume, in order."""

    return tuple(
        ref_index
        for _kind, ref_index, _hyp_index in operations
        if ref_index is not None
    )


def hypothesis_indices(
    operations: Iterable[tuple[str, int | None, int | None]],
) -> tuple[int, ...]:
    """The hypothesis-word positions one window's operations consume, in order."""

    return tuple(
        hyp_index
        for _kind, _ref_index, hyp_index in operations
        if hyp_index is not None
    )


# ---------------------------------------------------------------------------
# 3. Re-aggregation -- the proof obligation.
# ---------------------------------------------------------------------------


def aggregate_window_rows(rows: Iterable[Mapping[str, object]]) -> dict[str, object]:
    """Pool per-window counts back to corpus totals: sum, then divide ONCE --
    the same corpus-aggregation rule ``asr-wer-whisper`` and fstalign both use,
    and the rule this module's exactness claim is stated in."""

    substitutions = deletions = insertions = reference_words = 0
    windows = 0
    for row in rows:
        windows += 1
        substitutions += int(row["substitutions"])
        deletions += int(row["deletions"])
        insertions += int(row["insertions"])
        reference_words += int(row["reference_words"])
    errors = substitutions + deletions + insertions
    return {
        "windows": windows,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "errors": errors,
        "reference_words": reference_words,
        "corpus_wer": (errors / reference_words) if reference_words else 0.0,
    }


def aggregate_entity_buckets(
    per_window: Iterable[Mapping[str, Mapping[str, object]]],
) -> dict[str, dict[str, object]]:
    """``reproduction.conec_entity_scoring.merge_buckets`` over window rows rather
    than call rows -- imported, never re-implemented, so the pooling rule cannot
    drift from the scorer's own."""

    from ..reproduction import conec_entity_scoring as _conec

    return _conec.merge_buckets(per_window)
