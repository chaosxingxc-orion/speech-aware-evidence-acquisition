#!/usr/bin/env python3
"""solver_reasoning_diag_read.py -- the offline, STATISTICS-ONLY read of the registered Solver reasoning diagnostic (owner ruling 330 A).

Reads the retained reasoning bytes of ``<data root>/diagnostics/SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1/reasoning/`` (and the answers beside them) and prints ONLY
numbers and booleans per row and per selection group: never a sentence, a quote, a hash prefix of text or an utterance. The question: is the non-terminating
Solver reasoning an ENUMERATION (it walks the supplied evidence and the candidate intents one by one, each mentioned a few times, in supply order) or a
REPETITION LOOP (a small block restated over and over)?

Per row: reasoning characters and approximate tokens (a regex word-and-punctuation count; NO tokenizer is contacted), the zlib compression ratio, the share of repeated
sentences and repeated lines, the longest repeated block of consecutive sentences with its repeat count, the position (fraction of the text) of the first repeat, the
enumeration signal (how many of the supplied intent labels and evidence ids the reasoning mentions, how often, and whether first mentions follow the supply order), and
whether the final answer's intent differs from the label last restated in the reasoning. Group summaries cover the four selection groups. The registered pattern word is
a fixed rule over those numbers (constants below); it is a reading aid, never a verdict.

Model-free. No server, no tokenizer, no network.

    python -B scripts/analysis/solver_reasoning_diag_read.py --data-root $SPEECHRL_DATA_DIR [--out READ.json]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import zlib
from collections import Counter
from pathlib import Path
from typing import Mapping, Sequence

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

RUN_ID = "SAEA-SLURP-SOLVER-REASONING-DIAGNOSTIC-V1"
SCHEMA = "saea-solver-reasoning-diag-read-v1"
PACKAGE = "docs/readiness/2026-10-18-slurp-solver-reasoning-diagnostic-v1"
GROUP_ORDER = ("forced-both", "forced-3072-only", "forced-6144-only", "natural-both")
INTENT_PREFIX = "intent-boundaries::intent-boundary:"

#: A sentence shorter than this (normalised characters) is never counted as a repeat: "Wait." and "So," restate nothing.
MIN_UNIT_CHARS = 12
#: Registered pattern rule (reading aid). LOOP: a block (reduced to its primitive period) repeats at least LOOP_REPEATS times and its repeats total at
#: least LOOP_REPEATED_CHARS characters, or at least
#: LOOP_TAIL_SHARE of the last quarter of the sentences are repeats. ENUMERATION: not a loop, at least ENUM_COVERAGE of the supplied intent labels are
#: mentioned and the first mentions follow the supply order for at least ENUM_ORDER of adjacent pairs.
LOOP_REPEATED_CHARS, LOOP_REPEATS, LOOP_TAIL_SHARE = 600, 3, 0.5
ENUM_COVERAGE, ENUM_ORDER = 0.5, 0.6

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")
_TOKEN = re.compile(r"\w+|[^\w\s]")


# --------------------------------------------------------------------------------------------------------------------- text units


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def sentence_units(text: str) -> list[tuple[str, int]]:
    """``[(normalised sentence, start offset)]`` for the non-empty sentences of ``text``."""

    units: list[tuple[str, int]] = []
    position = 0
    for piece in _SENTENCE_SPLIT.split(text):
        if not piece or not piece.strip():
            continue
        start = text.find(piece, position)
        position = start + len(piece) if start >= 0 else position
        units.append((_normalise(piece), max(start, 0)))
    return units


def line_units(text: str) -> list[str]:
    return [_normalise(line) for line in text.split("\n") if line.strip()]


def repeat_flags(units: Sequence[str]) -> list[bool]:
    """``True`` for a unit (long enough to mean something) that equals an EARLIER unit."""

    seen: set[str] = set()
    flags = []
    for unit in units:
        flags.append(len(unit) >= MIN_UNIT_CHARS and unit in seen)
        if len(unit) >= MIN_UNIT_CHARS:
            seen.add(unit)
    return flags


def longest_repeated_block(units: Sequence[str]) -> dict[str, object]:
    """The longest run of CONSECUTIVE sentences that occurs at least twice (by total characters), with its non-overlapping occurrence count.

    O(n^2) longest-common-substring over the sentence list; blocks made only of short units are ignored. Returns zeros when nothing repeats."""

    n = len(units)
    best_len = 0
    best_chars = 0
    best_end = 0
    previous = [0] * (n + 1)
    for i in range(1, n + 1):
        current = [0] * (n + 1)
        for j in range(i + 1, n + 1):
            if units[i - 1] == units[j - 1] and len(units[i - 1]) >= MIN_UNIT_CHARS:
                current[j] = previous[j - 1] + 1
                length = min(current[j], j - i)            # an overlapping match cannot be longer than the gap
                chars = sum(len(u) for u in units[i - length:i])
                if chars > best_chars:
                    best_len, best_chars, best_end = length, chars, i
        previous = current
    if best_len == 0:
        return {"block_sentences": 0, "block_chars": 0, "repeat_count": 0, "repeated_chars_total": 0}
    block = list(units[best_end - best_len:best_end])
    for period in range(1, best_len + 1):                  # reduce to the primitive period: S S S S -> S, counted four times
        if best_len % period == 0 and block == block[:period] * (best_len // period):
            block = block[:period]
            break
    size = len(block)
    count, index = 0, 0
    while index + size <= n:
        if list(units[index:index + size]) == block:
            count += 1
            index += size
        else:
            index += 1
    chars = sum(len(u) for u in block)
    return {"block_sentences": size, "block_chars": chars, "repeat_count": count, "repeated_chars_total": chars * count}


# --------------------------------------------------------------------------------------------------------------------- enumeration signal


def label_pattern(label: str) -> re.Pattern[str]:
    """A label as the reasoning may write it: ``weather_query`` or ``weather query`` (case-insensitive, bounded by non-identifier characters)."""

    words = [re.escape(part) for part in label.split("_") if part]
    return re.compile(r"(?<![A-Za-z0-9_])" + r"[_ ]".join(words) + r"(?![A-Za-z0-9_])", re.IGNORECASE)


def split_supplied_ids(evidence_ids: Sequence[str]) -> tuple[list[str], list[str]]:
    """``(intent labels in supply order, other evidence ids)``: the intent-boundary cards carry the candidate intents."""

    labels, others = [], []
    for evidence_id in evidence_ids:
        if evidence_id.startswith(INTENT_PREFIX):
            labels.append(evidence_id[len(INTENT_PREFIX):])
        else:
            others.append(evidence_id)
    return labels, others


def enumeration_signal(text: str, labels: Sequence[str], other_ids: Sequence[str]) -> dict[str, object]:
    positions: dict[str, list[int]] = {}
    for label in labels:
        found = [m.start() for m in label_pattern(label).finditer(text)]
        if found:
            positions[label] = found
    first = sorted((found[0], index) for index, label in enumerate(labels) if (found := positions.get(label)))
    ordered_pairs = sum(1 for (_, a), (_, b) in zip(first, first[1:]) if b > a)
    other_mentioned = 0
    for evidence_id in other_ids:
        tail = evidence_id.rsplit(":", 1)[-1]
        if tail and label_pattern(tail).search(text):
            other_mentioned += 1
    mentions = [len(found) for found in positions.values()]
    return {
        "labels_supplied": len(labels), "labels_mentioned": len(positions),
        "label_coverage": (len(positions) / len(labels)) if labels else None,
        "label_mentions_total": sum(mentions), "label_mentions_max_single": max(mentions) if mentions else 0,
        "label_mentions_mean_per_mentioned": (sum(mentions) / len(mentions)) if mentions else 0.0,
        "first_mention_order_share": (ordered_pairs / (len(first) - 1)) if len(first) > 1 else None,
        "other_evidence_supplied": len(other_ids), "other_evidence_mentioned": other_mentioned,
    }


def answer_intent(answer_text: str | None) -> str | None:
    """The scenario_action intent of a final answer (``{"scenario": s, "action": a, ...}``), else ``None``."""

    if not answer_text:
        return None
    try:
        document = json.loads(answer_text)
    except ValueError:
        return None
    if isinstance(document, Mapping) and isinstance(document.get("scenario"), str) and isinstance(document.get("action"), str):
        return f"{document['scenario']}_{document['action']}"
    return None


def restatement_signal(text: str, labels: Sequence[str], answer: str | None) -> dict[str, object]:
    """Which label the reasoning mentioned LAST, which it last RESTATED (inside a sentence that repeats an earlier sentence), and whether the final answer
    differs from either. ``None`` means the fact does not exist (no label mentioned / no restated label / no parseable answer)."""

    units = sentence_units(text)
    flags = repeat_flags([u for u, _ in units])

    def labels_in(chunk: str) -> list[str]:
        return [label for label in labels if label_pattern(label).search(chunk)]

    last_mention = None
    last_at = -1
    for label in labels:
        for match in label_pattern(label).finditer(text):
            if match.start() > last_at:
                last_at, last_mention = match.start(), label
    last_restated = None
    for (unit, start), repeated in zip(units, flags):
        if repeated:
            hit = labels_in(unit)
            if hit:
                last_restated = hit[-1]
    return {
        "answer_intent_parsed": answer is not None,
        "answer_intent_mentioned": bool(answer and label_pattern(answer).search(text)),
        "last_mentioned_label_exists": last_mention is not None,
        "answer_equals_last_mentioned": (answer == last_mention) if (answer and last_mention) else None,
        "last_restated_label_exists": last_restated is not None,
        "answer_changed_after_last_restatement": (answer != last_restated) if (answer and last_restated) else None,
    }


# --------------------------------------------------------------------------------------------------------------------- per-row statistics


def analyze_text(text: str, *, evidence_ids: Sequence[str] = (), answer_text: str | None = None) -> dict[str, object]:
    """Statistics of one reasoning text. Never returns text."""

    data = text.encode("utf-8")
    units = sentence_units(text)
    unit_text = [u for u, _ in units]
    flags = repeat_flags(unit_text)
    lines = line_units(text)
    line_flags = repeat_flags(lines)
    first_repeat = next((index for index, flag in enumerate(flags) if flag), None)
    quarter = flags[len(flags) - max(1, len(flags) // 4):] if flags else []
    block = longest_repeated_block(unit_text)
    labels, others = split_supplied_ids(evidence_ids)
    answer = answer_intent(answer_text)
    row: dict[str, object] = {
        "reasoning_chars": len(text), "reasoning_bytes": len(data), "tokens_approx": len(_TOKEN.findall(text)),
        "tokens_approx_basis": "regex-word-and-punctuation (no tokenizer)",
        "zlib_ratio": (len(zlib.compress(data, 9)) / len(data)) if data else None,
        "sentences": len(units), "repeated_sentence_share": (sum(flags) / len(flags)) if flags else 0.0,
        "lines": len(lines), "repeated_line_share": (sum(line_flags) / len(line_flags)) if line_flags else 0.0,
        "tail_repeated_sentence_share": (sum(quarter) / len(quarter)) if quarter else 0.0,
        "first_repeat_sentence_index": first_repeat,
        "first_repeat_char_fraction": (units[first_repeat][1] / len(text)) if first_repeat is not None and text else None,
        **block, **enumeration_signal(text, labels, others), **restatement_signal(text, labels, answer),
    }
    row["pattern"] = pattern_word(row)
    return row


def pattern_word(row: Mapping[str, object]) -> str:
    """The registered reading aid: ``repetition-loop``, ``enumeration`` or ``other`` (constants at the top of the module)."""

    if (int(row["repeated_chars_total"]) >= LOOP_REPEATED_CHARS and int(row["repeat_count"]) >= LOOP_REPEATS) or float(row["tail_repeated_sentence_share"]) >= LOOP_TAIL_SHARE:
        return "repetition-loop"
    coverage, order = row.get("label_coverage"), row.get("first_mention_order_share")
    if coverage is not None and coverage >= ENUM_COVERAGE and order is not None and order >= ENUM_ORDER:
        return "enumeration"
    return "other"


# --------------------------------------------------------------------------------------------------------------------- group summaries


def _summary(values: Sequence[float]) -> dict[str, object]:
    clean = [v for v in values if v is not None]
    if not clean:
        return {"n": 0}
    return {"n": len(clean), "mean": statistics.fmean(clean), "median": statistics.median(clean), "min": min(clean), "max": max(clean)}


SUMMARY_FIELDS = ("reasoning_chars", "tokens_approx", "zlib_ratio", "repeated_sentence_share", "repeated_line_share", "tail_repeated_sentence_share",
                  "block_chars", "repeat_count", "repeated_chars_total", "first_repeat_char_fraction", "label_coverage", "label_mentions_max_single", "first_mention_order_share")


def group_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {"rows": len(rows), "patterns": dict(Counter(str(r["pattern"]) for r in rows))}
    for field in SUMMARY_FIELDS:
        out[field] = _summary([r.get(field) for r in rows])           # type: ignore[arg-type]
    out["answer_changed_after_last_restatement"] = dict(Counter(str(r.get("answer_changed_after_last_restatement")) for r in rows))
    out["answer_equals_last_mentioned"] = dict(Counter(str(r.get("answer_equals_last_mentioned")) for r in rows))
    out["rows_with_a_repeated_block"] = sum(1 for r in rows if int(r.get("repeat_count") or 0) >= 2)
    return out


def read_diagnostic(roster: Mapping, reasoning_dir: Path, answers_dir: Path | None = None) -> dict[str, object]:
    """Analyse every roster row whose reasoning file exists. Rows without a file are counted, not guessed."""

    rows, missing = [], []
    for entry in roster["rows"]:
        stem = re.sub(r"[^A-Za-z0-9._-]", "_", entry["sample_id"]).strip(".") or "sample"
        path = Path(reasoning_dir) / f"{stem}.txt"
        if not path.is_file():
            missing.append(entry["sample_id"])
            continue
        answer_path = Path(answers_dir) / f"{stem}.txt" if answers_dir is not None else None
        answer = answer_path.read_text(encoding="utf-8") if answer_path is not None and answer_path.is_file() else None
        stats = analyze_text(path.read_text(encoding="utf-8"), evidence_ids=entry.get("supplied_evidence_ids", []), answer_text=answer)
        stats.update(sample_id=entry["sample_id"], group=entry["group"], supplied_bin=entry["stratum"]["supplied_bin"],
                     gold_empty=entry["stratum"]["gold_empty"])
        rows.append(stats)
    by_group = {group: group_summary([r for r in rows if r["group"] == group]) for group in GROUP_ORDER}
    return {"schema": SCHEMA, "run_id": RUN_ID, "rows_read": len(rows), "rows_missing": len(missing), "rows": rows,
            "by_group": by_group, "all_rows": group_summary(rows),
            "pattern_rule": {"loop_repeated_chars": LOOP_REPEATED_CHARS, "loop_repeats": LOOP_REPEATS, "loop_tail_share": LOOP_TAIL_SHARE,
                             "enum_coverage": ENUM_COVERAGE, "enum_order": ENUM_ORDER, "min_unit_chars": MIN_UNIT_CHARS},
            "model_contacts": 0, "text_printed": False}


def _default_data_root() -> str:
    return os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "/home/chao/saea-data/speechrl-data"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--data-root", default=_default_data_root())
    parser.add_argument("--roster", type=Path, default=REPO / PACKAGE / "roster-v1.json")
    parser.add_argument("--out", type=Path, default=None, help="also write the statistics here (under the data root's analysis directory)")
    args = parser.parse_args(argv)
    root = Path(args.data_root) / "diagnostics" / RUN_ID
    report = read_diagnostic(json.loads(Path(args.roster).read_text(encoding="utf-8")), root / "reasoning", root / "answers")
    blob = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.out is not None:
        Path(args.out).write_bytes(blob.encode("utf-8"))
    sys.stdout.write(blob)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
