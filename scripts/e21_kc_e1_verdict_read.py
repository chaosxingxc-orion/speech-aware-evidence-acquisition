#!/usr/bin/env python3
"""Decide KC-E1 against its preregistered rule, from three sealed manifests.

Exposure row ``SAEA-E21-KC-E1-VERDICT-V1`` (``model-free-check``), registered and
committed before the first sealed byte was opened. **Zero model, GPU, tool,
embedder, tokenizer, network, audio-decode and paid-API contacts.** Reference
transcripts and ``wer_tags`` are reached only through the registered scoring
path's own loaders, and only inside ``scripts/e21_window_pairing_read.py``, which
produced the per-window rows this script consumes; nothing here opens a reference.

The rule is ``docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md``
section 5, quoted verbatim in the verdict note and applied here as written:

* **primary** -- the call-clustered CI90 LOWER bound on the pooled ConEC-mirror
  PERSON entity-WER REDUCTION (comparator minus KC-E1, so a positive value means
  fewer errors) must be ``> 0`` against the sealed comparator AND against the form
  twin KU-E1c;
* **guards** -- corpus-WER non-inferiority (call-clustered CI90 UPPER bound on
  ``KC-E1 - comparator`` ``<= 0``), numeric-value accuracy not worse at the
  CALL-pooled figure (CI90 lower bound on the accuracy delta ``>= 0``),
  over-generation not worse (insertions per reference word), and the
  negation-critical rate as an advisory point estimate;
* **NULL** if either primary lower bound includes 0; **HARMFUL** if any guard
  fails.

The pairing unit is the fixed 90-second window and the bootstrap cluster is the
call (44) -- the owner's 2026-09-06 ruling, section 3. Every headline statistic is
a POOLED ratio, ``sum(numerator) / sum(denominator)`` over the resampled units,
run through ``analysis.paired.resampled_statistic(cluster_of=...)`` at seed
20260903, 10,000 replicates, CI90. The window-level interval is reported beside it
and labelled optimistic; the saves / harms / ties and exact sign test at n = 1,593
come from ``analysis.paired.paired_contrast`` on the per-window rates, whose own
bootstrap is the MEAN of per-window differences and is never the decision interval.
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

RESULT_SCHEMA = "saea-e21-kc-e1-verdict-v1"
EXPOSURE_ROW = "SAEA-E21-KC-E1-VERDICT-V1"

#: Arm slug -> (sealed run id, human label). ``comparator`` is the sealed direct
#: baseline every Earnings mechanism cell pairs against by name
#: (``docs/readiness/2026-09-06-earnings-agentic-metric-baseline-v1.md`` section 7).
ARM_RUNS = {
    "comparator": "SAEA-E21-FULL44-DIRECT-BASELINE-V2",
    "ku-e1c": "SAEA-E21-KU-E1C-PLACEBO-44-V1",
    "kc-e1": "SAEA-E21-KC-E1-BRIEF-44-V1",
}

#: The three contrasts of the three-way reading. ``(left, right)`` with the
#: module convention ``delta = right - left``; ``improvement`` re-signs that so a
#: positive number always means the RIGHT arm is better on the metric.
CONTRASTS = (
    ("total", "comparator", "kc-e1", "KC-E1 vs the sealed comparator -- moves evidence AND instruction"),
    ("form", "comparator", "ku-e1c", "KU-E1c vs the sealed comparator -- the form effect alone"),
    ("content", "ku-e1c", "kc-e1", "KC-E1 vs KU-E1c -- the one factor, the brief's CONTENT"),
)

PUBLISHED_CLASSES = ("PERSON", "ORG", "GPE", "LOC", "PRODUCT", "EVENT", "NORP", "FAC")

#: The window-level interval is an explicitly OPTIMISTIC bound -- 1,593 units
#: treated as independent, which they are not -- and it decides nothing. It is
#: computed for the primary, the guards and the two classes that carry real weight,
#: and skipped for the thin classes where it would only add a wider wrong number.
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

#: name -> (how to read one window row's numerator and denominator,
#:          +1 if a HIGHER pooled ratio is better, -1 if LOWER is better)
#: Every one of these is a pooled ratio: sum the counts over the resampled units,
#: then divide ONCE. Never an average of per-window rates.
def _window_metrics() -> dict[str, tuple]:
    metrics: dict[str, tuple] = {
        "corpus_wer": (
            lambda row: (
                row["substitutions"] + row["deletions"] + row["insertions"],
                row["reference_words"],
            ),
            -1,
            "pooled (S + D + I) / reference words -- the ConEC __ALL__ bucket and asr-wer-whisper agree on it",
        ),
        "non_entity_wer": (
            _bucket_reader(conec.NON_ENTITY_BUCKET),
            -1,
            "pooled (S + D) / non-entity reference words; insertions are unattributable and excluded",
        ),
        "unlabelled_wer": (
            _bucket_reader(conec.UNLABELLED_BUCKET),
            -1,
            "pooled (S + D) / unlabelled reference words -- the normalization-transfer residue, reported not claimed",
        ),
        "numeric_accuracy_window": (
            lambda row: (row["numeric_matched"], row["numeric_expected"]),
            +1,
            "WINDOW-pooled numeric-value accuracy -- a DIAGNOSTIC; the guard is the call-pooled figure",
        ),
        "negation_critical_rate": (
            lambda row: (row["negation_critical_reference_words"], row["reference_words"]),
            -1,
            "HIGH-impact reference words / reference words; advisory only (100 HIGH words on all 44)",
        ),
        "insertions_per_reference_word": (
            lambda row: (row["insertions"], row["reference_words"]),
            -1,
            "the over-generation guard: a brief that gets read aloud shows up here first",
        ),
    }
    for name in PUBLISHED_CLASSES:
        metrics[f"entity_wer_{name}"] = (
            _bucket_reader(name),
            -1,
            f"ConEC-mirror {name} entity WER: pooled (S + D) / tagged reference words",
        )
    return metrics


def _bucket_reader(bucket: str):
    def read(row: dict) -> tuple[int, int]:
        counts = row["entity_class_counts"][bucket]
        return counts[0] + counts[1], counts[2]

    return read


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
    whose denominator is zero on this metric (a class it contains no reference word
    of) carries no rate and is skipped -- the weighting is therefore "equal per call
    that contains the class", which is stated rather than hidden.
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
    optimistic = (
        paired.resampled_statistic(
            sample_ids=window_ids,
            statistic=_natural_statistic(pairs, sign),
            seed=seed,
            n_replicates=replicates,
            ci_level=ci_level,
        )
        if metric in OPTIMISTIC_METRICS
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
        "improvement_sign_convention": (
            "positive = the RIGHT arm is better on this metric"
        ),
        "natural_mixture_call_clustered": _interval(clustered),
        "natural_mixture_window_level_OPTIMISTIC": (
            _interval(optimistic) if optimistic is not None else None
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
            "published 90.73 was computed at; delta = KC-E1 minus comparator, "
            "higher is better"
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


def _token_throughput_covariate(*, kc_e1_path: Path, ku_e1c_path: Path) -> dict:
    """Both arms' per-call brief token counts, prompt/completion totals, throughput
    and GPU hours, out of the two flights' OWN receipts.

    The twin was matched to the arm on the FLIGHT tokenizer, line by line and call by
    call, so what is left is the constant ``[evidence <id>] `` header of the two
    evidence blocks -- 7 tokens, on every window. This block re-derives that residual
    from the two receipts rather than quoting it, so a verdict that reads the
    arm-versus-twin contrast as a content effect can show the prompt-volume difference
    it is resting on.
    """

    def load(path: Path) -> tuple[dict, str]:
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()

    kc_e1, kc_e1_sha = load(kc_e1_path)
    ku_e1c, ku_e1c_sha = load(ku_e1c_path)

    def envelope(receipt: dict) -> dict[str, list[int]]:
        return {
            str(entry["sample_id"]): [int(v) for v in entry["text_tokens"]]
            for entry in receipt["tokens"]["calls_whose_envelope_varies_within_the_call"]
        }

    arm = envelope(kc_e1)
    twin = envelope(ku_e1c)
    if set(arm) != set(twin):
        raise SystemExit("the two flight receipts do not carry the same 44 calls")
    per_call = []
    residuals: set[int] = set()
    for sample_id in sorted(arm):
        low_arm, high_arm = arm[sample_id][0], arm[sample_id][-1]
        low_twin, high_twin = twin[sample_id][0], twin[sample_id][-1]
        residuals.add(low_twin - low_arm)
        residuals.add(high_twin - high_arm)
        per_call.append(
            {
                "sample_id": sample_id,
                "kc_e1_text_tokens_min": low_arm,
                "kc_e1_text_tokens_max": high_arm,
                "ku_e1c_text_tokens_min": low_twin,
                "ku_e1c_text_tokens_max": high_twin,
                "twin_minus_arm_min": low_twin - low_arm,
                "twin_minus_arm_max": high_twin - high_arm,
            }
        )
    return {
        "sources": {
            "kc-e1": {"path": str(kc_e1_path), "sha256": kc_e1_sha},
            "ku-e1c": {"path": str(ku_e1c_path), "sha256": ku_e1c_sha},
        },
        "constant_residual_twin_minus_arm": sorted(residuals),
        "per_call_brief_text_tokens": per_call,
        "totals": {
            "kc-e1": {
                "prompt_tokens": kc_e1["tokens"]["prompt_total"],
                "completion_tokens": kc_e1["tokens"]["completion_total"],
                "comparator_prompt_tokens": kc_e1["tokens"]["comparator_prompt_total"],
                "comparator_completion_tokens": kc_e1["tokens"][
                    "comparator_completion_total"
                ],
                "per_window_prompt_min_median_max": [
                    kc_e1["tokens"]["per_window_prompt_min"],
                    kc_e1["tokens"]["per_window_prompt_median"],
                    kc_e1["tokens"]["per_window_prompt_max"],
                ],
                "per_window_text_min_median_max": [
                    kc_e1["tokens"]["per_window_text_min"],
                    kc_e1["tokens"]["per_window_text_median"],
                    kc_e1["tokens"]["per_window_text_max"],
                ],
                "gpu_hours": kc_e1["cost"]["gpu_hours"],
                "gpu_seconds": kc_e1["cost"]["gpu_seconds"],
                "audio_seconds_used": kc_e1["cost"]["audio_seconds_used"],
                "peak_vram_mib": kc_e1["cost"]["peak_vram_mib"],
                "throughput": kc_e1["throughput"],
            },
            "ku-e1c": {
                "prompt_tokens": ku_e1c["tokens"]["prompt_tokens_total"],
                "completion_tokens": ku_e1c["tokens"]["completion_tokens_total"],
                "per_window_prompt": ku_e1c["tokens"]["per_window_prompt"],
                "per_window_completion": ku_e1c["tokens"]["per_window_completion"],
                "worst_realized_request": ku_e1c["tokens"]["worst_realized_request"],
                "slot_tokens": ku_e1c["tokens"]["slot_tokens"],
                "margin_factor": ku_e1c["tokens"]["margin_factor"],
                "fit_reference": ku_e1c["tokens"]["fit_reference"],
                "gpu_hours": ku_e1c["cost"]["gpu_hours"],
                "gpu_seconds": ku_e1c["cost"]["gpu_seconds"],
                "audio_seconds_used": ku_e1c["cost"]["audio_seconds_used"],
                "peak_vram_mib": ku_e1c["cost"]["peak_vram_mib"],
                "comparator_gpu_hours": ku_e1c["cost"]["comparator_gpu_hours"],
                "throughput": ku_e1c["throughput"],
            },
        },
        "saturation_reported_by_the_flights": {
            "kc-e1": kc_e1["saturation"],
            "ku-e1c": ku_e1c["saturation"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reaggregation-dir", type=Path, required=True)
    parser.add_argument("--rows-dir", type=Path, required=True)
    parser.add_argument(
        "--rows-prefix",
        default="verdict-v1-window-rows-",
        help="rows file basename prefix; the arm slug and .json complete it",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=wp.E21_WINDOW_SEED)
    parser.add_argument("--replicates", type=int, default=wp.E21_WINDOW_REPLICATES)
    parser.add_argument("--ci-level", type=float, default=wp.E21_WINDOW_CI_LEVEL)
    parser.add_argument(
        "--kc-e1-flight-receipt",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-06-e21-kc-e1-brief-44-v1/flight/flight-receipt.json",
    )
    parser.add_argument(
        "--ku-e1c-flight-receipt",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-06-e21-kc-e1-brief-44-v1/flight-placebo/flight-receipt.json",
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

    anchors: dict[str, dict] = {}
    rows_by_arm: dict[str, list[dict]] = {}
    rows_files: dict[str, dict] = {}
    for slug in ARM_RUNS:
        anchor = _identity_anchor(args.reaggregation_dir / slug / "reaggregation.json")
        if anchor["verdict"] != "PASS" or anchor["checks_failed"]:
            raise SystemExit(
                f"arm {slug!r} did not reproduce its own sealed numbers "
                f"({anchor['failed_checks']}); no contrast is computed"
            )
        if anchor["source_run_id"] != ARM_RUNS[slug]:
            raise SystemExit(
                f"arm {slug!r} anchor names run {anchor['source_run_id']!r}, expected "
                f"{ARM_RUNS[slug]!r}"
            )
        rows_path = args.rows_dir / f"{args.rows_prefix}{slug}.json"
        document = _load_rows(rows_path)
        if document["source_run_id"] != ARM_RUNS[slug]:
            raise SystemExit(f"{rows_path} is not {ARM_RUNS[slug]}'s rows file")
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

    by_window: dict[str, dict[str, dict]] = {}
    for slug, rows in rows_by_arm.items():
        by_window[slug] = {row["window_id"]: row for row in rows}
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
            identifier
            for identifier, row in table.items()
            if bool(row.get("saturated"))
        )
        for slug, table in by_window.items()
    }
    saturated_union = sorted({wid for ids in saturated.values() for wid in ids})
    surviving_ids = tuple(wid for wid in window_ids if wid not in set(saturated_union))
    # A saturated window is charged NO reference word -- obs_loop stitched nothing
    # from it, so charge_operations_to_windows lands its untranscribed reference
    # mass on the NEIGHBOURING window's deletion cursor. Dropping the window
    # therefore cannot remove that cost, and a window-level exclusion is close to
    # vacuous here. The honest exclusion is at the CALL, which removes the whole
    # cluster the saturated slice sits in from every arm.
    saturated_calls = sorted({wp.call_of(wid) for wid in saturated_union})
    surviving_call_ids = tuple(
        wid for wid in window_ids if wp.call_of(wid) not in set(saturated_calls)
    )

    metrics = _window_metrics()

    def build(pairs_slug_left: str, pairs_slug_right: str, reader, ids):
        left_table = by_window[pairs_slug_left]
        right_table = by_window[pairs_slug_right]
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

        # Saturation sensitivity: drop the union of both treated arms' saturated
        # windows from ALL THREE arms and recompute the primary and the two hard
        # guards. Reported beside the primary, never replacing it.
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
                    call: sum(
                        1 for wid in surviving_ids if wp.call_of(wid) == call
                    )
                    for call in calls
                },
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
            )
        sensitivity[contrast] = sensitivity_block

        call_sensitivity_block: dict[str, dict] = {}
        surviving_calls = sorted(
            {wp.call_of(wid) for wid in surviving_call_ids}
        )
        for metric in ("entity_wer_PERSON", "corpus_wer", "insertions_per_reference_word"):
            reader, sign, note = metrics[metric]
            pairs = build(left_slug, right_slug, reader, surviving_call_ids)
            call_sensitivity_block[metric] = _contrast_block(
                metric=metric,
                note=note,
                sign=sign,
                pairs=pairs,
                window_ids=surviving_call_ids,
                windows_per_call={
                    call: windows_per_call[call] for call in surviving_calls
                },
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
            )
        call_sensitivity[contrast] = call_sensitivity_block

        # Descriptive layer at the window unit: saves / harms / ties and the exact
        # sign test at n = 1,593, through analysis.paired.paired_contrast. Its own
        # bootstrap is the MEAN of per-window differences and is NOT the decision
        # interval; it is carried so the reader can see the two estimators apart.
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

    # ---- the per-call table, all 44 calls, both headline metrics ----
    roster = {}
    if args.roster_table.exists():
        for line in args.roster_table.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit():
                roster[cells[0]] = cells[1]

    per_call: list[dict] = []
    for call in calls:
        entry: dict[str, object] = {"sample_id": call, "roster": roster.get(call, "unknown")}
        entry["windows"] = windows_per_call[call]
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
        per_call.append(entry)

    # ---- the E5 roster halves, reported apart ----
    roster_halves: dict[str, dict] = {}
    for label in sorted({entry["roster"] for entry in per_call}):
        members = {entry["sample_id"] for entry in per_call if entry["roster"] == label}
        ids = tuple(wid for wid in window_ids if wp.call_of(wid) in members)
        half: dict[str, dict] = {}
        for metric in ("corpus_wer", "entity_wer_PERSON", "entity_wer_ORG"):
            reader, sign, _note = metrics[metric]
            half[metric] = {}
            for slug in ARM_RUNS:
                numerator = denominator = 0
                for identifier in ids:
                    n, d = reader(by_window[slug][identifier])
                    numerator += n
                    denominator += d
                half[metric][slug] = (
                    100.0 * numerator / denominator if denominator else 0.0
                )
        roster_halves[label] = {"calls": len(members), "windows": len(ids), "pooled_percent": half}

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
                        "hypothesis_words_charged": by_window[slug][wid]["hypothesis_words"],
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
            "The two treated arms saturated two windows each on FOUR DISJOINT calls, so "
            "the covariate is balanced in count and carried by different calls in each "
            "arm. A saturated window contributes the empty string to its arm's stitched "
            "hypothesis (reproduction.obs_loop's own quarantine), so it is charged no "
            "operation at all and its reference words fall out of that arm's totals as "
            "deletions charged to the neighbouring window's cursor. The sensitivity "
            "excludes the UNION from all three arms and is reported beside the primary, "
            "never in place of it. Two exclusions are reported, because the window-level "
            "one is nearly vacuous: a saturated window is charged NO reference word (it "
            "stitched nothing), so its untranscribed reference mass has already landed on "
            "the NEIGHBOURING window's deletion cursor and dropping the window cannot "
            "remove it. The CALL-level exclusion drops the whole cluster the saturated "
            "slice sits in, from all three arms, and is the one that actually bounds the "
            "covariate."
        ),
    }

    covariate = _token_throughput_covariate(
        kc_e1_path=args.kc_e1_flight_receipt,
        ku_e1c_path=args.ku_e1c_flight_receipt,
    )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "token-throughput-covariate.json").write_text(
        json.dumps(covariate, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = {
        "schema": RESULT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW,
        "decides": "SAEA-E21-KC-E1-BRIEF-44-V1",
        "preregistration": (
            "docs/readiness/2026-09-06-e21-kc-e1-pre-meeting-brief-v2-preregistration.md"
        ),
        "arms": ARM_RUNS,
        "identity_anchors": anchors,
        "rows_files": rows_files,
        "pairing": {
            "unit": "fixed 90-second window",
            "cluster": "call",
            "windows": len(window_ids),
            "calls": len(calls),
            "seed": args.seed,
            "n_replicates": args.replicates,
            "ci_level": args.ci_level,
            "estimator": "pooled ratio, sum(numerator) / sum(denominator) over the resampled units",
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
            "no model, GPU, tool, embedding, tokenizer, network, audio-decode or paid-API "
            "contact; no reference transcript is opened by this script"
        ),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    (args.out_dir / "result-summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "| call | roster | windows | baseline corpus WER % | placebo corpus WER % | brief corpus WER % "
        "| baseline PERSON % | placebo PERSON % | brief PERSON % | PERSON ref words | saturated (brief/placebo) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for entry in per_call:
        def fmt(value):
            return "--" if value is None else f"{value:.2f}"

        lines.append(
            f"| {entry['sample_id']} | {entry['roster']} | {entry['windows']} "
            f"| {fmt(entry['comparator_corpus_wer_percent'])} "
            f"| {fmt(entry['ku-e1c_corpus_wer_percent'])} "
            f"| {fmt(entry['kc-e1_corpus_wer_percent'])} "
            f"| {fmt(entry['comparator_person_entity_wer_percent'])} "
            f"| {fmt(entry['ku-e1c_person_entity_wer_percent'])} "
            f"| {fmt(entry['kc-e1_person_entity_wer_percent'])} "
            f"| {entry['comparator_person_reference_words']} "
            f"| {entry['kc-e1_saturated_windows']}/{entry['ku-e1c_saturated_windows']} |"
        )
    (args.out_dir / "per-call-table.md").write_text(
        "# KC-E1 verdict — the 44 calls, corpus WER and PERSON entity WER, three arms\n\n"
        "Pooled per call from the sealed per-window rows of each arm. `baseline` is\n"
        "`SAEA-E21-FULL44-DIRECT-BASELINE-V2`, `placebo` is `SAEA-E21-KU-E1C-PLACEBO-44-V1`,\n"
        "`brief` is `SAEA-E21-KC-E1-BRIEF-44-V1`. PERSON entity WER is `(S + D) / tagged\n"
        "reference words`; the reference-word count is identical in all three arms and is\n"
        "printed once.\n\n" + "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"windows {len(window_ids)} calls {len(calls)}")
    for contrast, left_slug, right_slug, _note in CONTRASTS:
        person = results[contrast]["metrics"]["entity_wer_PERSON"]
        corpus = results[contrast]["metrics"]["corpus_wer"]
        interval = person["natural_mixture_call_clustered"]
        corpus_interval = corpus["natural_mixture_call_clustered"]
        print(
            f"{contrast:8} PERSON reduction {100*interval['point_estimate']:+.3f} pp "
            f"[{100*interval['ci_low']:+.3f}, {100*interval['ci_high']:+.3f}]   "
            f"corpus improvement {100*corpus_interval['point_estimate']:+.3f} pp "
            f"[{100*corpus_interval['ci_low']:+.3f}, {100*corpus_interval['ci_high']:+.3f}]"
        )
    print(f"elapsed {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
