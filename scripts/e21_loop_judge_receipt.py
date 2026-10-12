#!/usr/bin/env python3
"""The E21-LOOP-1 judge inventory, priced model-free on the sealed comparator.

Exposure row ``SAEA-E21-MF-LOOP-1-PREP-V1`` (``model-free-check``), registered
and committed before the first sealed byte is opened. **Zero model, GPU,
server, tokenizer, tool, embedder, network, audio-decode and paid-API
contacts.** Nothing here decides a cell; it measures the instrument E21-LOOP-1
will fly with, and the flagged-window count it produces IS that cell's contact
budget.

The two questions, and why they can be answered without a contact
------------------------------------------------------------------
A judge under the Reviewer seat changes no byte of what a flight sends (WAVE
W1 section 2), so its own admission question is not "does it help the score"
but **"when it fires, is the row actually wrong"** (precision) and **"of the
rows that are wrong, how many does it catch"** (recall). Both are properties
of a judge, a draft and a truth set, and this repository already holds all
three: the draft is the sealed comparator's own per-window pass-1 hypothesis,
recovered -- never re-derived -- through ``analysis.e21_window_pairing``; the
truth is the ConEC alignment that same instrument charges to each window.

What the truth set is, exactly
-------------------------------
A **PERSON/ORG substitution**: an alignment operation of kind
``OP_SUBSTITUTION`` whose reference word carries at least one PERSON or ORG
entity ID. Deletions are counted and reported separately and are NOT in the
recall denominator, for a structural reason rather than a convenient one: a
deletion consumes no hypothesis word, so no span-based judge reading the draft
can point at it. Insertions never reach an entity bucket at all (fstalign
attributes no insertion to a tag), so they cannot be PERSON/ORG errors by
construction.

The index bridge, and its one stated convention
------------------------------------------------
Judges flag spans over their own view of the draft: ``e21-brief-name-near-miss
-v1`` over the draft's RAW whitespace words, ``earnings-numeric-format-flag-v1``
over the draft's WHISPER-NORMALIZED words. The alignment is over the whole
call's normalized hypothesis. Every flag is therefore lifted into the call's
normalized hypothesis index space before it is joined with the truth:

* a raw span ``[a, b)`` becomes ``[cum[a], cum[b])`` where ``cum[j]`` is the
  normalized word count of the window's own first ``j`` raw words -- the same
  PREFIX-NORMALIZATION construction ``hypothesis_window_boundaries`` uses at
  the window grain, applied one level finer;
* a window-local normalized index is offset by that window's own global
  boundary.

The convention this inherits: a token the normalizer merges across a boundary
is charged to the EARLIER position. It moves no total, and the number of
windows whose local normalization disagrees with the global partition is
reported as a covariate rather than hidden.

Usage (WSL2)::

    python scripts/e21_loop_judge_receipt.py --out-dir <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_loop_flags as flags_module,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    e21_window_pairing as wp,
)
from speech_aware_evidence_acquisition.core import policies as _policies  # noqa: E402,F401
from speech_aware_evidence_acquisition.core.base import JUDGES  # noqa: E402
from speech_aware_evidence_acquisition.core.judges import (  # noqa: E402
    E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1,
    E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1,
    EARNINGS_NUMERIC_FORMAT_JUDGE_V1,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.references import (  # noqa: E402
    reference_entity_mentions,
    reference_tokens,
)
from speech_aware_evidence_acquisition.reproduction import (  # noqa: E402
    conec_entity_scoring as conec,
)
from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (  # noqa: E402
    normalize_whisper_english,
)

RESULT_SCHEMA = "saea-e21-loop-judge-receipt-v1"
EXPOSURE_ROW = "SAEA-E21-MF-LOOP-1-PREP-V1"
CARRIER = "earnings21-original"

#: The sealed comparator whose pass-1 hypothesis IS E21-LOOP-1's draft: the
#: same run KC-E1f bound as its predecessor and the same one the cell is
#: paired against.
SEALED_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
SEALED_ATTEMPT = "attempt-20260904T233816Z-bcd338"

#: The identity anchor: this read refuses to publish a precision if the
#: comparator it decomposed does not reproduce its own sealed corpus numbers
#: through this instrument. Quoted from the sealed verdicts.
SEALED_ANCHOR = {
    "windows": 1593,
    "calls": 44,
    "substitutions": 13098,
    "deletions": 5701,
    "insertions": 10700,
    "reference_words": 359765,
    "person_reference_words": 2917,
    "org_reference_words": 4363,
    "person_entity_wer_percent": 22.489,
    "org_entity_wer_percent": 17.213,
}

#: The brief cap KC-E1 and KC-E1f both flew. E21-LOOP-1 supplies the SAME
#: brief, so the judge is priced against the same entry set the Solver will
#: be given.
BRIEF_MAX_ENTRIES_PER_CLASS = flags_module.BRIEF_MAX_ENTRIES_PER_CLASS

#: Reported sensitivity band for the near-miss judge. The FLOWN operating
#: point is the judge's own frozen default; the rest are covariates, so a
#: reader can see the shape of the trade rather than a single number.
DISTANCE_LADDER = (0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.45)

DEFAULT_DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR",
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET"),
    )
)


class ReceiptError(RuntimeError):
    """A model-free read input is malformed -- fail closed, never guess."""


# ---------------------------------------------------------------------------
# The brief's PERSON and ORG classes
# ---------------------------------------------------------------------------


def brief_classes(lock, data_root: Path, sample_id: str) -> tuple[list[str], list[str]]:
    """This call's PERSON and ORG brief entries, at the flown cap.

    Delegates to ``analysis.e21_loop_flags.brief_classes``, which is the ONE
    authority for the Reviewer's inputs: the plan builder calls the same
    function, so a plan can never be built from a different brief than the one
    this receipt priced.
    """

    return flags_module.brief_classes(
        lock, data_root, sample_id,
        carrier_lock_key=CARRIER,
        max_entries=BRIEF_MAX_ENTRIES_PER_CLASS,
    )


# ---------------------------------------------------------------------------
# The index bridge
# ---------------------------------------------------------------------------


def raw_word_normalized_bounds(raw_words: Sequence[str]) -> tuple[int, ...]:
    """``cum[j]`` = the normalized word count of the first ``j`` raw words.

    ``cum[0]`` is 0 and ``cum[len(raw)]`` is the whole text's normalized
    length, so raw word ``j`` occupies normalized ``[cum[j], cum[j + 1])`` --
    possibly empty (a filler the normalizer drops) and possibly wider than one
    (a raw token the normalizer splits). Built by PREFIX normalization, the
    construction ``analysis.e21_window_pairing.hypothesis_window_boundaries``
    uses at the window grain, so the two agree wherever they overlap.
    """

    cumulative = [0]
    prefix = ""
    for word in raw_words:
        prefix = f"{prefix} {word}" if prefix else word
        cumulative.append(len(normalize_whisper_english(prefix).split()))
    return tuple(cumulative)


def lift_raw_span(
    span: tuple[int, int], cumulative: Sequence[int], offset: int, limit: int
) -> tuple[int, int] | None:
    """A raw-word span, lifted into the call's normalized hypothesis indices."""

    start, end = span
    if start < 0 or end <= start or end > len(cumulative) - 1:
        return None
    low = offset + cumulative[start]
    high = offset + cumulative[end]
    low = max(low, offset)
    high = min(high, limit)
    if high <= low:
        return None
    return (low, high)


def lift_normalized_span(
    span: tuple[int, int], offset: int, limit: int
) -> tuple[int, int] | None:
    start, end = span
    low = max(offset + start, offset)
    high = min(offset + end, limit)
    if high <= low:
        return None
    return (low, high)


# ---------------------------------------------------------------------------
# The read
# ---------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _outputs_text(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            rows[str(row["sample_id"])] = str(row["text"])
    return rows


def _entity_hyp_indices(
    operations: Sequence[tuple[str, int | None, int | None]],
    owners: Sequence[tuple[str, ...]],
    entity_types: Mapping[str, str],
    wanted: frozenset[str],
) -> tuple[set[int], int]:
    """(the hypothesis indices of PERSON/ORG substitutions, the PERSON/ORG
    deletion count) among one window's charged operations."""

    substitutions: set[int] = set()
    deletions = 0
    for kind, ref_index, hyp_index in operations:
        if ref_index is None:
            continue
        owner = owners[ref_index]
        if not owner:
            # ``transfer_owners`` returns None for a whole-string reference
            # word whose ownership could not be resolved, and an empty tuple
            # for one that carries no entity id: neither is a PERSON/ORG word.
            continue
        classes = {entity_types.get(entity_id, "") for entity_id in owner}
        if not classes & wanted:
            continue
        if kind == conec.OP_SUBSTITUTION and hyp_index is not None:
            substitutions.add(hyp_index)
        elif kind == conec.OP_DELETION:
            deletions += 1
    return substitutions, deletions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--calls",
        type=int,
        default=0,
        help="debug only: stop after N calls; a receipt is written only at 0",
    )
    args = parser.parse_args(argv)

    started = time.time()
    attempt_dir = args.data_root / "runs" / SEALED_RUN / SEALED_ATTEMPT
    outputs_path = attempt_dir / f"{SEALED_RUN}.outputs.jsonl"
    trace_path = attempt_dir / f"{SEALED_RUN}.trace.jsonl"
    for path in (outputs_path, trace_path):
        if not path.is_file():
            raise ReceiptError(f"sealed artifact missing: {path}")

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    outputs_text = _outputs_text(outputs_path)
    windows = wp.stitched_windows_from_trace(trace_path)
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)

    near_miss = JUDGES.resolve(E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1)
    numeric = JUDGES.resolve(EARNINGS_NUMERIC_FORMAT_JUDGE_V1)
    alignment = JUDGES.resolve(E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1)
    wanted = frozenset({"PERSON", "ORG"})

    # Per-judge accumulators, plus one for the whole inventory (the union of
    # its flags), which is what actually prices the cell.
    judge_ids = [
        E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1,
        EARNINGS_NUMERIC_FORMAT_JUDGE_V1,
        E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1,
    ]
    stats = {
        name: {
            "flagged_spans": 0,
            "flagged_spans_hitting_a_person_org_substitution": 0,
            "flagged_windows": 0,
            "flagged_windows_carrying_a_person_org_substitution": 0,
            "person_org_substitutions_covered": 0,
            "person_org_substitutions_in_a_flagged_window": 0,
            "flagged_normalized_words": 0,
        }
        for name in ("inventory", *judge_ids)
    }
    ladder = {
        f"{value:.2f}": {
            "flagged_spans": 0,
            "flagged_spans_hitting_a_person_org_substitution": 0,
            "flagged_windows": 0,
            "flagged_windows_carrying_a_person_org_substitution": 0,
            "person_org_substitutions_covered": 0,
            "person_org_substitutions_in_a_flagged_window": 0,
        }
        for value in DISTANCE_LADDER
    }

    totals = {
        "windows": 0,
        "calls": 0,
        "substitutions": 0,
        "deletions": 0,
        "insertions": 0,
        "reference_words": 0,
        "normalized_hypothesis_words": 0,
        "raw_draft_words": 0,
        "person_org_substitutions": 0,
        "person_org_deletions": 0,
        "windows_carrying_a_person_org_substitution": 0,
        "windows_whose_local_normalization_disagrees": 0,
        "normalization_word_delta": 0,
        "empty_windows": 0,
        "brief_person_entries": 0,
        "brief_org_entries": 0,
    }
    entity_totals: list[dict] = []
    per_call: list[dict] = []
    flag_code_counts: Counter[str] = Counter()

    sample_ids = sorted(windows)
    if args.calls:
        sample_ids = sample_ids[: args.calls]

    for sample_id in sample_ids:
        spans = windows[sample_id]
        person_terms, org_terms = brief_classes(lock, args.data_root, sample_id)
        totals["brief_person_entries"] += len(person_terms)
        totals["brief_org_entries"] += len(org_terms)

        raw_tokens = reference_tokens(lock, args.data_root, CARRIER, sample_id)
        mentions = reference_entity_mentions(lock, args.data_root, CARRIER, sample_id)
        owners_by_index: list[list[str]] = [[] for _ in raw_tokens]
        entity_types: dict[str, str] = {}
        for mention in mentions:
            entity_types[mention.entity_id] = mention.entity_type
            for index in mention.token_indices:
                owners_by_index[index].append(mention.entity_id)
        owners = [tuple(sorted(ids)) for ids in owners_by_index]

        whole_words = conec.whole_string_whisper_words(raw_tokens)
        chunked_words, chunked_owners = conec.run_chunked_whisper_words(raw_tokens, owners)
        transferred = conec.transfer_owners(chunked_words, chunked_owners, whole_words)
        hypothesis_words = conec.hypothesis_whisper_words(outputs_text[sample_id])
        operations = conec.aligned_operations(whole_words, hypothesis_words)
        boundaries = wp.hypothesis_window_boundaries(spans, normalize_whisper_english)
        charged = wp.charge_operations_to_windows(
            operations, boundaries, len(hypothesis_words)
        )

        call_person_org = 0
        call_covered = 0
        call_flagged_windows = 0
        for index, (span, window_operations) in enumerate(zip(spans, charged)):
            totals["windows"] += 1
            offset = boundaries[index - 1] if index else 0
            limit = boundaries[index]
            entity_totals.append(
                conec.entity_wer_buckets(window_operations, transferred, entity_types)
            )

            truth, deletion_count = _entity_hyp_indices(
                window_operations, transferred, entity_types, wanted
            )
            totals["person_org_substitutions"] += len(truth)
            totals["person_org_deletions"] += deletion_count
            call_person_org += len(truth)
            if truth:
                totals["windows_carrying_a_person_org_substitution"] += 1

            draft = span.text
            raw_words = draft.split()
            totals["raw_draft_words"] += len(raw_words)
            totals["normalized_hypothesis_words"] += limit - offset
            if not raw_words:
                totals["empty_windows"] += 1
                continue
            cumulative = raw_word_normalized_bounds(raw_words)
            if cumulative[-1] != limit - offset:
                totals["windows_whose_local_normalization_disagrees"] += 1
                totals["normalization_word_delta"] += cumulative[-1] - (limit - offset)

            window_spans: dict[str, list[tuple[int, int]]] = {}
            verdict = near_miss(
                draft, {"person_terms": person_terms, "org_terms": org_terms}, {}
            )
            window_spans[E21_BRIEF_NAME_NEAR_MISS_JUDGE_V1] = [
                lifted
                for flag in verdict.flags
                if (lifted := lift_raw_span(flag.span, cumulative, offset, limit))
                is not None
            ]
            for flag in verdict.flags:
                flag_code_counts[flag.code] += 1

            verdict = numeric(draft, {}, {})
            window_spans[EARNINGS_NUMERIC_FORMAT_JUDGE_V1] = [
                lifted
                for flag in verdict.flags
                if (lifted := lift_normalized_span(flag.span, offset, limit)) is not None
            ]
            for flag in verdict.flags:
                flag_code_counts[flag.code] += 1

            # The alignment judge on a PASS-1 draft compares the draft with
            # itself: its predecessor IS the draft, so it can only report a
            # perfect alignment. Measured rather than assumed -- the number
            # this produces is the reason the loop places it after the Solve,
            # not before it.
            verdict = alignment(draft, {"predecessor_text": draft}, {})
            window_spans[E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1] = [
                lifted
                for flag in verdict.flags
                if flag.span is not None
                and (lifted := lift_normalized_span(flag.span, offset, limit)) is not None
            ]
            for flag in verdict.flags:
                flag_code_counts[flag.code] += 1
                stats[E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1]["flagged_spans"] += 1

            union: list[tuple[int, int]] = []
            for name in judge_ids:
                lifted_spans = window_spans[name]
                bucket = stats[name]
                if name != E21_SUBSTITUTION_ALIGNMENT_JUDGE_V1:
                    bucket["flagged_spans"] += len(lifted_spans)
                covered: set[int] = set()
                for low, high in lifted_spans:
                    bucket["flagged_normalized_words"] += high - low
                    hits = truth & set(range(low, high))
                    if hits:
                        bucket["flagged_spans_hitting_a_person_org_substitution"] += 1
                        covered |= hits
                bucket["person_org_substitutions_covered"] += len(covered)
                if lifted_spans:
                    bucket["flagged_windows"] += 1
                    # The number that prices the LOOP rather than the flag: the
                    # Solver hears the whole re-cut window and is shown its whole
                    # word range, so every PERSON/ORG substitution in a FLAGGED
                    # WINDOW is reachable, not only the ones a span covers.
                    bucket["person_org_substitutions_in_a_flagged_window"] += len(truth)
                    if truth:
                        bucket[
                            "flagged_windows_carrying_a_person_org_substitution"
                        ] += 1
                union.extend(lifted_spans)

            bucket = stats["inventory"]
            bucket["flagged_spans"] += len(union)
            covered = set()
            for low, high in union:
                bucket["flagged_normalized_words"] += high - low
                hits = truth & set(range(low, high))
                if hits:
                    bucket["flagged_spans_hitting_a_person_org_substitution"] += 1
                    covered |= hits
            bucket["person_org_substitutions_covered"] += len(covered)
            call_covered += len(covered)
            if union:
                bucket["flagged_windows"] += 1
                bucket["person_org_substitutions_in_a_flagged_window"] += len(truth)
                call_flagged_windows += 1
                if truth:
                    bucket["flagged_windows_carrying_a_person_org_substitution"] += 1

            for value in DISTANCE_LADDER:
                rung = ladder[f"{value:.2f}"]
                rung_verdict = near_miss(
                    draft,
                    {
                        "person_terms": person_terms,
                        "org_terms": org_terms,
                        "max_distance": value,
                    },
                    {},
                )
                rung_spans = [
                    lifted
                    for flag in rung_verdict.flags
                    if (lifted := lift_raw_span(flag.span, cumulative, offset, limit))
                    is not None
                ]
                rung["flagged_spans"] += len(rung_spans)
                rung_covered: set[int] = set()
                for low, high in rung_spans:
                    hits = truth & set(range(low, high))
                    if hits:
                        rung["flagged_spans_hitting_a_person_org_substitution"] += 1
                        rung_covered |= hits
                rung["person_org_substitutions_covered"] += len(rung_covered)
                if rung_spans:
                    rung["flagged_windows"] += 1
                    rung["person_org_substitutions_in_a_flagged_window"] += len(truth)
                    if truth:
                        rung[
                            "flagged_windows_carrying_a_person_org_substitution"
                        ] += 1

        totals["calls"] += 1
        per_call.append(
            {
                "sample_id": sample_id,
                "windows": len(spans),
                "brief_person_entries": len(person_terms),
                "brief_org_entries": len(org_terms),
                "person_org_substitutions": call_person_org,
                "person_org_substitutions_covered": call_covered,
                "flagged_windows": call_flagged_windows,
            }
        )

    aggregate = conec.merge_buckets(entity_totals)
    for kind in ("substitutions", "deletions", "insertions"):
        totals[kind] = int(aggregate[conec.OVERALL_BUCKET][kind])
    totals["reference_words"] = int(aggregate[conec.OVERALL_BUCKET]["reference_words"])

    checks: list[dict] = []

    def check(name: str, actual, expected, ok: bool, note: str = "") -> None:
        checks.append(
            {
                "check": name,
                "actual": actual,
                "expected": expected,
                "verdict": "PASS" if ok else "FAIL",
                **({"note": note} if note else {}),
            }
        )

    if not args.calls:
        for key in (
            "windows",
            "calls",
            "substitutions",
            "deletions",
            "insertions",
            "reference_words",
        ):
            check(key, totals[key], SEALED_ANCHOR[key], totals[key] == SEALED_ANCHOR[key])
        for entity, key in (("PERSON", "person"), ("ORG", "org")):
            bucket = aggregate.get(entity, {"wer": 0.0, "reference_words": 0})
            check(
                f"{key}_reference_words",
                bucket["reference_words"],
                SEALED_ANCHOR[f"{key}_reference_words"],
                bucket["reference_words"] == SEALED_ANCHOR[f"{key}_reference_words"],
            )
            measured = bucket["wer"] * 100.0
            check(
                f"{key}_entity_wer_percent",
                round(measured, 3),
                SEALED_ANCHOR[f"{key}_entity_wer_percent"],
                abs(measured - SEALED_ANCHOR[f"{key}_entity_wer_percent"]) <= 0.001,
            )

    def rates(bucket: Mapping[str, int]) -> dict[str, object]:
        spans = int(bucket["flagged_spans"])
        hits = int(bucket["flagged_spans_hitting_a_person_org_substitution"])
        covered = int(bucket["person_org_substitutions_covered"])
        truth_total = totals["person_org_substitutions"]
        windows = int(bucket["flagged_windows"])
        return {
            **{key: int(value) for key, value in bucket.items()},
            "span_precision": (hits / spans) if spans else None,
            "substitution_recall": (covered / truth_total) if truth_total else None,
            "substitution_recall_including_deletions": (
                covered / (truth_total + totals["person_org_deletions"])
                if truth_total + totals["person_org_deletions"]
                else None
            ),
            "flagged_window_share": (windows / totals["windows"])
            if totals["windows"]
            else None,
            "window_precision": (
                int(bucket.get("flagged_windows_carrying_a_person_org_substitution", 0))
                / windows
            )
            if windows
            else None,
            # Window-level RECALL: the share of PERSON/ORG substitutions that
            # sit in a window this judge flagged. It is the loop's own ceiling
            # -- a substitution in an unflagged window is never contacted -- and
            # it is always at least the span-level recall.
            "window_recall": (
                int(bucket.get("person_org_substitutions_in_a_flagged_window", 0))
                / truth_total
            )
            if truth_total
            else None,
            "window_recall_of_windows": (
                int(bucket.get("flagged_windows_carrying_a_person_org_substitution", 0))
                / totals["windows_carrying_a_person_org_substitution"]
            )
            if totals["windows_carrying_a_person_org_substitution"]
            else None,
        }

    payload = {
        "schema": RESULT_SCHEMA,
        "exposure_row": EXPOSURE_ROW,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.time() - started, 3),
        "contacts": {
            "model": 0,
            "gpu": 0,
            "server": 0,
            "tokenizer": 0,
            "tool": 0,
            "embedder": 0,
            "network": 0,
            "audio_decode": 0,
            "paid_api_usd": 0,
        },
        "source": {
            "run_id": SEALED_RUN,
            "attempt_id": SEALED_ATTEMPT,
            "outputs_sha256": _sha256(outputs_path),
            "trace_sha256": _sha256(trace_path),
            "brief_max_entries_per_class": BRIEF_MAX_ENTRIES_PER_CLASS,
        },
        "identity_anchor": checks,
        "identity_anchor_verdict": (
            "PASS" if all(entry["verdict"] == "PASS" for entry in checks) else "FAIL"
        ),
        "truth_definition": {
            "positive": (
                "an OP_SUBSTITUTION whose reference word carries a PERSON or ORG "
                "entity id, in the sealed comparator's own ConEC alignment"
            ),
            "excluded": (
                "PERSON/ORG deletions consume no hypothesis word, so no span-based "
                "judge reading the draft can point at one; they are counted and "
                "reported, and recall is given both without and with them in the "
                "denominator"
            ),
            "insertions": (
                "never reach an entity bucket at all (fstalign attributes no "
                "insertion to a tag)"
            ),
        },
        "totals": totals,
        "judges": {
            name: {
                "version": JUDGES.resolve(name).version
                if name != "inventory"
                else None,
                **rates(bucket),
            }
            for name, bucket in stats.items()
        },
        "near_miss_distance_ladder": {
            key: {
                **{name: int(value) for name, value in rung.items()},
                "span_precision": (
                    rung["flagged_spans_hitting_a_person_org_substitution"]
                    / rung["flagged_spans"]
                )
                if rung["flagged_spans"]
                else None,
                "substitution_recall": (
                    rung["person_org_substitutions_covered"]
                    / totals["person_org_substitutions"]
                )
                if totals["person_org_substitutions"]
                else None,
                "flagged_window_share": rung["flagged_windows"] / totals["windows"]
                if totals["windows"]
                else None,
                "window_recall": (
                    rung["person_org_substitutions_in_a_flagged_window"]
                    / totals["person_org_substitutions"]
                )
                if totals["person_org_substitutions"]
                else None,
                "window_precision": (
                    rung["flagged_windows_carrying_a_person_org_substitution"]
                    / rung["flagged_windows"]
                )
                if rung["flagged_windows"]
                else None,
            }
            for key, rung in ladder.items()
        },
        "flag_codes": dict(sorted(flag_code_counts.items())),
        "contact_budget": {
            "flagged_windows": stats["inventory"]["flagged_windows"],
            "windows": totals["windows"],
            "contacts_per_window": (
                stats["inventory"]["flagged_windows"] / totals["windows"]
            )
            if totals["windows"]
            else None,
            "kc_e1f_contacts": SEALED_ANCHOR["windows"],
            "share_of_kc_e1f": (
                stats["inventory"]["flagged_windows"] / SEALED_ANCHOR["windows"]
            ),
        },
        "per_call": per_call,
    }

    if args.calls:
        print(json.dumps({key: payload[key] for key in ("totals", "judges")}, indent=2))
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.out_dir / "judge-receipt.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    print(f"identity anchor: {payload['identity_anchor_verdict']}")
    for name, block in payload["judges"].items():
        print(
            f"{name}: spans {block['flagged_spans']}, windows {block['flagged_windows']} "
            f"({(block['flagged_window_share'] or 0) * 100:.2f} %), "
            f"span precision {block['span_precision']}, "
            f"recall {block['substitution_recall']}"
        )
    print(f"contact budget: {json.dumps(payload['contact_budget'])}")
    return 0 if payload["identity_anchor_verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
