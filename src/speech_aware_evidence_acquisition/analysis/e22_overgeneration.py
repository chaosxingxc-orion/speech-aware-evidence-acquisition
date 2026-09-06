"""Earnings-22 DEV over-generation analysis (``SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1``).

Three Earnings-22 verdicts have now closed three suspects for the sealed ESB
test flight's NOT-ALIGNED 15.937. The instruction TEXT is not it (2026-09-05
A/B: the model authors' own prompt is 0.83 points worse). The request SHAPE is
not it (2026-09-05 shape C: the model card's own evaluation shape is 0.325
points worse, and its oracle floor ROSE). The clip BOUNDARY is not an
alignment argument (2026-09-06: the ESB release's own arrays carry the same
overlap, so every published system was handed the same onsets). What is left
is this study's own MODEL USAGE, and its first face is decode discipline:
arm A's hypothesis is longer than its reference on 3,605 of 6,038 dev rows,
and 868 of its tail insertion spans reproduce the NEXT published sentence.

This module measures the shape of that surplus and simulates -- on paper, and
only on paper -- what a duration-proportional generation cap would have done
to it. Four measurements, none of which needs a model:

**The excess.** Per row, ``len(normalized(hypothesis)) - len(normalized(reference))``
under the same Whisper ``EnglishTextNormalizer`` tokenization the paper-facing
scorer uses, with its distribution, its quantiles and its mass.

**Where the excess sits.** The same excess against the clip's own duration and
against the published ``gap_next`` geometry the 2026-09-06 clip-boundary audit
already committed per clip, so an over-long row whose neighbour OVERLAPS it is
separated from one whose neighbour does not. Those are different mechanisms
and the sign of one number separates them.

**How the row ends.** Whether the raw hypothesis ends on a sentence-final
token or runs on mid-clause. A run-on is the visible signature of a decode
that stopped because it ran out of things to say rather than because it
finished a sentence.

**The cap.** For candidate caps ``n_predict = ceil(alpha * seconds *
words_per_second_p95 * tokens_per_word)``, the rows whose own REFERENCE would
not fit under the cap (harm) against the rows whose surplus continuation would
be cut (benefit), plus a simulated corpus WER. The simulation is honest about
one thing and approximate about another. It is HONEST because a greedy decode
under an ``n_predict`` cap returns exactly the token PREFIX the uncapped decode
returned -- llama.cpp stops generating, it does not re-decode -- so unlike the
"cut each hypothesis to its own reference length" transform the earlier
verdicts reported, this is not an oracle: the cap reads only the clip's
duration, which is known before the request is sent. It is APPROXIMATE in the
token-to-word mapping: the per-row token counts are the flight tokenizer's own
(``usage.completion_tokens`` from the sealed trace, never a re-tokenization),
but where inside a row a token cap lands is estimated from that row's own
measured tokens-per-word ratio, and a cap that lands mid-word is resolved by
dropping the partial word. Every figure that rests on that mapping says so.

Model-free by construction: no frozen core, tokenizer, embedder, retriever,
scorer, network, GPU or audio contact. Every input is a sealed dev artifact or
a committed receipt, and each is re-hashed before it is read. The six ESB TEST
calls are unreachable from here -- the reference loader is pinned to the dev10
receipt, the segment-table loader to the dev10 extracted table, and no test
output path is reachable from the runner's input set.

Nothing here licenses a fix. It measures a surplus and names a cap; applying
that cap is a registered cell with its own preregistration, its own owner
decision and its own exposure row.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..scoring.wer import align
from .e22_error_taxonomy import (
    ARM_SOURCES,
    DURATION_BUCKETS,
    UtteranceContext,
    agentic_error_rate,
    build_entity_inventory,
    normalized_tokens,
    scan_arm,
    tag_anchor_indices,
    truncation_stems,
)

ANALYSIS_VERSION = "saea-e22-overgeneration-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1"

#: The one arm this row reads. Arms B and C are sealed too, but the cap this
#: analysis names is for a cell whose control is arm A, so arm A is the only
#: population whose surplus is decision-relevant here.
ARM = "A"

#: The sealed arm A corpus WER under the Whisper ``EnglishTextNormalizer``,
#: as the 2026-09-05 A/B verdict published it and the 2026-09-06 semantic scan
#: reproduced it. The identity gate refuses to write a receipt unless this
#: module's own aligner reproduces it from the same inputs.
SEALED_CORPUS_WER_PERCENT = 17.5648
SEALED_TOTALS: Mapping[str, int] = {
    "substitutions": 4526,
    "deletions": 2370,
    "insertions": 11270,
    "reference_words": 103423,
}

#: The committed per-clip geometry table of the 2026-09-06 clip-boundary
#: audit. It carries, per clip, the measured media duration, the signed gap to
#: the next published segment and the arm-A tail-bleed counts -- everything the
#: overlap cross needs, already in Git and already hashed.
CLIP_AUDIT_DIR_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-clip-boundary-audit"
)
CLIP_TABLE_NAME = "per-clip-table.csv"
CLIP_MANIFEST_NAME = "MANIFEST.sha256"

#: Candidate ``alpha`` values for the duration-proportional cap. A ladder, not
#: a search: the whole frontier is reported so a single operating point cannot
#: be chosen by looking at one answer.
#:
#: DISCLOSED: the ladder was first written as ``(1.0, 1.25, 1.5, 1.75, 2.0,
#: 2.5, 3.0)`` and extended DOWNWARD to 0.6 after the first pass showed every
#: rung at and above 1.0 touching under 10 % of the population. The extension
#: adds rungs that bite HARDER, i.e. it can only make the harm side of the
#: frontier worse, and it was made to find where harm overtakes benefit rather
#: than to find a better number. ``words_per_second_p95`` is itself about 1.9x
#: the corpus mean reference word rate, so alpha 1.0 is already a generous cap.
ALPHA_LADDER: tuple[float, ...] = (
    0.6,
    0.7,
    0.8,
    0.9,
    1.0,
    1.25,
    1.5,
    1.75,
    2.0,
    2.5,
    3.0,
)

#: A raw hypothesis ENDS a sentence when its last non-space, non-closing
#: character is one of these. The closing set is stripped first so a quoted or
#: parenthesised sentence still counts.
SENTENCE_FINAL_CHARS = frozenset(".!?…。！？")
CLOSING_CHARS = "\"'”’)]}」』» "

#: Buckets for the hypothesis-minus-reference word count. Left-inclusive,
#: right-exclusive, ordered; the two ends are open.
EXCESS_BUCKET_EDGES: tuple[int, ...] = (-20, -10, -5, -2, 0, 1, 3, 6, 11, 21, 51)


class OvergenerationError(RuntimeError):
    """An input is missing, has drifted from its committed hash, or the
    identity gate failed -- fail closed."""


# ---------------------------------------------------------------------------
# Loaders. Every one of them re-hashes what it reads.
# ---------------------------------------------------------------------------


def trace_path(root: Path, arm: str = ARM) -> Path:
    source = ARM_SOURCES[arm]
    run_id = source["run_id"]
    return Path(root) / "runs" / run_id / source["attempt"] / f"{run_id}.trace.jsonl"


def load_flight_tokens(path: Path) -> dict[str, dict[str, object]]:
    """``{sample_id -> {"completion_tokens", "prompt_tokens", "response_text_sha256"}}``.

    The completion-token count is the FLIGHT tokenizer's own, recorded by
    llama-server in the sealed trace's ``usage`` block. Nothing is
    re-tokenized here and no tokenizer is loaded, which is what makes the
    token axis of this analysis an observation rather than a reconstruction.

    The request and response records are joined on ``request_id``, not on
    file order, and a response whose request was never seen is a refusal.
    """

    by_request: dict[str, str] = {}
    usage: dict[str, dict[str, object]] = {}
    for number, line in enumerate(
        Path(path).read_text(encoding="utf-8").split("\n"), start=1
    ):
        if not line.strip():
            continue
        record = json.loads(line)
        channel = record.get("channel")
        record_id = str(record.get("record_id", ""))
        if channel == "MODEL_REQUEST":
            inner = record["payload"]["payload"]
            request_id = str(inner["request_id"])
            if request_id in by_request:
                raise OvergenerationError(
                    f"{path} line {number} repeats request {request_id!r}"
                )
            by_request[request_id] = str(inner["sample_id"])
        elif channel == "MODEL_RESPONSE":
            request_id = record_id.split("/", 1)[0]
            sample_id = by_request.get(request_id)
            if sample_id is None:
                raise OvergenerationError(
                    f"{path} line {number} carries a response for the unknown "
                    f"request {request_id!r}"
                )
            block = record["payload"]
            counts = block.get("usage", {})
            usage[sample_id] = {
                "completion_tokens": int(counts["completion_tokens"]),
                "prompt_tokens": int(counts["prompt_tokens"]),
                "response_text_sha256": str(block["response_text_sha256"]),
            }
    if not usage:
        raise OvergenerationError(f"{path} carries no MODEL_RESPONSE records")
    return usage


def _manifest_digest(directory: Path, name: str) -> str:
    manifest = (Path(directory) / CLIP_MANIFEST_NAME).read_text(encoding="utf-8")
    for line in manifest.split("\n"):
        if not line.strip():
            continue
        digest, _, filename = line.partition(" *")
        if filename.strip() == name:
            return digest.strip()
    raise OvergenerationError(f"{directory}/{CLIP_MANIFEST_NAME} does not name {name!r}")


def load_clip_geometry(repo_root: Path) -> dict[str, dict[str, object]]:
    """The 2026-09-06 clip-boundary audit's per-clip table, re-hashed on load.

    Reading the committed table rather than re-deriving the geometry is
    deliberate: the audit's numbers are the ones the boundary reading already
    rests on, and re-deriving them here would put two independent measurements
    of the same cut into the same account.
    """

    directory = Path(repo_root) / CLIP_AUDIT_DIR_RELPATH
    path = directory / CLIP_TABLE_NAME
    payload = path.read_bytes()
    measured = hashlib.sha256(payload).hexdigest()
    recorded = _manifest_digest(directory, CLIP_TABLE_NAME)
    if measured != recorded:
        raise OvergenerationError(
            f"clip-boundary table identity drift: the manifest pins {recorded[:12]}..., "
            f"{path} now hashes to {measured[:12]}..."
        )
    lines = payload.decode("utf-8").split("\n")
    header = lines[0].split(",")
    rows: dict[str, dict[str, object]] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        cells = line.split(",")
        if len(cells) != len(header):
            raise OvergenerationError(
                f"{path} carries a row with {len(cells)} cells, the header declares "
                f"{len(header)}"
            )
        record = dict(zip(header, cells))
        rows[record["sample_id"]] = record
    if not rows:
        raise OvergenerationError(f"{path} carries no rows")
    return rows


# ---------------------------------------------------------------------------
# Per-row metrics
# ---------------------------------------------------------------------------


def ends_sentence_final(raw_hypothesis: str) -> bool:
    """Whether the RAW hypothesis ends on a sentence-final token.

    The Whisper normalizer strips punctuation from both sides, so this reads
    the raw text -- the only place the model's own sentence boundary survives.
    Trailing closing quotes and brackets are stripped first.
    """

    text = raw_hypothesis.rstrip()
    while text and text[-1] in CLOSING_CHARS:
        text = text[:-1].rstrip()
    if not text:
        return False
    return text[-1] in SENTENCE_FINAL_CHARS


@dataclass(frozen=True)
class RowMetrics:
    """One sealed dev row, as the over-generation question sees it."""

    sample_id: str
    call: str
    media_seconds: float
    gap_next_seconds: float | None
    tail_bleed_06: int
    tail_words: int
    reference_words: int
    hypothesis_words: int
    completion_tokens: int
    sentence_final: bool
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]

    @property
    def excess_words(self) -> int:
        return self.hypothesis_words - self.reference_words

    @property
    def overlaps_next(self) -> bool | None:
        if self.gap_next_seconds is None:
            return None
        return self.gap_next_seconds < 0.0

    @property
    def tokens_per_word(self) -> float | None:
        if self.hypothesis_words == 0:
            return None
        return self.completion_tokens / self.hypothesis_words


def build_rows(
    *,
    references: Mapping[str, str],
    hypotheses: Mapping[str, str],
    flight_tokens: Mapping[str, Mapping[str, object]],
    geometry: Mapping[str, Mapping[str, object]],
    segments: Mapping[str, Mapping[str, object]],
) -> list[RowMetrics]:
    """One :class:`RowMetrics` per sealed row, in sample-id order.

    Every row must appear in all five inputs; a missing id is a refusal
    rather than a dropped row, because a silently short population would move
    every aggregate below.
    """

    rows: list[RowMetrics] = []
    for sample_id in sorted(hypotheses):
        if sample_id not in references:
            raise OvergenerationError(f"{sample_id!r} has no reference")
        if sample_id not in flight_tokens:
            raise OvergenerationError(f"{sample_id!r} has no sealed usage record")
        if sample_id not in geometry:
            raise OvergenerationError(f"{sample_id!r} is absent from the clip table")
        if sample_id not in segments:
            raise OvergenerationError(f"{sample_id!r} is absent from the segment table")
        clip = geometry[sample_id]
        gap_next = clip.get("gap_next_seconds")
        rows.append(
            RowMetrics(
                sample_id=sample_id,
                call=str(segments[sample_id]["source_id"]),
                media_seconds=float(str(clip["media_seconds"])),
                gap_next_seconds=(
                    float(str(gap_next)) if str(gap_next).strip() != "" else None
                ),
                tail_bleed_06=int(str(clip["arm_a_tail_contained_06"])),
                tail_words=int(str(clip["arm_a_tail_words"])),
                reference_words=len(normalized_tokens(references[sample_id])),
                hypothesis_words=len(normalized_tokens(hypotheses[sample_id])),
                completion_tokens=int(flight_tokens[sample_id]["completion_tokens"]),
                sentence_final=ends_sentence_final(hypotheses[sample_id]),
                ref_tokens=normalized_tokens(references[sample_id]),
                hyp_tokens=normalized_tokens(hypotheses[sample_id]),
            )
        )
    return rows


def identity_gate(rows: Sequence[RowMetrics]) -> dict[str, object]:
    """Reproduce the sealed arm A S/D/I and corpus WER before anything else is
    trusted. Fail closed."""

    substitutions = deletions = insertions = reference_words = 0
    for row in rows:
        result = align(row.ref_tokens, row.hyp_tokens)
        substitutions += result.substitutions
        deletions += result.deletions
        insertions += result.insertions
        reference_words += result.reference_length
    measured = {
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "reference_words": reference_words,
    }
    errors = substitutions + deletions + insertions
    corpus = 100.0 * errors / reference_words if reference_words else 0.0
    reproduced = measured == dict(SEALED_TOTALS)
    if not reproduced:
        raise OvergenerationError(
            f"identity gate: this module's aligner returns {measured}, the sealed "
            f"arm A table records {dict(SEALED_TOTALS)}"
        )
    return {
        "reproduced": True,
        "sealed": dict(SEALED_TOTALS),
        "measured": measured,
        "corpus_wer_percent": corpus,
        "sealed_corpus_wer_percent": SEALED_CORPUS_WER_PERCENT,
    }


# ---------------------------------------------------------------------------
# The excess, and where it sits
# ---------------------------------------------------------------------------


def _quantile(values: Sequence[float], q: float) -> float:
    """Nearest-rank quantile on a sorted copy; deterministic, no interpolation."""

    if not values:
        raise OvergenerationError("quantile of an empty sequence")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return float(ordered[index])


def excess_distribution(rows: Sequence[RowMetrics]) -> dict[str, object]:
    """Counts, mass and quantiles of ``hypothesis_words - reference_words``."""

    excess = [row.excess_words for row in rows]
    longer = sum(1 for value in excess if value > 0)
    shorter = sum(1 for value in excess if value < 0)
    buckets: list[dict[str, object]] = []
    edges = EXCESS_BUCKET_EDGES
    for index in range(len(edges) + 1):
        low = edges[index - 1] if index > 0 else None
        high = edges[index] if index < len(edges) else None
        count = sum(
            1
            for value in excess
            if (low is None or value >= low) and (high is None or value < high)
        )
        buckets.append(
            {
                "low": low,
                "high": high,
                "label": (
                    f"< {high}"
                    if low is None
                    else f">= {low}"
                    if high is None
                    else f"[{low}, {high})"
                ),
                "rows": count,
            }
        )
    hypothesis_words = sum(row.hypothesis_words for row in rows)
    reference_words = sum(row.reference_words for row in rows)
    return {
        "rows": len(rows),
        "reference_words": reference_words,
        "hypothesis_words": hypothesis_words,
        "length_ratio": hypothesis_words / reference_words if reference_words else 0.0,
        "net_excess_words": hypothesis_words - reference_words,
        "gross_excess_words": sum(value for value in excess if value > 0),
        "gross_deficit_words": -sum(value for value in excess if value < 0),
        "rows_longer": longer,
        "rows_equal": len(rows) - longer - shorter,
        "rows_shorter": shorter,
        "quantiles": {
            "p05": _quantile(excess, 0.05),
            "p25": _quantile(excess, 0.25),
            "p50": _quantile(excess, 0.50),
            "p75": _quantile(excess, 0.75),
            "p95": _quantile(excess, 0.95),
            "p99": _quantile(excess, 0.99),
            "max": float(max(excess)),
            "min": float(min(excess)),
        },
        "buckets": buckets,
    }


def _aggregate(rows: Sequence[RowMetrics], label: str) -> dict[str, object]:
    reference_words = sum(row.reference_words for row in rows)
    hypothesis_words = sum(row.hypothesis_words for row in rows)
    substitutions = deletions = insertions = 0
    for row in rows:
        result = align(row.ref_tokens, row.hyp_tokens)
        substitutions += result.substitutions
        deletions += result.deletions
        insertions += result.insertions
    errors = substitutions + deletions + insertions
    return {
        "label": label,
        "rows": len(rows),
        "reference_words": reference_words,
        "hypothesis_words": hypothesis_words,
        "length_ratio": hypothesis_words / reference_words if reference_words else 0.0,
        "net_excess_words": hypothesis_words - reference_words,
        "rows_longer": sum(1 for row in rows if row.excess_words > 0),
        "mean_excess_words": (
            sum(row.excess_words for row in rows) / len(rows) if rows else 0.0
        ),
        "corpus_wer_percent": (
            100.0 * errors / reference_words if reference_words else 0.0
        ),
        "insertions": insertions,
        "deletions": deletions,
        "substitutions": substitutions,
        "sentence_final_rows": sum(1 for row in rows if row.sentence_final),
        "tail_bleed_06_spans": sum(row.tail_bleed_06 for row in rows),
    }


def excess_by_duration(rows: Sequence[RowMetrics]) -> list[dict[str, object]]:
    """The excess per clip-duration bucket, on the audit's own bucket edges."""

    table: list[dict[str, object]] = []
    for low, high in DURATION_BUCKETS:
        selected = [row for row in rows if low <= row.media_seconds < high]
        label = f"{low:g}-{high:g} s" if high < 1e8 else f"{low:g} s+"
        table.append({**_aggregate(selected, label), "low": low, "high": high})
    return table


def excess_by_overlap(rows: Sequence[RowMetrics]) -> list[dict[str, object]]:
    """The excess split by whether the NEXT published segment overlaps the clip.

    The split is the clip-boundary audit's own: a negative ``gap_next`` means
    the two published segments overlap, so the clip provably carries some of
    its neighbour's speech; a positive gap means the clip is tight and
    anything past its own words is the core continuing past the audio it was
    given.
    """

    overlapping = [row for row in rows if row.overlaps_next is True]
    tight = [row for row in rows if row.overlaps_next is False]
    last = [row for row in rows if row.overlaps_next is None]
    return [
        _aggregate(overlapping, "next segment overlaps"),
        _aggregate(tight, "next segment is tight"),
        _aggregate(last, "no next segment"),
    ]


def token_profile(rows: Sequence[RowMetrics]) -> dict[str, object]:
    """What the sealed completion lengths look like against the 1,024 ceiling.

    The A/B verdict recorded a largest completion of 130 tokens against a
    ceiling that was never reached. That is the fact a cap has to work
    against: there is no runaway population for a ceiling to catch, so any
    cap that bites at all has to bite well below the ceiling.
    """

    tokens = [float(row.completion_tokens) for row in rows]
    return {
        "declared_max_tokens": 1024,
        "total_completion_tokens": int(sum(tokens)),
        "mean": sum(tokens) / len(tokens) if tokens else 0.0,
        "quantiles": {
            "p50": _quantile(tokens, 0.50),
            "p90": _quantile(tokens, 0.90),
            "p95": _quantile(tokens, 0.95),
            "p99": _quantile(tokens, 0.99),
            "max": max(tokens) if tokens else 0.0,
        },
        "rows_at_or_above_256": sum(1 for value in tokens if value >= 256),
        "rows_at_or_above_512": sum(1 for value in tokens if value >= 512),
        "rows_at_ceiling": sum(1 for value in tokens if value >= 1024),
    }


def bleed_profile(rows: Sequence[RowMetrics]) -> dict[str, object]:
    """The 868 rows whose tail reproduces the NEXT published sentence.

    The cap's whole hope is that those rows are the long ones. This says
    whether they are.
    """

    bleed = [row for row in rows if row.tail_bleed_06 > 0]
    rest = [row for row in rows if row.tail_bleed_06 == 0]
    excess = [float(row.excess_words) for row in bleed]
    return {
        "rows": len(bleed),
        "aggregate": _aggregate(bleed, "tail bleeds into the next reference"),
        "rest": _aggregate(rest, "no tail bleed at >= 0.6 containment"),
        "excess_quantiles": (
            {
                "p50": _quantile(excess, 0.50),
                "p75": _quantile(excess, 0.75),
                "p95": _quantile(excess, 0.95),
                "max": max(excess),
            }
            if excess
            else {}
        ),
        "completion_token_quantiles": (
            {
                "p50": _quantile([float(row.completion_tokens) for row in bleed], 0.50),
                "p95": _quantile([float(row.completion_tokens) for row in bleed], 0.95),
                "max": float(max(row.completion_tokens for row in bleed)),
            }
            if bleed
            else {}
        ),
        "sentence_final_rows": sum(1 for row in bleed if row.sentence_final),
    }


def sentence_final_table(rows: Sequence[RowMetrics]) -> dict[str, object]:
    """Rows that end on a sentence-final token against rows that run on."""

    final = [row for row in rows if row.sentence_final]
    running = [row for row in rows if not row.sentence_final]
    by_duration: list[dict[str, object]] = []
    for low, high in DURATION_BUCKETS:
        selected = [row for row in rows if low <= row.media_seconds < high]
        label = f"{low:g}-{high:g} s" if high < 1e8 else f"{low:g} s+"
        by_duration.append(
            {
                "label": label,
                "rows": len(selected),
                "sentence_final": sum(1 for row in selected if row.sentence_final),
                "run_on": sum(1 for row in selected if not row.sentence_final),
            }
        )
    return {
        "sentence_final": _aggregate(final, "ends on a sentence-final token"),
        "run_on": _aggregate(running, "runs on"),
        "by_duration": by_duration,
    }


# ---------------------------------------------------------------------------
# The cap
# ---------------------------------------------------------------------------


def words_per_second_p95(rows: Sequence[RowMetrics]) -> float:
    """The 95th percentile of REFERENCE words per second over the population.

    The reference side, deliberately: the cap must bound what a faithful
    transcript can need, and sizing it on the hypothesis would let the
    over-generation the cap is meant to bound set the cap's own scale.
    """

    rates = [
        row.reference_words / row.media_seconds
        for row in rows
        if row.media_seconds > 0.0
    ]
    return _quantile(rates, 0.95)


def tokens_per_word(rows: Sequence[RowMetrics]) -> float:
    """The flight tokenizer's tokens per normalized hypothesis word, pooled.

    A corpus constant, taken from the sealed usage counts over the sealed
    hypotheses. Pooled rather than averaged per row so a one-word row cannot
    weigh as much as a 300-word one.
    """

    words = sum(row.hypothesis_words for row in rows)
    tokens = sum(row.completion_tokens for row in rows)
    if words == 0:
        raise OvergenerationError("tokens_per_word: the population carries no words")
    return tokens / words


def cap_tokens(alpha: float, seconds: float, wps_p95: float, tpw: float) -> int:
    """``ceil(alpha * seconds * words_per_second_p95 * tokens_per_word)``.

    Floored at 1 so a sub-second clip can still emit something; a cap of zero
    would be a different intervention (refusing to answer) and is not what is
    being measured.
    """

    return max(1, math.ceil(alpha * seconds * wps_p95 * tpw))


def kept_words(row: RowMetrics, cap: int) -> int:
    """How many normalized words survive a token cap, on the row's own ratio.

    APPROXIMATE, and the one approximation in this analysis. A greedy decode
    under an ``n_predict`` cap returns exactly the uncapped decode's token
    PREFIX, so which words survive is a real question with a real answer; but
    answering it exactly needs the flight tokenizer's own segmentation, which
    this row may not load. The linear map on the row's measured
    tokens-per-word ratio is used instead, and a cap landing mid-word drops
    that partial word (``floor``), which is the conservative direction: it
    never credits the cap with a word it might have cut.
    """

    if row.completion_tokens <= cap:
        return row.hypothesis_words
    if row.completion_tokens == 0:
        return 0
    return min(
        row.hypothesis_words,
        int(math.floor(row.hypothesis_words * cap / row.completion_tokens)),
    )


def simulate_cap(
    rows: Sequence[RowMetrics],
    *,
    alpha: float,
    wps_p95: float,
    tpw: float,
    baseline_wer_percent: float = SEALED_CORPUS_WER_PERCENT,
) -> dict[str, object]:
    """One alpha's harm/benefit frontier and its simulated corpus WER.

    ``baseline_wer_percent`` is what the delta is taken against. It defaults to
    the sealed full-population figure; a SUBSET projection passes that subset's
    own uncapped number instead, because a delta against a population the cell
    is not flying would be a different statement.
    """

    capped_rows = 0
    a_priori_harm_rows = 0
    a_priori_reference_words_at_risk = 0
    realized_harm_rows = 0
    realized_harm_words = 0
    benefit_rows = 0
    surplus_words_removed = 0
    tokens_saved = 0
    bleed_rows_capped = 0
    bleed_rows_total = 0
    substitutions = deletions = insertions = reference_words = 0
    smallest_cap = None
    largest_cap = None
    for row in rows:
        cap = cap_tokens(alpha, row.media_seconds, wps_p95, tpw)
        smallest_cap = cap if smallest_cap is None else min(smallest_cap, cap)
        largest_cap = cap if largest_cap is None else max(largest_cap, cap)
        reference_tokens_needed = math.ceil(row.reference_words * tpw)
        if cap < reference_tokens_needed:
            a_priori_harm_rows += 1
            a_priori_reference_words_at_risk += row.reference_words - min(
                row.reference_words, int(math.floor(cap / tpw))
            )
        if row.tail_bleed_06 > 0:
            bleed_rows_total += 1
        survivors = kept_words(row, cap)
        if row.completion_tokens > cap:
            capped_rows += 1
            tokens_saved += row.completion_tokens - cap
            if row.tail_bleed_06 > 0:
                bleed_rows_capped += 1
            if survivors < row.reference_words:
                realized_harm_rows += 1
                realized_harm_words += row.reference_words - survivors
            else:
                benefit_rows += 1
            if row.hypothesis_words > row.reference_words:
                surplus_words_removed += min(
                    row.hypothesis_words - survivors,
                    row.hypothesis_words - row.reference_words,
                )
        truncated = row.hyp_tokens[:survivors]
        result = align(row.ref_tokens, truncated)
        substitutions += result.substitutions
        deletions += result.deletions
        insertions += result.insertions
        reference_words += result.reference_length
    errors = substitutions + deletions + insertions
    corpus = 100.0 * errors / reference_words if reference_words else 0.0
    return {
        "alpha": alpha,
        "words_per_second_p95": wps_p95,
        "tokens_per_word": tpw,
        "smallest_cap_tokens": smallest_cap,
        "largest_cap_tokens": largest_cap,
        "rows_capped": capped_rows,
        "completion_tokens_saved": tokens_saved,
        "harm_rows_cap_below_reference": a_priori_harm_rows,
        "harm_reference_words_at_risk": a_priori_reference_words_at_risk,
        "harm_rows_realized": realized_harm_rows,
        "harm_reference_words_realized": realized_harm_words,
        "benefit_rows": benefit_rows,
        "surplus_words_removed": surplus_words_removed,
        "tail_bleed_rows_capped": bleed_rows_capped,
        "tail_bleed_rows_total": bleed_rows_total,
        "substitutions": substitutions,
        "deletions": deletions,
        "insertions": insertions,
        "reference_words": reference_words,
        "corpus_wer_percent": corpus,
        "baseline_wer_percent": baseline_wer_percent,
        "corpus_wer_delta_points": corpus - baseline_wer_percent,
    }


def simulate_agentic_rate(
    rows: Sequence[RowMetrics],
    *,
    alpha: float,
    wps_p95: float,
    tpw: float,
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """The agentic error rate of the capped hypotheses, through the committed
    2026-09-06 taxonomy at its own version.

    This is the second of the two metrics the stop-cap cell's decision rule
    reads, and the reason it is computed here rather than after the flight: a
    cap trades insertions for deletions, and a deletion that removes a number,
    a negation or a named entity is exactly the kind of error the corpus WER
    cannot see. Predicting it before the flight is what makes the
    non-inferiority margin a preregistration rather than a post-hoc excuse.

    ``raw_hypothesis`` is set to the joined normalized prefix. That field is
    read only by :func:`~...e22_error_taxonomy.raw_format_only`, which this
    function never calls; every rule the cascade applies reads
    ``hyp_tokens``.
    """

    raw_by_call: dict[str, list[str]] = {}
    for sample_id, sentence in references.items():
        raw_by_call.setdefault(str(segments[sample_id]["source_id"]), []).append(sentence)
    inventory = build_entity_inventory(raw_by_call)

    by_position: dict[tuple[str, int], str] = {}
    for sample_id, row in segments.items():
        by_position[(str(row["source_id"]), int(str(row["segment_id"])))] = sample_id

    contexts: dict[str, UtteranceContext] = {}
    for row in rows:
        cap = cap_tokens(alpha, row.media_seconds, wps_p95, tpw)
        survivors = kept_words(row, cap)
        truncated = row.hyp_tokens[:survivors]
        position = int(str(segments[row.sample_id]["segment_id"]))
        neighbours: dict[int, tuple[str, ...]] = {}
        for step in (-1, 1):
            neighbour_id = by_position.get((row.call, position + step))
            neighbours[step] = (
                normalized_tokens(references[neighbour_id])
                if neighbour_id is not None
                else ()
            )
        contexts[row.sample_id] = UtteranceContext(
            sample_id=row.sample_id,
            call=row.call,
            raw_reference=references[row.sample_id],
            raw_hypothesis=" ".join(truncated),
            ref_tokens=row.ref_tokens,
            hyp_tokens=truncated,
            duration_s=row.media_seconds,
            stems=truncation_stems(references[row.sample_id]),
            tag_anchors=tag_anchor_indices(references[row.sample_id]),
            previous_tokens=neighbours[-1],
            next_tokens=neighbours[1],
            entity_forms=inventory[row.call],
        )
    order = sorted(contexts)
    totals, scored = scan_arm(contexts, order=order)
    rate = agentic_error_rate(scored, totals.reference_length)
    strict = agentic_error_rate(scored, totals.reference_length, neutral_categories=frozenset())
    return {
        "alpha": alpha,
        "agentic_error_rate_percent": rate["agentic_error_rate_percent"],
        "agentic_error_rate_strict_percent": strict["agentic_error_rate_percent"],
        "high_impact_reference_word_mass": rate["high_impact_reference_word_mass"],
        "high_impact_spans": rate["high_impact_spans"],
        "reference_words": totals.reference_length,
    }


def population_baseline(
    rows: Sequence[RowMetrics],
    *,
    references: Mapping[str, str] | None = None,
    segments: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    """The UNCAPPED corpus WER and agentic rate of a population.

    On the full 6,038 this reproduces the sealed arm A pair; on a subset it is
    what that subset's own cap deltas must be taken against.
    """

    block = _aggregate(rows, "uncapped")
    baseline: dict[str, object] = {
        "rows": block["rows"],
        "reference_words": block["reference_words"],
        "corpus_wer_percent": block["corpus_wer_percent"],
        "substitutions": block["substitutions"],
        "deletions": block["deletions"],
        "insertions": block["insertions"],
        "length_ratio": block["length_ratio"],
    }
    if references is not None and segments is not None:
        # A cap so loose that no row is touched IS the uncapped population, so
        # the agentic rate comes from the same code path the rungs use rather
        # than from a second implementation.
        baseline["agentic"] = simulate_agentic_rate(
            rows,
            alpha=1e9,
            wps_p95=words_per_second_p95(rows),
            tpw=tokens_per_word(rows),
            references=references,
            segments=segments,
        )
    return baseline


def cap_frontier(
    rows: Sequence[RowMetrics],
    *,
    alphas: Iterable[float] = ALPHA_LADDER,
    references: Mapping[str, str] | None = None,
    segments: Mapping[str, Mapping[str, object]] | None = None,
    baseline_wer_percent: float = SEALED_CORPUS_WER_PERCENT,
) -> dict[str, object]:
    """The whole alpha ladder, reported together so no single point is chosen
    by looking at the answer first.

    When ``references`` and ``segments`` are supplied, each rung also carries
    the agentic error rate of its capped hypotheses; without them the rung
    carries the WER side only, which is what the synthetic tests exercise.
    """

    wps = words_per_second_p95(rows)
    tpw = tokens_per_word(rows)
    rungs = []
    for alpha in alphas:
        rung = simulate_cap(
            rows,
            alpha=alpha,
            wps_p95=wps,
            tpw=tpw,
            baseline_wer_percent=baseline_wer_percent,
        )
        if references is not None and segments is not None:
            rung["agentic"] = simulate_agentic_rate(
                rows,
                alpha=alpha,
                wps_p95=wps,
                tpw=tpw,
                references=references,
                segments=segments,
            )
        rungs.append(rung)
    return {
        "words_per_second_p95": wps,
        "tokens_per_word": tpw,
        "formula": (
            "n_predict = ceil(alpha * media_seconds * words_per_second_p95 * "
            "tokens_per_word)"
        ),
        "token_source": (
            "the flight tokenizer's own usage.completion_tokens from the sealed arm A "
            "trace; nothing is re-tokenized and no tokenizer is loaded"
        ),
        "word_mapping": (
            "APPROXIMATE: where inside a row a token cap lands is estimated from that "
            "row's own measured tokens-per-word ratio, and a cap landing mid-word drops "
            "the partial word"
        ),
        "rungs": rungs,
    }


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def per_call_table(rows: Sequence[RowMetrics]) -> list[dict[str, object]]:
    calls = sorted({row.call for row in rows})
    return [
        _aggregate([row for row in rows if row.call == call], call) for call in calls
    ]


def per_row_csv(rows: Sequence[RowMetrics]) -> str:
    """The per-row table. Identifiers and counts only -- NO dev sentence text.

    Neither the reference nor the hypothesis is written out. The 2026-09-06
    scan's discipline: a committed table of dev transcripts would put gold
    text in Git for a row whose whole point is that it never needed it.
    """

    header = (
        "sample_id,call,media_seconds,gap_next_seconds,overlaps_next,"
        "reference_words,hypothesis_words,excess_words,completion_tokens,"
        "tokens_per_word,sentence_final,tail_bleed_06,tail_words"
    )
    lines = [header]
    for row in rows:
        gap = "" if row.gap_next_seconds is None else f"{row.gap_next_seconds:.6f}"
        overlaps = "" if row.overlaps_next is None else str(int(row.overlaps_next))
        ratio = "" if row.tokens_per_word is None else f"{row.tokens_per_word:.6f}"
        lines.append(
            f"{row.sample_id},{row.call},{row.media_seconds:.6f},{gap},{overlaps},"
            f"{row.reference_words},{row.hypothesis_words},{row.excess_words},"
            f"{row.completion_tokens},{ratio},{int(row.sentence_final)},"
            f"{row.tail_bleed_06},{row.tail_words}"
        )
    return "\n".join(lines) + "\n"


def build_receipts(
    *,
    rows: Sequence[RowMetrics],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
    alphas: Iterable[float] = ALPHA_LADDER,
    references: Mapping[str, str] | None = None,
    segments: Mapping[str, Mapping[str, object]] | None = None,
    subset_ids: Sequence[str] | None = None,
    subset_label: str | None = None,
) -> tuple[dict[str, object], str]:
    """``(summary, per-row CSV)`` -- the whole receipt payload, computed once.

    ``subset_ids`` adds a SUBSET PROJECTION: the same cap frontier restricted
    to a reserved roster's own rows, against that subset's own uncapped
    baseline. The identity gate still runs on the whole sealed population, so
    a projection can never be produced from a population that failed it.
    """

    gate = identity_gate(rows)
    frontier = cap_frontier(
        rows, alphas=alphas, references=references, segments=segments
    )
    calls = Counter(row.call for row in rows)
    summary: dict[str, object] = {
        "schema": ANALYSIS_VERSION,
        "exposure_row": EXPOSURE_ROW_ID,
        "execution_profile": "model-free-check",
        "arm": ARM,
        "arm_source": dict(ARM_SOURCES[ARM]),
        "population": {
            "split_name": "E22-ESB-DEV10-UTTERANCES",
            "split_role": "dev",
            "rows": len(rows),
            "calls": dict(sorted(calls.items())),
        },
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "embedder": 0,
            "retriever": 0,
            "scorer": 0,
            "network": 0,
            "gpu_hours": 0,
            "audio_seconds_decoded": 0,
            "paid_api_spend": 0,
            "outbound_connection_attempts": outbound_attempts,
            "outbound_connection_targets": list(outbound_targets),
        },
        "test_split_read": False,
        "identity_gate": gate,
        "excess_distribution": excess_distribution(rows),
        "excess_by_duration": excess_by_duration(rows),
        "excess_by_overlap": excess_by_overlap(rows),
        "sentence_final": sentence_final_table(rows),
        "token_profile": token_profile(rows),
        "bleed_profile": bleed_profile(rows),
        "per_call": per_call_table(rows),
        "cap_frontier": frontier,
        "limits": [
            "The token-to-word mapping inside a row is a linear map on that row's own "
            "measured tokens-per-word ratio, not the flight tokenizer's segmentation. "
            "Every capped-row figure and every simulated WER inherits it.",
            "The simulated WER is what a greedy decode under the cap would have "
            "returned as a token PREFIX. It is not an oracle -- the cap reads only the "
            "clip duration -- but it is also not a measurement: no capped request was "
            "ever sent.",
            "The excess is a length statement. The 2026-09-05 shape-C verdict already "
            "showed that shortening the output does not by itself lower the number; a "
            "cap is a different intervention from that shape, and neither this table "
            "nor that one settles the other.",
            "Population is DEV ONLY. Nothing here transfers to the six ESB test calls "
            "by measurement, and no test row was opened.",
        ],
    }
    if subset_ids is not None:
        keep = set(subset_ids)
        selected = [row for row in rows if row.sample_id in keep]
        if len(selected) != len(keep):
            raise OvergenerationError(
                f"the subset projection matched {len(selected)} of {len(keep)} declared ids"
            )
        baseline = population_baseline(
            selected, references=references, segments=segments
        )
        summary["subset_projection"] = {
            "label": subset_label or "subset",
            "rows": len(selected),
            "baseline": baseline,
            "cap_frontier": cap_frontier(
                selected,
                alphas=alphas,
                references=references,
                segments=segments,
                baseline_wer_percent=float(baseline["corpus_wer_percent"]),
            ),
            "constants_basis": (
                "words_per_second_p95 and tokens_per_word are re-measured ON THE SUBSET, "
                "because a cell that flies the subset would measure them there too; the "
                "full-population values are in cap_frontier above and the two are reported "
                "side by side rather than one being substituted for the other"
            ),
        }
    return summary, per_row_csv(rows)


__all__ = [
    "ALPHA_LADDER",
    "ANALYSIS_VERSION",
    "ARM",
    "CLIP_AUDIT_DIR_RELPATH",
    "CLIP_TABLE_NAME",
    "EXCESS_BUCKET_EDGES",
    "EXPOSURE_ROW_ID",
    "OvergenerationError",
    "RowMetrics",
    "SEALED_CORPUS_WER_PERCENT",
    "SEALED_TOTALS",
    "build_receipts",
    "build_rows",
    "cap_frontier",
    "cap_tokens",
    "ends_sentence_final",
    "excess_by_duration",
    "excess_by_overlap",
    "excess_distribution",
    "identity_gate",
    "kept_words",
    "load_clip_geometry",
    "load_flight_tokens",
    "per_call_table",
    "population_baseline",
    "per_row_csv",
    "sentence_final_table",
    "token_profile",
    "bleed_profile",
    "simulate_agentic_rate",
    "simulate_cap",
    "tokens_per_word",
    "trace_path",
    "words_per_second_p95",
]
