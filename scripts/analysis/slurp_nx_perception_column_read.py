#!/usr/bin/env python3
"""NX programme E2 for the PERCEPTION node: the node-local reader for a sealed Perception template column.

Programme ``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`` C0.1 / C1 item E2, owner
decision 239 (2026-10-10). A sealed run whose Perception node carries a ``template_variants`` group
(receipt ``saea-perception-branch-arms-v4`` under ``native_episode_receipt.perception_branches``, level 2)
holds, per row, K Perception notes -- one per instruction-template arm -- and K first-visit Solver answers,
each Solver contact rendered over ITS OWN arm's note. This reader scores each arm against the DELIVERING
(locked-template) arm, PAIRED per row:

(i)   the Perception NOTE metrics the P-SV branch reader already reads
      (``slurp_perception_branch_read``): gold intent on the candidate list (``present``), gold rank
      (1/2/3/4+/absent), top-1, list size, ``note_parse_status`` and the contact's own prompt tokens;
(ii)  the optional ENTITY-PRESENCE verdict a note may carry -- ``entity_presence`` in
      ``{present, none, unsure}`` and an optional ``heard_values`` count (a non-negative integer). A note that
      carries no such field is ``absent`` (the field is not part of the registered note schema; a template
      that asks for it is what makes it appear). Precision and recall of ``none`` against the empty-gold label
      (``none`` is the positive class: gold has no entity), of ``present`` against non-empty gold, the
      unsure rate, and the paired differences of the per-row ``none``-on-empty / ``none``-on-non-empty
      indicators;
(iii) the LEVEL-2 SOLVER column: each arm's first-visit Solver answer scored by
      ``slurp_nx_solver_column_read`` (the normalised exact-set primary, empty-gold false fill, non-empty
      exact, paired vs the delivering arm), reusing that reader's functions rather than re-implementing them;
(iv)  E2b, the DISTINCTION TAG (NX round R6): the ``E=`` presence verdict and up to three ``M=`` heard
      mentions at the head of every candidate's ``distinction`` string, parsed exactly as
      ``configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md`` defines (classes ``ok`` / ``absent`` /
      ``invalid``; ``unsure`` admitted only where the arm's ``--tag-set`` allows it, default ``none,some``).
      Per arm, on the rank-1 candidate and on the list majority: parse classes; AUC / precision / recall of
      ``E=none`` against empty gold; precision / recall of ``E=some`` against non-empty gold; the ``unsure``
      rate by gold class; heard-mention containment (share of gold entities whose normalised surface equals an
      offered ``M=`` surface, per slot type) and option precision. The surface normalisation is the registered
      delivery normaliser's filler normalisation (``rails.slurp_projection_v3.normalize_filler_p2``), reused.
      The key-path reader of (ii) is untouched.

Statistics. Every difference is a per-row paired difference (arm minus delivering arm), reported with a
WHOLE-UTTERANCE CLUSTER bootstrap CI95 (``analysis.paired.resampled_statistic``, 10,000 draws, seed
20260915, a cluster being one SLURP utterance id) and the paired Wilson read of the discordant rows.

Gold discipline: gold (intent and entities) enters only offline, through the governed SLURP loaders exactly
as ``slurp_nx_solver_column_read`` loads it; the test split is refused. Text discipline: no utterance text,
transcript, gold value, filler, note body or model output is printed or persisted -- only ids, counts, rates,
pp, slot TYPE names, arm ids and hashes (a note is parsed in memory and discarded). Zero model, server,
tokenizer, scorer-subprocess, network and GPU contact.

    PYTHONDONTWRITEBYTECODE=1 python -B scripts/analysis/slurp_nx_perception_column_read.py \\
        --data-root "$SPEECHRL_DATA_DIR" --lock docs/datasets.lock.json \\
        --run-id <RUN_ID> --attempt-id <ATTEMPT_ID> --split train
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _p in (str(REPO_ROOT / "src"), str(REPO_ROOT / "scripts" / "analysis")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import slurp_nx_solver_column_read as SC  # noqa: E402
import slurp_perception_branch_read as PB  # noqa: E402

READ_ID = "SAEA-NX-PERCEPTION-TEMPLATE-COLUMN-READ-V1"
RECIPE = "slurp-nx-perception-column-read-v1"
SCHEMA_VERSION = "saea-nx-perception-column-read-v1"
SEED = SC.SEED
DRAWS = SC.DRAWS
CI_LEVEL = SC.CI_LEVEL
V4_SCHEMA = "saea-perception-branch-arms-v4"
DEFAULT_LOCK = SC.DEFAULT_LOCK
DEFAULT_DATA_ROOT = SC.DEFAULT_DATA_ROOT

PRESENCE_VALUES = ("present", "none", "unsure")
#: Verdict classes a note can fall into: the three schema values, ``invalid`` (the field is carried
#: with another value) and ``absent`` (the field is not carried at all).
VERDICTS = (*PRESENCE_VALUES, "invalid", "absent")
RANK_BUCKETS = PB.RANK_BUCKETS

#: ``(metric, subset of rows, higher_is_better)`` of the paired note reads.
NOTE_METRICS = (
    ("present", "all", True),
    ("top1", "all", True),
)
#: The paired per-row verdict indicators. ``none_on_empty`` is the recall of ``none``;
#: ``none_on_nonempty`` is the false-``none`` rate (lower is better).
PRESENCE_METRICS = (
    ("none_on_empty", "empty_gold", True),
    ("none_on_nonempty", "nonempty_gold", False),
    ("present_on_nonempty", "nonempty_gold", True),
)


#: E2b (NX round R6): the pinned distinction-tag grammar this reader parses exactly.
TAG_GRAMMAR_RELPATH = "configs/probes/nx/perception/r6/TAG-GRAMMAR-v1.md"
TAG_VALUES = ("none", "some", "unsure")
#: The tag set an arm allows unless ``--tag-set`` widens it (``unsure`` only for a template that asks for it).
DEFAULT_TAG_SET = ("none", "some")
TAG_CLASSES = ("ok", "absent", "invalid")
MAX_MENTIONS, MAX_MENTION_WORDS, MAX_TRAILER_WORDS = 3, 4, 8
#: Verdict classes of a row on the rank-1 candidate or the list majority.
TAG_VERDICTS = (*TAG_VALUES, "split", "invalid", "absent")
_TAG_HEAD = re.compile(r"E=([A-Za-z]+)")
#: Higher score = more likely "no entity"; the AUC of ``E=none`` against empty gold uses this order.
_NONE_SCORE = {"some": 0, "unsure": 1, "none": 2}


class PerceptionColumnReadError(RuntimeError):
    """The sealed run, its gold or its branch group is not what this reader reads."""


# ---------------------------------------------------------------------------
# pure parts (unit-tested on synthetic sealed records)


def entity_presence_of(note_text: object) -> dict:
    """The optional entity-presence verdict one note carries, parsed in memory.

    ``{"verdict": one of VERDICTS, "heard_values": int | None}``. ``absent``: the note carries no
    ``entity_presence`` key (or is not a JSON object); ``invalid``: the key is carried with a value outside
    :data:`PRESENCE_VALUES`. ``heard_values`` is read only when it is a non-negative integer (a bool is not).
    """

    if not isinstance(note_text, str):
        return {"verdict": "absent", "heard_values": None}
    try:
        document = json.loads(note_text)
    except (ValueError, TypeError):
        return {"verdict": "absent", "heard_values": None}
    if not isinstance(document, Mapping) or "entity_presence" not in document:
        return {"verdict": "absent", "heard_values": None}
    value = document["entity_presence"]
    verdict = value if isinstance(value, str) and value in PRESENCE_VALUES else "invalid"
    heard = document.get("heard_values")
    heard = heard if isinstance(heard, int) and not isinstance(heard, bool) and heard >= 0 else None
    return {"verdict": verdict, "heard_values": heard}


def note_row(*, status: str, candidates: Sequence[str], verdict: Mapping, prompt_tokens: int | None,
             gold_intent: str, gold_empty: bool) -> dict:
    """One arm's note on one row, as the read consumes it. No text."""

    outcome = PB.branch_row_outcome(candidates, gold_intent)
    v = verdict["verdict"]
    return {
        "present": bool(outcome["present"]), "rank": outcome["rank"], "top1": bool(outcome["top1"]),
        "list_size": len(candidates), "status": status, "verdict": v,
        "heard_values": verdict["heard_values"], "prompt_tokens": prompt_tokens,
        "gold_empty": bool(gold_empty),
        # the paired per-row indicators (None outside their subset)
        "none_on_empty": (int(v == "none") if gold_empty else None),
        "none_on_nonempty": (int(v == "none") if not gold_empty else None),
        "present_on_nonempty": (int(v == "present") if not gold_empty else None),
    }


def _indicator(row: Mapping, metric: str) -> int | None:
    value = row[metric]
    return None if value is None else int(value)


def paired_indicator(
    arm_rows: Mapping[str, Mapping], ref_rows: Mapping[str, Mapping], ids: Sequence[str], metric: str,
    *, seed: int = SEED, draws: int = DRAWS,
) -> dict:
    """One arm vs the delivering arm on one 0/1 per-row indicator, PAIRED, whole-utterance cluster
    bootstrap -- the same arithmetic as ``slurp_nx_solver_column_read.paired_metric``."""

    subset = [s for s in ids if _indicator(arm_rows[s], metric) is not None]
    arm_v = {s: _indicator(arm_rows[s], metric) for s in subset}
    ref_v = {s: _indicator(ref_rows[s], metric) for s in subset}
    return _paired_values(arm_v, ref_v, subset, seed=seed, draws=draws)


def _paired_values(arm_v: Mapping[str, float], ref_v: Mapping[str, float], subset: Sequence[str],
                   *, seed: int, draws: int, binary: bool = True) -> dict:
    from speech_aware_evidence_acquisition.analysis.paired import resampled_statistic

    n = len(subset)
    if n == 0:
        return {"n": 0, "mean_arm": None, "mean_delivering": None, "diff": None, "ci95": None,
                **({"b_arm_only": 0, "c_delivering_only": 0, "discordant_share": None, "wilson95": None}
                   if binary else {})}
    diff = {s: arm_v[s] - ref_v[s] for s in subset}
    result = resampled_statistic(
        sample_ids=list(subset), statistic=lambda chosen: sum(diff[s] for s in chosen) / len(chosen),
        seed=seed, n_replicates=draws, ci_level=CI_LEVEL, cluster_of=SC.utterance_id,
    )
    scale = 100.0 if binary else 1.0
    out = {
        "n": n, "mean_arm": sum(arm_v.values()) / n, "mean_delivering": sum(ref_v.values()) / n,
        "diff": scale * result.point_estimate, "ci95": [scale * result.ci_low, scale * result.ci_high],
    }
    if binary:
        b = sum(1 for s in subset if arm_v[s] == 1 and ref_v[s] == 0)
        c = sum(1 for s in subset if arm_v[s] == 0 and ref_v[s] == 1)
        lo, hi = SC.wilson(b, b + c)
        out.update({"b_arm_only": b, "c_delivering_only": c,
                    "discordant_share": (b / (b + c)) if b + c else None,
                    "wilson95": [lo, hi] if b + c else None})
    return out


def _rate(count: int, n: int) -> dict:
    lo, hi = SC.wilson(count, n)
    return {"n": n, "count": count, "rate": (count / n) if n else None, "wilson95": [lo, hi]}


def presence_table(rows: Mapping[str, Mapping], ids: Sequence[str]) -> dict:
    """Precision and recall of ``none`` against the empty-gold label, of ``present`` against non-empty
    gold, the unsure rate and the verdict counts, over the rows that CARRY a verdict. Counts only."""

    counts = Counter(rows[s]["verdict"] for s in ids)
    carried = [s for s in ids if rows[s]["verdict"] != "absent"]
    empty = [s for s in carried if rows[s]["gold_empty"]]
    nonempty = [s for s in carried if not rows[s]["gold_empty"]]
    none_total = sum(1 for s in carried if rows[s]["verdict"] == "none")
    none_tp = sum(1 for s in empty if rows[s]["verdict"] == "none")
    present_total = sum(1 for s in carried if rows[s]["verdict"] == "present")
    present_tp = sum(1 for s in nonempty if rows[s]["verdict"] == "present")
    heard = {
        "empty_gold": [rows[s]["heard_values"] for s in empty if rows[s]["heard_values"] is not None],
        "nonempty_gold": [rows[s]["heard_values"] for s in nonempty if rows[s]["heard_values"] is not None],
    }
    return {
        "verdict_counts": {k: counts.get(k, 0) for k in VERDICTS},
        "rows_carrying_a_verdict": len(carried),
        "none_precision": _rate(none_tp, none_total),
        "none_recall": _rate(none_tp, len(empty)),
        "present_precision": _rate(present_tp, present_total),
        "present_recall": _rate(present_tp, len(nonempty)),
        "unsure_rate": _rate(sum(1 for s in carried if rows[s]["verdict"] == "unsure"), len(carried)),
        "heard_values": {
            k: {"n": len(v), "mean": (sum(v) / len(v)) if v else None} for k, v in heard.items()
        },
    }


def note_table(rows: Mapping[str, Mapping], ids: Sequence[str]) -> dict:
    ranks = Counter(PB._rank_bucket(rows[s]["rank"]) for s in ids)
    sizes = Counter(str(rows[s]["list_size"]) for s in ids)
    statuses = Counter(rows[s]["status"] for s in ids)
    tokens = [rows[s]["prompt_tokens"] for s in ids if rows[s]["prompt_tokens"] is not None]
    n = len(ids)
    return {
        "present": _rate(sum(rows[s]["present"] for s in ids), n),
        "top1": _rate(sum(rows[s]["top1"] for s in ids), n),
        "gold_rank": {b: ranks.get(b, 0) for b in RANK_BUCKETS},
        "list_size": dict(sorted(sizes.items(), key=lambda kv: int(kv[0]))),
        "note_parse_status": dict(sorted(statuses.items())),
        "prompt_tokens": {
            "n": len(tokens), "mean": (sum(tokens) / len(tokens)) if tokens else None,
            "median": statistics.median(tokens) if tokens else None,
            "max": max(tokens) if tokens else None,
        },
    }


# ---------------------------------------------------------------------------
# E2b: the distinction tag (TAG-GRAMMAR-v1.md), pure parts


def validate_tag_set(tag_set: Sequence[str]) -> tuple[str, ...]:
    """The allowed ``E=`` values of one arm. Refuses a value outside the grammar, a duplicate, and a set that
    drops ``none`` or ``some`` (every template asks for both)."""

    values = tuple(tag_set)
    if len(set(values)) != len(values) or not set(values) <= set(TAG_VALUES):
        raise PerceptionColumnReadError(
            f"a tag set may name only {list(TAG_VALUES)} once each; got {list(values)}"
        )
    if not {"none", "some"} <= set(values):
        raise PerceptionColumnReadError(f"a tag set must admit 'none' and 'some'; got {list(values)}")
    return tuple(v for v in TAG_VALUES if v in values)


def parse_tag_set_args(specs: Sequence[str] | None) -> dict[str, tuple[str, ...]]:
    """``--tag-set ARM=none,some,unsure`` (repeatable) -> ``{arm: allowed values}``. Refuses a malformed spec and
    a repeated arm."""

    out: dict[str, tuple[str, ...]] = {}
    for spec in specs or ():
        arm, sep, values = spec.partition("=")
        if not sep or not arm or not values:
            raise PerceptionColumnReadError(f"--tag-set must read ARM=value[,value...]; got {spec!r}")
        if arm in out:
            raise PerceptionColumnReadError(f"--tag-set names arm {arm!r} twice")
        out[arm] = validate_tag_set(values.split(","))
    return out


def _words_ok(text: str, limit: int) -> bool:
    """One or more ASCII words joined by single spaces, no ``;``, at most ``limit`` words."""

    if not text or ";" in text or not text.isascii() or not text.isprintable():
        return False
    tokens = text.split(" ")
    return all(tokens) and len(tokens) <= limit


def _tag(cls: str, verdict: str | None = None, mentions: Sequence[str] = (), reason: str | None = None) -> dict:
    return {"cls": cls, "verdict": verdict, "mentions": tuple(mentions), "reason": reason}


def parse_distinction_tag(distinction: object, *, tag_set: Sequence[str] = DEFAULT_TAG_SET) -> dict:
    """One candidate's ``distinction`` against TAG-GRAMMAR-v1.

    ``{"cls": ok | absent | invalid, "verdict": none | some | unsure | None, "mentions": (...), "reason": str | None}``.
    ``absent``: not a string or no ``E=`` head. ``invalid``: the head is present but the grammar fails -- a value
    outside ``tag_set``, a malformed head, a separator other than ``"; "``, no trailing words, an ``M=`` part after
    anything but ``E=some``, more than three mentions, a mention over four words, trailing words over eight. The
    verdict and the mentions are returned only for ``ok``.
    """

    allowed = validate_tag_set(tag_set)
    if not isinstance(distinction, str) or not distinction.startswith("E="):
        return _tag("absent")
    parts = distinction.split(";")
    head = _TAG_HEAD.fullmatch(parts[0])
    if head is None:
        return _tag("invalid", reason="head_form")
    verdict = head.group(1)
    if verdict not in allowed:
        return _tag("invalid", reason="head_value")
    segments = []
    for part in parts[1:]:
        if not part.startswith(" "):
            return _tag("invalid", reason="separator")
        segments.append(part[1:])
    if not segments:
        return _tag("invalid", reason="no_trailer")
    *middle, trailer = segments
    if trailer.startswith("M="):
        return _tag("invalid", reason="no_trailer")
    mentions = []
    for segment in middle:
        if not segment.startswith("M="):
            return _tag("invalid", reason="middle_not_mention")
        text = segment[2:]
        if not _words_ok(text, MAX_MENTION_WORDS):
            return _tag("invalid", reason="mention_form")
        mentions.append(text)
    if mentions and verdict != "some":
        return _tag("invalid", reason=f"mention_after_{verdict}")
    if len(mentions) > MAX_MENTIONS:
        return _tag("invalid", reason="mention_count")
    if not _words_ok(trailer, MAX_TRAILER_WORDS):
        return _tag("invalid", reason="trailer_form")
    return _tag("ok", verdict, mentions)


def note_tags(note_text: object, tag_set: Sequence[str] = DEFAULT_TAG_SET) -> list[dict]:
    """Every candidate's parsed tag, in candidate order, from one note text parsed in memory. ``[]`` for a note
    that is not a JSON object with a ``candidates`` list. Nothing is kept of the text."""

    if not isinstance(note_text, str):
        return []
    try:
        document = json.loads(note_text)
    except (ValueError, TypeError):
        return []
    candidates = document.get("candidates") if isinstance(document, Mapping) else None
    if not isinstance(candidates, list):
        return []
    return [
        parse_distinction_tag(row.get("distinction") if isinstance(row, Mapping) else None, tag_set=tag_set)
        for row in candidates
    ]


def list_majority(parses: Sequence[Mapping]) -> str:
    """The verdict held by MORE THAN HALF of the ``ok`` candidates; ``split`` when none does; ``invalid`` when no
    candidate is ``ok`` and one is ``invalid``; ``absent`` otherwise."""

    ok = [p["verdict"] for p in parses if p["cls"] == "ok"]
    if not ok:
        return "invalid" if any(p["cls"] == "invalid" for p in parses) else "absent"
    value, count = Counter(ok).most_common(1)[0]
    return value if 2 * count > len(ok) else "split"


def tag_summary(parses: Sequence[Mapping]) -> dict:
    """What the loader keeps per note: the candidates' parses, the rank-1 verdict class and the list majority."""

    rank1 = parses[0] if parses else _tag("absent")
    verdict = rank1["verdict"] if rank1["cls"] == "ok" else rank1["cls"]
    return {"candidates": [dict(p) for p in parses], "rank1": dict(rank1), "rank1_verdict": verdict,
            "majority": list_majority(parses)}


def _none_auc(verdicts: Mapping[str, str], gold_empty: Mapping[str, bool], ids: Sequence[str],
              *, seed: int, draws: int) -> dict:
    """AUC of ``E=none`` (none 2 > unsure 1 > some 0) for empty gold over the rows that carry a verdict, with a
    whole-utterance cluster bootstrap CI95. Closed-form on the three score levels, so each draw is a bincount."""

    import numpy as np

    carried = [s for s in ids if verdicts[s] in _NONE_SCORE]
    n_pos = sum(1 for s in carried if gold_empty[s])
    n_neg = len(carried) - n_pos
    if n_pos == 0 or n_neg == 0:
        return {"n": len(carried), "auc": None, "ci95": None}
    clusters = sorted({SC.utterance_id(s) for s in carried})
    index = {c: k for k, c in enumerate(clusters)}
    table = np.zeros((len(clusters), 6), dtype=np.float64)  # cluster x (level x label)
    for s in carried:
        table[index[SC.utterance_id(s)], _NONE_SCORE[verdicts[s]] * 2 + int(gold_empty[s])] += 1

    def auc_of(counts):
        grid = counts.reshape(3, 2)
        pos, neg = grid[:, 1], grid[:, 0]
        total_pos, total_neg = pos.sum(), neg.sum()
        if total_pos == 0 or total_neg == 0:
            return None
        score = sum(
            (1.0 if i > j else 0.5 if i == j else 0.0) * pos[i] * neg[j] for i in range(3) for j in range(3)
        )
        return float(score / (total_pos * total_neg))

    point = auc_of(table.sum(axis=0))
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(clusters), size=(draws, len(clusters)))
    values = [a for a in (auc_of(np.bincount(row, minlength=len(clusters)) @ table) for row in picks) if a is not None]
    tail = 100.0 * (1.0 - CI_LEVEL) / 2.0
    ci = [float(np.percentile(values, tail)), float(np.percentile(values, 100.0 - tail))] if values else None
    return {"n": len(carried), "auc": point, "ci95": ci}


def tag_verdict_table(verdicts: Mapping[str, str], gold_empty: Mapping[str, bool], ids: Sequence[str],
                      *, seed: int = SEED, draws: int = DRAWS) -> dict:
    """The presence read of one verdict source (rank-1 or list majority): verdict counts; AUC, precision and
    recall of ``none`` against empty gold; precision and recall of ``some`` against non-empty gold; the ``unsure``
    rate by gold class. Recall is given over the rows that carry a verdict (parity with the key-path reader) and over
    ALL rows of the gold class (a row without a tag is a miss). Counts only."""

    ids = list(ids)
    counts = Counter(verdicts[s] for s in ids)
    carried = [s for s in ids if verdicts[s] in TAG_VALUES]
    empty_all = [s for s in ids if gold_empty[s]]
    nonempty_all = [s for s in ids if not gold_empty[s]]
    empty = [s for s in carried if gold_empty[s]]
    nonempty = [s for s in carried if not gold_empty[s]]
    none_total = sum(1 for s in carried if verdicts[s] == "none")
    none_tp = sum(1 for s in empty if verdicts[s] == "none")
    some_total = sum(1 for s in carried if verdicts[s] == "some")
    some_tp = sum(1 for s in nonempty if verdicts[s] == "some")
    return {
        "verdict_counts": {k: counts.get(k, 0) for k in TAG_VERDICTS},
        "rows_carrying_a_verdict": len(carried),
        "none_auc": _none_auc(verdicts, gold_empty, ids, seed=seed, draws=draws),
        "none_precision": _rate(none_tp, none_total),
        "none_recall": _rate(none_tp, len(empty)),
        "none_recall_all_rows": _rate(none_tp, len(empty_all)),
        "some_precision": _rate(some_tp, some_total),
        "some_recall": _rate(some_tp, len(nonempty)),
        "some_recall_all_rows": _rate(some_tp, len(nonempty_all)),
        "unsure_rate": _rate(sum(1 for s in carried if verdicts[s] == "unsure"), len(carried)),
        "unsure_by_gold": {
            "empty_gold": _rate(sum(1 for s in empty if verdicts[s] == "unsure"), len(empty)),
            "nonempty_gold": _rate(sum(1 for s in nonempty if verdicts[s] == "unsure"), len(nonempty)),
        },
    }


def tag_parse_table(summaries: Mapping[str, Mapping], ids: Sequence[str]) -> dict:
    """Parse classes on the rank-1 candidate (rows) and over every candidate, with the invalid reasons."""

    rank1 = Counter(summaries[s]["rank1"]["cls"] for s in ids)
    every, reasons, candidates = Counter(), Counter(), 0
    for s in ids:
        for p in summaries[s]["candidates"]:
            candidates += 1
            every[p["cls"]] += 1
            if p["reason"]:
                reasons[p["reason"]] += 1
    return {
        "rank1": {k: rank1.get(k, 0) for k in TAG_CLASSES},
        "every_candidate": {"n": candidates, **{k: every.get(k, 0) for k in TAG_CLASSES}},
        "invalid_reasons": dict(sorted(reasons.items())),
    }


def _normaliser():
    from speech_aware_evidence_acquisition.rails.slurp_projection_v3 import normalize_filler_p2

    return normalize_filler_p2


def mention_table(offered: Mapping[str, Sequence[str]], gold: Mapping[str, Mapping], ids: Sequence[str],
                  *, ok_rows: Mapping[str, bool]) -> dict:
    """Heard-mention containment and option precision for one source of offered ``M=`` surfaces.

    Containment: the share of gold entities whose normalised surface equals an offered normalised surface of the
    same row (per slot type too). Option precision: the share of offered (row-distinct) normalised surfaces that equal
    a gold entity's normalised surface of the row, with the matched options split by the matched gold slot type (a
    mention carries no type). The surface normalisation is the registered delivery normaliser's filler normalisation.
    Counts and slot TYPE names only."""

    norm = _normaliser()
    gold_n = gold_ok = contained = contained_ok = offered_n = matched = offered_empty = rows_offering = 0
    by_type: dict[str, list[int]] = {}
    matched_by_type: Counter = Counter()
    for sid in ids:
        entities = gold[sid]["entities"]
        surfaces = list(dict.fromkeys(norm(m) for m in offered[sid]))
        offered_set = set(surfaces)
        gold_type: dict[str, str] = {}
        for e in entities:
            gold_type.setdefault(norm(e.filler), e.type)
        if surfaces:
            rows_offering += 1
        for e in entities:
            hit = norm(e.filler) in offered_set
            gold_n += 1
            contained += int(hit)
            if ok_rows[sid]:
                gold_ok += 1
                contained_ok += int(hit)
            slot = by_type.setdefault(e.type, [0, 0])
            slot[0] += 1
            slot[1] += int(hit)
        for surface in surfaces:
            offered_n += 1
            if not entities:
                offered_empty += 1
            if surface in gold_type:
                matched += 1
                matched_by_type[gold_type[surface]] += 1
    return {
        "rows_offering_any": rows_offering,
        "gold_entities": gold_n, "containment": _rate(contained, gold_n),
        "gold_entities_on_ok_rows": gold_ok, "containment_on_ok_rows": _rate(contained_ok, gold_ok),
        "offered_options": offered_n, "option_precision": _rate(matched, offered_n),
        "offered_options_on_empty_gold_rows": offered_empty,
        "containment_by_slot_type": {
            t: {"gold_entities": n, **_rate(c, n)} for t, (n, c) in sorted(by_type.items())
        },
        "matched_options_by_slot_type": dict(sorted(matched_by_type.items())),
    }


def distinction_tag_table(summaries: Mapping[str, Mapping], gold: Mapping[str, Mapping], ids: Sequence[str],
                          tag_set: Sequence[str], *, seed: int = SEED, draws: int = DRAWS) -> dict:
    """The whole E2b read of one arm."""

    ids = list(ids)
    gold_empty = {s: not gold[s]["entities"] for s in ids}
    rank1 = {s: summaries[s]["rank1_verdict"] for s in ids}
    majority = {s: summaries[s]["majority"] for s in ids}
    ok1 = {s: summaries[s]["rank1"]["cls"] == "ok" for s in ids}
    rank1_mentions = {s: summaries[s]["rank1"]["mentions"] if ok1[s] else () for s in ids}
    union_mentions = {
        s: tuple(m for p in summaries[s]["candidates"] if p["cls"] == "ok" for m in p["mentions"]) for s in ids
    }
    return {
        "tag_set": list(tag_set),
        "grammar": TAG_GRAMMAR_RELPATH,
        "parse": tag_parse_table(summaries, ids),
        "rank1": tag_verdict_table(rank1, gold_empty, ids, seed=seed, draws=draws),
        "majority": tag_verdict_table(majority, gold_empty, ids, seed=seed, draws=draws),
        "mentions": {
            "rank1": mention_table(rank1_mentions, gold, ids, ok_rows=ok1),
            "list_union": mention_table(
                union_mentions, gold, ids,
                ok_rows={s: any(p["cls"] == "ok" for p in summaries[s]["candidates"]) for s in ids}),
        },
    }


def read_columns(
    notes: Mapping[str, Mapping[str, Mapping]], solver_texts: Mapping[str, Mapping[str, str]],
    gold: Mapping[str, Mapping], *, arm_ids: Sequence[str], delivering: str, twin: str | None = None,
    normalised_solver_texts: Mapping[str, Mapping[str, str]] | None = None,
    tag_sets: Mapping[str, Sequence[str]] | None = None,
    seed: int = SEED, draws: int = DRAWS,
) -> dict:
    """The whole Perception column read.

    ``notes[arm][sample_id]`` is the dict :func:`load_sealed_columns` builds (``status``,
    ``candidates``, ``verdict``, ``tag``, ``prompt_tokens``, no text); ``solver_texts[arm][sample_id]`` the arm's
    level-2 first-visit Solver answer; ``gold[sample_id]`` carries ``intent`` and ``entities``. ``tag_sets[arm]``
    is the arm's allowed ``E=`` values (default ``none,some``); it is reported with the E2b tables, which are read
    only for arms whose notes carry a ``tag`` summary.
    """

    arm_ids = list(arm_ids)
    if delivering not in arm_ids:
        raise PerceptionColumnReadError("the delivering arm is not among the arms")
    tag_sets = dict(tag_sets or {})
    stray = sorted(set(tag_sets) - set(arm_ids))
    if stray:
        raise PerceptionColumnReadError(f"a tag set names arm(s) {stray} that the run does not have")
    tag_sets = {arm: validate_tag_set(tag_sets.get(arm, DEFAULT_TAG_SET)) for arm in arm_ids}
    ids = sorted(notes[delivering])
    for arm in arm_ids:
        if sorted(notes[arm]) != ids or sorted(solver_texts[arm]) != ids:
            raise PerceptionColumnReadError(f"arm {arm!r} does not cover the delivering arm's rows")
    missing = [s for s in ids if s not in gold]
    if missing:
        raise PerceptionColumnReadError(f"{len(missing)} roster ids are absent from the gold")
    scored = {
        arm: {
            sid: note_row(
                status=notes[arm][sid]["status"], candidates=notes[arm][sid]["candidates"],
                verdict=notes[arm][sid]["verdict"], prompt_tokens=notes[arm][sid]["prompt_tokens"],
                gold_intent=gold[sid]["intent"], gold_empty=not gold[sid]["entities"],
            )
            for sid in ids
        }
        for arm in arm_ids
    }
    subsets = {
        "all": ids,
        "empty_gold": [s for s in ids if not gold[s]["entities"]],
        "nonempty_gold": [s for s in ids if gold[s]["entities"]],
    }
    arms_out = {}
    for arm in arm_ids:
        rows = scored[arm]
        paired = {}
        if arm != delivering:
            for metric, subset_name, _higher in (*NOTE_METRICS, *PRESENCE_METRICS):
                paired[metric] = paired_indicator(
                    rows, scored[delivering], subsets[subset_name], metric, seed=seed, draws=draws,
                )
            tokens = [s for s in ids
                      if rows[s]["prompt_tokens"] is not None and scored[delivering][s]["prompt_tokens"] is not None]
            paired["prompt_tokens"] = _paired_values(
                {s: float(rows[s]["prompt_tokens"]) for s in tokens},
                {s: float(scored[delivering][s]["prompt_tokens"]) for s in tokens},
                tokens, seed=seed, draws=draws, binary=False,
            )
            paired["list_size"] = _paired_values(
                {s: float(rows[s]["list_size"]) for s in ids},
                {s: float(scored[delivering][s]["list_size"]) for s in ids},
                ids, seed=seed, draws=draws, binary=False,
            )
        summaries = {s: notes[arm][s].get("tag") for s in ids}
        arms_out[arm] = {
            "role": ("delivering" if arm == delivering else "twin" if arm == twin else "candidate"),
            "notes": note_table(rows, ids),
            "entity_presence": presence_table(rows, ids),
            "paired_vs_delivering": paired,
            "distinction_tag": (
                distinction_tag_table(summaries, gold, ids, tag_sets[arm], seed=seed, draws=draws)
                if all(v is not None for v in summaries.values()) else None
            ),
        }
    solver_gold = {sid: {"entities": gold[sid]["entities"]} for sid in ids}
    solver = SC.read_columns(
        solver_texts, solver_gold, arm_ids=arm_ids, delivering=delivering, twin=twin,
        normalised_texts=normalised_solver_texts, seed=seed, draws=draws,
    )
    return {
        "read_id": READ_ID, "recipe": RECIPE, "schema_version": SCHEMA_VERSION, "status": "DESCRIPTIVE",
        "rows": len(ids), "rows_empty_gold": len(subsets["empty_gold"]),
        "rows_nonempty_gold": len(subsets["nonempty_gold"]),
        "bootstrap": {"draws": draws, "seed": seed, "ci_level": CI_LEVEL,
                      "cluster": "whole utterance (first three colon segments of the sample id)"},
        "arm_order": arm_ids, "delivering_arm": delivering, "twin_arm": twin,
        "tag_sets": {arm: list(values) for arm, values in tag_sets.items()},
        "arms": arms_out,
        "solver_column": {
            "view": "level-2 first-visit Solver answer of each arm over that arm's own note",
            "primary_metric": solver["primary_metric"], "primary_view": solver["primary_view"],
            "mechanical_screen": solver["mechanical_screen"], "arms": solver["arms"],
            "raw_diagnostic": solver["raw_diagnostic"], "raw_vs_normalised": solver["raw_vs_normalised"],
        },
    }


# ---------------------------------------------------------------------------
# the sealed-run side


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_sealed_columns(outputs_rows: Sequence[Mapping], trace_records: Mapping[str, Mapping],
                        *, tag_sets: Mapping[str, Sequence[str]] | None = None) -> dict:
    """Every arm's note metrics and level-2 Solver answer for every row of a sealed Perception template
    column. ``outputs_rows`` / ``trace_records`` are a verified bundle's own. Refuses a row whose receipt is
    not the Perception template (v4, level 2) shape, whose arm group differs from the first row's, or whose
    trace pairs disagree with the sealed contacts' digests. ``tag_sets[arm]`` is the arm's allowed ``E=`` values
    for the E2b parse (default ``none,some``); a set naming an arm the run does not have is refused."""

    from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
        parse_perception_branch_note, validate_perception_branch_receipt,
    )

    arm_ids = templates = delivering = twin = None
    allowed: dict[str, tuple[str, ...]] = {}
    notes: dict[str, dict[str, dict]] = {}
    solver_texts: dict[str, dict[str, str]] = {}
    normaliser_ids: dict[str, str | None] = {}
    for row in outputs_rows:
        sid = row.get("sample_id")
        if not isinstance(sid, str) or not sid:
            raise PerceptionColumnReadError("an outputs row has no sample id")
        episode = row.get("native_episode_receipt")
        block = episode.get("perception_branches") if isinstance(episode, Mapping) else None
        if not isinstance(block, Mapping) or block.get("schema") != V4_SCHEMA or block.get("level") != 2:
            raise PerceptionColumnReadError(
                f"{sid}: perception_branches is not a level-2 {V4_SCHEMA} template receipt; this reader "
                "reads Perception template columns only"
            )
        branch_rows = block["branches"]
        row_arm_ids = tuple(item["branch_id"] for item in branch_rows)
        row_twin = next((i["branch_id"] for i in branch_rows if i.get("replicate_of")), None)
        validate_perception_branch_receipt(
            block, branch_ids=list(row_arm_ids), delivered_branch_id=row_arm_ids[-1],
            twin_branch_id=row_twin, phase_id=block["phase_id"], level=2,
            error_type=PerceptionColumnReadError,
        )
        row_templates = [item["instruction_template"] for item in branch_rows]
        if arm_ids is None:
            arm_ids, templates, delivering, twin = row_arm_ids, row_templates, row_arm_ids[-1], row_twin
            stray = sorted(set(tag_sets or {}) - set(arm_ids))
            if stray:
                raise PerceptionColumnReadError(f"a tag set names arm(s) {stray} that the run does not have")
            allowed = {arm: validate_tag_set((tag_sets or {}).get(arm, DEFAULT_TAG_SET)) for arm in arm_ids}
            notes = {arm: {} for arm in arm_ids}
            solver_texts = {arm: {} for arm in arm_ids}
        elif (row_arm_ids, row_templates, row_twin) != (arm_ids, templates, twin):
            raise PerceptionColumnReadError(f"{sid}: the arm group or its templates differ from the first row's")
        deliver_receipt = episode.get("deliver_normaliser")
        normaliser_ids[sid] = (
            deliver_receipt.get("normaliser_id") if isinstance(deliver_receipt, Mapping) else None
        )
        request_of: dict[str, tuple[str, str, str]] = {}
        for visit in episode.get("role_visits") or ():
            if not isinstance(visit, Mapping) or visit.get("stage") not in ("perception", "solver"):
                continue
            execution = visit.get("execution_receipt")
            for contact in (execution.get("contacts") if isinstance(execution, Mapping) else None) or ():
                request_of[contact["agent_contact_id"]] = (
                    contact["request_id"], contact["request_sha256"], contact["response_text_sha256"],
                )

        def trace_text(contact_id: str, what: str) -> tuple[str, Mapping]:
            found = request_of.get(contact_id)
            if found is None:
                raise PerceptionColumnReadError(f"{sid}: {what} names a contact the row did not record")
            request_id, request_sha, response_sha = found
            request = trace_records.get(f"{request_id}/request")
            response = trace_records.get(f"{request_id}/response")
            if not isinstance(request, Mapping) or not isinstance(response, Mapping):
                raise PerceptionColumnReadError(f"{sid}: {what} has no trace pair")
            text = response.get("text")
            if (
                not isinstance(text, str) or request.get("payload_sha256") != request_sha
                or _sha(text) != response_sha
            ):
                raise PerceptionColumnReadError(f"{sid}: {what} trace differs from its sealed contact")
            return text, response

        for item in branch_rows:
            arm = item["branch_id"]
            text, response = trace_text(item["contact_id"], f"branch {arm!r} Perception contact")
            if _sha(text) != item["note_sha256"]:
                raise PerceptionColumnReadError(f"{sid}: branch {arm!r} note differs from its sealed hash")
            status, candidates, _raw = parse_perception_branch_note(text)
            if status != item["note_parse_status"] or list(candidates) != list(item["candidate_intent_ids"]):
                raise PerceptionColumnReadError(f"{sid}: branch {arm!r} note differs from its sealed parse")
            usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
            tokens = usage.get("prompt_tokens")
            notes[arm][sid] = {
                "status": status, "candidates": tuple(candidates),
                "verdict": entity_presence_of(text),
                "tag": tag_summary(note_tags(text, allowed[arm])),
                "prompt_tokens": tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else None,
            }
            del text
            answer, _ = trace_text(item["solver_contact_id"], f"branch {arm!r} Solver contact")
            solver_texts[arm][sid] = answer
    if arm_ids is None:
        raise PerceptionColumnReadError("no row of the run carries a Perception template receipt")
    return {"arm_ids": arm_ids, "templates": templates, "delivering": delivering, "twin": twin,
            "tag_sets": allowed, "notes": notes, "solver_texts": solver_texts, "normaliser_ids": normaliser_ids}


# ---------------------------------------------------------------------------
# rendering


def _pct(value: float | None) -> str:
    return "-" if value is None else f"{100.0 * value:.2f}"


def _ci(p: Mapping, key: str = "ci95", fmt: str = "{:+.2f}") -> str:
    return "-" if p[key] is None else "[" + ", ".join(fmt.format(x) for x in p[key]) + "]"


def render(report: Mapping) -> str:
    order, arms = report["arm_order"], report["arms"]
    lines = [
        f"# {report['read_id']} tables ({report['schema_version']})", "",
        f"{report['rows']} rows ({report['rows_empty_gold']} empty-gold, {report['rows_nonempty_gold']} "
        f"non-empty-gold). Delivering arm `{report['delivering_arm']}`"
        + (f", twin `{report['twin_arm']}`" if report["twin_arm"] else "")
        + f". Bootstrap: {report['bootstrap']['draws']} draws, seed {report['bootstrap']['seed']}, "
        "whole-utterance clusters, CI95. DESCRIPTIVE; development numbers.", "",
        "## Perception note: marginal rates (%)", "",
        "| arm | role | gold on list | top-1 | mean prompt tokens | mean list size |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for arm in order:
        n = arms[arm]["notes"]
        sizes = n["list_size"]
        total = sum(sizes.values())
        mean_size = sum(int(k) * v for k, v in sizes.items()) / total if total else None
        tokens = n["prompt_tokens"]["mean"]
        lines.append(
            f"| {arm} | {arms[arm]['role']} | {_pct(n['present']['rate'])} | {_pct(n['top1']['rate'])} | "
            f"{'-' if tokens is None else f'{tokens:.1f}'} | {'-' if mean_size is None else f'{mean_size:.2f}'} |"
        )
    lines += ["", "## Perception note: paired difference vs the delivering arm", "",
              "| arm | metric | n | diff | CI95 | b (arm only) | c (delivering only) | Wilson95 |",
              "| --- | --- | ---: | ---: | --- | ---: | ---: | --- |"]
    for arm in order:
        for metric, p in arms[arm]["paired_vs_delivering"].items():
            diff = "-" if p["diff"] is None else f"{p['diff']:+.2f}"
            b, c = p.get("b_arm_only", "-"), p.get("c_delivering_only", "-")
            wil = _ci(p, "wilson95", "{:.3f}") if "wilson95" in p else "-"
            lines.append(f"| {arm} | {metric} | {p['n']} | {diff} | {_ci(p)} | {b} | {c} | {wil} |")
    lines += ["", "## Entity-presence verdict (rows carrying one)", "",
              "| arm | present / none / unsure / invalid / absent | none precision | none recall | "
              "present precision | present recall | unsure rate |",
              "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm in order:
        e = arms[arm]["entity_presence"]
        vc = e["verdict_counts"]
        lines.append(
            f"| {arm} | {' / '.join(str(vc[k]) for k in VERDICTS)} | {_pct(e['none_precision']['rate'])} | "
            f"{_pct(e['none_recall']['rate'])} | {_pct(e['present_precision']['rate'])} | "
            f"{_pct(e['present_recall']['rate'])} | {_pct(e['unsure_rate']['rate'])} |"
        )
    tagged = [arm for arm in order if arms[arm].get("distinction_tag")]
    if tagged:
        lines += ["", "## Distinction tag (E2b): parse classes (rank-1 rows; every candidate)", "",
                  "| arm | tag set | rank-1 ok / absent / invalid | every candidate ok / absent / invalid | invalid reasons |",
                  "| --- | --- | --- | --- | --- |"]
        for arm in tagged:
            t = arms[arm]["distinction_tag"]
            r1, ev = t["parse"]["rank1"], t["parse"]["every_candidate"]
            lines.append(
                f"| {arm} | {','.join(t['tag_set'])} | {' / '.join(str(r1[k]) for k in TAG_CLASSES)} | "
                f"{' / '.join(str(ev[k]) for k in TAG_CLASSES)} (of {ev['n']}) | "
                f"{', '.join(f'{k} {v}' for k, v in t['parse']['invalid_reasons'].items()) or '-'} |"
            )
        for source, title in (("rank1", "rank-1 candidate"), ("majority", "list majority")):
            lines += ["", f"## Distinction tag (E2b): presence verdict on the {title} (%)", "",
                      "| arm | " + " / ".join(TAG_VERDICTS) + " | none AUC [CI95] | none precision | none recall | "
                      "some precision | some recall | unsure rate | unsure on empty / non-empty gold |",
                      "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
            for arm in tagged:
                v = arms[arm]["distinction_tag"][source]
                auc = v["none_auc"]
                auc_text = "-" if auc["auc"] is None else (
                    f"{auc['auc']:.3f} " + ("-" if auc["ci95"] is None else f"[{auc['ci95'][0]:.3f}, {auc['ci95'][1]:.3f}]"))
                ub = v["unsure_by_gold"]
                lines.append(
                    f"| {arm} | {' / '.join(str(v['verdict_counts'][k]) for k in TAG_VERDICTS)} | {auc_text} | "
                    f"{_pct(v['none_precision']['rate'])} | {_pct(v['none_recall']['rate'])} | "
                    f"{_pct(v['some_precision']['rate'])} | {_pct(v['some_recall']['rate'])} | "
                    f"{_pct(v['unsure_rate']['rate'])} | {_pct(ub['empty_gold']['rate'])} / {_pct(ub['nonempty_gold']['rate'])} |"
                )
        lines += ["", "## Distinction tag (E2b): heard mentions", "",
                  "| arm | source | rows offering | gold entities | containment | option precision | offered options | by slot type (containment) |",
                  "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |"]
        for arm in tagged:
            for source in ("rank1", "list_union"):
                m = arms[arm]["distinction_tag"]["mentions"][source]
                by_type = ", ".join(f"{t} {_pct(v['rate'])} ({v['n']})" for t, v in m["containment_by_slot_type"].items())
                lines.append(
                    f"| {arm} | {source} | {m['rows_offering_any']} | {m['gold_entities']} | "
                    f"{_pct(m['containment']['rate'])} | {_pct(m['option_precision']['rate'])} | "
                    f"{m['offered_options']} | {by_type or '-'} |"
                )
    solver = report["solver_column"]
    lines += ["", f"## Level-2 Solver column (primary `{solver['primary_metric']}`, normalised view)", "",
              "| arm | role | exact set | empty-gold false fill | non-empty exact |",
              "| --- | --- | ---: | ---: | ---: |"]
    for arm in order:
        m = solver["arms"][arm]["marginal"]
        lines.append(
            f"| {arm} | {solver['arms'][arm]['role']} | {_pct(m['exact_set']['rate'])} | "
            f"{_pct(m['empty_gold_false_fill']['rate'])} | {_pct(m['nonempty_exact']['rate'])} |"
        )
    lines += ["", "| arm | metric | n | diff pp | CI95 pp | b | c |", "| --- | --- | ---: | ---: | --- | ---: | ---: |"]
    for arm in order:
        for metric, p in solver["arms"][arm]["paired_vs_delivering"].items():
            diff = "-" if p["diff_pp"] is None else f"{p['diff_pp']:+.2f}"
            lines.append(
                f"| {arm} | {metric} | {p['n']} | {diff} | {_ci(p, 'ci95_pp')} | {p['b_arm_only']} | "
                f"{p['c_delivering_only']} |"
            )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI


def load_gold(lock, data_root: Path, split: str) -> dict:
    """Gold (intent and entities) per sample id through the governed SLURP loaders; the test split is
    refused."""

    if split not in ("train", "devel"):
        raise PerceptionColumnReadError(f"split {split!r} is not read here (the test split is closed)")
    from speech_aware_evidence_acquisition.data.slurp import load_slurp_split
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    records = load_slurp_split(lock, data_root, split, workers=4)
    return {
        r.sample_id: {"intent": r.intent, "entities": tuple(SlotEntity(e.type, e.filler) for e in r.entities)}
        for r in records
    }


def build(args) -> dict:
    from speech_aware_evidence_acquisition.core.bundle import verify_bundle
    from speech_aware_evidence_acquisition.data.lock import load_lock

    data_root = Path(args.data_root)
    directory = data_root / "runs" / args.run_id / args.attempt_id
    if not directory.is_dir():
        raise PerceptionColumnReadError(f"no sealed attempt directory at {directory}")
    manifest = directory / f"{args.run_id}.run-manifest.json"
    bundle = verify_bundle(manifest)
    tag_sets = parse_tag_set_args(getattr(args, "tag_set", None))
    sealed = load_sealed_columns(bundle.outputs_rows, bundle.trace_records, tag_sets=tag_sets)
    gold = load_gold(load_lock(Path(args.lock)), data_root, args.split)
    normalised = SC.normalise_texts(sealed["solver_texts"], sealed["normaliser_ids"])
    report = read_columns(
        sealed["notes"], sealed["solver_texts"], gold, arm_ids=sealed["arm_ids"],
        delivering=sealed["delivering"], twin=sealed["twin"], normalised_solver_texts=normalised,
        tag_sets=sealed["tag_sets"], seed=args.seed, draws=args.draws,
    )
    report["inputs"] = {
        "run_id": args.run_id, "attempt_id": args.attempt_id, "split": args.split,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "templates": dict(zip(sealed["arm_ids"], sealed["templates"], strict=True)),
        "deliver_normaliser_ids": dict(sorted(Counter(str(v) for v in sealed["normaliser_ids"].values()).items())),
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-root", default=DEFAULT_DATA_ROOT)
    parser.add_argument("--lock", default=str(REPO_ROOT / DEFAULT_LOCK))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    parser.add_argument("--split", choices=("train", "devel"), required=True)
    parser.add_argument("--draws", type=int, default=DRAWS)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--tag-set", action="append", default=[], metavar="ARM=VALUES",
                        help="the E= values an arm's template allows, e.g. p3=none,some,unsure (default none,some "
                             "for every arm; a value the arm does not allow parses as invalid); repeatable")
    args = parser.parse_args(argv)
    report = build(args)
    out_dir = Path(args.out_dir) if args.out_dir else Path(args.data_root) / "analysis" / READ_ID / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    texts = {"report.json": json.dumps(report, indent=2, sort_keys=True) + "\n", "tables.md": render(report)}
    for name, text in texts.items():
        (out_dir / name).write_text(text, encoding="utf-8", newline="\n")
    print("wrote", out_dir)
    print(json.dumps({n: _sha(t) for n, t in sorted(texts.items())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
