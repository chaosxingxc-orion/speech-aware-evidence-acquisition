#!/usr/bin/env python3
"""The paired read of `SAEA-E21-FULL44-NULL-REPLICATE-V1` against its sealed comparator.

Exposure row `SAEA-E21-FULL44-NULL-REPLICATE-V1`; this read spends no model, GPU,
tool, embedding, network or audio-decode contact and opens no Earnings-22 surface.
`docs/readiness/2026-09-08-e21-own-null-replicate-v1-preregistration.md` is the rule.
Section 2's falsifier is a SEPARATE step that runs before any score file is opened and
is not repeated here.

**This read decides nothing.** There is no ADMITTED/NOT-ADMITTED verdict, because the
cell has no factor to admit: it is the same request, twice.  Its whole output is the
NULL DISTRIBUTION -- per metric, the delta, its call-clustered CI90 and that interval's
half-width, which section 4 fixes in advance as the per-metric non-inferiority margin
of every future Earnings-21 cell.

Every statistic is computed by the same functions the tail cell's read used
(`build_e21_tail2s_verdict`), so the null and the effects it will be compared against
come out of one instrument rather than two dialects: the identity gate, the pooled
ratios, `analysis.paired.resampled_statistic` at 10,000 replicates / seed 20260903 /
CI90, and `analysis.e21_window_pairing`'s per-window decomposition with its own
byte-for-byte stitch proof.

Signed as *replicate minus comparator* throughout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("SAEA_REPO_ROOT", "")
    or "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition"
)
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
for candidate in (Path(__file__).resolve().parent, REPO_ROOT / "scripts"):
    if (candidate / "build_e21_tail2s_verdict.py").is_file():
        sys.path.insert(0, str(candidate))
        break

import build_e21_tail2s_verdict as t2  # noqa: E402
from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402

RUN_ID = "SAEA-E21-FULL44-NULL-REPLICATE-V1"
COMPARATOR_RUN = t2.COMPARATOR_RUN
COMPARATOR_ATTEMPT = t2.COMPARATOR_ATTEMPT

#: Section 3 of the cross-carrier preregistration: the margin Earnings-21 has been
#: borrowing.  Reported beside every measured half-width so the replacement is visible.
IMPORTED_MARGIN = t2.IMPORTED_MARGIN

#: Section 5's signed predictions.
PREDICTED_WER_RANGE = (-0.35, +0.35)
PREDICTED_IDENTITY_RATE_BELOW = 0.60
PREDICTED_SATURATION_RANGE = (0, 2)


def raw_completions(trace_path: Path) -> dict[str, str]:
    """base request id -> the raw `MODEL_RESPONSE` text, before obs_loop's
    saturation quarantine.  The quarantined text is what enters the hypothesis;
    the raw text is what the model actually emitted, and the null wants both."""

    out: dict[str, str] = {}
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        payload = record.get("payload") or {}
        if record.get("channel") != "MODEL_RESPONSE" or payload.get("stitch"):
            continue
        out[str(record.get("record_id", "")).split("/", 1)[0]] = str(payload["text"])
    return out


def identity_section(left_trace: Path, right_trace: Path) -> dict:
    """The per-window text-identity rate, on both the accepted span and the raw
    completion, plus the per-call rate."""

    left = wp.stitched_windows_from_trace(left_trace)
    right = wp.stitched_windows_from_trace(right_trace)
    left_raw, right_raw = raw_completions(left_trace), raw_completions(right_trace)

    left_span = {
        span.identifier: span for spans in left.values() for span in spans
    }
    right_span = {
        span.identifier: span for spans in right.values() for span in spans
    }
    shared = sorted(set(left_span) & set(right_span))

    accepted_identical: list[str] = []
    raw_identical: list[str] = []
    differing: list[str] = []
    for window_id in shared:
        a, b = left_span[window_id], right_span[window_id]
        if a.text == b.text:
            accepted_identical.append(window_id)
        else:
            differing.append(window_id)
        if left_raw.get(a.request_id, "") == right_raw.get(b.request_id, ""):
            raw_identical.append(window_id)

    per_call: dict[str, dict] = {}
    for sample_id, spans in left.items():
        ids = [span.identifier for span in spans if span.identifier in set(shared)]
        same = sum(1 for w in ids if left_span[w].text == right_span[w].text)
        per_call[sample_id] = {
            "windows": len(ids),
            "identical": same,
            "identity_rate": same / len(ids) if ids else 0.0,
        }
    calls_all_identical = [c for c, row in per_call.items() if row["identical"] == row["windows"]]

    return {
        "windows_paired": len(shared),
        "accepted_span_identical": len(accepted_identical),
        "accepted_span_identity_rate": len(accepted_identical) / len(shared) if shared else 0.0,
        "raw_completion_identical": len(raw_identical),
        "raw_completion_identity_rate": len(raw_identical) / len(shared) if shared else 0.0,
        "windows_differing": len(differing),
        "calls_with_every_window_identical": sorted(calls_all_identical),
        "per_call": per_call,
        "basis": (
            "accepted span = analysis.e21_window_pairing.WindowSpan.text, which is what "
            "reproduction.obs_loop actually stitched (a decode-cap-saturated window "
            "contributes the empty string). raw completion = the window's own "
            "MODEL_RESPONSE text before that quarantine."
        ),
    }


def reaggregation_gate(rows: dict, label: str, anchors: dict | None) -> dict:
    """Per-window rows must re-aggregate to the arm's own corpus totals."""

    totals = {
        "windows": len(rows),
        "calls": len({row["sample_id"] for row in rows.values()}),
        "substitutions": sum(row["substitutions"] for row in rows.values()),
        "deletions": sum(row["deletions"] for row in rows.values()),
        "insertions": sum(row["insertions"] for row in rows.values()),
        "reference_words": sum(row["reference_words"] for row in rows.values()),
    }
    totals["errors"] = (
        totals["substitutions"] + totals["deletions"] + totals["insertions"]
    )
    totals["corpus_wer_percent"] = 100.0 * totals["errors"] / totals["reference_words"]
    checks = []
    if anchors is not None:
        for key, expected in anchors.items():
            checks.append({
                "check": key,
                "actual": totals.get(key),
                "expected": expected,
                "verdict": "PASS" if totals.get(key) == expected else "FAIL",
            })
    return {
        "arm": label,
        "totals": totals,
        "checks": checks,
        "verdict": "FAIL" if any(c["verdict"] == "FAIL" for c in checks) else "PASS",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-read", type=Path, required=True)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--data-root", type=Path, default=Path(
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")))
    parser.add_argument("--comparator-window-rows", type=Path, required=True)
    parser.add_argument("--cell-window-rows", type=Path, required=True)
    parser.add_argument("--falsifier", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--window-rows-only", choices=("comparator", "cell"), default=None,
        help="compute ONE arm's per-window rows into its cache and stop",
    )
    args = parser.parse_args(argv)

    comparator_attempt = args.data_root / "runs" / COMPARATOR_RUN / COMPARATOR_ATTEMPT

    if args.window_rows_only is not None:
        from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
        from speech_aware_evidence_acquisition.reproduction import semantic_impact

        lock = load_lock(umbrella_lock_path(REPO_ROOT))
        taxonomy = semantic_impact.load_taxonomy(
            REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
        )
        if args.window_rows_only == "comparator":
            directory, stem, cache = comparator_attempt, COMPARATOR_RUN, args.comparator_window_rows
        else:
            directory, stem, cache = args.attempt_dir, args.run_id, args.cell_window_rows
        rows = t2.window_rows(
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

    roster = t2.load_json(t2.ROSTER)
    sector_of = {row["sample_id"]: row["sector"] for row in roster["calls"]}
    rate_of = {row["sample_id"]: str(row["sample_rate_hz"]) for row in roster["calls"]}
    windows_of = {row["sample_id"]: int(row["fixed_90s_windows"]) for row in roster["calls"]}

    comparator = {k: t2.derived(v) for k, v in t2.call_rows_from_score_read(
        t2.load_json(t2.AGENTIC_BASELINE)).items()}
    t2.attach_sealed_semantic(comparator)
    cell = {k: t2.derived(v) for k, v in t2.call_rows_from_score_read(
        t2.load_json(args.score_read)).items()}
    ids = sorted(set(comparator) & set(cell))

    result: dict = {
        "schema": "saea-e21-null-replicate-verdict-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": args.run_id,
        "cell": args.run_id,
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT},
        "carrier_lock_key": t2.CARRIER,
        "split_identity_hash": t2.SPLIT_IDENTITY,
        "calls_paired": len(ids),
        "decides_nothing": (
            "This is a REPLICATE, not a cell with a factor: the same request, twice. It "
            "admits and refutes nothing. Its output is the null distribution and the "
            "per-metric margins section 4 of the preregistration derives from it."
        ),
        "sign_convention": "every delta is replicate minus comparator",
        "statistics": {
            "module": "analysis.paired.resampled_statistic",
            "seed": t2.SEED,
            "replicates": t2.REPLICATES,
            "ci_level": t2.CI_LEVEL,
            "honest_interval": "call-clustered (44 clusters)",
            "optimistic_interval": "window-level stratified by call",
        },
    }
    if args.falsifier is not None and args.falsifier.is_file():
        falsifier = t2.load_json(args.falsifier)
        result["falsifier"] = {
            key: falsifier[key] for key in (
                "verdict", "windows_checked", "sealed_windows", "calls_checked",
                "disagreeing_rows", "wire", "saturated_slice_count", "saturated_windows",
                "skipped_slice_count", "compared_fields",
            ) if key in falsifier
        }

    # ---- 1. identity gate on the comparator -------------------------------
    gate = []

    def check(name, actual, expected, tolerance):
        ok = abs(actual - expected) <= tolerance
        gate.append({"check": name, "actual": actual, "expected": expected,
                     "verdict": "PASS" if ok else "FAIL"})

    A = t2.SEALED_ANCHORS
    check("corpus_wer_percent",
          round(t2.pooled(comparator, ids, "__wer_errors", "reference_words", 100.0), 4),
          A["corpus_wer_percent"], 0.0001)
    for key in ("substitutions", "deletions", "insertions", "reference_words"):
        check(key, sum(comparator[i][key] for i in ids), A[key], 0)
    check("conec_overall_wer_percent",
          round(t2.pooled(comparator, ids, "conec_errors", "conec_reference_words", 100.0), 3),
          A["conec_overall_wer_percent"], 0.0005)
    check("conec_non_entity_wer_percent",
          round(t2.pooled(comparator, ids, "conec_non_entity_errors",
                          "conec_non_entity_reference_words", 100.0), 3),
          A["conec_non_entity_wer_percent"], 0.0005)
    check("numeric_value_accuracy_percent",
          round(t2.pooled(comparator, ids, "numeric_matched", "numeric_expected", 100.0), 4),
          A["numeric_value_accuracy_percent"], 0.0001)
    check("semantic_high_impact_error_rate_percent",
          round(t2.pooled(comparator, ids, "semantic_high_reference_words",
                          "semantic_reference_words", 100.0), 5),
          A["semantic_high_impact_error_rate_percent"], 0.00001)
    result["identity_gate"] = {
        "verdict": "FAIL" if any(row["verdict"] == "FAIL" for row in gate) else "PASS",
        "checks": gate,
        "basis": (
            "the sealed comparator's own committed score receipts, re-pooled from its 44 "
            "per-call rows; no arm is re-flown and no scorer is re-run"
        ),
    }
    if result["identity_gate"]["verdict"] == "FAIL":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(result["identity_gate"], indent=1))
        return 1

    # ---- 2. the null table, per metric, at 44 clusters ---------------------
    metrics: dict[str, dict] = {}
    for name, (numerator, denominator, lower_is_better, scale) in t2.POOLED.items():
        left = t2.pooled(comparator, ids, numerator, denominator, scale)
        right = t2.pooled(cell, ids, numerator, denominator, scale)
        interval = t2.bootstrap_delta(
            comparator, cell, ids, numerator, denominator, scale,
            cluster_of=lambda sample_id: sample_id,
        )
        half_width = (interval["ci_high"] - interval["ci_low"]) / 2.0
        metrics[name] = {
            "lower_is_better": lower_is_better,
            "comparator": left,
            "replicate": right,
            "delta": right - left,
            "call_clustered_ci90": interval,
            "ci90_half_width": half_width,
            "measured_margin": half_width,
            "imported_margin_it_replaces": IMPORTED_MARGIN,
            "measured_margin_is_wider_than_imported": half_width > IMPORTED_MARGIN,
            "excludes_zero": interval["ci_low"] > 0 or interval["ci_high"] < 0,
            "equal_stratum": {
                "comparator": t2.equal_stratum(comparator, ids, numerator, denominator, scale),
                "replicate": t2.equal_stratum(cell, ids, numerator, denominator, scale),
            },
        }
    result["null_table"] = metrics
    result["margin_rule"] = {
        "rule": (
            "Section 4: for each metric the Earnings-21 non-inferiority margin becomes the "
            "half-width of this null's own call-clustered CI90, margin_m = (ci_high_m - "
            "ci_low_m) / 2, replacing the imported Earnings-22 half-width of "
            f"{IMPORTED_MARGIN:.4f} for THIS CARRIER ONLY. A future Earnings-21 cell "
            "demonstrates an effect on metric m iff its CI90 is disjoint from this null's "
            "MEASURED interval, not merely from zero."
        ),
        "measured_by": args.run_id,
        "margins": {
            name: {
                "margin": block["ci90_half_width"],
                "null_ci90": [block["call_clustered_ci90"]["ci_low"],
                              block["call_clustered_ci90"]["ci_high"]],
                "null_point": block["call_clustered_ci90"]["point"],
            }
            for name, block in metrics.items()
        },
        "caveat": (
            "A single replicate measures this null with 44 clusters and no more. The "
            "interval is itself uncertain; it is a better margin than an imported one, not "
            "an exact one, and every verdict that uses it must name this cell."
        ),
    }

    # ---- 3. per-call and per-stratum --------------------------------------
    result["per_call"] = [
        {
            "sample_id": sample_id,
            "sector": sector_of[sample_id],
            "sample_rate_hz": rate_of[sample_id],
            "windows": windows_of[sample_id],
            "comparator_wer_percent": 100.0 * comparator[sample_id]["__wer_errors"]
            / comparator[sample_id]["reference_words"],
            "replicate_wer_percent": 100.0 * cell[sample_id]["__wer_errors"]
            / cell[sample_id]["reference_words"],
            "comparator_sdi": [comparator[sample_id]["substitutions"],
                               comparator[sample_id]["deletions"],
                               comparator[sample_id]["insertions"]],
            "replicate_sdi": [cell[sample_id]["substitutions"], cell[sample_id]["deletions"],
                              cell[sample_id]["insertions"]],
            "reference_words": comparator[sample_id]["reference_words"],
            "comparator_numeric_accuracy_percent": 100.0
            * comparator[sample_id]["numeric_matched"] / comparator[sample_id]["numeric_expected"],
            "replicate_numeric_accuracy_percent": 100.0
            * cell[sample_id]["numeric_matched"] / cell[sample_id]["numeric_expected"],
        }
        for sample_id in ids
    ]
    for row in result["per_call"]:
        row["wer_delta"] = row["replicate_wer_percent"] - row["comparator_wer_percent"]
    deltas = [row["wer_delta"] for row in result["per_call"]]
    result["per_call_spread"] = {
        "calls_better": sum(1 for d in deltas if d < 0),
        "calls_worse": sum(1 for d in deltas if d > 0),
        "calls_identical": sum(1 for d in deltas if d == 0),
        "min_delta": min(deltas),
        "max_delta": max(deltas),
        "largest_absolute_delta_call": max(result["per_call"], key=lambda r: abs(r["wer_delta"]))[
            "sample_id"
        ],
    }

    def totals(rows):
        block = {
            "substitutions": sum(rows[i]["substitutions"] for i in ids),
            "deletions": sum(rows[i]["deletions"] for i in ids),
            "insertions": sum(rows[i]["insertions"] for i in ids),
            "reference_words": sum(rows[i]["reference_words"] for i in ids),
        }
        block["errors"] = block["substitutions"] + block["deletions"] + block["insertions"]
        block["substitution_plus_deletion"] = block["substitutions"] + block["deletions"]
        return block

    left_totals, right_totals = totals(comparator), totals(cell)
    result["error_structure"] = {
        "comparator": left_totals,
        "replicate": right_totals,
        "change": {key: right_totals[key] - left_totals[key] for key in left_totals},
    }

    strata_tables = {}
    for label, mapping in (("by_sector", sector_of), ("by_sample_rate_hz", rate_of)):
        table = {}
        for stratum in sorted({mapping[i] for i in ids}):
            members = [i for i in ids if mapping[i] == stratum]
            left = t2.pooled(comparator, members, "__wer_errors", "reference_words", 100.0)
            right = t2.pooled(cell, members, "__wer_errors", "reference_words", 100.0)
            table[stratum] = {
                "calls": len(members),
                "reference_words": sum(comparator[i]["reference_words"] for i in members),
                "comparator_wer_percent": left,
                "replicate_wer_percent": right,
                "delta": right - left,
            }
        strata_tables[label] = table
    result["per_stratum"] = strata_tables

    # ---- 4. the window level ----------------------------------------------
    left_rows = t2.load_json(args.comparator_window_rows)
    right_rows = t2.load_json(args.cell_window_rows)
    result["window_reaggregation"] = {
        "comparator": reaggregation_gate(left_rows, COMPARATOR_RUN, {
            "windows": 1593, "calls": 44,
            "substitutions": A["substitutions"], "deletions": A["deletions"],
            "insertions": A["insertions"], "reference_words": A["reference_words"],
        }),
        "replicate": reaggregation_gate(right_rows, args.run_id, {
            "windows": 1593, "calls": 44,
            "substitutions": right_totals["substitutions"],
            "deletions": right_totals["deletions"],
            "insertions": right_totals["insertions"],
            "reference_words": right_totals["reference_words"],
        }),
    }
    shared = sorted(set(left_rows) & set(right_rows))
    misaligned = [
        w for w in shared
        if (left_rows[w]["start_seconds"], left_rows[w]["end_seconds"])
        != (right_rows[w]["start_seconds"], right_rows[w]["end_seconds"])
    ]
    windows: dict = {
        "status": "OK" if not misaligned and len(shared) == len(left_rows) == len(right_rows)
        else "MISALIGNED",
        "windows_left": len(left_rows),
        "windows_right": len(right_rows),
        "windows_paired": len(shared),
        "span_misaligned": len(misaligned),
        "span_misaligned_examples": misaligned[:10],
        "saturated_comparator": sorted(w for w in left_rows if left_rows[w]["saturated"]),
        "saturated_replicate": sorted(w for w in right_rows if right_rows[w]["saturated"]),
    }
    if windows["status"] == "OK":
        for label, kwargs in (
            ("corpus_wer_window_level_clustered_by_call_ci90", {"cluster_of": wp.call_of}),
            ("corpus_wer_window_level_stratified_by_call_ci90", {"strata_of": wp.call_of}),
        ):
            interval = t2.bootstrap_delta(
                left_rows, right_rows, shared, "__wer_errors", "reference_words", 100.0,
                **kwargs,
            )
            interval["ci90_half_width"] = (interval["ci_high"] - interval["ci_low"]) / 2.0
            windows[label] = interval
        moved = [
            w for w in shared
            if (left_rows[w]["substitutions"], left_rows[w]["deletions"],
                left_rows[w]["insertions"])
            != (right_rows[w]["substitutions"], right_rows[w]["deletions"],
                right_rows[w]["insertions"])
        ]
        windows["windows_with_a_different_operation_count"] = len(moved)
        windows["window_operation_identity_rate"] = 1.0 - len(moved) / len(shared)
    result["windows"] = windows

    # ---- 5. text identity --------------------------------------------------
    result["text_identity"] = identity_section(
        comparator_attempt / f"{COMPARATOR_RUN}.trace.jsonl",
        args.attempt_dir / f"{args.run_id}.trace.jsonl",
    )

    # ---- 6. the signed predictions of section 5 ---------------------------
    wer = metrics["corpus_wer_percent"]["call_clustered_ci90"]
    identity_rate = result["text_identity"]["accepted_span_identity_rate"]
    saturated_here = len(windows["saturated_replicate"])
    result["prediction_check"] = {
        "corpus_wer_delta": {
            "predicted_range": list(PREDICTED_WER_RANGE),
            "observed": wer["point"],
            "held": PREDICTED_WER_RANGE[0] <= wer["point"] <= PREDICTED_WER_RANGE[1],
        },
        "ci90_half_width_wider_than_the_imported_margin": {
            "predicted": True,
            "imported_margin": IMPORTED_MARGIN,
            "observed": metrics["corpus_wer_percent"]["ci90_half_width"],
            "held": metrics["corpus_wer_percent"]["ci90_half_width"] > IMPORTED_MARGIN,
        },
        "text_identity_rate_below_60_percent": {
            "predicted_below": PREDICTED_IDENTITY_RATE_BELOW,
            "observed": identity_rate,
            "held": identity_rate < PREDICTED_IDENTITY_RATE_BELOW,
        },
        "saturation_between_0_and_2": {
            "predicted_range": list(PREDICTED_SATURATION_RANGE),
            "observed": saturated_here,
            "observed_windows": windows["saturated_replicate"],
            "comparator_saturated": len(windows["saturated_comparator"]),
            "held": PREDICTED_SATURATION_RANGE[0] <= saturated_here <= PREDICTED_SATURATION_RANGE[1],
        },
        "both_tail_cell_clause_2_failures_have_null_half_widths_above_the_imported_margin": {
            "metrics": ["numeric_value_accuracy_percent", "conec_non_entity_wer_percent"],
            "observed": {
                name: metrics[name]["ci90_half_width"]
                for name in ("numeric_value_accuracy_percent", "conec_non_entity_wer_percent")
            },
            "imported_margin": IMPORTED_MARGIN,
            "held": all(
                metrics[name]["ci90_half_width"] > IMPORTED_MARGIN
                for name in ("numeric_value_accuracy_percent", "conec_non_entity_wer_percent")
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "identity_gate": result["identity_gate"]["verdict"],
        "windows": windows["status"],
        "corpus_wer": {
            "comparator": metrics["corpus_wer_percent"]["comparator"],
            "replicate": metrics["corpus_wer_percent"]["replicate"],
            "delta": metrics["corpus_wer_percent"]["delta"],
            "ci90": [wer["ci_low"], wer["ci_high"]],
            "half_width": metrics["corpus_wer_percent"]["ci90_half_width"],
        },
        "text_identity_rate": identity_rate,
        "saturated_replicate": windows["saturated_replicate"],
        "margins": result["margin_rule"]["margins"],
        "predictions": {k: v["held"] for k, v in result["prediction_check"].items()},
        "out": str(args.out),
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
