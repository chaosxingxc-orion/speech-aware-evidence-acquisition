#!/usr/bin/env python3
"""The single registered read of the SLURP logprob-as-judge probe.

Preregistration:
``docs/readiness/2026-09-08-slurp-logprob-judge-probe-v1-preregistration.md``.

The question, in one line: does the frozen core's own token confidence predict
its own errors well enough to be a Reviewer signal?

**Everything is measured WITHIN the probe arm.** The probe flies a new arm --
greedy is not bitwise reproducible across batch compositions on llama-server,
and this arm carries a decoding parameter the sealed comparator did not -- so
its answers are its own. Its official scores are paired against its own
confidences, never against the sealed comparator's rows, and this read makes no
accuracy comparison between the two arms at all.

Four measurements, exactly as preregistered:

1. **AUROC** of each row-level confidence statistic against ``intent error``
   and against ``any slot error``, with a cluster bootstrap over speakers
   (``analysis.paired.resampled_statistic``, which resamples whole clusters).
2. **The 86-flag operating point.** The confidence flag is set at whatever
   threshold flags the same number of rows the MF-9 schema judge flagged on
   KC-S1b (86), and its precision and recall are reported there -- alone, and
   in UNION with the schema and legality judges recomputed on this arm's own
   rows.
3. **The precision-recall curve** of a confidence-gated re-ask: rows flagged
   against errors caught, over every distinct threshold.
4. The **admission verdict**, applied mechanically.

Inputs are files, not a live dataset, so every function here is unit-testable
on synthetic traces (``tests/unit/test_slurp_logprob_judge_read.py``) and the
dataset-side provenance stays in the flight read that produces them:

``--trace``          the arm's own ``*.trace.jsonl`` (MODEL_LOGPROBS records)
``--outputs``        the arm's own sealed ``*.outputs.jsonl``
``--per-sample``     ``core.scoring_batch`` per-sample scores for this arm
``--clusters``       ``{sample_id: speaker_id}``, from the governed
                     ``metadata.json`` (``data.slurp``'s own speaker index)
``--label-inventory`` ``{"entity_types": [...], "legal_pairs": [[scen, act]...]}``,
                     mined from TRAIN alone

Model-free: zero model, GPU, tool, embedding and network contacts.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]

SEED = 20260908
N_REPLICATES = 10_000
CI_LEVEL = 0.90

#: The MF-9 schema judge's own numbers on KC-S1b
#: (``docs/readiness/2026-09-08-mf9-slurp-slot-gap-audit-v1.md`` section 5.1).
#: The flag budget and the precision bar are FIXED by the owner-approved
#: admission rule; they are a bar this arm must clear, not a number recomputed
#: from this arm.
SCHEMA_JUDGE_FLAG_BUDGET = 86
SCHEMA_JUDGE_PRECISION = 72.09

#: The admission rule, fixed before the flight.
ADMISSION_AUROC = 0.75
ADMISSION_AUROC_CI90_LOWER = 0.70

#: Every confidence statistic this read computes. Each is oriented so that a
#: LOWER value means LESS confident, i.e. a higher expected error rate -- so a
#: statistic is a flag score after negation and an AUROC is computed against
#: the negated value throughout.
STATISTICS = (
    "min_token_logprob",
    "mean_token_logprob",
    "intent_mean_token_logprob",
    "intent_min_token_logprob",
    "first_intent_token_margin",
)


class LogprobReadError(RuntimeError):
    """The read refuses: malformed trace, missing join, or an unusable shape."""


# ---------------------------------------------------------------------------
# Reading what the flight sealed
# ---------------------------------------------------------------------------


def load_jsonl(path: Path | str) -> list[Mapping[str, object]]:
    rows: list[Mapping[str, object]] = []
    text = Path(path).read_text(encoding="utf-8")
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise LogprobReadError(f"{path} line {number} is malformed: {error}") from error
        if not isinstance(row, Mapping):
            raise LogprobReadError(f"{path} line {number} is not an object")
        rows.append(row)
    return rows


def logprobs_by_request(trace_rows: Iterable[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    """``{request_id: logprobs object}`` from a run's MODEL_LOGPROBS records.

    The record id is ``<request_id>/logprobs`` -- the same convention
    MODEL_REQUEST and MODEL_RESPONSE use -- so the join back to an outputs row
    is exact and needs no heuristic.
    """

    found: dict[str, Mapping[str, object]] = {}
    for record in trace_rows:
        if record.get("channel") != "MODEL_LOGPROBS":
            continue
        record_id = str(record.get("record_id", ""))
        if not record_id.endswith("/logprobs"):
            raise LogprobReadError(f"unexpected MODEL_LOGPROBS record id {record_id!r}")
        request_id = record_id[: -len("/logprobs")]
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            raise LogprobReadError(f"{record_id}: payload is not an object")
        logprobs = payload.get("logprobs")
        if not isinstance(logprobs, Mapping):
            raise LogprobReadError(f"{record_id}: logprobs is not an object")
        if request_id in found:
            raise LogprobReadError(f"duplicate MODEL_LOGPROBS record for {request_id!r}")
        found[request_id] = logprobs
    return found


def token_entries(logprobs: Mapping[str, object]) -> list[Mapping[str, object]]:
    """The generated tokens, in generation order.

    llama-server's chat endpoint shape (pinned build 04ccc72a,
    ``tools/server/server-task.cpp:456-460``): ``{"content": [{"token",
    "logprob", "top_logprobs": [...]}, ...]}``. Only GENERATED tokens appear
    here -- the prompt's tokens never get probabilities on this build.
    """

    content = logprobs.get("content")
    if not isinstance(content, list) or not content:
        raise LogprobReadError("logprobs object carries no non-empty 'content' list")
    entries: list[Mapping[str, object]] = []
    for index, item in enumerate(content):
        if not isinstance(item, Mapping):
            raise LogprobReadError(f"logprobs content[{index}] is not an object")
        value = item.get("logprob")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise LogprobReadError(f"logprobs content[{index}] has no numeric logprob")
        entries.append(item)
    return entries


# ---------------------------------------------------------------------------
# Row-level confidence statistics
# ---------------------------------------------------------------------------


def _value_span(text: str, key: str) -> tuple[int, int] | None:
    """Character span of the JSON string VALUE of ``key`` in ``text``.

    Deliberately literal rather than a JSON walk: the statistic has to point at
    a region of the GENERATED TOKEN STREAM, and only the raw text preserves the
    offsets the token stream is aligned to. Returns None when the key is absent
    or the row did not produce a quoted string value for it.
    """

    needle = f'"{key}"'
    at = text.find(needle)
    if at < 0:
        return None
    cursor = at + len(needle)
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(text) or text[cursor] != ":":
        return None
    cursor += 1
    while cursor < len(text) and text[cursor] in " \t\r\n":
        cursor += 1
    if cursor >= len(text) or text[cursor] != '"':
        return None
    start = cursor + 1
    end = start
    while end < len(text):
        if text[end] == "\\":
            end += 2
            continue
        if text[end] == '"':
            return (start, end)
        end += 1
    return None


def _token_offsets(entries: Sequence[Mapping[str, object]]) -> list[tuple[int, int]]:
    offsets: list[tuple[int, int]] = []
    cursor = 0
    for entry in entries:
        token = str(entry.get("token", ""))
        offsets.append((cursor, cursor + len(token)))
        cursor += len(token)
    return offsets


def _overlapping(
    entries: Sequence[Mapping[str, object]],
    offsets: Sequence[tuple[int, int]],
    span: tuple[int, int],
) -> list[Mapping[str, object]]:
    start, end = span
    return [
        entry
        for entry, (low, high) in zip(entries, offsets)
        if low < end and high > start
    ]


def _margin(entry: Mapping[str, object]) -> float | None:
    """top-1 minus top-2 logprob at one token, or None when the request asked
    for fewer than two alternatives (``top_logprobs`` k < 2)."""

    alternatives = entry.get("top_logprobs")
    if not isinstance(alternatives, list) or len(alternatives) < 2:
        return None
    values: list[float] = []
    for item in alternatives[:2]:
        if not isinstance(item, Mapping):
            return None
        value = item.get("logprob")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return None
        values.append(float(value))
    return values[0] - values[1]


def row_confidence(logprobs: Mapping[str, object]) -> dict[str, float | None]:
    """Every preregistered statistic for one row.

    The generated text is RECONSTRUCTED from the token stream itself
    (concatenating the entries' own ``token`` fields) rather than taken from the
    outputs row: the intent-span statistics are alignments INTO the token
    stream, and only its own reconstruction is guaranteed to share its offsets.
    The caller checks that the reconstruction matches the sealed text.
    """

    entries = token_entries(logprobs)
    values = [float(entry["logprob"]) for entry in entries]  # type: ignore[arg-type]
    text = "".join(str(entry.get("token", "")) for entry in entries)
    offsets = _token_offsets(entries)

    intent_entries: list[Mapping[str, object]] = []
    first_intent_entry: Mapping[str, object] | None = None
    for key in ("scenario", "action"):
        span = _value_span(text, key)
        if span is None:
            continue
        matched = _overlapping(entries, offsets, span)
        intent_entries.extend(matched)
        if key == "scenario" and matched and first_intent_entry is None:
            first_intent_entry = matched[0]
    if first_intent_entry is None and intent_entries:
        first_intent_entry = intent_entries[0]
    intent_values = [
        float(entry["logprob"]) for entry in intent_entries  # type: ignore[arg-type]
    ]

    return {
        "min_token_logprob": min(values),
        "mean_token_logprob": sum(values) / len(values),
        "intent_mean_token_logprob": (
            sum(intent_values) / len(intent_values) if intent_values else None
        ),
        "intent_min_token_logprob": min(intent_values) if intent_values else None,
        "first_intent_token_margin": (
            _margin(first_intent_entry) if first_intent_entry is not None else None
        ),
        "token_count": float(len(values)),
        "intent_token_count": float(len(intent_values)),
        "reconstructed_text": text,  # type: ignore[dict-item]
    }


# ---------------------------------------------------------------------------
# Labels: the arm's own official errors, and the deterministic judges
# ---------------------------------------------------------------------------


def error_labels(per_sample: Iterable[Mapping[str, object]]) -> dict[str, dict[str, bool]]:
    """``{sample_id: {"intent_error": bool, "slot_error": bool,
    "unmatched_gold": bool}}`` from this arm's own per-sample official scores.

    * ``intent_error`` -- ``scenario_action_exact`` is 0. This is the official
      intent column, row by row.
    * ``unmatched_gold`` -- ``slot_f1_exact_fn > 0``: at least one gold
      ``(type, filler)`` pair the row did not produce. This is the probe's own
      reading of MF-9's precision denominator ("carries an unmatched gold
      mention"); it is STRICTER than MF-9's type-matched reading, which is why
      the probe recomputes every judge under this definition rather than
      comparing to MF-9's own counts.
    * ``slot_error`` -- any false negative OR any false positive.
    """

    labels: dict[str, dict[str, bool]] = {}
    for entry in per_sample:
        sample_id = entry.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise LogprobReadError("per-sample score entry lacks a sample_id")
        try:
            intent = float(entry["scenario_action_exact"])  # type: ignore[arg-type]
            false_negatives = float(entry["slot_f1_exact_fn"])  # type: ignore[arg-type]
            false_positives = float(entry["slot_f1_exact_fp"])  # type: ignore[arg-type]
        except (KeyError, TypeError, ValueError) as error:
            raise LogprobReadError(
                f"per-sample score entry for {sample_id!r} is missing an official field: {error}"
            ) from error
        if sample_id in labels:
            raise LogprobReadError(f"duplicate per-sample score entry for {sample_id!r}")
        labels[sample_id] = {
            "intent_error": intent == 0.0,
            "unmatched_gold": false_negatives > 0.0,
            "slot_error": false_negatives > 0.0 or false_positives > 0.0,
        }
    return labels


def deterministic_judges(
    text: str, inventory: Mapping[str, object]
) -> dict[str, bool]:
    """The two free judges, recomputed on THIS arm's own row.

    ``schema`` -- MF-9 section 3's rule, restated for a direct arm that has no
    per-intent block: the row is unparsed, OR names an entity type outside the
    55-type SLURP vocabulary, OR repeats a type. (MF-9's block-membership
    clause has no meaning here; the closed-list instruction lists the 55 types,
    not a per-intent subset, and the note records the difference rather than
    pretending the two judges are the same object.)

    ``legality`` -- the row's ``(scenario, action)`` pair is not one of the
    legal TRAIN pairs, i.e. the locked ``slurp-legal-label-projection-v2``
    judge fires on it.
    """

    types = {str(value) for value in inventory.get("entity_types", ())}
    legal_pairs = {
        (str(pair[0]), str(pair[1]))
        for pair in inventory.get("legal_pairs", ())
        if isinstance(pair, (list, tuple)) and len(pair) == 2
    }

    try:
        parsed = json.loads(text)
        if not isinstance(parsed, Mapping):
            raise ValueError("response is not a JSON object")
    except (json.JSONDecodeError, ValueError):
        return {"schema": True, "legality": True, "unparsed": True}

    entities = parsed.get("entities")
    seen: list[str] = []
    schema = False
    if entities is None:
        entities = []
    if not isinstance(entities, list):
        schema = True
        entities = []
    for item in entities:
        if not isinstance(item, Mapping) or "type" not in item:
            schema = True
            continue
        name = str(item.get("type"))
        if types and name not in types:
            schema = True
        if name in seen:
            schema = True
        seen.append(name)

    scenario = parsed.get("scenario")
    action = parsed.get("action")
    legality = not (
        isinstance(scenario, str)
        and isinstance(action, str)
        and (scenario, action) in legal_pairs
    )
    return {"schema": schema, "legality": legality, "unparsed": False}


# ---------------------------------------------------------------------------
# The statistics the verdict turns on
# ---------------------------------------------------------------------------


def auroc(scores: Sequence[float], labels: Sequence[bool]) -> float:
    """Rank AUROC with ties handled by mid-rank, the definition every
    tie-bearing statistic here needs (a confidence flag has many ties).

    ``scores`` is oriented so that HIGHER means MORE likely to be an error.
    Returns 0.5 when either class is empty -- the value that says "this
    statistic separates nothing here" -- rather than raising, so a stratum with
    no errors does not abort a whole bootstrap.
    """

    if len(scores) != len(labels):
        raise LogprobReadError("scores and labels must be the same length")
    positives = [score for score, label in zip(scores, labels) if label]
    negatives = [score for score, label in zip(scores, labels) if not label]
    if not positives or not negatives:
        return 0.5
    order = sorted(range(len(scores)), key=lambda index: scores[index])
    ranks = [0.0] * len(scores)
    index = 0
    while index < len(order):
        end = index
        while end + 1 < len(order) and scores[order[end + 1]] == scores[order[index]]:
            end += 1
        mid = (index + end) / 2.0 + 1.0
        for position in range(index, end + 1):
            ranks[order[position]] = mid
        index = end + 1
    positive_rank_sum = sum(
        rank for rank, label in zip(ranks, labels) if label
    )
    n_pos, n_neg = len(positives), len(negatives)
    return (positive_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def flag_at_budget(
    scores: Mapping[str, float], budget: int
) -> tuple[set[str], float]:
    """The ``budget`` least-confident rows, and the threshold that selects them.

    ``scores`` is oriented so HIGHER means MORE likely to be an error. Ties at
    the boundary are INCLUDED -- a threshold cannot split identical evidence --
    so the returned set may exceed ``budget``; the caller reports the actual
    count, never the requested one.
    """

    if budget <= 0:
        raise LogprobReadError("flag budget must be positive")
    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    if budget >= len(ordered):
        return set(scores), -math.inf
    threshold = ordered[budget - 1][1]
    return {key for key, value in scores.items() if value >= threshold}, threshold


def precision_recall(
    flagged: Iterable[str], errors: Mapping[str, bool]
) -> dict[str, float | int]:
    flagged = set(flagged)
    error_ids = {key for key, value in errors.items() if value}
    hit = len(flagged & error_ids)
    return {
        "flagged": len(flagged),
        "errors": len(error_ids),
        "caught": hit,
        "precision": 100.0 * hit / len(flagged) if flagged else 0.0,
        "recall": 100.0 * hit / len(error_ids) if error_ids else 0.0,
    }


def precision_at_budget_over_sequence(
    ids: Sequence[str],
    *,
    scores: Mapping[str, float],
    errors: Mapping[str, bool],
    budget: int,
    population: int,
) -> float:
    """Precision at the flag budget over a RESAMPLED id sequence.

    ``analysis.paired.resampled_statistic`` hands its statistic a sequence in
    which ids REPEAT -- a cluster drawn twice contributes its members twice --
    and its own docstring says a statistic must therefore work over the
    sequence rather than over ``set(ids)``. Collapsing to a set here would
    silently throw the resampling away and produce a CI that is too narrow, so
    every step below keeps the multiplicity: the ranking, the budget, the
    threshold and the precision.

    The budget is RESCALED to the replicate's own size, so a replicate that
    draws fewer rows flags proportionally fewer of them. Boundary ties are
    included, exactly as in :func:`flag_at_budget`.
    """

    scored = sorted(
        ((scores[sample_id], sample_id) for sample_id in ids),
        key=lambda item: (-item[0], item[1]),
    )
    if not scored or population <= 0:
        return 0.0
    scaled = min(max(1, round(budget * len(scored) / population)), len(scored))
    threshold = scored[scaled - 1][0]
    drawn = [sample_id for value, sample_id in scored if value >= threshold]
    hits = sum(1 for sample_id in drawn if errors.get(sample_id, False))
    return 100.0 * hits / len(drawn)


def precision_recall_curve(
    scores: Mapping[str, float], errors: Mapping[str, bool]
) -> list[dict[str, float | int]]:
    """One point per DISTINCT threshold: how many rows a confidence-gated
    re-ask would flag, and how many errors it would reach."""

    thresholds = sorted({value for value in scores.values()}, reverse=True)
    curve: list[dict[str, float | int]] = []
    for threshold in thresholds:
        flagged = {key for key, value in scores.items() if value >= threshold}
        point = dict(precision_recall(flagged, errors))
        point["flag_score_threshold"] = threshold
        point["statistic_cutoff"] = -threshold
        curve.append(point)
    return curve


def admission_verdict(
    *,
    auroc_point: float,
    auroc_ci_low: float,
    precision_at_budget: float,
    precision_ci_low: float,
) -> dict[str, object]:
    """The rule, fixed before the flight and applied mechanically here."""

    by_auroc = auroc_point >= ADMISSION_AUROC and auroc_ci_low >= ADMISSION_AUROC_CI90_LOWER
    by_precision = (
        precision_at_budget > SCHEMA_JUDGE_PRECISION
        and precision_ci_low > SCHEMA_JUDGE_PRECISION
    )
    return {
        "admitted": bool(by_auroc or by_precision),
        "by_auroc": bool(by_auroc),
        "by_precision": bool(by_precision),
        "rule": (
            f"ADMITTED if AUROC >= {ADMISSION_AUROC} for intent error with cluster-"
            f"bootstrap CI90 lower bound >= {ADMISSION_AUROC_CI90_LOWER}, OR if "
            f"precision at {SCHEMA_JUDGE_FLAG_BUDGET} flags exceeds the schema judge's "
            f"{SCHEMA_JUDGE_PRECISION} % with CI90 lower bound above it; otherwise NOT "
            "ADMITTED and the re-ask module falls back to the deterministic judges"
        ),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def build_rows(
    *,
    trace: Sequence[Mapping[str, object]],
    outputs: Sequence[Mapping[str, object]],
    per_sample: Sequence[Mapping[str, object]],
    inventory: Mapping[str, object],
) -> dict[str, dict[str, Any]]:
    """One record per sample: its confidences, its official errors, its judges."""

    logprobs = logprobs_by_request(trace)
    labels = error_labels(per_sample)
    rows: dict[str, dict[str, Any]] = {}
    for row in outputs:
        sample_id = row.get("sample_id")
        request_id = row.get("request_id")
        text = row.get("text")
        if not isinstance(sample_id, str) or not isinstance(request_id, str):
            raise LogprobReadError("outputs row lacks sample_id/request_id")
        if not isinstance(text, str):
            raise LogprobReadError(f"outputs row {sample_id!r} lacks a text field")
        if request_id not in logprobs:
            raise LogprobReadError(
                f"outputs row {sample_id!r} (request {request_id!r}) has no "
                "MODEL_LOGPROBS record -- the server returned no distribution for it"
            )
        if sample_id not in labels:
            raise LogprobReadError(f"no per-sample official score for {sample_id!r}")
        confidence = row_confidence(logprobs[request_id])
        reconstructed = str(confidence.pop("reconstructed_text"))
        rows[sample_id] = {
            "sample_id": sample_id,
            "request_id": request_id,
            "confidence": confidence,
            "labels": labels[sample_id],
            "judges": deterministic_judges(text, inventory),
            # A token stream that does not rebuild the sealed answer means the
            # span statistics are aligned to the wrong string. Reported, never
            # silently tolerated: the caller decides whether to refuse.
            "token_stream_rebuilds_text": reconstructed == text,
        }
    missing = sorted(set(labels) - set(rows))
    if missing:
        raise LogprobReadError(f"{len(missing)} scored sample(s) have no outputs row")
    return rows


def analyse(
    rows: Mapping[str, Mapping[str, Any]],
    *,
    clusters: Mapping[str, str],
    seed: int = SEED,
    n_replicates: int = N_REPLICATES,
    ci_level: float = CI_LEVEL,
    flag_budget: int = SCHEMA_JUDGE_FLAG_BUDGET,
) -> dict[str, Any]:
    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic

    sample_ids = sorted(rows)
    unclustered = [sample_id for sample_id in sample_ids if sample_id not in clusters]
    if unclustered:
        raise LogprobReadError(
            f"{len(unclustered)} sample(s) have no speaker cluster, e.g. {unclustered[:3]}"
        )

    def cluster_of(sample_id: str) -> str:
        return str(clusters[sample_id])

    document: dict[str, Any] = {
        "n": len(sample_ids),
        "clusters": len({cluster_of(sample_id) for sample_id in sample_ids}),
        "seed": seed,
        "n_replicates": n_replicates,
        "ci_level": ci_level,
        "token_stream_mismatches": sorted(
            sample_id
            for sample_id in sample_ids
            if not rows[sample_id]["token_stream_rebuilds_text"]
        ),
        "auroc": {},
        "operating_point": {},
        "curves": {},
    }

    for target in ("intent_error", "slot_error"):
        errors = {
            sample_id: bool(rows[sample_id]["labels"][target]) for sample_id in sample_ids
        }
        document["auroc"][target] = {}
        for statistic in STATISTICS:
            usable = [
                sample_id
                for sample_id in sample_ids
                if rows[sample_id]["confidence"].get(statistic) is not None
            ]
            if not usable:
                document["auroc"][target][statistic] = {
                    "status": "UNAVAILABLE",
                    "reason": "no row carries this statistic",
                }
                continue
            # Negated: a LOWER logprob (or margin) means LESS confident, so the
            # flag score must rise as confidence falls.
            flag_score = {
                sample_id: -float(rows[sample_id]["confidence"][statistic])
                for sample_id in usable
            }

            def statistic_over(ids: Sequence[str], _score=flag_score, _errors=errors) -> float:
                return auroc(
                    [_score[sample_id] for sample_id in ids],
                    [_errors[sample_id] for sample_id in ids],
                )

            result = resampled_statistic(
                sample_ids=usable,
                statistic=statistic_over,
                seed=seed,
                n_replicates=n_replicates,
                ci_level=ci_level,
                cluster_of=cluster_of,
            )
            document["auroc"][target][statistic] = {
                "status": "OK",
                "n": len(usable),
                "auroc": result.point_estimate,
                "ci90": [result.ci_low, result.ci_high],
                "sigma_hat": result.sigma_hat,
            }

    # -- the 86-flag operating point, and the unions -------------------------
    primary = "min_token_logprob"
    usable = [
        sample_id
        for sample_id in sample_ids
        if rows[sample_id]["confidence"].get(primary) is not None
    ]
    flag_score = {
        sample_id: -float(rows[sample_id]["confidence"][primary]) for sample_id in usable
    }
    flagged, threshold = flag_at_budget(flag_score, flag_budget)
    schema_flagged = {
        sample_id for sample_id in sample_ids if rows[sample_id]["judges"]["schema"]
    }
    legality_flagged = {
        sample_id for sample_id in sample_ids if rows[sample_id]["judges"]["legality"]
    }
    for target in ("intent_error", "slot_error", "unmatched_gold"):
        errors = {
            sample_id: bool(rows[sample_id]["labels"][target]) for sample_id in sample_ids
        }
        document["operating_point"][target] = {
            "statistic": primary,
            "requested_budget": flag_budget,
            # The flag score is the NEGATED statistic (higher = less
            # confident), so both are reported: the threshold the flag applies,
            # and the cutoff in the statistic's own units, which is the number a
            # reader of a logprob wants. Non-finite (the whole population
            # flagged) is reported as null rather than as JSON's non-standard
            # -Infinity literal.
            "flag_score_threshold": threshold if math.isfinite(threshold) else None,
            "statistic_cutoff": -threshold if math.isfinite(threshold) else None,
            "confidence": precision_recall(flagged, errors),
            "schema_judge": precision_recall(schema_flagged, errors),
            "legality_judge": precision_recall(legality_flagged, errors),
            "union_confidence_schema": precision_recall(flagged | schema_flagged, errors),
            "union_all_three": precision_recall(
                flagged | schema_flagged | legality_flagged, errors
            ),
        }
        document["curves"][target] = precision_recall_curve(flag_score, errors)

    # -- the verdict ---------------------------------------------------------
    intent_auroc = document["auroc"]["intent_error"].get(primary, {})

    intent_errors = {
        sample_id: bool(rows[sample_id]["labels"]["intent_error"])
        for sample_id in sample_ids
    }

    def precision_over(ids: Sequence[str]) -> float:
        return precision_at_budget_over_sequence(
            ids,
            scores=flag_score,
            errors=intent_errors,
            budget=flag_budget,
            population=len(flag_score),
        )

    precision_boot = resampled_statistic(
        sample_ids=usable,
        statistic=precision_over,
        seed=seed,
        n_replicates=n_replicates,
        ci_level=ci_level,
        cluster_of=cluster_of,
    )
    document["precision_at_budget_bootstrap"] = {
        "precision": precision_boot.point_estimate,
        "ci90": [precision_boot.ci_low, precision_boot.ci_high],
        "note": (
            "the flag budget is rescaled to each replicate's own size, so a replicate "
            "that draws fewer rows flags proportionally fewer of them"
        ),
    }
    document["verdict"] = admission_verdict(
        auroc_point=float(intent_auroc.get("auroc", 0.0)),
        auroc_ci_low=float((intent_auroc.get("ci90") or [0.0, 0.0])[0]),
        precision_at_budget=float(
            document["operating_point"]["intent_error"]["confidence"]["precision"]
        ),
        precision_ci_low=float(precision_boot.ci_low),
    )
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--per-sample", type=Path, required=True)
    parser.add_argument("--clusters", type=Path, required=True)
    parser.add_argument("--label-inventory", type=Path, required=True)
    parser.add_argument("--flag-budget", type=int, default=SCHEMA_JUDGE_FLAG_BUDGET)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--replicates", type=int, default=N_REPLICATES)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    if str(REPO / "src") not in sys.path:
        sys.path.insert(0, str(REPO / "src"))

    per_sample_doc = json.loads(args.per_sample.read_text(encoding="utf-8"))
    per_sample = (
        per_sample_doc["per_sample"]
        if isinstance(per_sample_doc, Mapping)
        else per_sample_doc
    )
    rows = build_rows(
        trace=load_jsonl(args.trace),
        outputs=load_jsonl(args.outputs),
        per_sample=per_sample,
        inventory=json.loads(args.label_inventory.read_text(encoding="utf-8")),
    )
    document = analyse(
        rows,
        clusters=json.loads(args.clusters.read_text(encoding="utf-8")),
        seed=args.seed,
        n_replicates=args.replicates,
        flag_budget=args.flag_budget,
    )
    document["schema"] = "saea-slurp-logprob-judge-read-v1"
    document["model_contacts"] = 0
    payload = json.dumps(document, indent=2, sort_keys=True, default=str) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8", newline="\n")
        print(f"wrote {args.output}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
