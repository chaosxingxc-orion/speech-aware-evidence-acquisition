#!/usr/bin/env python3
"""The paired read of `SAEA-E21-FULL44-TAIL2S-V1` against its sealed comparator.

Exposure row `SAEA-E21-FULL44-TAIL2S-V1` (the cell's own; this read spends no
model, GPU, tool, embedding, network or audio-decode contact and opens no
Earnings-22 surface).  Section 4.3 of
`docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md` is
the rule; section 2 fixes the pairing and the statistics; section 4.4's media
falsifier is a SEPARATE step that runs before any score file is opened and is
not repeated here.

What it computes, in the order section 2 requires:

1. **The identity gate.**  The sealed comparator reproduces section 1.4's own
   published anchors from its own committed score receipts, to the digit,
   before a single contrast is computed.
2. **The call-clustered contrast**, which section 2 names the HONEST interval:
   44 clusters, `analysis.paired.resampled_statistic` over the pooled ratio,
   10,000 replicates, seed 20260903, CI90.
3. **The window-level contrast** stratified by call, explicitly labelled the
   optimistic bound, and the section 4.3 clause-3 mechanism slice on the
   interior windows that end within 20 ms of active speech beside the windows
   that already carry 2.0 s or more.
4. **Both weightings**: the natural mixture (pooled over the corpus) and the
   equal-stratum mean of per-call rates.

Every number is signed as *cell minus comparator*, so a NEGATIVE corpus-WER
delta is an improvement and a POSITIVE numeric-accuracy delta is.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("SAEA_REPO_ROOT", "")
    or Path(__file__).resolve().parents[1]
)
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402
from speech_aware_evidence_acquisition.analysis import paired  # noqa: E402

CARRIER = "earnings21-original"
SPLIT_IDENTITY = "fcc1b0bc55432d02347dcdf730c6bcef561a9b0ad9605c45b367e1ed3da5d69e"
SEED = wp.E21_WINDOW_SEED
REPLICATES = wp.E21_WINDOW_REPLICATES
CI_LEVEL = wp.E21_WINDOW_CI_LEVEL

COMPARATOR_RUN = "SAEA-E21-FULL44-DIRECT-BASELINE-V2"
COMPARATOR_ATTEMPT = "attempt-20260904T233816Z-bcd338"

AGENTIC_BASELINE = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-agentic-metric-baseline"
    / "scoring/verified-score-read.json"
)
SEMANTIC_BASELINE = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-semantic-impact-baseline"
    / "verdict/result-summary.json"
)
ROSTER = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-04-e21-full44-roster"
    / "flight-roster-receipt.json"
)
TS2_ROSTER = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-07-e21-buf90-tail2s-media"
    / "roster/flight-roster-receipt.json"
)

#: Section 1.4's published anchors, quoted here so the identity gate compares
#: against a committed CLAIM rather than against whatever this run recomputes.
SEALED_ANCHORS = {
    "corpus_wer_percent": 8.1995,
    "substitutions": 13098,
    "deletions": 5701,
    "insertions": 10700,
    "reference_words": 359765,
    "conec_overall_wer_percent": 8.200,
    "conec_non_entity_wer_percent": 4.730,
    "numeric_value_accuracy_percent": 90.7335,
    "semantic_high_impact_error_rate_percent": 0.02780,
}

#: Section 3: Earnings-21 has NO measured same-request null.  The Earnings-22
#: null is IMPORTED and the verdict must say so.  Its own interval is
#: [-0.2356, +0.0692] corpus-WER points about a point estimate of -0.0844; the
#: half-width is (0.0692 - (-0.2356)) / 2.
E22_NULL_POINT = -0.0844
E22_NULL_LOW = -0.2356
E22_NULL_HIGH = +0.0692
IMPORTED_MARGIN = (E22_NULL_HIGH - E22_NULL_LOW) / 2.0  # 0.1524 points


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Per-call rows, one shape for both arms
# ---------------------------------------------------------------------------


def call_rows_from_score_read(document: dict) -> dict[str, dict]:
    """`{sample_id: {...}}` from a `core.scoring_batch --include-per-sample` read
    or from the committed agentic-metric baseline receipt (same shape)."""

    # A `core.scoring_batch` result wraps its scorers in a "scores" key; the
    # `scores.json` finalize seals is the same mapping unwrapped. Accept both,
    # and refuse anything that is neither.
    scores = document.get("scores") if "scores" in document else document
    if not isinstance(scores, dict) or "asr-wer-whisper" not in scores:
        raise SystemExit("score document carries no asr-wer-whisper block")
    rows: dict[str, dict] = {}

    for entry in scores["asr-wer-whisper"]["per_sample"]:
        sample_id = str(entry["sample_id"])
        rows[sample_id] = {
            "sample_id": sample_id,
            "substitutions": int(entry["substitutions"]),
            "deletions": int(entry["deletions"]),
            "insertions": int(entry["insertions"]),
            "hits": int(entry["hits"]),
            "reference_words": int(entry["substitutions"])
            + int(entry["deletions"])
            + int(entry["hits"]),
        }

    for entry in scores["conec-entity-wer-official"]["per_sample"]:
        row = rows[str(entry["sample_id"])]
        buckets = entry["by_entity_type"]
        overall = buckets["__ALL__"]
        non_entity = buckets["__NON_ENTITY__"]
        row["conec_reference_words"] = int(overall["reference_words"])
        row["conec_errors"] = int(overall["errors"])
        row["conec_non_entity_reference_words"] = int(non_entity["reference_words"])
        row["conec_non_entity_errors"] = int(non_entity["errors"])
        for entity in ("PERSON", "ORG", "GPE"):
            bucket = buckets.get(entity) or {"errors": 0, "reference_words": 0}
            row[f"conec_{entity.lower()}_errors"] = int(bucket["errors"])
            row[f"conec_{entity.lower()}_reference_words"] = int(bucket["reference_words"])

    for entry in scores["numeric-value-accuracy-v1"]["per_sample"]:
        row = rows[str(entry["sample_id"])]
        row["numeric_expected"] = int(entry["expected_numeric_words"])
        row["numeric_matched"] = int(entry["matched_numeric_words"])

    semantic = scores.get("semantic-high-impact-error-rate-v1")
    if semantic is not None:
        for entry in semantic["per_sample"]:
            row = rows[str(entry["sample_id"])]
            row["semantic_high_reference_words"] = int(entry["high_impact_reference_words"])
            row["semantic_reference_words"] = int(entry["reference_words"])
            row["semantic_high_insertions"] = int(entry["high_impact_insertions"])
    return rows


def attach_sealed_semantic(rows: dict[str, dict]) -> None:
    """The sealed comparator's manifest declared four scorers and the semantic
    one was scored under its OWN registered row, so its per-call figures come
    from that row's committed receipt rather than from the agentic-metric read."""

    document = load_json(SEMANTIC_BASELINE)
    for entry in document["per_call"]:
        row = rows[str(entry["sample_id"])]
        row["semantic_high_reference_words"] = int(entry["high_impact_reference_words"])
        row["semantic_reference_words"] = int(entry["reference_words"])
        row["semantic_high_insertions"] = int(entry["high_impact_insertions"])


# ---------------------------------------------------------------------------
# Pooled ratios
# ---------------------------------------------------------------------------

#: name -> (numerator key, denominator key, "lower is better"?, scale)
POOLED = {
    "corpus_wer_percent": ("__wer_errors", "reference_words", True, 100.0),
    "conec_overall_wer_percent": ("conec_errors", "conec_reference_words", True, 100.0),
    "conec_non_entity_wer_percent": (
        "conec_non_entity_errors",
        "conec_non_entity_reference_words",
        True,
        100.0,
    ),
    "conec_person_wer_percent": (
        "conec_person_errors",
        "conec_person_reference_words",
        True,
        100.0,
    ),
    "conec_org_wer_percent": ("conec_org_errors", "conec_org_reference_words", True, 100.0),
    "numeric_value_accuracy_percent": ("numeric_matched", "numeric_expected", False, 100.0),
    "semantic_high_impact_error_rate_percent": (
        "semantic_high_reference_words",
        "semantic_reference_words",
        True,
        100.0,
    ),
}


def derived(row: dict) -> dict:
    row = dict(row)
    row["__wer_errors"] = row["substitutions"] + row["deletions"] + row["insertions"]
    return row


def pooled(rows: dict[str, dict], ids, numerator: str, denominator: str, scale: float) -> float:
    top = sum(rows[i][numerator] for i in ids)
    bottom = sum(rows[i][denominator] for i in ids)
    return (scale * top / bottom) if bottom else 0.0


def equal_stratum(rows: dict[str, dict], ids, numerator: str, denominator: str, scale: float) -> float:
    """Equal-stratum weighting: the unweighted mean of the per-call rates."""

    values = [
        scale * rows[i][numerator] / rows[i][denominator]
        for i in ids
        if rows[i][denominator]
    ]
    return statistics.fmean(values) if values else 0.0


def bootstrap_delta(
    left: dict[str, dict],
    right: dict[str, dict],
    ids,
    numerator: str,
    denominator: str,
    scale: float,
    *,
    cluster_of=None,
    strata_of=None,
) -> dict:
    """CI on `pooled(right) - pooled(left)` under this study's frozen draws."""

    ids = list(ids)

    def statistic(resampled):
        return pooled(right, resampled, numerator, denominator, scale) - pooled(
            left, resampled, numerator, denominator, scale
        )

    result = paired.resampled_statistic(
        sample_ids=ids,
        statistic=statistic,
        seed=SEED,
        n_replicates=REPLICATES,
        ci_level=CI_LEVEL,
        cluster_of=cluster_of,
        strata_of=strata_of,
    )
    return {
        "point": result.point_estimate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "sigma_hat": result.sigma_hat,
        "n": len(ids),
        "replicates": REPLICATES,
        "seed": SEED,
        "ci_level": CI_LEVEL,
    }


# ---------------------------------------------------------------------------
# The window decomposition
# ---------------------------------------------------------------------------


def _saturated_request_ids(trace_path: Path) -> set[str]:
    """Base request ids whose OBS record says the decode saturated or was skipped."""

    out: set[str] = set()
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("channel") != "OBS":
            continue
        payload = record.get("payload") or {}
        if payload.get("obs_saturated") or payload.get("obs_skipped"):
            out.add(str(record["record_id"]).split("/", 1)[0])
    return out


def _quarantine_saturated(windows, trace_path: Path):
    """`reproduction.obs_loop` replaces a decode-cap-saturated slice's text with
    `""` BEFORE the stitch (its "saturation quarantine"), but
    `analysis.e21_window_pairing.stitched_windows_from_trace` recovers each
    window from the raw `MODEL_RESPONSE` and so re-admits exactly what the stitch
    excluded. The KC-E1 closure named that defect
    (`docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-44-v1/flight/README.md`)
    and it is repaired under the instrument's own row
    `SAEA-E21-MF-WINDOW-PAIRING-V1`.

    This applies the SAME rule on top of the registered instrument rather than
    re-implementing its reader, and only while the instrument itself does not yet
    carry the flag; `assert_stitch_reproduces_outputs` then proves the result
    byte for byte, so a wrong quarantine cannot pass silently. The comparator
    saturated no window, so on that arm this is a no-op by construction.
    """

    from dataclasses import replace

    if "saturated" in wp.WindowSpan.__dataclass_fields__:
        return windows, {
            call: tuple(span.identifier for span in spans if getattr(span, "saturated", False))
            for call, spans in windows.items()
        }
    saturated = _saturated_request_ids(trace_path)
    if not saturated:
        return windows, {}
    repaired = {}
    hit: dict[str, tuple[str, ...]] = {}
    for call, spans in windows.items():
        new_spans = []
        names = []
        for span in spans:
            if span.request_id in saturated and span.text:
                new_spans.append(replace(span, text=""))
                names.append(span.identifier)
            else:
                new_spans.append(span)
        repaired[call] = tuple(new_spans)
        if names:
            hit[call] = tuple(names)
    return repaired, hit


def window_rows(trace_path: Path, outputs_path: Path, data_root: Path, lock, taxonomy):
    """Per-window operation rows for ONE arm, through the registered instrument."""

    from speech_aware_evidence_acquisition.data.references import (
        reference_entity_mentions,
        reference_tokens,
    )
    from speech_aware_evidence_acquisition.reproduction import conec_entity_scoring as conec
    from speech_aware_evidence_acquisition.reproduction import semantic_impact
    from speech_aware_evidence_acquisition.reproduction.asr_wer_whisper import (
        normalize_whisper_english,
    )

    outputs_text = {}
    for line in outputs_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entry = json.loads(line)
            outputs_text[str(entry["sample_id"])] = str(entry["text"])

    windows = wp.stitched_windows_from_trace(trace_path)
    windows, _hit = _quarantine_saturated(windows, trace_path)
    # The instrument's own proof, run on whatever the two lines above produced:
    # if the quarantine were wrong the rebuild would not be byte-identical.
    wp.assert_stitch_reproduces_outputs(windows, outputs_text)
    saturated_requests = _saturated_request_ids(trace_path)

    rows: dict[str, dict] = {}
    for sample_id in sorted(windows):
        spans = windows[sample_id]
        raw_tokens = reference_tokens(lock, data_root, CARRIER, sample_id)
        mentions = reference_entity_mentions(lock, data_root, CARRIER, sample_id)
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
        if boundaries[-1] != len(hypothesis_words):
            raise SystemExit(
                f"sample {sample_id}: prefix boundaries end at {boundaries[-1]} but the "
                f"scorer aligned {len(hypothesis_words)} hypothesis words"
            )
        charged = wp.charge_operations_to_windows(operations, boundaries, len(hypothesis_words))

        for span, window_operations in zip(spans, charged):
            buckets = conec.entity_wer_buckets(window_operations, transferred, entity_types)
            impact = semantic_impact.semantic_impact_counts(
                window_operations, whole_words, hypothesis_words, taxonomy
            )
            overall = buckets[conec.OVERALL_BUCKET]
            rows[span.identifier] = {
                "window_id": span.identifier,
                "sample_id": sample_id,
                "window_index": span.window_index,
                "start_seconds": span.start_seconds,
                "end_seconds": span.end_seconds,
                "substitutions": overall["substitutions"],
                "deletions": overall["deletions"],
                "insertions": overall["insertions"],
                "reference_words": overall["reference_words"],
                "conec_errors": overall["errors"],
                "conec_reference_words": overall["reference_words"],
                "semantic_high_reference_words": impact["high_impact_reference_words"],
                "semantic_reference_words": impact["reference_words"],
                "saturated": bool(
                    getattr(span, "saturated", False)
                    or span.request_id in saturated_requests
                ),
            }
            row = rows[span.identifier]
            row["__wer_errors"] = (
                row["substitutions"] + row["deletions"] + row["insertions"]
            )
    return rows


# ---------------------------------------------------------------------------


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-read", type=Path, required=True)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    parser.add_argument("--run-id", default="SAEA-E21-FULL44-TAIL2S-V1")
    parser.add_argument("--data-root", type=Path, default=Path(
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--skip-windows", action="store_true")
    parser.add_argument(
        "--comparator-window-rows", type=Path, default=None,
        help="cache of the comparator's per-window rows; computed and written if absent",
    )
    parser.add_argument(
        "--cell-window-rows", type=Path, default=None,
        help="cache of the cell's per-window rows; computed and written if absent",
    )
    parser.add_argument(
        "--window-rows-only", choices=("comparator", "cell"), default=None,
        help=(
            "compute ONE arm's per-window rows into its cache and stop. The two arms "
            "are independent, so running this twice side by side halves the wall clock "
            "of the decomposition; the full read then finds both caches warm."
        ),
    )
    args = parser.parse_args(argv)

    if args.window_rows_only is not None:
        from speech_aware_evidence_acquisition.data.lock import (
            load_lock, umbrella_lock_path,
        )
        from speech_aware_evidence_acquisition.reproduction import semantic_impact

        lock = load_lock(umbrella_lock_path(REPO_ROOT))
        taxonomy = semantic_impact.load_taxonomy(
            REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
        )
        if args.window_rows_only == "comparator":
            directory = args.data_root / "runs" / COMPARATOR_RUN / COMPARATOR_ATTEMPT
            stem, cache = COMPARATOR_RUN, args.comparator_window_rows
        else:
            directory, stem, cache = args.attempt_dir, args.run_id, args.cell_window_rows
        if cache is None:
            raise SystemExit("--window-rows-only needs the matching --*-window-rows path")
        rows = window_rows(
            directory / f"{stem}.trace.jsonl",
            directory / f"{stem}.outputs.jsonl",
            args.data_root, lock, taxonomy,
        )
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(rows), encoding="utf-8")
        print(json.dumps({
            "arm": args.window_rows_only,
            "windows": len(rows),
            "calls": len({row["sample_id"] for row in rows.values()}),
            "saturated": sorted(w for w, r in rows.items() if r["saturated"]),
            "errors": sum(row["__wer_errors"] for row in rows.values()),
            "reference_words": sum(row["reference_words"] for row in rows.values()),
            "out": str(cache),
        }, indent=1))
        return 0

    roster = load_json(ROSTER)
    sector_of = {row["sample_id"]: row["sector"] for row in roster["calls"]}
    rate_of = {row["sample_id"]: str(row["sample_rate_hz"]) for row in roster["calls"]}
    windows_of = {row["sample_id"]: int(row["fixed_90s_windows"]) for row in roster["calls"]}

    comparator = {k: derived(v) for k, v in call_rows_from_score_read(
        load_json(AGENTIC_BASELINE)).items()}
    attach_sealed_semantic(comparator)
    cell = {k: derived(v) for k, v in call_rows_from_score_read(
        load_json(args.score_read)).items()}

    ids = sorted(set(comparator) & set(cell))
    result: dict = {
        "schema": "saea-e21-tail2s-verdict-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": args.run_id,
        "cell": args.run_id,
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT},
        "carrier_lock_key": CARRIER,
        "split_identity_hash": SPLIT_IDENTITY,
        "calls_paired": len(ids),
        "sign_convention": "every delta is cell minus comparator",
        "statistics": {
            "module": "analysis.paired.resampled_statistic",
            "seed": SEED,
            "replicates": REPLICATES,
            "ci_level": CI_LEVEL,
            "honest_interval": "call-clustered (44 clusters); section 2",
            "optimistic_interval": "window-level stratified by call; section 2 labels it a bound",
        },
        "null": {
            "measured_on_this_carrier": False,
            "imported_from": "Earnings-22 same-request null, 1,432 rows",
            "point": E22_NULL_POINT,
            "ci90": [E22_NULL_LOW, E22_NULL_HIGH],
            "imported_margin_half_width": IMPORTED_MARGIN,
            "note": (
                "Section 3: no same-request null has been measured on Earnings-21. The "
                "clause-1 threshold of -0.2356 and the clause-2 margin of "
                f"{IMPORTED_MARGIN:.4f} points are IMPORTED from Earnings-22, not measured "
                "here, and measuring this carrier's own null is the named next cell."
            ),
        },
    }

    # ---- 1. identity gate --------------------------------------------------
    gate = []

    def check(name, actual, expected, tolerance):
        ok = abs(actual - expected) <= tolerance
        gate.append(
            {"check": name, "actual": actual, "expected": expected,
             "verdict": "PASS" if ok else "FAIL"}
        )

    check("corpus_wer_percent",
          round(pooled(comparator, ids, "__wer_errors", "reference_words", 100.0), 4),
          SEALED_ANCHORS["corpus_wer_percent"], 0.0001)
    for key in ("substitutions", "deletions", "insertions", "reference_words"):
        check(key, sum(comparator[i][key] for i in ids), SEALED_ANCHORS[key], 0)
    check("conec_overall_wer_percent",
          round(pooled(comparator, ids, "conec_errors", "conec_reference_words", 100.0), 3),
          SEALED_ANCHORS["conec_overall_wer_percent"], 0.0005)
    check("conec_non_entity_wer_percent",
          round(pooled(comparator, ids, "conec_non_entity_errors",
                       "conec_non_entity_reference_words", 100.0), 3),
          SEALED_ANCHORS["conec_non_entity_wer_percent"], 0.0005)
    check("numeric_value_accuracy_percent",
          round(pooled(comparator, ids, "numeric_matched", "numeric_expected", 100.0), 4),
          SEALED_ANCHORS["numeric_value_accuracy_percent"], 0.0001)
    check("semantic_high_impact_error_rate_percent",
          round(pooled(comparator, ids, "semantic_high_reference_words",
                       "semantic_reference_words", 100.0), 5),
          SEALED_ANCHORS["semantic_high_impact_error_rate_percent"], 0.00001)
    result["identity_gate"] = {
        "verdict": "FAIL" if any(row["verdict"] == "FAIL" for row in gate) else "PASS",
        "checks": gate,
        "basis": (
            "the sealed comparator's own committed score receipts, re-pooled from its "
            "44 per-call rows; no arm is re-flown and no scorer is re-run"
        ),
    }
    if result["identity_gate"]["verdict"] == "FAIL":
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(result["identity_gate"], indent=1))
        return 1

    # ---- 2. call-clustered contrast (the honest interval) ------------------
    metrics: dict[str, dict] = {}
    for name, (numerator, denominator, lower_is_better, scale) in POOLED.items():
        left = pooled(comparator, ids, numerator, denominator, scale)
        right = pooled(cell, ids, numerator, denominator, scale)
        interval = bootstrap_delta(
            comparator, cell, ids, numerator, denominator, scale,
            cluster_of=lambda sample_id: sample_id,
        )
        metrics[name] = {
            "lower_is_better": lower_is_better,
            "comparator": left,
            "cell": right,
            "delta": right - left,
            "call_clustered_ci90": interval,
            "natural_mixture": {"comparator": left, "cell": right, "delta": right - left},
            "equal_stratum": {
                "comparator": equal_stratum(comparator, ids, numerator, denominator, scale),
                "cell": equal_stratum(cell, ids, numerator, denominator, scale),
                "delta": equal_stratum(cell, ids, numerator, denominator, scale)
                - equal_stratum(comparator, ids, numerator, denominator, scale),
            },
        }
    result["metrics"] = metrics

    # ---- per-call and per-stratum tables ----------------------------------
    result["per_call"] = [
        {
            "sample_id": sample_id,
            "sector": sector_of[sample_id],
            "sample_rate_hz": rate_of[sample_id],
            "windows": windows_of[sample_id],
            "comparator_wer_percent": 100.0 * comparator[sample_id]["__wer_errors"]
            / comparator[sample_id]["reference_words"],
            "cell_wer_percent": 100.0 * cell[sample_id]["__wer_errors"]
            / cell[sample_id]["reference_words"],
            "comparator_sdi": [comparator[sample_id]["substitutions"],
                               comparator[sample_id]["deletions"],
                               comparator[sample_id]["insertions"]],
            "cell_sdi": [cell[sample_id]["substitutions"], cell[sample_id]["deletions"],
                         cell[sample_id]["insertions"]],
            "reference_words": comparator[sample_id]["reference_words"],
            "comparator_numeric_accuracy_percent": 100.0
            * comparator[sample_id]["numeric_matched"] / comparator[sample_id]["numeric_expected"],
            "cell_numeric_accuracy_percent": 100.0
            * cell[sample_id]["numeric_matched"] / cell[sample_id]["numeric_expected"],
        }
        for sample_id in ids
    ]
    for row in result["per_call"]:
        row["wer_delta"] = row["cell_wer_percent"] - row["comparator_wer_percent"]

    # ---- the error structure: what actually moved -------------------------
    def totals(rows):
        return {
            "substitutions": sum(rows[i]["substitutions"] for i in ids),
            "deletions": sum(rows[i]["deletions"] for i in ids),
            "insertions": sum(rows[i]["insertions"] for i in ids),
            "reference_words": sum(rows[i]["reference_words"] for i in ids),
        }

    left_totals, right_totals = totals(comparator), totals(cell)
    for side in (left_totals, right_totals):
        side["errors"] = side["substitutions"] + side["deletions"] + side["insertions"]
        side["substitution_plus_deletion"] = side["substitutions"] + side["deletions"]
        side["insertion_share_of_errors"] = side["insertions"] / side["errors"]
    result["error_structure"] = {
        "comparator": left_totals,
        "cell": right_totals,
        "change": {
            key: right_totals[key] - left_totals[key]
            for key in ("substitutions", "deletions", "insertions", "errors",
                        "substitution_plus_deletion", "reference_words")
        },
        "insertion_share_change_pp": 100.0 * (
            right_totals["insertion_share_of_errors"]
            - left_totals["insertion_share_of_errors"]
        ),
        "reading": (
            "The ConEC entity buckets and the __NON_ENTITY__ bucket exclude insertions "
            "(fstalign's RecordTagWer cannot attribute an insertion to a tag), so they "
            "see only the substitution-plus-deletion block. Corpus WER counts all three. "
            "That is why the two families of metric move in opposite directions here."
        ),
    }

    strata_tables = {}
    for label, mapping in (("by_sector", sector_of), ("by_sample_rate_hz", rate_of)):
        table = {}
        for stratum in sorted({mapping[i] for i in ids}):
            members = [i for i in ids if mapping[i] == stratum]
            left = pooled(comparator, members, "__wer_errors", "reference_words", 100.0)
            right = pooled(cell, members, "__wer_errors", "reference_words", 100.0)
            table[stratum] = {
                "calls": len(members),
                "reference_words": sum(comparator[i]["reference_words"] for i in members),
                "comparator_wer_percent": left,
                "cell_wer_percent": right,
                "delta": right - left,
            }
        strata_tables[label] = table
    result["per_stratum"] = strata_tables

    # ---- 3. the window decomposition --------------------------------------
    if args.skip_windows:
        result["windows"] = {"status": "SKIPPED by request"}
    else:
        try:
            from speech_aware_evidence_acquisition.data.lock import (
                load_lock, umbrella_lock_path,
            )
            from speech_aware_evidence_acquisition.reproduction import semantic_impact

            lock = load_lock(umbrella_lock_path(REPO_ROOT))
            taxonomy = semantic_impact.load_taxonomy(
                REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
            )
            comparator_attempt = (
                args.data_root / "runs" / COMPARATOR_RUN / COMPARATOR_ATTEMPT
            )

            def cached(path, trace, outputs):
                if path is not None and Path(path).is_file():
                    return json.loads(Path(path).read_text(encoding="utf-8"))
                rows = window_rows(trace, outputs, args.data_root, lock, taxonomy)
                if path is not None:
                    Path(path).parent.mkdir(parents=True, exist_ok=True)
                    Path(path).write_text(json.dumps(rows), encoding="utf-8")
                return rows

            left_rows = cached(
                args.comparator_window_rows,
                comparator_attempt / f"{COMPARATOR_RUN}.trace.jsonl",
                comparator_attempt / f"{COMPARATOR_RUN}.outputs.jsonl",
            )
            right_rows = cached(
                args.cell_window_rows,
                args.attempt_dir / f"{args.run_id}.trace.jsonl",
                args.attempt_dir / f"{args.run_id}.outputs.jsonl",
            )
            result["windows"] = window_section(left_rows, right_rows)
        except Exception as error:  # noqa: BLE001 - reported, never swallowed
            result["windows"] = {
                "status": "BLOCKED",
                "error": f"{type(error).__name__}: {error}",
                "instrument_carries_saturation_fix": "saturated"
                in wp.WindowSpan.__dataclass_fields__,
                "named_cause": (
                    "analysis.e21_window_pairing.stitched_windows_from_trace re-admits a "
                    "decode-cap-saturated window's raw text, which reproduction.obs_loop "
                    "excluded from the stitch. Named by the KC-E1 closure "
                    "(docs/checks/speech-aware-evidence-acquisition/"
                    "2026-09-06-e21-kc-e1-brief-44-v1/flight/README.md) and fixed under the "
                    "instrument's own row SAEA-E21-MF-WINDOW-PAIRING-V1."
                ),
            }

    # ---- 4. the decision, section 4.3 quoted before it is applied ---------
    wer = metrics["corpus_wer_percent"]["call_clustered_ci90"]
    clause1 = {
        "rule": (
            "ADMITTED clause 1 -- Corpus WER, and it must beat the null. The CI90 upper "
            "bound on the delta is < -0.2356, below zero and disjoint from the "
            "Earnings-22 same-request null's interval, which is the closest measured null "
            "this carrier has and is labelled as imported."
        ),
        "delta": wer["point"],
        "ci90": [wer["ci_low"], wer["ci_high"]],
        "threshold_upper_bound_below": E22_NULL_LOW,
        "point_negative": wer["point"] < 0,
        "verdict": "PASS" if (wer["ci_high"] < E22_NULL_LOW and wer["point"] < 0) else "FAIL",
    }
    clause2_rows = []
    for name in (
        "numeric_value_accuracy_percent",
        "conec_overall_wer_percent",
        "conec_non_entity_wer_percent",
        "semantic_high_impact_error_rate_percent",
    ):
        block = metrics[name]
        interval = block["call_clustered_ci90"]
        if block["lower_is_better"]:
            ok = interval["ci_high"] < IMPORTED_MARGIN
            bound = f"CI90 upper {interval['ci_high']:.5f} < +{IMPORTED_MARGIN:.4f}"
            harm_demonstrated = interval["ci_low"] > 0.0
            improvement_demonstrated = interval["ci_high"] < 0.0
        else:
            ok = interval["ci_low"] > -IMPORTED_MARGIN
            bound = f"CI90 lower {interval['ci_low']:.5f} > -{IMPORTED_MARGIN:.4f}"
            harm_demonstrated = interval["ci_high"] < 0.0
            improvement_demonstrated = interval["ci_low"] > 0.0
        clause2_rows.append({
            "metric": name,
            "lower_is_better": block["lower_is_better"],
            "comparator": block["comparator"],
            "cell": block["cell"],
            "delta": block["delta"],
            "ci90": [interval["ci_low"], interval["ci_high"]],
            "non_inferiority_test": bound,
            "excludes_zero": interval["ci_low"] > 0 or interval["ci_high"] < 0,
            # Three separate questions, kept separate on purpose: a metric can
            # fail non-inferiority at an IMPORTED margin without any harm having
            # been demonstrated, when its own interval is simply wider than that
            # margin. Reporting only the PASS/FAIL would read as a harm.
            "harm_demonstrated": harm_demonstrated,
            "improvement_demonstrated": improvement_demonstrated,
            "reading": (
                "harm demonstrated" if harm_demonstrated
                else "improvement demonstrated" if improvement_demonstrated
                else "interval straddles zero: neither a demonstrated harm nor a "
                     "demonstrated improvement"
            ),
            "verdict": "PASS" if ok else "FAIL",
            "why_not" : None if ok else (
                "the CI90 is WIDER than the imported margin, so non-inferiority "
                "cannot be established at that margin; this is a statement about "
                "the margin and the interval, not a measured worsening"
            ),
        })
    clause2 = {
        "rule": (
            "ADMITTED clause 2 -- No agentic metric worsens. numeric-value-accuracy-v1 and "
            "conec-entity-wer-official (overall and non-entity) are non-inferior at their "
            "own CI90, and semantic-high-impact-error-rate-v1 does not rise. Its sealed "
            "0.02780 % is a STRICT LOWER BOUND on the true content-impact rate and this "
            "verdict repeats that when it uses it."
        ),
        "margin": IMPORTED_MARGIN,
        "margin_basis": (
            "IMPORTED, not measured: section 3 says a carrier with no measured null uses "
            "zero plus a margin equal to the Earnings-22 null's own half-width on the same "
            "scale. Earnings-21 has no measured same-request null."
        ),
        "metrics": clause2_rows,
        "any_harm_demonstrated": any(r["harm_demonstrated"] for r in clause2_rows),
        "metrics_failing_non_inferiority": [
            r["metric"] for r in clause2_rows if r["verdict"] == "FAIL"
        ],
        "verdict": "PASS" if all(r["verdict"] == "PASS" for r in clause2_rows) else "FAIL",
    }
    clause3 = result["windows"].get("clause_3") if isinstance(result.get("windows"), dict) else None
    if clause3 is None:
        clause3 = {
            "rule": (
                "ADMITTED clause 3 -- The effect concentrates where the audit predicts: the "
                "per-window contrast is larger on the interior windows that end within 20 ms "
                "of active speech than on the windows that already carry 2.0 s or more."
            ),
            "verdict": "BLOCKED",
            "why": result.get("windows", {}).get("error", "window decomposition unavailable"),
        }
    verdicts = [clause1["verdict"], clause2["verdict"], clause3["verdict"]]
    result["decision"] = {
        "rule_source": (
            "docs/readiness/2026-09-07-cross-carrier-silence-tail-v1-preregistration.md "
            "section 4.3, quoted verbatim above each clause before it is applied"
        ),
        "clause_1_corpus_wer": clause1,
        "clause_2_no_agentic_metric_worsens": clause2,
        "clause_3_mechanism_concentration": clause3,
        "verdict": (
            "ADMITTED" if all(v == "PASS" for v in verdicts)
            else ("BLOCKED" if "BLOCKED" in verdicts and "FAIL" not in verdicts
                  else "NOT ADMITTED")
        ),
    }

    # ---- 5. the signed prediction of section 5 ----------------------------
    result["prediction_check"] = {
        "section_5": (
            "Earnings-21: largest effect, same direction, smaller in size than "
            "Earnings-22's. Predicted corpus-WER delta -0.2 to -1.5 points from the "
            "sealed 8.1995."
        ),
        "predicted_range": [-1.5, -0.2],
        "observed_delta": wer["point"],
        "inside_predicted_range": -1.5 <= wer["point"] <= -0.2,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "identity_gate": result["identity_gate"]["verdict"],
        "corpus_wer": metrics["corpus_wer_percent"],
        "windows": result["windows"].get("status", "OK"),
        "decision": result["decision"]["verdict"],
        "clauses": [
            result["decision"]["clause_1_corpus_wer"]["verdict"],
            result["decision"]["clause_2_no_agentic_metric_worsens"]["verdict"],
            result["decision"]["clause_3_mechanism_concentration"]["verdict"],
        ],
        "prediction": result["prediction_check"],
        "out": str(args.out),
    }, indent=1, default=str))
    return 0


def window_section(left_rows: dict, right_rows: dict) -> dict:
    """The window-level intervals plus section 4.3's clause-3 mechanism slice."""

    ts2 = load_json(TS2_ROSTER)
    trailing = {}
    final_index = {}
    for item in ts2["items"]:
        window_id = item["sample_id"].split("@")[0]
        trailing[window_id] = float(item["source_trailing_silence_seconds"])
        call = item["call_sample_id"]
        final_index[call] = max(final_index.get(call, 0), int(item["window_index"]))

    shared = sorted(set(left_rows) & set(right_rows))
    # A window id is a POSITION in the stitch order, so a skipped slice in one
    # arm would shift every later id and pair two different spans. Refuse that
    # rather than report it: every paired id must carry the same cut span.
    misaligned = [
        w for w in shared
        if (left_rows[w]["start_seconds"], left_rows[w]["end_seconds"])
        != (right_rows[w]["start_seconds"], right_rows[w]["end_seconds"])
    ]
    section: dict = {
        "status": "OK" if not misaligned and len(shared) == len(left_rows) == len(right_rows)
        else "MISALIGNED",
        "windows_left": len(left_rows),
        "windows_right": len(right_rows),
        "windows_paired": len(shared),
        "span_misaligned": len(misaligned),
        "span_misaligned_examples": misaligned[:10],
        "saturated_left": sorted(w for w in left_rows if left_rows[w]["saturated"]),
        "saturated_right": sorted(w for w in right_rows if right_rows[w]["saturated"]),
    }
    if section["status"] == "MISALIGNED":
        return section

    def interval(ids, numerator, denominator, strata_of=None, cluster_of=None):
        return bootstrap_delta(left_rows, right_rows, ids, numerator, denominator, 100.0,
                               strata_of=strata_of, cluster_of=cluster_of)

    section["corpus_wer_window_level_stratified_by_call_ci90"] = interval(
        shared, "__wer_errors", "reference_words", strata_of=wp.call_of
    )
    section["corpus_wer_window_level_clustered_by_call_ci90"] = interval(
        shared, "__wer_errors", "reference_words", cluster_of=wp.call_of
    )

    interior_mid_speech = [
        w for w in shared
        if trailing.get(w, 0.0) <= 0.02
        and left_rows[w]["window_index"] != final_index.get(left_rows[w]["sample_id"])
    ]
    already_silent = [w for w in shared if trailing.get(w, 0.0) >= 2.0]
    others = [w for w in shared if w not in set(interior_mid_speech) | set(already_silent)]

    slices = {}
    for label, subset in (
        ("interior_ends_within_20ms_of_speech", interior_mid_speech),
        ("already_carries_2s_or_more", already_silent),
        ("remainder", others),
    ):
        if not subset:
            slices[label] = {"n": 0}
            continue
        left = pooled(left_rows, subset, "__wer_errors", "reference_words", 100.0)
        right = pooled(right_rows, subset, "__wer_errors", "reference_words", 100.0)
        slices[label] = {
            "n": len(subset),
            "comparator_wer_percent": left,
            "cell_wer_percent": right,
            "delta": right - left,
            "clustered_by_call_ci90": interval(
                subset, "__wer_errors", "reference_words", cluster_of=wp.call_of
            ),
        }
    section["mechanism_slices"] = slices
    a = slices["interior_ends_within_20ms_of_speech"]
    b = slices["already_carries_2s_or_more"]
    section["clause_3"] = {
        "rule": (
            "section 4.3 item 3: the per-window contrast is LARGER on the interior "
            "windows that end within 20 ms of active speech than on the windows that "
            "already carry 2.0 s or more of trailing silence"
        ),
        "interior_delta": a.get("delta"),
        "already_silent_delta": b.get("delta"),
        "verdict": (
            "PASS" if (a.get("n") and b.get("n") and a["delta"] < b["delta"]) else "FAIL"
        ),
    }
    return section


if __name__ == "__main__":
    raise SystemExit(main())
