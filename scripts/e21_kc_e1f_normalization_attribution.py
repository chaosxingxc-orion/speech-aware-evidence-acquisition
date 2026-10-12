#!/usr/bin/env python3
"""The preregistration's §5.1 obligation, made into a refusable instrument.

Exposure row ``SAEA-E21-KC-E1F-VERDICT-V1`` (``model-free-check``), registered and
committed before the first sealed byte was opened. **Zero model, GPU, tool,
embedder, tokenizer, network, audio-decode and paid-API contacts.** No reference
transcript is opened here at all: this script reads two sealed hypothesis sets and
compares them to each other.

The obligation, quoted from
``docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md``
§5.1:

    The invariant is exact in **raw whitespace-token space**: the delivered
    hypothesis differs from the comparator's only inside accepted substitution
    spans, with identical token counts. It is **not** automatically exact after the
    Whisper normalizer [...] So the delivered hypothesis's *normalized* length can
    move, **but only by the normalization delta of the substituted spans**, and
    nowhere else. [...] **A deletion or insertion delta that cannot be attributed
    to a substituted span is a defect report, not a result**, and aborts the read.

Why a normalized LENGTH delta is exactly the deletion/insertion delta
---------------------------------------------------------------------
For any alignment of a hypothesis against a reference, ``|hyp| = S + I + H`` and
``|ref| = S + D + H``, so ``I - D = |hyp| - |ref|``. The reference is the same
bytes in every arm, so **the arm's ``(I - D)`` minus the comparator's ``(I - D)``
IS the normalized hypothesis-length delta**, digit for digit. Attributing the
length delta to substituted spans therefore attributes the deletion/insertion
move itself; this script asserts the identity rather than assuming it.

How the attribution is computed, and what makes it refusable
-------------------------------------------------------------
The Whisper normalizer is not a per-token map and is not local at a token
boundary (``analysis.e21_window_pairing``'s own docstring measures the effect:
splitting a stitch per span and normalizing the pieces yields 18 more words than
normalizing the whole string, on 13 of the 44 calls). So "the span normalizes to
N words" is not well defined in isolation, and the only construction that IS is
the one the pairing module already uses: normalize each PREFIX of the whole call
and take its word count. ``c[b]`` is then the number of whole-string-normalized
words the first ``b`` raw tokens account for, and any contiguous raw range's
contribution is a difference of two such counts -- a genuine partition of the
words the scorer actually aligned.

Each call is segmented on its raw tokens (identical counts in both arms, which is
checked first):

* every maximal run of positions where the two arms' raw tokens differ is a
  **substituted span** -- the delivery rule admits nothing else, and the flight's
  own delivery-integrity guard already proved the two texts agree everywhere
  else;
* each span is widened by ``--context-tokens`` (default 8) raw tokens on each
  side, and overlapping widened segments are merged: this is the **attributed
  zone**, the region where a normalizer merge could reach across the edit;
* everything left over is **interior**, and its contribution delta must be
  EXACTLY ZERO in every segment. A non-zero interior segment is a normalized-word
  change more than ``--context-tokens`` tokens away from any substitution -- which
  is precisely the defect §5.1 names, and it makes this script exit non-zero.

The verdict runner refuses to compute a contrast unless this instrument's own
verdict is ``PASS``.

What it writes
--------------
* ``<out-dir>/attribution.json`` -- the committed receipt: the identities, the
  raw-space construction checks, the ``I - D`` identity, the per-call table, the
  interior-zero proof, every span that carries a non-zero normalization delta
  (window id, raw index range, token counts, normalized words on each side and a
  content-free shape signature), and the per-window movement summary. **Not one
  hypothesis character**, exactly as the predecessor-binding receipt is
  content-free: hypothesis text is sealed model output and lives under
  ``SPEECHRL_DATA_DIR`` with the sealed outputs.
* ``<spans-out>`` -- the full span table for every substituted span, written
  beside the per-window rows under ``SPEECHRL_DATA_DIR``, never into Git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: E402
    normalize_whisper_english,
)

RESULT_SCHEMA = "saea-e21-repair-normalization-attribution-v1"
EXPOSURE_ROW = "SAEA-E21-KC-E1F-VERDICT-V1"

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)

COMPARATOR_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
COMPARATOR_ATTEMPT = "attempt-20260904T233816Z-bcd338"

_DIGIT = re.compile(r"\d")
_ALPHA = re.compile(r"[A-Za-z]")


def _shape(tokens: list[str]) -> str:
    """A content-free signature of a raw span: which character classes it carries.

    This is a property of the span, never its text -- ``DIGIT`` says a token
    carried a digit, not which digit. It exists so the verdict can say what KIND
    of substitution moved a normalized word count (a numeral splitting under the
    normalizer, say) without putting one character of sealed model output into
    Git.
    """

    joined = "".join(tokens)
    parts = []
    if _DIGIT.search(joined):
        parts.append("DIGIT")
    if _ALPHA.search(joined):
        parts.append("ALPHA")
    if any(character in joined for character in ",.$%-'"):
        parts.append("PUNCT")
    return "+".join(parts) if parts else "OTHER"


def _outputs_text(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        rows[str(record["sample_id"])] = str(record["text"])
    return rows


def _prefix_counts(tokens: list[str], boundaries: list[int]) -> dict[int, int]:
    """``{b: len(normalize(" ".join(tokens[:b])).split())}`` for each boundary."""

    counts: dict[int, int] = {}
    for boundary in boundaries:
        if boundary == 0:
            counts[0] = 0
            continue
        counts[boundary] = len(
            normalize_whisper_english(" ".join(tokens[:boundary])).split()
        )
    return counts


def _spans(left: list[str], right: list[str]) -> list[tuple[int, int]]:
    """Maximal runs of differing positions, as half-open raw index ranges."""

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, (a, b) in enumerate(zip(left, right)):
        if a != b:
            if start is None:
                start = index
        elif start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(left)))
    return runs


def _attributed_zones(
    spans: list[tuple[int, int]], radius: int, length: int
) -> list[tuple[int, int]]:
    """Each span widened by ``radius`` tokens on both sides, overlaps merged."""

    zones: list[tuple[int, int]] = []
    for start, end in spans:
        low = max(0, start - radius)
        high = min(length, end + radius)
        if zones and low <= zones[-1][1]:
            zones[-1] = (zones[-1][0], max(zones[-1][1], high))
        else:
            zones.append((low, high))
    return zones


def _window_offsets(spans: tuple[wp.WindowSpan, ...]) -> list[int]:
    """Cumulative raw-token offset of each window's first token, plus the total."""

    offsets = [0]
    for span in spans:
        offsets.append(offsets[-1] + len(span.text.split()))
    return offsets


def _analyse_call(
    *,
    sample_id: str,
    comparator_windows: tuple[wp.WindowSpan, ...],
    treated_windows: tuple[wp.WindowSpan, ...],
    comparator_text: str,
    treated_text: str,
    radius: int,
) -> dict:
    left = comparator_text.split()
    right = treated_text.split()
    failures: list[dict] = []
    if len(left) != len(right):
        failures.append(
            {
                "kind": "raw_token_count_moved",
                "sample_id": sample_id,
                "comparator": len(left),
                "treated": len(right),
            }
        )
        return {
            "sample_id": sample_id,
            "failures": failures,
            "raw_tokens": {"comparator": len(left), "treated": len(right)},
        }

    left_offsets = _window_offsets(comparator_windows)
    right_offsets = _window_offsets(treated_windows)
    if left_offsets != right_offsets or left_offsets[-1] != len(left):
        failures.append(
            {
                "kind": "window_token_offsets_disagree",
                "sample_id": sample_id,
                "comparator_total": left_offsets[-1],
                "treated_total": right_offsets[-1],
                "raw_tokens": len(left),
            }
        )

    spans = _spans(left, right)
    zones = _attributed_zones(spans, radius, len(left))

    segments: list[tuple[int, int, str]] = []
    cursor = 0
    for low, high in zones:
        if low > cursor:
            segments.append((cursor, low, "interior"))
        segments.append((low, high, "attributed"))
        cursor = high
    if cursor < len(left):
        segments.append((cursor, len(left), "interior"))

    boundaries = sorted(
        {0, len(left)}
        | {low for low, _high, _kind in segments}
        | {high for _low, high, _kind in segments}
        | set(left_offsets)
    )
    left_counts = _prefix_counts(left, boundaries)
    right_counts = _prefix_counts(right, boundaries)

    interior_tokens = 0
    attributed_tokens = 0
    interior_nonzero: list[dict] = []
    attributed_delta = 0
    for low, high, kind in segments:
        delta = (right_counts[high] - right_counts[low]) - (
            left_counts[high] - left_counts[low]
        )
        if kind == "interior":
            interior_tokens += high - low
            if delta != 0:
                interior_nonzero.append(
                    {
                        "sample_id": sample_id,
                        "raw_token_range": [low, high],
                        "normalized_delta": delta,
                    }
                )
        else:
            attributed_tokens += high - low
            attributed_delta += delta

    if interior_nonzero:
        failures.append(
            {
                "kind": "unattributed_normalization_delta",
                "sample_id": sample_id,
                "segments": interior_nonzero,
            }
        )

    total_delta = right_counts[len(left)] - left_counts[len(left)]
    if attributed_delta + sum(
        row["normalized_delta"] for row in interior_nonzero
    ) != total_delta:
        failures.append(
            {
                "kind": "segment_deltas_do_not_sum",
                "sample_id": sample_id,
                "attributed": attributed_delta,
                "total": total_delta,
            }
        )

    span_rows: list[dict] = []
    for start, end in spans:
        low = max(0, start - radius)
        high = min(len(left), end + radius)
        if low not in left_counts:
            left_counts[low] = _prefix_counts(left, [low])[low]
            right_counts[low] = _prefix_counts(right, [low])[low]
        if high not in left_counts:
            left_counts[high] = _prefix_counts(left, [high])[high]
            right_counts[high] = _prefix_counts(right, [high])[high]
        window_index = 0
        while (
            window_index + 1 < len(left_offsets)
            and left_offsets[window_index + 1] <= start
        ):
            window_index += 1
        span_rows.append(
            {
                "sample_id": sample_id,
                "window_id": wp.window_id(sample_id, window_index + 1),
                "raw_token_range": [start, end],
                "raw_tokens": end - start,
                "context_range": [low, high],
                "comparator_normalized_words_in_context": left_counts[high]
                - left_counts[low],
                "treated_normalized_words_in_context": right_counts[high]
                - right_counts[low],
                "normalized_delta": (right_counts[high] - right_counts[low])
                - (left_counts[high] - left_counts[low]),
                "comparator_shape": _shape(left[start:end]),
                "treated_shape": _shape(right[start:end]),
            }
        )

    per_window: list[dict] = []
    for index in range(len(left_offsets) - 1):
        low = left_offsets[index]
        high = left_offsets[index + 1]
        delta = (right_counts[high] - right_counts[low]) - (
            left_counts[high] - left_counts[low]
        )
        changed = sum(
            1 for start, end in spans if start < high and end > low
        )
        per_window.append(
            {
                "window_id": wp.window_id(sample_id, index + 1),
                "raw_tokens": high - low,
                "substituted_spans": changed,
                "comparator_normalized_words": left_counts[high] - left_counts[low],
                "treated_normalized_words": right_counts[high] - right_counts[low],
                "normalized_delta": delta,
            }
        )

    return {
        "sample_id": sample_id,
        "raw_tokens": {"comparator": len(left), "treated": len(right)},
        "differing_positions": sum(end - start for start, end in spans),
        "spans": len(spans),
        "interior_tokens": interior_tokens,
        "attributed_zone_tokens": attributed_tokens,
        "normalized_words": {
            "comparator": left_counts[len(left)],
            "treated": right_counts[len(left)],
            "delta": total_delta,
        },
        "attributed_delta": attributed_delta,
        "interior_nonzero": interior_nonzero,
        "span_rows": span_rows,
        "per_window": per_window,
        "failures": failures,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--treated-run-id", required=True)
    parser.add_argument("--treated-attempt-id", required=True)
    parser.add_argument("--comparator-run-id", default=COMPARATOR_RUN)
    parser.add_argument("--comparator-attempt-id", default=COMPARATOR_ATTEMPT)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--spans-out",
        type=Path,
        default=None,
        help=(
            "where the full span table goes (default: "
            "$SPEECHRL_DATA_DIR/runs/SAEA-E21-MF-WINDOW-PAIRING-V1/"
            "kce1f-attribution-spans-<treated run id>.json); never inside the repository"
        ),
    )
    parser.add_argument(
        "--context-tokens",
        type=int,
        default=8,
        help=(
            "how many raw tokens on each side of a substituted span count as its "
            "normalization boundary; the interior beyond it must move by exactly zero"
        ),
    )
    args = parser.parse_args(argv)
    started = time.time()

    def attempt_dir(run_id: str, attempt_id: str) -> Path:
        run_dir = args.data_root / "runs" / run_id
        nested = run_dir / attempt_id
        return nested if nested.exists() else run_dir

    comparator_dir = attempt_dir(args.comparator_run_id, args.comparator_attempt_id)
    treated_dir = attempt_dir(args.treated_run_id, args.treated_attempt_id)

    comparator_outputs = _outputs_text(
        comparator_dir / f"{args.comparator_run_id}.outputs.jsonl"
    )
    treated_outputs = _outputs_text(treated_dir / f"{args.treated_run_id}.outputs.jsonl")
    comparator_windows = wp.stitched_windows_from_trace(
        comparator_dir / f"{args.comparator_run_id}.trace.jsonl"
    )
    treated_windows = wp.stitched_windows_from_trace(
        treated_dir / f"{args.treated_run_id}.trace.jsonl"
    )
    wp.assert_stitch_reproduces_outputs(comparator_windows, comparator_outputs)
    wp.assert_stitch_reproduces_outputs(treated_windows, treated_outputs)
    if set(comparator_outputs) != set(treated_outputs):
        raise SystemExit("the two arms do not carry the same calls")

    calls: list[dict] = []
    failures: list[dict] = []
    for sample_id in sorted(comparator_outputs):
        result = _analyse_call(
            sample_id=sample_id,
            comparator_windows=comparator_windows[sample_id],
            treated_windows=treated_windows[sample_id],
            comparator_text=comparator_outputs[sample_id],
            treated_text=treated_outputs[sample_id],
            radius=args.context_tokens,
        )
        failures.extend(result.pop("failures"))
        calls.append(result)
        print(
            f"{sample_id} spans {result['spans']:4} differing {result['differing_positions']:5} "
            f"normalized delta {result['normalized_words']['delta']:+d} "
            f"interior nonzero {len(result['interior_nonzero'])}",
            flush=True,
        )

    spans_path = args.spans_out or (
        args.data_root
        / "runs"
        / "SAEA-E21-MF-WINDOW-PAIRING-V1"
        / f"kce1f-attribution-spans-{args.treated_run_id}.json"
    )
    spans_path.parent.mkdir(parents=True, exist_ok=True)
    spans_path.write_text(
        json.dumps(
            {
                "schema": RESULT_SCHEMA + "-spans",
                "exposure_row": EXPOSURE_ROW,
                "treated_run_id": args.treated_run_id,
                "comparator_run_id": args.comparator_run_id,
                "context_tokens": args.context_tokens,
                "spans": [row for call in calls for row in call["span_rows"]],
                "per_window": [row for call in calls for row in call["per_window"]],
            },
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    spans_sha256 = hashlib.sha256(spans_path.read_bytes()).hexdigest()

    moving_spans = [
        row
        for call in calls
        for row in call["span_rows"]
        if row["normalized_delta"] != 0
    ]
    moving_windows = [
        row
        for call in calls
        for row in call["per_window"]
        if row["normalized_delta"] != 0
    ]
    windows_without_a_span_that_moved = [
        row for row in moving_windows if row["substituted_spans"] == 0
    ]
    totals = {
        "calls": len(calls),
        "raw_tokens": sum(call["raw_tokens"]["comparator"] for call in calls),
        "differing_positions": sum(call["differing_positions"] for call in calls),
        "substituted_spans": sum(call["spans"] for call in calls),
        "interior_tokens": sum(call["interior_tokens"] for call in calls),
        "attributed_zone_tokens": sum(call["attributed_zone_tokens"] for call in calls),
        "comparator_normalized_words": sum(
            call["normalized_words"]["comparator"] for call in calls
        ),
        "treated_normalized_words": sum(
            call["normalized_words"]["treated"] for call in calls
        ),
        "normalized_word_delta": sum(
            call["normalized_words"]["delta"] for call in calls
        ),
        "attributed_delta": sum(call["attributed_delta"] for call in calls),
        "spans_with_a_non_zero_delta": len(moving_spans),
        "windows_with_a_non_zero_delta": len(moving_windows),
        "windows_that_moved_without_carrying_a_span": len(
            windows_without_a_span_that_moved
        ),
    }
    verdict = "FAIL" if failures else "PASS"

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "attribution.json").write_text(
        json.dumps(
            {
                "schema": RESULT_SCHEMA,
                "study": "speech-aware-evidence-acquisition",
                "exposure_row": EXPOSURE_ROW,
                "verdict": verdict,
                "obligation": (
                    "preregistration section 5.1: the delivered hypothesis differs from "
                    "the comparator's only inside accepted substitution spans in RAW "
                    "whitespace-token space, so its NORMALIZED length may move only by "
                    "the normalization delta of those spans; a deletion or insertion "
                    "delta that cannot be attributed to a substituted span is a defect "
                    "report and aborts the read"
                ),
                "identity": (
                    "|hyp| = S + I + H and |ref| = S + D + H, so (I - D) is |hyp| minus "
                    "a constant reference length: the arm's normalized-word delta "
                    "against the comparator IS its (insertions - deletions) delta"
                ),
                "treated_run_id": args.treated_run_id,
                "treated_attempt_id": args.treated_attempt_id,
                "comparator_run_id": args.comparator_run_id,
                "comparator_attempt_id": args.comparator_attempt_id,
                "context_tokens": args.context_tokens,
                "totals": totals,
                "failures": failures,
                "spans_with_a_non_zero_delta": moving_spans,
                "windows_that_moved": moving_windows,
                "per_call": [
                    {
                        key: value
                        for key, value in call.items()
                        if key not in {"span_rows", "per_window"}
                    }
                    for call in calls
                ],
                "spans_table": {"path": str(spans_path), "sha256": spans_sha256},
                "zero_contact": (
                    "no model, GPU, tool, embedding, tokenizer, network, audio-decode or "
                    "paid-API contact; no reference transcript is opened by this script"
                ),
                "elapsed_seconds": round(time.time() - started, 1),
            },
            indent=1,
            sort_keys=True,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(json.dumps(totals, indent=1, sort_keys=True))
    print(f"verdict {verdict}; spans table -> {spans_path} ({spans_sha256[:12]}...)")
    print(f"elapsed {time.time() - started:.1f}s")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
