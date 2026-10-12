#!/usr/bin/env python3
"""The paired read of `SAEA-E21-FULL44-DISPATCH-ADMISSION-V1` against BOTH depth-0 arms.

Exposure row `SAEA-E21-FULL44-DISPATCH-ADMISSION-V1`; this read spends no model, GPU,
tool, embedding, network or audio-decode contact and opens no Earnings-22 surface.
`docs/readiness/2026-09-08-e21-dispatcher-admission-v1-preregistration.md` is the rule.
Section 2's falsifier is a SEPARATE step that runs before any score file is opened and
is not repeated here.

Section 3.1 fixes two pairings:

* **A**, against the sealed comparator `SAEA-E21-FULL44-DIRECT-BASELINE-V2` -- the arm
  every Earnings-21 margin is defined against, and the one section 4's status is stated
  on;
* **B**, against the depth-0 own-null replicate `SAEA-E21-FULL44-NULL-REPLICATE-V1`,
  which re-flew the same request on the same resident session. B isolates the
  dispatcher from everything the replicate already absorbed.

Section 4's admission rule is applied to pairing A, in the order it fixes:
HARMFUL, else ADMITTED, else NEUTRAL, with the semantic high-impact rate ADVISORY and
never gating because its own same-request null excludes zero.

Every statistic comes from the same functions the null replicate's and the tail cell's
reads used (`build_e21_tail2s_verdict`), so the effects and the margins they are
compared against come out of one instrument rather than two dialects.

Signed as *cell minus the arm it is paired against* throughout.
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

RUN_ID = "SAEA-E21-FULL44-DISPATCH-ADMISSION-V1"
COMPARATOR_RUN = t2.COMPARATOR_RUN
COMPARATOR_ATTEMPT = t2.COMPARATOR_ATTEMPT

NULL_RUN = "SAEA-E21-FULL44-NULL-REPLICATE-V1"
NULL_ATTEMPT = "attempt-20260908T113102Z-bdde07"
NULL_RECEIPT = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-full44-null-replicate-v1"
)
NULL_SCORE_READ = NULL_RECEIPT / "flight/verified-score-read.json"
NULL_RESULT_SUMMARY = NULL_RECEIPT / "verdict/result-summary.json"

#: Section 4: the semantic high-impact rate is reported in full and never gates,
#: because its own same-request null EXCLUDES zero (null verdict section 2.2).
ADVISORY_METRICS = ("semantic_high_impact_error_rate_percent",)

#: Section 6's signed predictions.
PREDICTED_WER_ABS_BELOW = 0.10
PREDICTED_IDENTITY_RATE_BELOW = 0.60
PREDICTED_SATURATION_RANGE = (0, 2)
PREDICTED_WPM_GAIN_PCT = (18.0, 23.0)
PREDICTED_ZERO_SLOT_SHARE_BELOW_PCT = 3.0

#: The depth-0 arms this cell's throughput is read against.
DEPTH0_DRY_RUN_RECEIPT = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-pipeline"
    / "obs-pipeline-dry-run.json"
)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def raw_completions(trace_path: Path) -> dict[str, str]:
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
    """The per-window text-identity rate, on the accepted span and the raw completion."""

    left = wp.stitched_windows_from_trace(left_trace)
    right = wp.stitched_windows_from_trace(right_trace)
    left_raw, right_raw = raw_completions(left_trace), raw_completions(right_trace)
    left_span = {span.identifier: span for spans in left.values() for span in spans}
    right_span = {span.identifier: span for spans in right.values() for span in spans}
    shared = sorted(set(left_span) & set(right_span))
    accepted = sum(1 for w in shared if left_span[w].text == right_span[w].text)
    raw = sum(
        1
        for w in shared
        if left_raw.get(left_span[w].request_id, "") == right_raw.get(right_span[w].request_id, "")
    )
    per_call: dict[str, dict] = {}
    shared_set = set(shared)
    for sample_id, spans in left.items():
        ids = [span.identifier for span in spans if span.identifier in shared_set]
        same = sum(1 for w in ids if left_span[w].text == right_span[w].text)
        per_call[sample_id] = {
            "windows": len(ids),
            "identical": same,
            "identity_rate": same / len(ids) if ids else 0.0,
        }
    return {
        "windows_paired": len(shared),
        "accepted_span_identical": accepted,
        "accepted_span_identity_rate": accepted / len(shared) if shared else 0.0,
        "raw_completion_identical": raw,
        "raw_completion_identity_rate": raw / len(shared) if shared else 0.0,
        "windows_differing": len(shared) - accepted,
        "calls_with_every_window_identical": sorted(
            c for c, row in per_call.items() if row["identical"] == row["windows"]
        ),
        "per_call": per_call,
    }


def reaggregation_gate(rows: dict, label: str, anchors: dict | None) -> dict:
    totals = {
        "windows": len(rows),
        "calls": len({row["sample_id"] for row in rows.values()}),
        "substitutions": sum(row["substitutions"] for row in rows.values()),
        "deletions": sum(row["deletions"] for row in rows.values()),
        "insertions": sum(row["insertions"] for row in rows.values()),
        "reference_words": sum(row["reference_words"] for row in rows.values()),
    }
    totals["errors"] = totals["substitutions"] + totals["deletions"] + totals["insertions"]
    totals["corpus_wer_percent"] = 100.0 * totals["errors"] / totals["reference_words"]
    checks = []
    if anchors is not None:
        for key, expected in anchors.items():
            checks.append({
                "check": key, "actual": totals.get(key), "expected": expected,
                "verdict": "PASS" if totals.get(key) == expected else "FAIL",
            })
    return {
        "arm": label, "totals": totals, "checks": checks,
        "verdict": "FAIL" if any(c["verdict"] == "FAIL" for c in checks) else "PASS",
    }


def pairing(left: dict, right: dict, ids, left_label: str, right_label: str) -> dict:
    """One arm against another, every pooled metric, call-clustered CI90."""

    metrics: dict[str, dict] = {}
    for name, (numerator, denominator, lower_is_better, scale) in t2.POOLED.items():
        a = t2.pooled(left, ids, numerator, denominator, scale)
        b = t2.pooled(right, ids, numerator, denominator, scale)
        interval = t2.bootstrap_delta(
            left, right, ids, numerator, denominator, scale,
            cluster_of=lambda sample_id: sample_id,
        )
        metrics[name] = {
            "lower_is_better": lower_is_better,
            left_label: a,
            right_label: b,
            "delta": b - a,
            "call_clustered_ci90": interval,
            "ci90_half_width": (interval["ci_high"] - interval["ci_low"]) / 2.0,
            "excludes_zero": interval["ci_low"] > 0 or interval["ci_high"] < 0,
            "equal_stratum": {
                left_label: t2.equal_stratum(left, ids, numerator, denominator, scale),
                right_label: t2.equal_stratum(right, ids, numerator, denominator, scale),
            },
        }
    return metrics


def adjudicate(metrics: dict, margins: dict) -> dict:
    """Section 4's rule, applied in the order it fixes."""

    rows: dict[str, dict] = {}
    for name, block in metrics.items():
        lower_is_better = block["lower_is_better"]
        delta = block["delta"]
        low = block["call_clustered_ci90"]["ci_low"]
        high = block["call_clustered_ci90"]["ci_high"]
        entry = margins.get(name)
        if entry is None:
            rows[name] = {"gating": False, "reason": "no measured null margin for this metric"}
            continue
        margin = float(entry["margin"])
        null_low, null_high = (float(v) for v in entry["null_ci90"])
        # Direction: on a lower-is-better metric the improving side is negative.
        improving_ci = (high < 0) if lower_is_better else (low > 0)
        harmful_ci = (low > 0) if lower_is_better else (high < 0)
        disjoint_from_null = high < null_low or low > null_high
        harmful_point = (delta > margin) if lower_is_better else (delta < -margin)
        rows[name] = {
            "gating": name not in ADVISORY_METRICS,
            "lower_is_better": lower_is_better,
            "delta": delta,
            "ci90": [low, high],
            "margin": margin,
            "null_ci90": [null_low, null_high],
            "abs_delta_over_margin": abs(delta) / margin if margin else None,
            "within_margin": abs(delta) <= margin,
            "ci90_on_improving_side_of_zero": improving_ci,
            "ci90_on_harmful_side_of_zero": harmful_ci,
            "disjoint_from_null_interval": disjoint_from_null,
            "demonstrated_gain": improving_ci and disjoint_from_null,
            "demonstrated_harm": harmful_ci and disjoint_from_null,
            "point_delta_exceeds_margin_on_the_harmful_side": harmful_point,
        }
    gating = {name: row for name, row in rows.items() if row.get("gating")}
    harmful = sorted(
        name for name, row in gating.items()
        if row["demonstrated_harm"] or row["point_delta_exceeds_margin_on_the_harmful_side"]
    )
    gains = sorted(name for name, row in gating.items() if row["demonstrated_gain"])
    if harmful:
        status = "HARMFUL"
    elif gains:
        status = "ADMITTED"
    else:
        status = "NEUTRAL"
    advisory = {name: row for name, row in rows.items() if not row.get("gating")}
    advisory_harmful = sorted(
        name for name, row in advisory.items()
        if row.get("demonstrated_harm") or row.get("point_delta_exceeds_margin_on_the_harmful_side")
    )
    return {
        "status": status,
        "harmful_metrics": harmful,
        "gaining_metrics": gains,
        "metrics": rows,
        "advisory_metrics": sorted(advisory),
        "advisory_would_be_harmful": advisory_harmful,
        "status_if_advisory_were_gating": (
            "HARMFUL" if advisory_harmful and not harmful else status
        ),
        "rule": (
            "Section 4 of docs/readiness/2026-09-08-e21-dispatcher-admission-v1-preregistration"
            ".md, evaluated in order: HARMFUL if a gating metric's CI90 is disjoint from its "
            "null interval on the harmful side or its point delta exceeds the margin on that "
            "side; else ADMITTED if a gating metric's CI90 is disjoint from its null interval "
            "on the improving side; else NEUTRAL. The semantic high-impact rate is ADVISORY "
            "and never gating because its own same-request null excludes zero."
        ),
        "margins_measured_by": {"run_id": NULL_RUN, "attempt_id": NULL_ATTEMPT},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-read", type=Path, required=True)
    parser.add_argument("--attempt-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--data-root", type=Path, default=Path(
        (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")))
    parser.add_argument("--comparator-window-rows", type=Path, required=True)
    parser.add_argument("--null-window-rows", type=Path, required=True)
    parser.add_argument("--cell-window-rows", type=Path, required=True)
    parser.add_argument("--falsifier", type=Path, default=None)
    parser.add_argument("--occupancy-cell", type=Path, default=None)
    parser.add_argument("--occupancy-null", type=Path, default=None)
    parser.add_argument("--flight-receipt", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--window-rows-only", choices=("comparator", "null", "cell"), default=None)
    args = parser.parse_args(argv)

    comparator_attempt = args.data_root / "runs" / COMPARATOR_RUN / COMPARATOR_ATTEMPT
    null_attempt = args.data_root / "runs" / NULL_RUN / NULL_ATTEMPT

    if args.window_rows_only is not None:
        from speech_aware_evidence_acquisition.data.lock import load_lock, umbrella_lock_path
        from speech_aware_evidence_acquisition.reproduction import semantic_impact

        lock = load_lock(umbrella_lock_path(REPO_ROOT))
        taxonomy = semantic_impact.load_taxonomy(
            REPO_ROOT / semantic_impact.ACTIVE_TAXONOMY_RELPATH
        )
        table = {
            "comparator": (comparator_attempt, COMPARATOR_RUN, args.comparator_window_rows),
            "null": (null_attempt, NULL_RUN, args.null_window_rows),
            "cell": (args.attempt_dir, args.run_id, args.cell_window_rows),
        }
        directory, stem, cache = table[args.window_rows_only]
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
    null = {k: t2.derived(v) for k, v in t2.call_rows_from_score_read(
        load(NULL_SCORE_READ)).items()}
    cell = {k: t2.derived(v) for k, v in t2.call_rows_from_score_read(
        t2.load_json(args.score_read)).items()}
    ids = sorted(set(comparator) & set(null) & set(cell))

    result: dict = {
        "schema": "saea-e21-dispatcher-admission-verdict-v1",
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": args.run_id,
        "cell": args.run_id,
        "module": "cross-call dispatcher (obs_prefetch_depth 1: prefetch of the next call's "
                  "cut plus a slot-saturating dispatcher across call boundaries)",
        "module_note": "docs/readiness/2026-09-08-e21-obs-pipeline-v1.md",
        "one_key": "obs_prefetch_depth",
        "comparator": {"run_id": COMPARATOR_RUN, "attempt_id": COMPARATOR_ATTEMPT},
        "null_replicate": {"run_id": NULL_RUN, "attempt_id": NULL_ATTEMPT},
        "carrier_lock_key": t2.CARRIER,
        "split_identity_hash": t2.SPLIT_IDENTITY,
        "calls_paired": len(ids),
        "sign_convention": "every delta is the cell minus the arm named in the pairing",
        "statistics": {
            "module": "analysis.paired.resampled_statistic",
            "seed": t2.SEED, "replicates": t2.REPLICATES, "ci_level": t2.CI_LEVEL,
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

    # ---- 1. identity gate on BOTH depth-0 arms ----------------------------
    gate = []

    def check(name, actual, expected, tolerance, arm):
        ok = abs(actual - expected) <= tolerance
        gate.append({"arm": arm, "check": name, "actual": actual, "expected": expected,
                     "verdict": "PASS" if ok else "FAIL"})

    A = t2.SEALED_ANCHORS
    check("corpus_wer_percent",
          round(t2.pooled(comparator, ids, "__wer_errors", "reference_words", 100.0), 4),
          A["corpus_wer_percent"], 0.0001, COMPARATOR_RUN)
    for key in ("substitutions", "deletions", "insertions", "reference_words"):
        check(key, sum(comparator[i][key] for i in ids), A[key], 0, COMPARATOR_RUN)
    check("conec_overall_wer_percent",
          round(t2.pooled(comparator, ids, "conec_errors", "conec_reference_words", 100.0), 3),
          A["conec_overall_wer_percent"], 0.0005, COMPARATOR_RUN)
    check("conec_non_entity_wer_percent",
          round(t2.pooled(comparator, ids, "conec_non_entity_errors",
                          "conec_non_entity_reference_words", 100.0), 3),
          A["conec_non_entity_wer_percent"], 0.0005, COMPARATOR_RUN)
    check("numeric_value_accuracy_percent",
          round(t2.pooled(comparator, ids, "numeric_matched", "numeric_expected", 100.0), 4),
          A["numeric_value_accuracy_percent"], 0.0001, COMPARATOR_RUN)
    check("semantic_high_impact_error_rate_percent",
          round(t2.pooled(comparator, ids, "semantic_high_reference_words",
                          "semantic_reference_words", 100.0), 5),
          A["semantic_high_impact_error_rate_percent"], 0.00001, COMPARATOR_RUN)

    null_summary = load(NULL_RESULT_SUMMARY)
    null_published = null_summary["null_table"]["corpus_wer_percent"]["replicate"]
    check("corpus_wer_percent",
          t2.pooled(null, ids, "__wer_errors", "reference_words", 100.0),
          null_published, 0.00005, NULL_RUN)

    result["identity_gate"] = {
        "verdict": "FAIL" if any(row["verdict"] == "FAIL" for row in gate) else "PASS",
        "checks": gate,
        "basis": (
            "the sealed comparator's own committed score receipts and the null replicate's "
            "own committed verified score read, re-pooled from their 44 per-call rows; no arm "
            "is re-flown and no scorer is re-run"
        ),
    }
    if result["identity_gate"]["verdict"] == "FAIL":
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(result["identity_gate"], indent=1))
        return 1

    # ---- 2. the two pairings ----------------------------------------------
    result["pairing_a_vs_comparator"] = pairing(comparator, cell, ids, "comparator", "cell")
    result["pairing_b_vs_null_replicate"] = pairing(null, cell, ids, "null_replicate", "cell")

    margins = null_summary["margin_rule"]["margins"]
    result["margins"] = {
        "measured_by": {"run_id": NULL_RUN, "attempt_id": NULL_ATTEMPT},
        "source": str(NULL_RESULT_SUMMARY.relative_to(REPO_ROOT)),
        "margins": margins,
        "caveat": (
            "A single replicate measures this null with 44 clusters and no more, AND it "
            "measures the noise of re-flying at depth 0, where a decode batch can only mix "
            "windows of one call. Section 4.1 of the preregistration says so in advance."
        ),
    }

    # ---- 3. the admission decision, on pairing A ---------------------------
    result["admission"] = adjudicate(result["pairing_a_vs_comparator"], margins)
    result["admission_against_null_replicate"] = adjudicate(
        result["pairing_b_vs_null_replicate"], margins
    )
    result["pairings_agree"] = (
        result["admission"]["status"] == result["admission_against_null_replicate"]["status"]
    )

    # ---- 4. per-call and per-stratum --------------------------------------
    result["per_call"] = []
    for sample_id in ids:
        row = {
            "sample_id": sample_id,
            "sector": sector_of[sample_id],
            "sample_rate_hz": rate_of[sample_id],
            "windows": windows_of[sample_id],
            "reference_words": comparator[sample_id]["reference_words"],
        }
        for label, arm in (("comparator", comparator), ("null", null), ("cell", cell)):
            row[f"{label}_wer_percent"] = (
                100.0 * arm[sample_id]["__wer_errors"] / arm[sample_id]["reference_words"]
            )
            row[f"{label}_sdi"] = [arm[sample_id]["substitutions"],
                                   arm[sample_id]["deletions"],
                                   arm[sample_id]["insertions"]]
            row[f"{label}_numeric_accuracy_percent"] = (
                100.0 * arm[sample_id]["numeric_matched"] / arm[sample_id]["numeric_expected"]
            )
        row["wer_delta_vs_comparator"] = row["cell_wer_percent"] - row["comparator_wer_percent"]
        row["wer_delta_vs_null"] = row["cell_wer_percent"] - row["null_wer_percent"]
        result["per_call"].append(row)
    deltas = [row["wer_delta_vs_comparator"] for row in result["per_call"]]
    result["per_call_spread"] = {
        "calls_better": sum(1 for d in deltas if d < 0),
        "calls_worse": sum(1 for d in deltas if d > 0),
        "calls_identical": sum(1 for d in deltas if d == 0),
        "min_delta": min(deltas), "max_delta": max(deltas),
        "largest_absolute_delta_call": max(
            result["per_call"], key=lambda r: abs(r["wer_delta_vs_comparator"]))["sample_id"],
        "null_replicate_per_call_range": [-1.0667, +0.2330],
        "note": (
            "the null replicate measured +/-1 point of per-call replicate noise on this "
            "carrier (its verdict section 5.1); no per-call reading here is admissible "
            "outside that band"
        ),
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

    left_totals, null_totals, right_totals = totals(comparator), totals(null), totals(cell)
    result["error_structure"] = {
        "comparator": left_totals,
        "null_replicate": null_totals,
        "cell": right_totals,
        "change_vs_comparator": {k: right_totals[k] - left_totals[k] for k in left_totals},
        "change_vs_null": {k: right_totals[k] - null_totals[k] for k in null_totals},
    }

    strata_tables = {}
    for label, mapping in (("by_sector", sector_of), ("by_sample_rate_hz", rate_of)):
        table = {}
        for stratum in sorted({mapping[i] for i in ids}):
            members = [i for i in ids if mapping[i] == stratum]
            a = t2.pooled(comparator, members, "__wer_errors", "reference_words", 100.0)
            n = t2.pooled(null, members, "__wer_errors", "reference_words", 100.0)
            b = t2.pooled(cell, members, "__wer_errors", "reference_words", 100.0)
            table[stratum] = {
                "calls": len(members),
                "reference_words": sum(comparator[i]["reference_words"] for i in members),
                "comparator_wer_percent": a,
                "null_wer_percent": n,
                "cell_wer_percent": b,
                "delta_vs_comparator": b - a,
                "delta_vs_null": b - n,
            }
        strata_tables[label] = table
    result["per_stratum"] = strata_tables

    # ---- 5. the window level ----------------------------------------------
    left_rows = t2.load_json(args.comparator_window_rows)
    null_rows = t2.load_json(args.null_window_rows)
    right_rows = t2.load_json(args.cell_window_rows)
    result["window_reaggregation"] = {
        "comparator": reaggregation_gate(left_rows, COMPARATOR_RUN, {
            "windows": 1593, "calls": 44,
            "substitutions": A["substitutions"], "deletions": A["deletions"],
            "insertions": A["insertions"], "reference_words": A["reference_words"],
        }),
        "null_replicate": reaggregation_gate(null_rows, NULL_RUN, {
            "windows": 1593, "calls": 44,
            "substitutions": null_totals["substitutions"],
            "deletions": null_totals["deletions"],
            "insertions": null_totals["insertions"],
            "reference_words": null_totals["reference_words"],
        }),
        "cell": reaggregation_gate(right_rows, args.run_id, {
            "windows": 1593, "calls": 44,
            "substitutions": right_totals["substitutions"],
            "deletions": right_totals["deletions"],
            "insertions": right_totals["insertions"],
            "reference_words": right_totals["reference_words"],
        }),
    }
    windows: dict = {}
    for label, other in (("vs_comparator", left_rows), ("vs_null_replicate", null_rows)):
        shared = sorted(set(other) & set(right_rows))
        misaligned = [
            w for w in shared
            if (other[w]["start_seconds"], other[w]["end_seconds"])
            != (right_rows[w]["start_seconds"], right_rows[w]["end_seconds"])
        ]
        block = {
            "status": "OK" if not misaligned and len(shared) == len(other) == len(right_rows)
            else "MISALIGNED",
            "windows_paired": len(shared),
            "span_misaligned": len(misaligned),
            "span_misaligned_examples": misaligned[:10],
        }
        if block["status"] == "OK":
            for name, kwargs in (
                ("corpus_wer_window_level_clustered_by_call_ci90", {"cluster_of": wp.call_of}),
                ("corpus_wer_window_level_stratified_by_call_ci90", {"strata_of": wp.call_of}),
            ):
                interval = t2.bootstrap_delta(
                    other, right_rows, shared, "__wer_errors", "reference_words", 100.0,
                    **kwargs,
                )
                interval["ci90_half_width"] = (interval["ci_high"] - interval["ci_low"]) / 2.0
                block[name] = interval
            moved = [
                w for w in shared
                if (other[w]["substitutions"], other[w]["deletions"], other[w]["insertions"])
                != (right_rows[w]["substitutions"], right_rows[w]["deletions"],
                    right_rows[w]["insertions"])
            ]
            block["windows_with_a_different_operation_count"] = len(moved)
            block["window_operation_identity_rate"] = 1.0 - len(moved) / len(shared)
        windows[label] = block
    windows["saturated_comparator"] = sorted(w for w in left_rows if left_rows[w]["saturated"])
    windows["saturated_null_replicate"] = sorted(w for w in null_rows if null_rows[w]["saturated"])
    windows["saturated_cell"] = sorted(w for w in right_rows if right_rows[w]["saturated"])
    result["windows"] = windows

    # ---- 6. text identity, against both arms -------------------------------
    result["text_identity"] = {
        "vs_comparator": identity_section(
            comparator_attempt / f"{COMPARATOR_RUN}.trace.jsonl",
            args.attempt_dir / f"{args.run_id}.trace.jsonl",
        ),
        "vs_null_replicate": identity_section(
            null_attempt / f"{NULL_RUN}.trace.jsonl",
            args.attempt_dir / f"{args.run_id}.trace.jsonl",
        ),
        "null_replicate_vs_comparator_published": {
            "accepted_span_identity_rate": 0.3390,
            "source": "docs/readiness/2026-09-08-e21-own-null-replicate-v1-verdict.md section 6",
        },
    }

    # ---- 7. throughput -----------------------------------------------------
    dry = load(DEPTH0_DRY_RUN_RECEIPT)["measured"]
    throughput: dict = {
        "depth0_comparator_own_server": {
            "windows_per_minute": dry["windows_per_minute"],
            "mean_slot_utilisation_pct": dry["mean_slot_utilisation_pct"],
            "zero_busy_share_pct": dry["zero_busy_share_pct"],
            "zero_busy_seconds": dry["zero_busy_seconds"],
            "all_slots_busy_share_pct": dry["all_slots_busy_share_pct"],
            "wall_seconds": dry["wall_seconds"],
            "source": str(DEPTH0_DRY_RUN_RECEIPT.relative_to(REPO_ROOT)),
        },
    }
    if args.occupancy_null is not None and args.occupancy_null.is_file():
        throughput["depth0_null_replicate_this_session"] = load(args.occupancy_null)
    if args.occupancy_cell is not None and args.occupancy_cell.is_file():
        throughput["depth1_cell_this_session"] = load(args.occupancy_cell)
    if args.flight_receipt is not None and args.flight_receipt.is_file():
        receipt = load(args.flight_receipt)
        throughput["cell_flight_receipt"] = {
            "run_wall_seconds": receipt["throughput"]["run_wall_seconds"],
            "windows_per_minute": receipt["throughput"]["windows_per_minute"],
            "realized_realtime_factor": receipt["throughput"]["realized_realtime_factor"],
            "gpu_hours": receipt["cost"]["gpu_hours"],
            "monitor_summary": receipt["serving"]["monitor_summary"],
        }
    cell_block = throughput.get("depth1_cell_this_session")
    null_block = throughput.get("depth0_null_replicate_this_session")
    if cell_block is not None:
        gains = {}
        for label, other in (
            ("vs_comparator_own_server", throughput["depth0_comparator_own_server"]),
            ("vs_null_replicate_same_session", null_block),
        ):
            if other is None:
                continue
            before = other.get("windows_per_minute") or other.get(
                "windows_per_minute_over_span")
            after = cell_block["windows_per_minute_over_span"]
            gains[label] = {
                "windows_per_minute_before": before,
                "windows_per_minute_after": after,
                "windows_per_minute_gain_pct": 100.0 * (after - before) / before,
                "zero_slot_share_pct_before": other["zero_busy_share_pct"],
                "zero_slot_share_pct_after": cell_block["zero_busy_share_pct"],
                "mean_slot_utilisation_pct_before": other["mean_slot_utilisation_pct"],
                "mean_slot_utilisation_pct_after": cell_block["mean_slot_utilisation_pct"],
            }
        throughput["gains"] = gains
        throughput["claim"] = (
            "section 5 of the preregistration: windows per minute, mean slot utilisation and "
            "zero-slot share, measured by the same server-log replay on both arms of this "
            "session and quoted from the dry-run receipt for the comparator's own server"
        )
    result["throughput"] = throughput

    # ---- 8. the signed predictions of section 6 ---------------------------
    wer_a = result["pairing_a_vs_comparator"]["corpus_wer_percent"]
    identity_rate = result["text_identity"]["vs_comparator"]["accepted_span_identity_rate"]
    saturated_here = len(windows["saturated_cell"])
    predictions = {
        "status_neutral": {
            "predicted": "NEUTRAL",
            "observed": result["admission"]["status"],
            "held": result["admission"]["status"] == "NEUTRAL",
        },
        "corpus_wer_delta_within_0_10_of_the_comparator": {
            "predicted_abs_below": PREDICTED_WER_ABS_BELOW,
            "observed": wer_a["delta"],
            "held": abs(wer_a["delta"]) < PREDICTED_WER_ABS_BELOW,
        },
        "every_gating_metric_inside_its_margin": {
            "observed": {
                name: row["within_margin"]
                for name, row in result["admission"]["metrics"].items()
                if row.get("gating")
            },
            "held": all(
                row["within_margin"]
                for row in result["admission"]["metrics"].values() if row.get("gating")
            ),
        },
        "falsifier_passes_on_1593_windows": {
            "observed": (result.get("falsifier") or {}).get("verdict"),
            "held": (result.get("falsifier") or {}).get("verdict") == "PASS",
        },
        "text_identity_rate_below_60_percent": {
            "predicted_below": PREDICTED_IDENTITY_RATE_BELOW,
            "observed": identity_rate,
            "held": identity_rate < PREDICTED_IDENTITY_RATE_BELOW,
        },
        "text_identity_below_the_null_replicates_own_33_90_percent": {
            "predicted_below": 0.3390,
            "observed": identity_rate,
            "held": identity_rate < 0.3390,
        },
        "saturation_between_0_and_2": {
            "predicted_range": list(PREDICTED_SATURATION_RANGE),
            "observed": saturated_here,
            "observed_windows": windows["saturated_cell"],
            "held": PREDICTED_SATURATION_RANGE[0] <= saturated_here
            <= PREDICTED_SATURATION_RANGE[1],
        },
    }
    if cell_block is not None and "gains" in throughput:
        for label, block in throughput["gains"].items():
            predictions[f"windows_per_minute_gain_18_to_23_pct_{label}"] = {
                "predicted_range_pct": list(PREDICTED_WPM_GAIN_PCT),
                "observed_pct": block["windows_per_minute_gain_pct"],
                "held": PREDICTED_WPM_GAIN_PCT[0] <= block["windows_per_minute_gain_pct"]
                <= PREDICTED_WPM_GAIN_PCT[1],
            }
        predictions["zero_slot_share_below_3_percent"] = {
            "predicted_below_pct": PREDICTED_ZERO_SLOT_SHARE_BELOW_PCT,
            "observed_pct": cell_block["zero_busy_share_pct"],
            "held": cell_block["zero_busy_share_pct"] < PREDICTED_ZERO_SLOT_SHARE_BELOW_PCT,
        }
    if args.flight_receipt is not None and args.flight_receipt.is_file():
        gpu_hours = throughput["cell_flight_receipt"]["gpu_hours"]
        predictions["gpu_hours_at_or_below_1_01"] = {
            "predicted_at_or_below": 1.01,
            "observed": gpu_hours,
            "held": gpu_hours <= 1.01,
        }
    result["prediction_check"] = predictions

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "identity_gate": result["identity_gate"]["verdict"],
        "STATUS": result["admission"]["status"],
        "status_vs_null_replicate": result["admission_against_null_replicate"]["status"],
        "pairings_agree": result["pairings_agree"],
        "harmful": result["admission"]["harmful_metrics"],
        "gains": result["admission"]["gaining_metrics"],
        "advisory_would_be_harmful": result["admission"]["advisory_would_be_harmful"],
        "corpus_wer": {
            "comparator": wer_a["comparator"], "cell": wer_a["cell"],
            "delta": wer_a["delta"],
            "ci90": [wer_a["call_clustered_ci90"]["ci_low"],
                     wer_a["call_clustered_ci90"]["ci_high"]],
        },
        "windows": {k: v["status"] for k, v in windows.items() if isinstance(v, dict)},
        "text_identity_rate_vs_comparator": identity_rate,
        "saturated_cell": windows["saturated_cell"],
        "throughput_gains": throughput.get("gains"),
        "predictions": {k: v["held"] for k, v in predictions.items()},
        "out": str(args.out),
    }, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
