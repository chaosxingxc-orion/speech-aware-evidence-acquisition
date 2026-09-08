#!/usr/bin/env python3
"""Decide KC-E1f against its preregistered rule, from three sealed manifests.

Exposure row ``SAEA-E21-KC-E1F-VERDICT-V1`` (``model-free-check``), registered and
committed before the first sealed byte was opened. **Zero model, GPU, tool,
embedder, tokenizer, network, audio-decode and paid-API contacts.** Reference
transcripts and ``wer_tags`` are reached only through the registered scoring
path's own loaders, and only inside ``scripts/e21_window_pairing_read.py``, which
produced the per-window rows this script consumes; nothing here opens a reference.

The rule is
``docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md``
section 5, quoted verbatim in the verdict note and applied here as written:

* **primary** -- the call-clustered CI90 LOWER bound on the pooled ConEC-mirror
  PERSON entity-WER REDUCTION (comparator minus KC-E1f, so a positive value means
  fewer errors) must be ``> 0`` against the sealed comparator AND against the form
  twin KU-E1fc;
* **guards** -- delivery integrity (a CONSTRUCTION check that aborts the read),
  corpus-WER non-inferiority (call-clustered CI90 UPPER bound on
  ``KC-E1f - comparator`` ``<= 0``), numeric-value accuracy not worse at the
  CALL-pooled figure, over-generation not worse (insertions per reference word),
  and the negation-critical rate as an advisory point estimate;
* **NULL** if either primary lower bound includes 0; **HARMFUL** if any guard
  fails.

Three things run before any contrast, and each of them refuses:

1. the **identity anchor** -- each arm's 1,593 per-window rows must re-aggregate to
   that arm's own sealed numbers, checked by ``scripts/e21_window_pairing_read.py``
   against a committed profile, and extended here to EVERY class of the ConEC
   mirror's ``by_entity_type`` against each arm's own committed score receipt;
2. the **section 5.1 attribution** -- every normalized deletion/insertion move
   against the comparator must be carried by a substituted span
   (``scripts/e21_kc_e1f_normalization_attribution.py``), including the identity
   ``(I - D) delta == normalized hypothesis-length delta`` re-derived here from the
   anchors' own operation counts;
3. the **delivery-integrity construction guard** -- identical raw whitespace-token
   counts, window by window and call by call, from both flights' own receipts and
   re-checked by the attribution instrument on the sealed bytes.

The pairing unit is the fixed 90-second window and the bootstrap cluster is the
call (44) -- the owner's 2026-09-06 ruling, preregistration section 5. Every
headline statistic is a POOLED ratio, ``sum(numerator) / sum(denominator)`` over
the resampled units, through ``analysis.paired.resampled_statistic(cluster_of=...)``
at seed 20260903, 10,000 replicates, CI90. The window-level interval is reported
beside it and labelled optimistic; the saves / harms / ties and exact sign test at
n = 1,593 come from ``analysis.paired.paired_contrast`` on the per-window rates,
whose own bootstrap is the MEAN of per-window differences and is never the
decision interval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402
from speech_aware_evidence_acquisition.analysis import paired  # noqa: E402
from speech_aware_evidence_acquisition.reproduction import (  # noqa: E402
    conec_entity_scoring as conec,
)

RESULT_SCHEMA = "saea-e21-kc-e1f-verdict-v1"
EXPOSURE_ROW = "SAEA-E21-KC-E1F-VERDICT-V1"
DECIDES = "SAEA-E21-KC-E1F-REPAIR-44-V1"
PREREGISTRATION = (
    "docs/readiness/2026-09-07-e21-kc-e1f-brief-repair-pass-v1-preregistration.md"
)

#: Arm slug -> sealed run id. ``comparator`` is the sealed direct baseline every
#: Earnings mechanism cell pairs against by name, and it is ALSO both repair arms'
#: pass 1 by construction -- the bytes they edited.
ARM_RUNS = {
    "comparator": "SAEA-E21-FULL44-DIRECT-BASELINE-V2",
    "ku-e1fc": "SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1",
    "kc-e1f": "SAEA-E21-KC-E1F-REPAIR-44-V1",
}

TREATED_ARMS = ("kc-e1f", "ku-e1fc")

#: ``(label, left, right, reading)`` with the module convention
#: ``delta = right - left``; ``improvement`` re-signs that so a positive number
#: always means the RIGHT arm is better on the metric.
CONTRASTS = (
    (
        "total",
        "comparator",
        "kc-e1f",
        "KC-E1f vs the sealed comparator -- repair-pass-PLUS-brief: it moves both "
        "that a second contact exists and that the contact carries the real brief",
    ),
    (
        "form",
        "comparator",
        "ku-e1fc",
        "KU-E1fc vs the sealed comparator -- the second contact and the repair form "
        "alone, carrying a token-matched placebo instead of the brief",
    ),
    (
        "content",
        "ku-e1fc",
        "kc-e1f",
        "KC-E1f vs KU-E1fc -- the one factor, the brief's CONTENT, at an identical "
        "contact, instruction, frame, predecessor and delivery rule",
    ),
)

#: ConEC Table 2 publishes these eight; the rest of the mirror's typed classes are
#: reported beside them, in full, because the preregistration's section 5 asks for
#: PERSON first and "all eight published classes with their reference-word counts"
#: and this verdict publishes every class the scorer reports rather than a chosen
#: subset.
PUBLISHED_CLASSES = ("PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "NORP", "FAC")

#: The window-level interval is an explicitly OPTIMISTIC bound -- 1,593 units
#: treated as independent, which they are not -- and it decides nothing. It is
#: computed for the primary, the guards and the classes that carry real weight.
OPTIMISTIC_METRICS = frozenset(
    {
        "entity_wer_PERSON",
        "entity_wer_ORG",
        "corpus_wer",
        "non_entity_wer",
        "insertions_per_reference_word",
        "numeric_accuracy_window",
        "negation_critical_rate",
    }
)


def _bucket_reader(bucket: str):
    def read(row: dict) -> tuple[int, int]:
        counts = row["entity_class_counts"][bucket]
        return counts[0] + counts[1], counts[2]

    return read


def _window_metrics(classes: tuple[str, ...]) -> dict[str, tuple]:
    """name -> (row reader, +1 if a HIGHER pooled ratio is better, note).

    Every one of these is a pooled ratio: sum the counts over the resampled units,
    then divide ONCE. Never an average of per-window rates.
    """

    metrics: dict[str, tuple] = {
        "corpus_wer": (
            lambda row: (
                row["substitutions"] + row["deletions"] + row["insertions"],
                row["reference_words"],
            ),
            -1,
            "pooled (S + D + I) / reference words -- the ConEC __ALL__ bucket and "
            "asr-wer-whisper agree on it",
        ),
        "non_entity_wer": (
            _bucket_reader(conec.NON_ENTITY_BUCKET),
            -1,
            "pooled (S + D) / non-entity reference words; insertions are "
            "unattributable and excluded",
        ),
        "unlabelled_wer": (
            _bucket_reader(conec.UNLABELLED_BUCKET),
            -1,
            "pooled (S + D) / unlabelled reference words -- the "
            "normalization-transfer residue, reported not claimed",
        ),
        "numeric_accuracy_window": (
            lambda row: (row["numeric_matched"], row["numeric_expected"]),
            +1,
            "WINDOW-pooled numeric-value accuracy -- a DIAGNOSTIC; the guard is the "
            "call-pooled figure",
        ),
        "negation_critical_rate": (
            lambda row: (
                row["negation_critical_reference_words"],
                row["reference_words"],
            ),
            -1,
            "HIGH-impact reference words / reference words; advisory only",
        ),
        "insertions_per_reference_word": (
            lambda row: (row["insertions"], row["reference_words"]),
            -1,
            "the over-generation guard: a brief that gets read aloud shows up here "
            "first",
        ),
    }
    for name in classes:
        if name in {conec.NON_ENTITY_BUCKET, conec.UNLABELLED_BUCKET}:
            continue
        metrics[f"entity_wer_{name}"] = (
            _bucket_reader(name),
            -1,
            f"ConEC-mirror {name} entity WER: pooled (S + D) / tagged reference words",
        )
    return metrics


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_rows(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != wp.RESULT_SCHEMA:
        raise SystemExit(f"{path} is not a {wp.RESULT_SCHEMA} rows file")
    return document


def _identity_anchor(reaggregation_path: Path) -> dict:
    """Refuse to compute a contrast for an arm whose own per-window rows do not
    re-aggregate to its own sealed numbers. This is the whole basis of the read."""

    document = json.loads(reaggregation_path.read_text(encoding="utf-8"))
    failures = [row for row in document["checks"] if row["verdict"] == "FAIL"]
    return {
        "path": str(reaggregation_path),
        "sha256": _sha256(reaggregation_path),
        "source_run_id": document["source_run_id"],
        "source_attempt_id": document["source_attempt_id"],
        "verdict": document["verdict"],
        "checks_total": len(document["checks"]),
        "checks_failed": len(failures),
        "failed_checks": [row["check"] for row in failures],
        "rows_sha256": document["rows_sha256"],
        "corpus_wer_percent": round(document["aggregate"]["corpus_wer"] * 100.0, 4),
        "substitutions": document["aggregate"]["substitutions"],
        "deletions": document["aggregate"]["deletions"],
        "insertions": document["aggregate"]["insertions"],
        "reference_words": document["aggregate"]["reference_words"],
        "per_call_numeric": document["per_call_numeric"],
    }


def _pooled(pairs, ids) -> tuple[float, float]:
    left_num = left_den = right_num = right_den = 0
    for identifier in ids:
        ln, ld, rn, rd = pairs[identifier]
        left_num += ln
        left_den += ld
        right_num += rn
        right_den += rd
    left = (left_num / left_den) if left_den else 0.0
    right = (right_num / right_den) if right_den else 0.0
    return left, right


def _natural_statistic(pairs, sign: int):
    def statistic(ids) -> float:
        left, right = _pooled(pairs, ids)
        return sign * (right - left)

    return statistic


def _equal_stratum_statistic(pairs, sign: int, windows_per_call: dict[str, int]):
    """Equal weight per CALL rather than per reference word.

    A cluster draw contributes every window of one call, so the number of times a
    call was drawn is its occurrence count divided by its own window count. A call
    whose denominator is zero on this metric carries no rate and is skipped -- the
    weighting is therefore "equal per call that contains the class", stated rather
    than hidden.
    """

    per_call: dict[str, tuple[int, int, int, int]] = {}
    for identifier, (ln, ld, rn, rd) in pairs.items():
        call = wp.call_of(identifier)
        acc = per_call.get(call, (0, 0, 0, 0))
        per_call[call] = (acc[0] + ln, acc[1] + ld, acc[2] + rn, acc[3] + rd)

    def statistic(ids) -> float:
        counts: dict[str, int] = {}
        for identifier in ids:
            call = wp.call_of(identifier)
            counts[call] = counts.get(call, 0) + 1
        total = 0.0
        accumulated = 0.0
        for call, seen in counts.items():
            draws = seen / windows_per_call[call]
            ln, ld, rn, rd = per_call[call]
            if ld <= 0 or rd <= 0:
                continue
            accumulated += draws * sign * ((rn / rd) - (ln / ld))
            total += draws
        return (accumulated / total) if total else 0.0

    return statistic


def _interval(result) -> dict[str, float]:
    return {
        "point_estimate": result.point_estimate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "ci_level": result.ci_level,
        "sigma_hat": result.sigma_hat,
        "n_replicates": result.n_replicates,
        "seed": result.seed,
    }


def _delta_interval(block: dict, reading: str = "natural_mixture_call_clustered") -> dict:
    """The RAW ``right - left`` interval of a metric block.

    The blocks carry the re-signed IMPROVEMENT interval, because a positive number
    meaning "better" is the only convention that reads the same across metrics.
    A guard, though, is written on the raw delta ("upper bound on KC-E1f minus
    comparator ``<= 0``"), so this flips it back exactly: for a lower-is-better
    metric the delta is the negated improvement and its bounds swap.
    """

    interval = block[reading]
    if block["higher_is_better"]:
        return {
            "point_estimate": interval["point_estimate"],
            "ci_low": interval["ci_low"],
            "ci_high": interval["ci_high"],
        }
    return {
        "point_estimate": -interval["point_estimate"],
        "ci_low": -interval["ci_high"],
        "ci_high": -interval["ci_low"],
    }


def _contrast_block(
    *,
    metric: str,
    note: str,
    sign: int,
    pairs: dict,
    window_ids: tuple[str, ...],
    windows_per_call: dict[str, int],
    seed: int,
    replicates: int,
    ci_level: float,
    optimistic: bool,
) -> dict:
    left, right = _pooled(pairs, window_ids)
    clustered = paired.resampled_statistic(
        sample_ids=window_ids,
        statistic=_natural_statistic(pairs, sign),
        seed=seed,
        n_replicates=replicates,
        ci_level=ci_level,
        cluster_of=wp.call_of,
    )
    window_level = (
        paired.resampled_statistic(
            sample_ids=window_ids,
            statistic=_natural_statistic(pairs, sign),
            seed=seed,
            n_replicates=replicates,
            ci_level=ci_level,
        )
        if optimistic
        else None
    )
    equal = paired.resampled_statistic(
        sample_ids=window_ids,
        statistic=_equal_stratum_statistic(pairs, sign, windows_per_call),
        seed=seed,
        n_replicates=replicates,
        ci_level=ci_level,
        cluster_of=wp.call_of,
    )
    return {
        "metric": metric,
        "note": note,
        "higher_is_better": sign > 0,
        "left_pooled": left,
        "right_pooled": right,
        "delta_right_minus_left": right - left,
        "improvement_point": sign * (right - left),
        "improvement_sign_convention": "positive = the RIGHT arm is better",
        "natural_mixture_call_clustered": _interval(clustered),
        "natural_mixture_window_level_OPTIMISTIC": (
            _interval(window_level) if window_level is not None else None
        ),
        "equal_stratum_per_call_clustered": _interval(equal),
    }


def _call_pooled_numeric_contrast(
    *,
    left_calls: dict[str, tuple[int, int]],
    right_calls: dict[str, tuple[int, int]],
    seed: int,
    replicates: int,
    ci_level: float,
) -> dict:
    """The numeric guard, at the CALL unit the comparator's own 90.73 lives at.

    A bag match inside one window is strictly stricter than one across the call, so
    the window-pooled figure understates every arm alike; the guard therefore stays
    on the call-pooled figure (preregistration section 5) and the window-pooled one
    is a diagnostic.
    """

    call_ids = tuple(sorted(left_calls))
    if set(left_calls) != set(right_calls):
        raise SystemExit("the two arms do not carry the same 44 calls")

    def pooled(ids):
        ln = ld = rn = rd = 0
        for call in ids:
            a, b = left_calls[call]
            c, d = right_calls[call]
            ln += a
            ld += b
            rn += c
            rd += d
        return (ln / ld if ld else 0.0), (rn / rd if rd else 0.0)

    def natural(ids) -> float:
        left, right = pooled(ids)
        return right - left

    def equal(ids) -> float:
        total = 0
        accumulated = 0.0
        for call in ids:
            a, b = left_calls[call]
            c, d = right_calls[call]
            if b <= 0 or d <= 0:
                continue
            accumulated += (c / d) - (a / b)
            total += 1
        return (accumulated / total) if total else 0.0

    left, right = pooled(call_ids)
    return {
        "metric": "numeric_accuracy_call_pooled",
        "note": (
            "the GUARD figure: bag-matched per call, the unit the comparator's "
            "published 90.73 was computed at; delta = right minus left, higher is "
            "better"
        ),
        "higher_is_better": True,
        "left_pooled": left,
        "right_pooled": right,
        "delta_right_minus_left": right - left,
        "improvement_point": right - left,
        "natural_mixture_call_clustered": _interval(
            paired.resampled_statistic(
                sample_ids=call_ids,
                statistic=natural,
                seed=seed,
                n_replicates=replicates,
                ci_level=ci_level,
            )
        ),
        "equal_stratum_per_call_clustered": _interval(
            paired.resampled_statistic(
                sample_ids=call_ids,
                statistic=equal,
                seed=seed,
                n_replicates=replicates,
                ci_level=ci_level,
            )
        ),
    }


def _rates_table(rows: list[dict], reader, sign: int) -> dict[str, dict[str, float]]:
    """Per-window rate for the descriptive saves / harms / ties layer."""

    table: dict[str, dict[str, float]] = {}
    for row in rows:
        numerator, denominator = reader(row)
        rate = (numerator / denominator) if denominator else 0.0
        table[row["window_id"]] = {"rate": sign * rate}
    return table


def _class_anchor(
    *,
    slug: str,
    by_entity_type: dict,
    rows: list[dict],
    classes: tuple[str, ...],
) -> list[dict]:
    """Every class of the ConEC mirror, per-window sums against the arm's OWN
    committed score receipt -- the 8-class anchor of the pairing read, widened to
    the whole ``by_entity_type`` key set so no reported column is unanchored."""

    checks: list[dict] = []
    for name in classes:
        substitutions = deletions = reference_words = 0
        for row in rows:
            counts = row["entity_class_counts"][name]
            substitutions += counts[0]
            deletions += counts[1]
            reference_words += counts[2]
        sealed = by_entity_type.get(name)
        if sealed is None:
            checks.append(
                {
                    "arm": slug,
                    "entity_type": name,
                    "verdict": "FAIL",
                    "reason": "the sealed score receipt carries no such class",
                }
            )
            continue
        ok = (
            substitutions == int(sealed["substitutions"])
            and deletions == int(sealed["deletions"])
            and reference_words == int(sealed["reference_words"])
        )
        checks.append(
            {
                "arm": slug,
                "entity_type": name,
                "verdict": "PASS" if ok else "FAIL",
                "window_rows": [substitutions, deletions, reference_words],
                "sealed": [
                    int(sealed["substitutions"]),
                    int(sealed["deletions"]),
                    int(sealed["reference_words"]),
                ],
            }
        )
    return checks


def _sealed_by_entity_type(document: dict) -> dict:
    """``by_entity_type`` out of either committed receipt shape: a flight receipt's
    ``scores_aggregates`` or a ``core.scoring_batch`` verified score read."""

    if "scores_aggregates" in document:
        return document["scores_aggregates"]["conec-entity-wer-official"][
            "by_entity_type"
        ]
    return document["scores"]["conec-entity-wer-official"]["aggregate"]["by_entity_type"]


def _sealed_hypothesis_words(document: dict) -> int:
    if "scores_aggregates" in document:
        return int(
            document["scores_aggregates"]["numeric-value-accuracy-v1"]["hypothesis_words"]
        )
    return int(
        document["scores"]["numeric-value-accuracy-v1"]["aggregate"]["hypothesis_words"]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reaggregation-dir", type=Path, required=True)
    parser.add_argument("--attribution-dir", type=Path, required=True)
    parser.add_argument("--rows-dir", type=Path, required=True)
    parser.add_argument(
        "--rows-prefix",
        default="kce1f-verdict-window-rows-",
        help="rows file basename prefix; the arm slug and .json complete it",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=wp.E21_WINDOW_SEED)
    parser.add_argument("--replicates", type=int, default=wp.E21_WINDOW_REPLICATES)
    parser.add_argument("--ci-level", type=float, default=wp.E21_WINDOW_CI_LEVEL)
    parser.add_argument(
        "--kc-e1f-flight-receipt",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-07-e21-kc-e1f-repair-44-v1/flight/flight-receipt.json",
    )
    parser.add_argument(
        "--ku-e1fc-flight-receipt",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-07-e21-kc-e1f-repair-44-v1/flight-twin/flight-receipt.json",
    )
    parser.add_argument(
        "--comparator-score-read",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-06-e21-agentic-metric-baseline/scoring/verified-score-read.json",
        help="the comparator's own committed verified score read, for the class anchor",
    )
    parser.add_argument(
        "--roster-table",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-06-e21-agentic-metric-baseline/verdict/per-call-table.md",
        help="the committed comparator per-call table, read for the E5 roster label only",
    )
    args = parser.parse_args(argv)
    started = time.time()

    # ---- 1. identity anchors, and the rows they pin ----
    anchors: dict[str, dict] = {}
    rows_by_arm: dict[str, list[dict]] = {}
    rows_files: dict[str, dict] = {}
    for slug, run_id in ARM_RUNS.items():
        anchor = _identity_anchor(args.reaggregation_dir / slug / "reaggregation.json")
        if anchor["verdict"] != "PASS" or anchor["checks_failed"]:
            raise SystemExit(
                f"arm {slug!r} did not reproduce its own sealed numbers "
                f"({anchor['failed_checks']}); no contrast is computed"
            )
        if anchor["source_run_id"] != run_id:
            raise SystemExit(
                f"arm {slug!r} anchor names run {anchor['source_run_id']!r}, expected "
                f"{run_id!r}"
            )
        rows_path = args.rows_dir / f"{args.rows_prefix}{slug}.json"
        document = _load_rows(rows_path)
        if document["source_run_id"] != run_id:
            raise SystemExit(f"{rows_path} is not {run_id}'s rows file")
        actual = _sha256(rows_path)
        if actual != anchor["rows_sha256"]:
            raise SystemExit(
                f"{rows_path} sha256 {actual} is not the anchored {anchor['rows_sha256']}"
            )
        anchors[slug] = anchor
        rows_by_arm[slug] = document["rows"]
        rows_files[slug] = {
            "path": str(rows_path),
            "sha256": actual,
            "rows": len(document["rows"]),
            "source_attempt_id": document["source_attempt_id"],
        }

    class_sets = {
        slug: tuple(sorted(rows[0]["entity_class_counts"])) for slug, rows in rows_by_arm.items()
    }
    if len({classes for classes in class_sets.values()}) != 1:
        raise SystemExit(f"the arms carry different class columns: {class_sets}")
    classes = class_sets["comparator"]

    # ---- 2. the class anchor, every class against each arm's own receipt ----
    receipts = {
        "kc-e1f": json.loads(args.kc_e1f_flight_receipt.read_text(encoding="utf-8")),
        "ku-e1fc": json.loads(args.ku_e1fc_flight_receipt.read_text(encoding="utf-8")),
        "comparator": json.loads(args.comparator_score_read.read_text(encoding="utf-8")),
    }
    class_checks: list[dict] = []
    for slug, document in receipts.items():
        class_checks.extend(
            _class_anchor(
                slug=slug,
                by_entity_type=_sealed_by_entity_type(document),
                rows=rows_by_arm[slug],
                classes=classes,
            )
        )
    class_failures = [row for row in class_checks if row["verdict"] == "FAIL"]
    if class_failures:
        raise SystemExit(
            "per-class identity anchor FAILED; no contrast is computed: "
            + json.dumps(class_failures[:8])
        )

    # ---- 3. the section 5.1 attribution, and the construction guard ----
    attribution: dict[str, dict] = {}
    attribution_checks: list[dict] = []
    spans_per_window: dict[str, dict[str, int]] = {}
    for slug in TREATED_ARMS:
        document = json.loads(
            (args.attribution_dir / slug / "attribution.json").read_text(encoding="utf-8")
        )
        if document["verdict"] != "PASS":
            raise SystemExit(
                f"the section 5.1 attribution of arm {slug!r} is a DEFECT REPORT "
                f"({document['failures'][:2]}); the read aborts rather than producing "
                "a number"
            )
        if document["treated_run_id"] != ARM_RUNS[slug]:
            raise SystemExit(f"attribution for {slug!r} names another run")
        spans_path = Path(document["spans_table"]["path"])
        if _sha256(spans_path) != document["spans_table"]["sha256"]:
            raise SystemExit(f"{spans_path} is not the attributed span table")
        spans_document = json.loads(spans_path.read_text(encoding="utf-8"))
        spans_per_window[slug] = {
            row["window_id"]: int(row["substituted_spans"])
            for row in spans_document["per_window"]
        }
        totals = document["totals"]

        # (a) the (I - D) identity, re-derived from the anchors rather than quoted.
        treated = anchors[slug]
        comparator = anchors["comparator"]
        operation_delta = (treated["insertions"] - treated["deletions"]) - (
            comparator["insertions"] - comparator["deletions"]
        )
        attribution_checks.append(
            {
                "arm": slug,
                "check": "insertion_minus_deletion_equals_normalized_length_delta",
                "operation_delta": operation_delta,
                "normalized_word_delta": totals["normalized_word_delta"],
                "verdict": "PASS"
                if operation_delta == totals["normalized_word_delta"]
                else "FAIL",
            }
        )
        # (a2) the same identity PER CALL, so the corpus-level match cannot be two
        # errors cancelling: each call's own (I - D) move must equal that call's own
        # attributed normalized-word delta.
        per_call_attribution = {
            row["sample_id"]: row["normalized_words"]["delta"]
            for row in document["per_call"]
        }
        per_call_operations = {call: 0 for call in per_call_attribution}
        for arm_rows, arm_sign in ((rows_by_arm[slug], 1), (rows_by_arm["comparator"], -1)):
            for row in arm_rows:
                call = wp.call_of(row["window_id"])
                per_call_operations[call] += arm_sign * (
                    row["insertions"] - row["deletions"]
                )
        mismatched = sorted(
            call
            for call, delta in per_call_operations.items()
            if delta != per_call_attribution[call]
        )
        attribution_checks.append(
            {
                "arm": slug,
                "check": "per_call_insertion_minus_deletion_equals_attributed_delta",
                "calls": len(per_call_attribution),
                "calls_that_disagree": mismatched,
                "verdict": "PASS" if not mismatched else "FAIL",
            }
        )
        # (b) the attributed share: the whole delta sits on substituted spans.
        attribution_checks.append(
            {
                "arm": slug,
                "check": "whole_delta_attributed_to_substituted_spans",
                "attributed_delta": totals["attributed_delta"],
                "normalized_word_delta": totals["normalized_word_delta"],
                "interior_tokens_that_moved": 0,
                "verdict": "PASS"
                if totals["attributed_delta"] == totals["normalized_word_delta"]
                else "FAIL",
            }
        )
        # (c) the normalized hypothesis length against each arm's OWN scorer.
        for role, key in (("comparator", "comparator_normalized_words"), (slug, "treated_normalized_words")):
            sealed = _sealed_hypothesis_words(receipts[role])
            attribution_checks.append(
                {
                    "arm": slug,
                    "check": f"normalized_hypothesis_words[{role}]",
                    "attribution": totals[key],
                    "sealed_scorer": sealed,
                    "verdict": "PASS" if totals[key] == sealed else "FAIL",
                }
            )
        # (d) the raw-space construction guarantee, on the sealed bytes.
        delivery = receipts[slug]["delivery_integrity"]
        attribution_checks.append(
            {
                "arm": slug,
                "check": "delivery_integrity_construction_guard",
                "windows_checked": delivery["windows_checked"],
                "violations": delivery["violations"],
                "raw_tokens_both_arms": totals["raw_tokens"],
                "differing_positions": totals["differing_positions"],
                "flight_reported_differing_positions": delivery[
                    "differing_token_positions_total"
                ],
                "verdict": "PASS"
                if (
                    delivery["violations"] == 0
                    and delivery["windows_checked"] == 1593
                    and totals["differing_positions"]
                    == delivery["differing_token_positions_total"]
                )
                else "FAIL",
            }
        )
        attribution[slug] = document

    attribution_failures = [
        row for row in attribution_checks if row["verdict"] == "FAIL"
    ]
    if attribution_failures:
        raise SystemExit(
            "the section 5.1 attribution did not close; the read aborts: "
            + json.dumps(attribution_failures)
        )

    # ---- 4. the paired contrasts ----
    by_window: dict[str, dict[str, dict]] = {
        slug: {row["window_id"]: row for row in rows} for slug, rows in rows_by_arm.items()
    }
    id_sets = {slug: set(table) for slug, table in by_window.items()}
    reference_ids = id_sets["comparator"]
    for slug, ids in id_sets.items():
        if ids != reference_ids:
            raise SystemExit(f"arm {slug!r} does not carry the comparator's window ids")
    window_ids = tuple(sorted(reference_ids))
    windows_per_call: dict[str, int] = {}
    for identifier in window_ids:
        call = wp.call_of(identifier)
        windows_per_call[call] = windows_per_call.get(call, 0) + 1
    calls = tuple(sorted(windows_per_call))

    saturated = {
        slug: sorted(
            identifier for identifier, row in table.items() if bool(row.get("saturated"))
        )
        for slug, table in by_window.items()
    }
    saturated_union = sorted({wid for ids in saturated.values() for wid in ids})
    surviving_ids = tuple(wid for wid in window_ids if wid not in set(saturated_union))
    saturated_calls = sorted({wp.call_of(wid) for wid in saturated_union})
    surviving_call_ids = tuple(
        wid for wid in window_ids if wp.call_of(wid) not in set(saturated_calls)
    )

    metrics = _window_metrics(classes)

    def build(left_slug: str, right_slug: str, reader, ids):
        left_table = by_window[left_slug]
        right_table = by_window[right_slug]
        pairs = {}
        for identifier in ids:
            ln, ld = reader(left_table[identifier])
            rn, rd = reader(right_table[identifier])
            pairs[identifier] = (ln, ld, rn, rd)
        return pairs

    results: dict[str, dict] = {}
    sensitivity: dict[str, dict] = {}
    call_sensitivity: dict[str, dict] = {}
    descriptive: dict[str, dict] = {}
    for contrast, left_slug, right_slug, contrast_note in CONTRASTS:
        block: dict[str, dict] = {}
        for metric, (reader, sign, note) in metrics.items():
            pairs = build(left_slug, right_slug, reader, window_ids)
            block[metric] = _contrast_block(
                metric=metric,
                note=note,
                sign=sign,
                pairs=pairs,
                window_ids=window_ids,
                windows_per_call=windows_per_call,
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
                optimistic=metric in OPTIMISTIC_METRICS,
            )
        left_calls = {
            row["sample_id"]: (row["call_numeric_matched"], row["call_numeric_expected"])
            for row in anchors[left_slug]["per_call_numeric"]
        }
        right_calls = {
            row["sample_id"]: (row["call_numeric_matched"], row["call_numeric_expected"])
            for row in anchors[right_slug]["per_call_numeric"]
        }
        block["numeric_accuracy_call_pooled"] = _call_pooled_numeric_contrast(
            left_calls=left_calls,
            right_calls=right_calls,
            seed=args.seed,
            replicates=args.replicates,
            ci_level=args.ci_level,
        )
        results[contrast] = {
            "left_arm": left_slug,
            "right_arm": right_slug,
            "left_run_id": ARM_RUNS[left_slug],
            "right_run_id": ARM_RUNS[right_slug],
            "reading": contrast_note,
            "metrics": block,
        }
        print(
            f"{contrast:8} PERSON "
            f"{100 * block['entity_wer_PERSON']['natural_mixture_call_clustered']['point_estimate']:+.3f} "
            f"corpus "
            f"{100 * block['corpus_wer']['natural_mixture_call_clustered']['point_estimate']:+.3f}",
            flush=True,
        )

        # Saturation sensitivity, both exclusions, reported beside the primary.
        sensitivity_block: dict[str, dict] = {}
        for metric in ("entity_wer_PERSON", "corpus_wer", "insertions_per_reference_word"):
            reader, sign, note = metrics[metric]
            pairs = build(left_slug, right_slug, reader, surviving_ids)
            sensitivity_block[metric] = _contrast_block(
                metric=metric,
                note=note,
                sign=sign,
                pairs=pairs,
                window_ids=surviving_ids,
                windows_per_call={
                    call: sum(1 for wid in surviving_ids if wp.call_of(wid) == call)
                    for call in calls
                },
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
                optimistic=False,
            )
        sensitivity[contrast] = sensitivity_block

        call_sensitivity_block: dict[str, dict] = {}
        surviving_calls = sorted({wp.call_of(wid) for wid in surviving_call_ids})
        for metric in ("entity_wer_PERSON", "corpus_wer", "insertions_per_reference_word"):
            reader, sign, note = metrics[metric]
            pairs = build(left_slug, right_slug, reader, surviving_call_ids)
            call_sensitivity_block[metric] = _contrast_block(
                metric=metric,
                note=note,
                sign=sign,
                pairs=pairs,
                window_ids=surviving_call_ids,
                windows_per_call={call: windows_per_call[call] for call in surviving_calls},
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
                optimistic=False,
            )
        call_sensitivity[contrast] = call_sensitivity_block

        contrast_descriptive: dict[str, dict] = {}
        for metric in ("corpus_wer", "entity_wer_PERSON"):
            reader, sign, _note = metrics[metric]
            left_rates = _rates_table(rows_by_arm[left_slug], reader, sign)
            right_rates = _rates_table(rows_by_arm[right_slug], reader, sign)
            computed = paired.paired_contrast(
                left_rates,
                right_rates,
                metrics=["rate"],
                seed=args.seed,
                n_replicates=args.replicates,
                ci_level=args.ci_level,
                cluster_of=wp.call_of,
            )["rate"]
            bearing = tuple(
                identifier
                for identifier in window_ids
                if reader(by_window[left_slug][identifier])[1] > 0
                or reader(by_window[right_slug][identifier])[1] > 0
            )
            bearing_contrast = paired.paired_contrast(
                left_rates,
                right_rates,
                metrics=["rate"],
                sample_ids=bearing,
                seed=args.seed,
                n_replicates=args.replicates,
                ci_level=args.ci_level,
                cluster_of=wp.call_of,
            )["rate"]
            contrast_descriptive[metric] = {
                "all_windows": {
                    "n": computed.n,
                    "saves": computed.saves,
                    "harms": computed.harms,
                    "ties": computed.ties,
                    "sign_test_p": computed.sign_test_p,
                    "mean_of_per_window_differences_NOT_THE_DECISION_INTERVAL": {
                        "point_estimate": computed.bootstrap.point_estimate,
                        "ci_low": computed.bootstrap.ci_low,
                        "ci_high": computed.bootstrap.ci_high,
                    },
                },
                "windows_carrying_the_denominator": {
                    "n": bearing_contrast.n,
                    "saves": bearing_contrast.saves,
                    "harms": bearing_contrast.harms,
                    "ties": bearing_contrast.ties,
                    "sign_test_p": bearing_contrast.sign_test_p,
                },
            }
        descriptive[contrast] = contrast_descriptive

    # ---- 5. the decision rule, applied as written ----
    total = results["total"]["metrics"]
    content = results["content"]["metrics"]
    primary_comparator = total["entity_wer_PERSON"]["natural_mixture_call_clustered"]
    primary_twin = content["entity_wer_PERSON"]["natural_mixture_call_clustered"]
    corpus_guard = _delta_interval(total["corpus_wer"])
    insertion_guard = _delta_interval(total["insertions_per_reference_word"])
    numeric_guard = total["numeric_accuracy_call_pooled"][
        "natural_mixture_call_clustered"
    ]
    negation_advisory = _delta_interval(total["negation_critical_rate"])

    guards = [
        {
            "guard": "delivery integrity (construction)",
            "test": (
                "for every window the delivered raw text equals the sealed predecessor "
                "outside the accepted substitution spans and carries the identical "
                "whitespace-token count -- it ABORTS THE READ rather than producing a "
                "number"
            ),
            "measured": {
                "windows_checked": 1593,
                "violations": sum(
                    receipts[slug]["delivery_integrity"]["violations"]
                    for slug in TREATED_ARMS
                ),
                "attribution_verdict": {
                    slug: attribution[slug]["verdict"] for slug in TREATED_ARMS
                },
            },
            "verdict": "PASS",
        },
        {
            "guard": "corpus WER non-inferiority",
            "test": "call-clustered CI90 UPPER bound on (KC-E1f - comparator) <= 0",
            "measured": corpus_guard,
            "verdict": "PASS" if corpus_guard["ci_high"] <= 0.0 else "FAIL",
        },
        {
            "guard": "numeric-value accuracy not worse (call-pooled)",
            "test": "CI90 LOWER bound on (KC-E1f - comparator) accuracy >= 0",
            "measured": {
                "point_estimate": numeric_guard["point_estimate"],
                "ci_low": numeric_guard["ci_low"],
                "ci_high": numeric_guard["ci_high"],
            },
            "verdict": "PASS" if numeric_guard["ci_low"] >= 0.0 else "FAIL",
        },
        {
            "guard": "over-generation not worse",
            "test": (
                "call-clustered CI90 UPPER bound on (KC-E1f - comparator) insertions "
                "per reference word <= 0"
            ),
            "measured": insertion_guard,
            "verdict": "PASS" if insertion_guard["ci_high"] <= 0.0 else "FAIL",
        },
        {
            "guard": "negation-critical rate not worse",
            "test": "advisory point estimate only; gates nothing",
            "measured": negation_advisory,
            "verdict": "ADVISORY",
        },
    ]
    failed_guards = [row["guard"] for row in guards if row["verdict"] == "FAIL"]
    primary_met = primary_comparator["ci_low"] > 0.0 and primary_twin["ci_low"] > 0.0
    if failed_guards:
        verdict = "HARMFUL"
    elif not primary_met:
        verdict = "NULL"
    else:
        verdict = "ADMITTED"

    decision = {
        "verdict": verdict,
        "reported_as": {
            "ADMITTED": "ADMITTED",
            "NULL": "NULL",
            "HARMFUL": "REJECTED (the preregistration's own word for a failed guard)",
        }[verdict],
        "primary": {
            "vs_comparator": {
                "required": "call-clustered CI90 lower bound > 0",
                "measured": primary_comparator,
                "verdict": "MET" if primary_comparator["ci_low"] > 0.0 else "NOT MET",
            },
            "vs_ku_e1fc": {
                "required": "call-clustered CI90 lower bound > 0",
                "measured": primary_twin,
                "verdict": "MET" if primary_twin["ci_low"] > 0.0 else "NOT MET",
            },
        },
        "guards": guards,
        "failed_guards": failed_guards,
    }

    # ---- 6. the mechanism table and the operation-delta localization ----
    def ledger(slug: str) -> dict:
        receipt = receipts[slug]
        return {
            "run_id": receipt["run_id"],
            "attempt_id": receipt["attempt_id"],
            "repair_ledger": receipt["repair_ledger"],
            "delivery_integrity": receipt["delivery_integrity"],
            "anchor_ratio": receipt["anchor_ratio"],
            "delivered_vs_comparator_operations": receipt[
                "delivered_vs_comparator_operations"
            ],
            "saturation": receipt["saturation"],
            "substitutions_per_call": receipt["substitutions_per_call"],
        }

    mechanism = {slug: ledger(slug) for slug in TREATED_ARMS}

    localization: dict[str, dict] = {}
    for slug in TREATED_ARMS:
        per_class: list[dict] = []
        for name in classes:
            moved_with_span = moved_without_span = 0
            deletion_delta = 0
            moved_windows: list[str] = []
            for identifier in window_ids:
                left_counts = by_window["comparator"][identifier]["entity_class_counts"][
                    name
                ]
                right_counts = by_window[slug][identifier]["entity_class_counts"][name]
                difference = right_counts[1] - left_counts[1]
                deletion_delta += difference
                if difference:
                    if spans_per_window[slug].get(identifier, 0) > 0:
                        moved_with_span += 1
                    else:
                        moved_without_span += 1
                        moved_windows.append(identifier)
            per_class.append(
                {
                    "entity_type": name,
                    "deletion_delta": deletion_delta,
                    "windows_whose_deletions_moved_and_carry_a_substitution": moved_with_span,
                    "windows_whose_deletions_moved_without_one": moved_without_span,
                    "windows_without_a_substitution": moved_windows[:20],
                }
            )
        person_windows = []
        for identifier in window_ids:
            left_counts = by_window["comparator"][identifier]["entity_class_counts"][
                "PERSON"
            ]
            right_counts = by_window[slug][identifier]["entity_class_counts"]["PERSON"]
            if right_counts[1] != left_counts[1]:
                person_windows.append(
                    {
                        "window_id": identifier,
                        "comparator_S_D_ref": left_counts,
                        "arm_S_D_ref": right_counts,
                        "substituted_spans_in_this_window": spans_per_window[slug].get(
                            identifier, 0
                        ),
                    }
                )
        localization[slug] = {
            "note": (
                "the OPERATION-level counterpart of the section 5.1 attribution: a "
                "window whose per-class deletion count moved must carry an accepted "
                "substitution, because the delivery rule changed no other byte. The "
                "mechanism cannot repair a deletion (section 9 item 1), so a moved "
                "PERSON deletion is a substituted span normalizing to a different "
                "number of words and re-seating the alignment, never a recovered word"
            ),
            "per_class": per_class,
            "person_windows_whose_deletions_moved": person_windows,
        }

    # ---- 7. the per-call table, all 44 calls ----
    roster = {}
    if args.roster_table.exists():
        for line in args.roster_table.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit():
                roster[cells[0]] = cells[1]

    per_call: list[dict] = []
    for call in calls:
        entry: dict[str, object] = {
            "sample_id": call,
            "roster": roster.get(call, "unknown"),
            "windows": windows_per_call[call],
        }
        for slug in ARM_RUNS:
            table = by_window[slug]
            substitutions = deletions = insertions = reference_words = 0
            person_errors = person_reference = 0
            saturated_here = 0
            for index in range(1, windows_per_call[call] + 1):
                row = table[wp.window_id(call, index)]
                substitutions += row["substitutions"]
                deletions += row["deletions"]
                insertions += row["insertions"]
                reference_words += row["reference_words"]
                person = row["entity_class_counts"]["PERSON"]
                person_errors += person[0] + person[1]
                person_reference += person[2]
                saturated_here += 1 if row.get("saturated") else 0
            entry[f"{slug}_corpus_wer_percent"] = (
                100.0 * (substitutions + deletions + insertions) / reference_words
                if reference_words
                else 0.0
            )
            entry[f"{slug}_person_entity_wer_percent"] = (
                100.0 * person_errors / person_reference if person_reference else None
            )
            entry[f"{slug}_person_reference_words"] = person_reference
            entry[f"{slug}_saturated_windows"] = saturated_here
        for slug in TREATED_ARMS:
            entry[f"{slug}_accepted_substitutions"] = receipts[slug][
                "substitutions_per_call"
            ].get(call)
        per_call.append(entry)

    roster_halves: dict[str, dict] = {}
    for label in sorted({str(entry["roster"]) for entry in per_call}):
        members = {entry["sample_id"] for entry in per_call if entry["roster"] == label}
        ids = tuple(wid for wid in window_ids if wp.call_of(wid) in members)
        half: dict[str, dict] = {}
        for metric in ("corpus_wer", "entity_wer_PERSON", "entity_wer_ORG"):
            reader, _sign, _note = metrics[metric]
            half[metric] = {}
            for slug in ARM_RUNS:
                numerator = denominator = 0
                for identifier in ids:
                    n, d = reader(by_window[slug][identifier])
                    numerator += n
                    denominator += d
                half[metric][slug] = 100.0 * numerator / denominator if denominator else 0.0
        roster_halves[label] = {
            "calls": len(members),
            "windows": len(ids),
            "pooled_percent": half,
        }

    saturation_block = {
        "per_arm": {
            slug: {
                "count": len(ids),
                "windows": [
                    {
                        "window_id": wid,
                        "sample_id": wp.call_of(wid),
                        "start_seconds": by_window[slug][wid]["start_seconds"],
                        "end_seconds": by_window[slug][wid]["end_seconds"],
                        "reference_words_charged": by_window[slug][wid]["reference_words"],
                        "hypothesis_words_charged": by_window[slug][wid][
                            "hypothesis_words"
                        ],
                        "substituted_spans_in_this_window": spans_per_window.get(
                            slug, {}
                        ).get(wid, 0),
                    }
                    for wid in ids
                ],
            }
            for slug, ids in saturated.items()
        },
        "union_excluded_by_the_sensitivity": saturated_union,
        "windows_after_exclusion": len(surviving_ids),
        "calls_carrying_a_saturated_window": saturated_calls,
        "windows_after_excluding_those_calls": len(surviving_call_ids),
        "calls_after_excluding_those_calls": len(
            {wp.call_of(wid) for wid in surviving_call_ids}
        ),
        "note": (
            "THIS IS WHERE THE REPAIR FORM DIFFERS FROM KC-E1 BY CONSTRUCTION. A "
            "saturated pass-2 decode reaches core.repair_alignment as the empty string, "
            "is refused as `empty_response` and DELIVERS PASS 1 -- so a saturated "
            "window here carries the comparator's own transcript and its full "
            "reference-word charge, where KC-E1's two saturated windows contributed the "
            "empty string and were charged nothing. The covariate is still named and "
            "still carried: the count per arm is published, and the sensitivity that "
            "drops the affected CALLS from all three arms is reported beside the "
            "primary, never in place of it."
        ),
    }

    covariate = {
        "note": (
            "the twin was matched to the arm on the FLIGHT tokenizer, per line and per "
            "window; what is left is the constant `[evidence <id>] ` header residual of "
            "the two evidence blocks, +7 tokens, measured on the requests that actually "
            "flew rather than projected"
        ),
        "token_match_measured_by_the_flight": receipts["ku-e1fc"]["token_match"],
        "sources": {
            slug: {
                "path": str(path),
                "sha256": _sha256(path),
            }
            for slug, path in (
                ("kc-e1f", args.kc_e1f_flight_receipt),
                ("ku-e1fc", args.ku_e1fc_flight_receipt),
            )
        },
        "tokens": {slug: receipts[slug]["tokens"] for slug in TREATED_ARMS},
        "cost": {slug: receipts[slug]["cost"] for slug in TREATED_ARMS},
        "throughput": {slug: receipts[slug]["throughput"] for slug in TREATED_ARMS},
        "serving": {
            slug: {
                "session_id": receipts[slug]["serving"]["session_id"],
                "geometry": receipts[slug]["serving"]["geometry"],
                "monitor_summary": receipts[slug]["serving"]["monitor_summary"],
            }
            for slug in TREATED_ARMS
        },
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": RESULT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW,
        "decides": DECIDES,
        "preregistration": PREREGISTRATION,
        "arms": ARM_RUNS,
        "decision": decision,
        "identity_anchors": anchors,
        "class_anchor": {
            "classes": list(classes),
            "checks": class_checks,
            "failed": len(class_failures),
        },
        "rows_files": rows_files,
        "section_5_1_attribution": {
            slug: {
                key: value
                for key, value in attribution[slug].items()
                if key not in {"per_call"}
            }
            for slug in TREATED_ARMS
        },
        "section_5_1_attribution_per_call": {
            slug: attribution[slug]["per_call"] for slug in TREATED_ARMS
        },
        "attribution_checks": attribution_checks,
        "operation_delta_localization": localization,
        "mechanism": mechanism,
        "pairing": {
            "unit": "fixed 90-second window",
            "cluster": "call",
            "windows": len(window_ids),
            "calls": len(calls),
            "seed": args.seed,
            "n_replicates": args.replicates,
            "ci_level": args.ci_level,
            "estimator": (
                "pooled ratio, sum(numerator) / sum(denominator) over the resampled units"
            ),
        },
        "contrasts": results,
        "saturation": saturation_block,
        "saturation_sensitivity": sensitivity,
        "saturation_sensitivity_saturated_calls_excluded": call_sensitivity,
        "descriptive_window_level": descriptive,
        "per_call": per_call,
        "roster_halves": roster_halves,
        "token_throughput_covariate": covariate,
        "zero_contact": (
            "no model, GPU, tool, embedding, tokenizer, network, audio-decode or "
            "paid-API contact; no reference transcript is opened by this script"
        ),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "result-summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (args.out_dir / "token-throughput-covariate.json").write_text(
        json.dumps(covariate, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "| call | roster | windows | baseline corpus WER % | placebo corpus WER % | "
        "repair corpus WER % | baseline PERSON % | placebo PERSON % | repair PERSON % | "
        "PERSON ref words | accepted substitutions (repair/placebo) | saturated "
        "(repair/placebo) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for entry in per_call:
        def fmt(value):
            return "--" if value is None else f"{value:.2f}"

        lines.append(
            f"| {entry['sample_id']} | {entry['roster']} | {entry['windows']} "
            f"| {fmt(entry['comparator_corpus_wer_percent'])} "
            f"| {fmt(entry['ku-e1fc_corpus_wer_percent'])} "
            f"| {fmt(entry['kc-e1f_corpus_wer_percent'])} "
            f"| {fmt(entry['comparator_person_entity_wer_percent'])} "
            f"| {fmt(entry['ku-e1fc_person_entity_wer_percent'])} "
            f"| {fmt(entry['kc-e1f_person_entity_wer_percent'])} "
            f"| {entry['comparator_person_reference_words']} "
            f"| {entry['kc-e1f_accepted_substitutions']}/"
            f"{entry['ku-e1fc_accepted_substitutions']} "
            f"| {entry['kc-e1f_saturated_windows']}/{entry['ku-e1fc_saturated_windows']} |"
        )
    (args.out_dir / "per-call-table.md").write_text(
        "# KC-E1f verdict — the 44 calls, corpus WER and PERSON entity WER, three arms\n\n"
        "Pooled per call from the sealed per-window rows of each arm. `baseline` is\n"
        "`SAEA-E21-FULL44-DIRECT-BASELINE-V2` (which is also both repair arms' pass 1),\n"
        "`placebo` is `SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1`, `repair` is\n"
        "`SAEA-E21-KC-E1F-REPAIR-44-V1`. PERSON entity WER is `(S + D) / tagged reference\n"
        "words`; the reference-word count is identical in all three arms and is printed\n"
        "once. Accepted substitutions come from each flight's own receipt.\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"VERDICT {verdict} ({decision['reported_as']})")
    for contrast, _left, _right, _note in CONTRASTS:
        person = results[contrast]["metrics"]["entity_wer_PERSON"][
            "natural_mixture_call_clustered"
        ]
        corpus = results[contrast]["metrics"]["corpus_wer"][
            "natural_mixture_call_clustered"
        ]
        print(
            f"{contrast:8} PERSON reduction {100 * person['point_estimate']:+.3f} pp "
            f"[{100 * person['ci_low']:+.3f}, {100 * person['ci_high']:+.3f}]   "
            f"corpus improvement {100 * corpus['point_estimate']:+.3f} pp "
            f"[{100 * corpus['ci_low']:+.3f}, {100 * corpus['ci_high']:+.3f}]"
        )
    for row in guards:
        print(f"guard {row['verdict']:8} {row['guard']}")
    print(f"elapsed {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
