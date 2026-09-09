#!/usr/bin/env python3
"""Decide whether KC-E1f REPLICATES, from four sealed manifests.

Exposure row ``SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1``. **Zero model, GPU, tool,
embedder, tokenizer, network, audio-decode and paid-API contacts**: every number
here comes from bytes that were already sealed, and the reference transcripts are
reached only through ``scripts/e21_window_pairing_read.py``, which produced the
per-window rows this script consumes.

The rule is section 3 of
``docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md``, written
before that verdict was known and quoted here as written:

    1. **The same roster, flown again.** All 44 discovery calls, the same 1,593
       fixed 90-second windows, the same configuration, as a second independent
       pass of the KC-E1f arm.
    2. **A second pass through the null band.** The replicate's PERSON effect and
       every gating guard must be re-read against the null's measured intervals,
       and the PERSON effect must again be disjoint from ``[-0.24338, +0.25680]``.
    3. **No freeze before both hold.**

So this read answers **REPLICATED / NOT REPLICATED**, on three components:

* **the primary** -- the call-clustered CI90 lower bound on the pooled ConEC-mirror
  PERSON entity-WER REDUCTION (comparator minus replicate, so a positive value
  means fewer errors) must be **disjoint from the carrier's own PERSON null
  interval**, i.e. strictly above ``+0.25680`` points, against the sealed
  comparator; and must be ``> 0`` against the form twin, which is the v2 primary's
  own second leg, unchanged;
* **the guards**, at the margins the Earnings-21 own-null replicate measured --
  corpus WER ``UB <= +0.05793``, numeric-value accuracy (call-pooled)
  ``LB >= -0.15651``, over-generation ``UB <= +0.02218``, delivery integrity by
  construction, the semantic rate advisory;
* **the replication contrast itself** -- first pass versus replicate, every metric,
  read against the same null band. Two passes of one configuration should differ
  by no more than that configuration's own replicate noise, and a metric whose
  first-pass-vs-replicate interval falls OUTSIDE the null band is reported as a
  failure of that expectation rather than hidden.

**Nothing about the instrument moves.** The estimand, the roster, the pairing unit,
the bootstrap cluster, the estimator, the seed, the draws, the CI level and both
weightings are the v1/v2 read's, and they are the v1 read's *functions*: this
script imports ``e21_kc_e1f_verdict_read`` and calls its helpers, so the
replication and the thing it replicates come out of one instrument rather than two
dialects. The margins are read from the committed receipts that measured them --
the null cell's own ``null_table`` and the v2 decision's ``margins`` block -- never
retyped here.

Three things run before any contrast, and each of them refuses:

1. the **identity anchor** -- each of the four arms' 1,593 per-window rows must
   re-aggregate to that arm's own sealed numbers;
2. the **section 5.1 attribution** of the replicate -- every normalized
   deletion/insertion move against the comparator must be carried by a substituted
   span, including the ``(I - D) delta == normalized hypothesis-length delta``
   identity, corpus-wide and per call;
3. the **delivery-integrity construction guard**, from the replicate's own flight
   receipt on the sealed bytes.

A failure in any of the three aborts the read rather than producing a number.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))
for candidate in (Path(__file__).resolve().parent, REPO_ROOT / "scripts"):
    if (candidate / "e21_kc_e1f_verdict_read.py").is_file():
        sys.path.insert(0, str(candidate))
        break

import e21_kc_e1f_verdict_read as v1  # noqa: E402

from speech_aware_evidence_acquisition.analysis import e21_window_pairing as wp  # noqa: E402

RESULT_SCHEMA = "saea-e21-kc-e1f-replication-v1"
EXPOSURE_ROW = "SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1"
RULE = "docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md section 3"

REPLICATE_RUN = "SAEA-E21-KC-E1F-REPAIR-44-REPLICATE-V1"

#: Arm slug -> sealed run id. The first three are the v2 read's own arms, at the
#: v2 read's own anchored rows files; the fourth is the second pass.
ARM_RUNS = {
    "comparator": "SAEA-E21-FULL44-DIRECT-BASELINE-V2",
    "ku-e1fc": "SAEA-E21-KU-E1FC-PLACEBO-REPAIR-44-V1",
    "kc-e1f": "SAEA-E21-KC-E1F-REPAIR-44-V1",
    "kc-e1f-rep": REPLICATE_RUN,
}

#: ``(label, left, right, reading)``; the module convention is ``delta = right -
#: left`` and ``improvement`` re-signs it so positive always means the RIGHT arm is
#: better. The first two decide; the third is the replication contrast; the last
#: two re-derive the first pass's own published contrasts through this same
#: instrument so the read anchors itself against the v2 decision it extends.
CONTRASTS = (
    (
        "replicate_vs_comparator",
        "comparator",
        "kc-e1f-rep",
        "the second pass against the sealed comparator -- the primary leg the "
        "replication clause names, and every gating guard",
    ),
    (
        "replicate_vs_twin",
        "ku-e1fc",
        "kc-e1f-rep",
        "the second pass against the first pass's token-matched placebo twin -- the "
        "primary's second leg, unchanged from v2",
    ),
    (
        "first_pass_vs_replicate",
        "kc-e1f",
        "kc-e1f-rep",
        "THE REPLICATION CONTRAST: two passes of one configuration. Every metric is "
        "read against the carrier's own null band, because that is the size of the "
        "difference the runtime can manufacture with nothing changed",
    ),
    (
        "first_pass_vs_comparator_ANCHOR",
        "comparator",
        "kc-e1f",
        "the v2 decision's own primary leg, recomputed here through this instrument "
        "and asserted equal to the published interval -- the read's self-anchor",
    ),
    (
        "first_pass_vs_twin_ANCHOR",
        "ku-e1fc",
        "kc-e1f",
        "the v2 decision's own second primary leg, likewise recomputed and asserted",
    ),
)

DECIDING_CONTRASTS = ("replicate_vs_comparator", "replicate_vs_twin")

#: metric name in this read -> key in the null cell's own published ``null_table``.
#: ``insertions_per_reference_word`` is absent there by construction: the null cell
#: never published it, and the v2 decision computed its band from that cell's own
#: per-window rows. It is read from the v2 decision's ``margins`` block instead.
NULL_TABLE_KEYS = {
    "corpus_wer": "corpus_wer_percent",
    "non_entity_wer": "conec_non_entity_wer_percent",
    "entity_wer_PERSON": "conec_person_wer_percent",
    "entity_wer_ORG": "conec_org_wer_percent",
    "negation_critical_rate": "semantic_high_impact_error_rate_percent",
    "numeric_accuracy_call_pooled": "numeric_value_accuracy_percent",
}

#: Metrics whose first-pass-vs-replicate interval the replication clause expects to
#: sit INSIDE the null band. Every metric with a measured band is read; these are
#: the ones the verdict line reports.
REPLICATION_BAND_METRICS = (
    "entity_wer_PERSON",
    "corpus_wer",
    "entity_wer_ORG",
    "non_entity_wer",
    "numeric_accuracy_call_pooled",
    "insertions_per_reference_word",
    "negation_critical_rate",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pp(interval: dict) -> dict[str, float]:
    """A raw ratio interval, in percentage points -- the unit every published
    Earnings-21 margin is written in."""

    return {
        "point": 100.0 * interval["point_estimate"],
        "ci_low": 100.0 * interval["ci_low"],
        "ci_high": 100.0 * interval["ci_high"],
    }


def _disjoint(interval_pp: dict[str, float], band: tuple[float, float]) -> bool:
    """True iff the measured CI90 and the null band do not overlap."""

    return interval_pp["ci_low"] > band[1] or interval_pp["ci_high"] < band[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reaggregation-dir", type=Path, required=True)
    parser.add_argument("--attribution-dir", type=Path, required=True)
    parser.add_argument("--rows-dir", type=Path, required=True)
    parser.add_argument(
        "--rows-file",
        action="append",
        default=[],
        metavar="SLUG=PATH",
        help="explicit rows file for an arm slug; repeatable",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=wp.E21_WINDOW_SEED)
    parser.add_argument("--replicates", type=int, default=wp.E21_WINDOW_REPLICATES)
    parser.add_argument("--ci-level", type=float, default=wp.E21_WINDOW_CI_LEVEL)
    parser.add_argument(
        "--replicate-flight-receipt",
        type=Path,
        required=True,
        help="the replicate's own committed flight receipt, for the class anchor "
        "and the delivery-integrity construction guard",
    )
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
    )
    parser.add_argument(
        "--roster-table",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-06-e21-agentic-metric-baseline/verdict/per-call-table.md",
        help="the committed comparator per-call table, read for the E5 roster label only",
    )
    parser.add_argument(
        "--null-summary",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-08-e21-full44-null-replicate-v1/verdict/result-summary.json",
        help="the cell that MEASURED this carrier's bands; they are read, never retyped",
    )
    parser.add_argument(
        "--v2-summary",
        type=Path,
        default=REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-08-e21-kc-e1f-verdict-v2/result-summary.json",
        help="the decision this replication discharges; its margins and its own "
        "measured intervals are read from here",
    )
    args = parser.parse_args(argv)
    started = time.time()

    explicit_rows = {}
    for item in args.rows_file:
        slug, _, path = item.partition("=")
        explicit_rows[slug] = Path(path)

    # ---- 0. the measured bands, read from the cells that measured them ----
    null_summary = json.loads(args.null_summary.read_text(encoding="utf-8"))
    v2_summary = json.loads(args.v2_summary.read_text(encoding="utf-8"))
    null_table = null_summary["null_table"]
    v2_margins = v2_summary["margins"]

    bands: dict[str, dict] = {}
    for metric, key in NULL_TABLE_KEYS.items():
        entry = null_table[key]
        bands[metric] = {
            "null_interval_pp": [
                entry["call_clustered_ci90"]["ci_low"],
                entry["call_clustered_ci90"]["ci_high"],
            ],
            "half_width_pp": entry["ci90_half_width"],
            "source": f"{null_summary['exposure_row']} null_table.{key}",
        }
    insertions = v2_margins["insertions_per_reference_word"]
    bands["insertions_per_reference_word"] = {
        "null_interval_pp": list(insertions["null_interval"]),
        "half_width_pp": insertions["margin"],
        "source": insertions["source"],
    }
    person_band = tuple(bands["entity_wer_PERSON"]["null_interval_pp"])
    person_half_width = bands["entity_wer_PERSON"]["half_width_pp"]

    # ---- 1. identity anchors, and the rows they pin ----
    anchors: dict[str, dict] = {}
    rows_by_arm: dict[str, list[dict]] = {}
    rows_files: dict[str, dict] = {}
    for slug, run_id in ARM_RUNS.items():
        anchor = v1._identity_anchor(args.reaggregation_dir / slug / "reaggregation.json")
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
        rows_path = explicit_rows.get(slug) or (args.rows_dir / f"rows-{slug}.json")
        document = v1._load_rows(rows_path)
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
        print(f"anchor {slug:12} PASS  rows {len(document['rows'])}", flush=True)

    class_sets = {
        slug: tuple(sorted(rows[0]["entity_class_counts"]))
        for slug, rows in rows_by_arm.items()
    }
    if len({classes for classes in class_sets.values()}) != 1:
        raise SystemExit(f"the arms carry different class columns: {class_sets}")
    classes = class_sets["comparator"]

    # ---- 2. the class anchor, every class against each arm's own receipt ----
    receipts = {
        "kc-e1f-rep": json.loads(
            args.replicate_flight_receipt.read_text(encoding="utf-8")
        ),
        "kc-e1f": json.loads(args.kc_e1f_flight_receipt.read_text(encoding="utf-8")),
        "ku-e1fc": json.loads(args.ku_e1fc_flight_receipt.read_text(encoding="utf-8")),
        "comparator": json.loads(args.comparator_score_read.read_text(encoding="utf-8")),
    }
    class_checks: list[dict] = []
    for slug, document in receipts.items():
        class_checks.extend(
            v1._class_anchor(
                slug=slug,
                by_entity_type=v1._sealed_by_entity_type(document),
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
    print(
        f"class anchor {len(class_checks)}/{len(class_checks)} PASS", flush=True
    )

    # ---- 3. the section 5.1 attribution of the replicate, and the construction guard ----
    attribution_checks: list[dict] = []
    attribution: dict[str, dict] = {}
    for slug in ("kc-e1f-rep",):
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
        totals = document["totals"]

        treated, comparator = anchors[slug], anchors["comparator"]
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
        per_call_attribution = {
            row["sample_id"]: row["normalized_words"]["delta"]
            for row in document["per_call"]
        }
        per_call_operations = {call: 0 for call in per_call_attribution}
        for arm_rows, arm_sign in (
            (rows_by_arm[slug], 1),
            (rows_by_arm["comparator"], -1),
        ):
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
        attribution_checks.append(
            {
                "arm": slug,
                "check": "whole_delta_attributed_to_substituted_spans",
                "attributed_delta": totals["attributed_delta"],
                "normalized_word_delta": totals["normalized_word_delta"],
                "verdict": "PASS"
                if totals["attributed_delta"] == totals["normalized_word_delta"]
                else "FAIL",
            }
        )
        for role, key in (
            ("comparator", "comparator_normalized_words"),
            (slug, "treated_normalized_words"),
        ):
            sealed = v1._sealed_hypothesis_words(receipts[role])
            attribution_checks.append(
                {
                    "arm": slug,
                    "check": f"normalized_hypothesis_words[{role}]",
                    "attribution": totals[key],
                    "sealed_scorer": sealed,
                    "verdict": "PASS" if totals[key] == sealed else "FAIL",
                }
            )
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

    attribution_failures = [row for row in attribution_checks if row["verdict"] == "FAIL"]
    if attribution_failures:
        raise SystemExit(
            "the section 5.1 attribution did not close; the read aborts: "
            + json.dumps(attribution_failures)
        )
    print("attribution + delivery guard PASS", flush=True)

    # ---- 4. the paired contrasts ----
    by_window = {
        slug: {row["window_id"]: row for row in rows} for slug, rows in rows_by_arm.items()
    }
    reference_ids = set(by_window["comparator"])
    for slug, table in by_window.items():
        if set(table) != reference_ids:
            raise SystemExit(f"arm {slug!r} does not carry the comparator's window ids")
    window_ids = tuple(sorted(reference_ids))
    windows_per_call: dict[str, int] = {}
    for identifier in window_ids:
        call = wp.call_of(identifier)
        windows_per_call[call] = windows_per_call.get(call, 0) + 1

    metrics = v1._window_metrics(classes)

    def build(left_slug: str, right_slug: str, reader, ids):
        left_table, right_table = by_window[left_slug], by_window[right_slug]
        pairs = {}
        for identifier in ids:
            ln, ld = reader(left_table[identifier])
            rn, rd = reader(right_table[identifier])
            pairs[identifier] = (ln, ld, rn, rd)
        return pairs

    results: dict[str, dict] = {}
    for contrast, left_slug, right_slug, contrast_note in CONTRASTS:
        block: dict[str, dict] = {}
        for metric, (reader, sign, note) in metrics.items():
            pairs = build(left_slug, right_slug, reader, window_ids)
            block[metric] = v1._contrast_block(
                metric=metric,
                note=note,
                sign=sign,
                pairs=pairs,
                window_ids=window_ids,
                windows_per_call=windows_per_call,
                seed=args.seed,
                replicates=args.replicates,
                ci_level=args.ci_level,
                optimistic=metric in v1.OPTIMISTIC_METRICS,
            )
        left_calls = {
            row["sample_id"]: (row["call_numeric_matched"], row["call_numeric_expected"])
            for row in anchors[left_slug]["per_call_numeric"]
        }
        right_calls = {
            row["sample_id"]: (row["call_numeric_matched"], row["call_numeric_expected"])
            for row in anchors[right_slug]["per_call_numeric"]
        }
        block["numeric_accuracy_call_pooled"] = v1._call_pooled_numeric_contrast(
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
        person = block["entity_wer_PERSON"]["natural_mixture_call_clustered"]
        corpus = block["corpus_wer"]["natural_mixture_call_clustered"]
        print(
            f"{contrast:34} PERSON {100 * person['point_estimate']:+.3f} "
            f"[{100 * person['ci_low']:+.3f}, {100 * person['ci_high']:+.3f}]  "
            f"corpus {100 * corpus['point_estimate']:+.3f}",
            flush=True,
        )

    # ---- 5. the self-anchor: the v2 decision's own two legs, recomputed ----
    anchor_checks: list[dict] = []
    for label, contrast_key, published_key in (
        ("primary vs comparator", "first_pass_vs_comparator_ANCHOR", "vs_comparator"),
        ("primary vs KU-E1fc", "first_pass_vs_twin_ANCHOR", "vs_ku_e1fc"),
    ):
        measured = results[contrast_key]["metrics"]["entity_wer_PERSON"][
            "natural_mixture_call_clustered"
        ]
        published = v2_summary["primary"][published_key]["measured"]
        moved = [
            field
            for field in ("point_estimate", "ci_low", "ci_high", "sigma_hat")
            if measured[field] != published[field]
        ]
        anchor_checks.append(
            {
                "check": f"v2 {label} reproduces to the digit",
                "contrast": contrast_key,
                "measured": {k: measured[k] for k in ("point_estimate", "ci_low", "ci_high", "sigma_hat")},
                "published": {k: published[k] for k in ("point_estimate", "ci_low", "ci_high", "sigma_hat")},
                "fields_that_moved": moved,
                "verdict": "PASS" if not moved else "FAIL",
            }
        )
    anchor_failures = [row for row in anchor_checks if row["verdict"] == "FAIL"]
    if anchor_failures:
        raise SystemExit(
            "this instrument does not reproduce the v2 decision it extends; the read "
            "aborts rather than deciding a replication against a moved reference: "
            + json.dumps(anchor_failures)
        )
    print("v2 self-anchor 2/2 PASS", flush=True)

    # ---- 6. the primary ----
    primary: dict[str, dict] = {}
    for leg, contrast_key, requirement, threshold in (
        (
            "vs_comparator",
            "replicate_vs_comparator",
            "call-clustered CI90 lower bound on the PERSON reduction DISJOINT from "
            "the carrier's own PERSON null interval, i.e. strictly above its upper "
            "edge -- section 3 item 2 of the v2 re-decision",
            person_band[1],
        ),
        (
            "vs_ku_e1fc",
            "replicate_vs_twin",
            "call-clustered CI90 lower bound > 0 -- the v2 primary's second leg, "
            "unchanged",
            0.0,
        ),
    ):
        block = results[contrast_key]["metrics"]["entity_wer_PERSON"]
        interval = block["natural_mixture_call_clustered"]
        equal = block["equal_stratum_per_call_clustered"]
        pp = _pp(interval)
        primary[leg] = {
            "required": requirement,
            "threshold_pp": threshold,
            "measured": interval,
            "point_estimate_pp": pp["point"],
            "ci90_pp": [pp["ci_low"], pp["ci_high"]],
            "equal_stratum_ci90_pp": [
                100.0 * equal["ci_low"],
                100.0 * equal["ci_high"],
            ],
            "person_null_interval_pp": list(person_band),
            "person_null_half_width_pp": person_half_width,
            "lower_bound_in_person_null_half_widths": pp["ci_low"] / person_half_width,
            "disjoint_from_the_person_null_interval": _disjoint(pp, person_band),
            "verdict": "MET" if pp["ci_low"] > threshold else "NOT MET",
        }

    # ---- 7. the guards, at the measured margins ----
    comparator_block = results["replicate_vs_comparator"]["metrics"]
    v2_guards = {row["guard"]: row for row in v2_summary["guards"]}
    guards: list[dict] = []

    delivery = receipts["kc-e1f-rep"]["delivery_integrity"]
    guards.append(
        {
            "guard": "delivery integrity (construction)",
            "gates": True,
            "test": "for every window the delivered raw text equals the sealed "
            "predecessor outside the accepted substitution spans and carries the "
            "identical whitespace-token count; a construction guarantee has no "
            "margin and it ABORTS THE READ rather than producing a number",
            "measured": {
                "windows_checked": delivery["windows_checked"],
                "violations": delivery["violations"],
                "attribution_verdict": attribution["kc-e1f-rep"]["verdict"],
            },
            "first_pass": v2_guards["delivery integrity (construction)"]["measured"],
            "verdict": "PASS"
            if delivery["violations"] == 0 and delivery["windows_checked"] == 1593
            else "FAIL",
        }
    )

    for guard_name, metric, side, band_key in (
        ("corpus WER non-inferiority", "corpus_wer", "upper", "corpus_wer"),
        (
            "numeric-value accuracy not worse (call-pooled)",
            "numeric_accuracy_call_pooled",
            "lower",
            "numeric_accuracy_call_pooled",
        ),
        (
            "over-generation not worse",
            "insertions_per_reference_word",
            "upper",
            "insertions_per_reference_word",
        ),
    ):
        # The v2 decision's own guard rows carry the same names, by construction:
        # this is the same guard on the same metric at the same margin, applied to
        # the second pass. A rename there must break this read rather than silently
        # drop the first pass's column.
        if guard_name not in v2_guards:
            raise SystemExit(
                f"the v2 decision carries no guard named {guard_name!r}; the "
                "first-pass column cannot be filled and the read refuses to publish "
                f"a one-sided guard table (v2 guards: {sorted(v2_guards)})"
            )
        delta = v1._delta_interval(comparator_block[metric])
        delta_pp = _pp(delta)
        equal_delta_pp = _pp(
            v1._delta_interval(
                comparator_block[metric], reading="equal_stratum_per_call_clustered"
            )
        )
        margin = bands[band_key]["half_width_pp"]
        if side == "upper":
            bound, allowed = delta_pp["ci_high"], +margin
            passed = bound <= allowed
            equal_passed = equal_delta_pp["ci_high"] <= allowed
        else:
            bound, allowed = delta_pp["ci_low"], -margin
            passed = bound >= allowed
            equal_passed = equal_delta_pp["ci_low"] >= allowed
        first_pass = v2_guards[guard_name]
        guards.append(
            {
                "guard": guard_name,
                "gates": True,
                "metric": metric,
                "test": f"call-clustered CI90 {side} bound on (replicate - comparator) "
                f"{'<=' if side == 'upper' else '>='} "
                f"{'+' if side == 'upper' else '-'}{margin:.5f} percentage points",
                "harmful_side": f"{side} bound",
                "margin_pp": margin,
                "margin_source": bands[band_key]["source"],
                "allowed_bound_pp": allowed,
                "harmful_bound_pp": bound,
                "point_estimate_pp": delta_pp["point"],
                "slack_pp": (allowed - bound) if side == "upper" else (bound - allowed),
                "equal_stratum_harmful_bound_pp": equal_delta_pp[
                    "ci_high" if side == "upper" else "ci_low"
                ],
                "equal_stratum_verdict": "PASS" if equal_passed else "FAIL",
                "first_pass_harmful_bound_pp": first_pass.get("harmful_bound_pp"),
                "first_pass_verdict": first_pass.get("v2_verdict"),
                "verdict": "PASS" if passed else "FAIL",
            }
        )

    advisory = v1._delta_interval(comparator_block["negation_critical_rate"])
    advisory_pp = _pp(advisory)
    guards.append(
        {
            "guard": "negation-critical / semantic high-impact rate",
            "gates": False,
            "metric": "negation_critical_rate",
            "test": "ADVISORY AND NEVER GATING on this carrier: its own same-request "
            "null EXCLUDES ZERO, so it cannot answer 'does not rise' at any margin "
            "(v2 re-decision section 2.3)",
            "point_estimate_pp": advisory_pp["point"],
            "ci90_pp": [advisory_pp["ci_low"], advisory_pp["ci_high"]],
            "null_interval_pp": bands["negation_critical_rate"]["null_interval_pp"],
            "verdict": "ADVISORY",
        }
    )

    failed_guards = [row["guard"] for row in guards if row["verdict"] == "FAIL"]

    # ---- 8. the replication contrast, every metric against the null band ----
    replication_block = results["first_pass_vs_replicate"]["metrics"]
    replication_table: list[dict] = []
    for metric in REPLICATION_BAND_METRICS:
        if metric not in replication_block or metric not in bands:
            continue
        delta = v1._delta_interval(replication_block[metric])
        delta_pp = _pp(delta)
        band = tuple(bands[metric]["null_interval_pp"])
        inside = not _disjoint(delta_pp, band)
        replication_table.append(
            {
                "metric": metric,
                "delta_replicate_minus_first_pass_pp": delta_pp["point"],
                "ci90_pp": [delta_pp["ci_low"], delta_pp["ci_high"]],
                "null_interval_pp": list(band),
                "null_half_width_pp": bands[metric]["half_width_pp"],
                "point_in_null_half_widths": abs(delta_pp["point"])
                / bands[metric]["half_width_pp"],
                "inside_the_null_band": inside,
                "reading": (
                    "the two passes differ by no more than this carrier's own "
                    "replicate noise"
                )
                if inside
                else (
                    "the two passes differ by MORE than this carrier's own replicate "
                    "noise on this metric -- reported, not hidden"
                ),
            }
        )
    outside_band = [row["metric"] for row in replication_table if not row["inside_the_null_band"]]

    # ---- 8b. the per-call table and the E5 halves ----
    # The owner's 2026-09-03 reporting rule: every verdict carries its per-stratum
    # table. On this carrier the call IS the stratum that matters -- it is the
    # bootstrap cluster, and the own-null cell measured about a POINT of per-call
    # replicate noise on corpus WER, so a per-call reading is published beside the
    # corpus one precisely so no reader mistakes a call's movement for an effect.
    roster: dict[str, str] = {}
    if args.roster_table.exists():
        for line in args.roster_table.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2 and cells[0].isdigit():
                roster[cells[0]] = cells[1]

    calls = tuple(sorted(windows_per_call))
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
        first, second = (
            entry["kc-e1f_person_entity_wer_percent"],
            entry["kc-e1f-rep_person_entity_wer_percent"],
        )
        entry["replicate_minus_first_pass_person_pp"] = (
            (second - first) if (first is not None and second is not None) else None
        )
        entry["replicate_minus_first_pass_corpus_pp"] = (
            entry["kc-e1f-rep_corpus_wer_percent"] - entry["kc-e1f_corpus_wer_percent"]
        )
        per_call.append(entry)

    roster_halves: dict[str, dict] = {}
    for label in sorted({str(entry["roster"]) for entry in per_call}):
        members = {entry["sample_id"] for entry in per_call if entry["roster"] == label}
        ids = tuple(wid for wid in window_ids if wp.call_of(wid) in members)
        half: dict[str, dict] = {"calls": len(members), "windows": len(ids)}
        for metric in ("corpus_wer", "entity_wer_PERSON", "entity_wer_ORG"):
            reader, _sign, _note = metrics[metric]
            half[metric] = {}
            for slug in ARM_RUNS:
                numerator = denominator = 0
                for identifier in ids:
                    num, den = reader(by_window[slug][identifier])
                    numerator += num
                    denominator += den
                half[metric][slug] = (
                    100.0 * numerator / denominator if denominator else None
                )
        roster_halves[label] = half
    roster_halves_note = (
        "REPORTED APART AND DESCRIPTIVELY, WITH NO INTERVAL. 34 of the 44 calls are "
        "the kb-construction half; the evaluation ten carry 342 paired windows, below "
        "the program's n >= 400 rule, and no verdict here quotes an interval on them."
    )

    # ---- 9. the verdict ----
    primary_met = all(row["verdict"] == "MET" for row in primary.values())
    replicated = primary_met and not failed_guards
    verdict = "REPLICATED" if replicated else "NOT REPLICATED"

    reasons: list[str] = []
    if not primary_met:
        for leg, row in primary.items():
            if row["verdict"] != "MET":
                reasons.append(
                    f"the primary leg {leg} is NOT MET: lower bound "
                    f"{row['ci90_pp'][0]:+.5f} pp against the threshold "
                    f"{row['threshold_pp']:+.5f} pp"
                )
    for name in failed_guards:
        reasons.append(f"gating guard FAILED: {name}")

    document = {
        "schema": RESULT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW,
        "rule": RULE,
        "decides": REPLICATE_RUN,
        "verdict": verdict,
        "verdict_reasons": reasons,
        "zero_contact": (
            "no model, GPU, tool, embedder, tokenizer, network, audio-decode or "
            "paid-API contact: every number is computed from bytes sealed before "
            "this read opened them"
        ),
        "arms": ARM_RUNS,
        "rows_files": rows_files,
        "pairing": {
            "unit": "fixed 90-second window",
            "windows": len(window_ids),
            "cluster": "call",
            "calls": len(windows_per_call),
            "estimator": "pooled ratio, sum(numerator) / sum(denominator) over the "
            "resampled units",
            "seed": args.seed,
            "n_replicates": args.replicates,
            "ci_level": args.ci_level,
        },
        "bands": bands,
        "identity": {
            "arm_identity_anchors": {slug: anchors[slug] for slug in ARM_RUNS},
            "class_anchor": {
                "checks": len(class_checks),
                "failed": len(class_failures),
                "verdict": "PASS",
            },
            "attribution_checks": attribution_checks,
            "v2_self_anchor": anchor_checks,
        },
        "primary": primary,
        "guards": guards,
        "failed_guards": failed_guards,
        "replication_contrast": {
            "note": "first pass versus replicate, signed replicate minus first pass, "
            "every metric against the carrier's own measured null band",
            "table": replication_table,
            "metrics_outside_the_null_band": outside_band,
        },
        "per_call": per_call,
        "roster_halves": {"note": roster_halves_note, "halves": roster_halves},
        "contrasts": results,
        "elapsed_seconds": time.time() - started,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "result-summary.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    guard_lines = [
        f"# The replication guard table -- {verdict}",
        "",
        "Call-clustered CI90, natural mixture, 44 call clusters, 1,593 paired "
        f"90-second windows, seed {args.seed}, {args.replicates} replicates. "
        "Percentage points. Signed replicate minus comparator; the margin is applied "
        "one-sidedly, on the harmful side only.",
        "",
        "| guard | required | replicate | first pass (v2) | verdict |",
        "|---|---|---:|---:|---|",
    ]
    for row in guards:
        if not row["gates"]:
            first_advisory = 100.0 * v2_guards["negation-critical rate not worse"][
                "measured"
            ]["point_estimate"]
            guard_lines.append(
                f"| {row['guard']} | advisory; gates nothing | "
                f"{row['point_estimate_pp']:+.5f} | {first_advisory:+.5f} | ADVISORY |"
            )
        elif "margin_pp" not in row:
            guard_lines.append(
                f"| {row['guard']} | construction; aborts the read | "
                f"{row['measured']['windows_checked']} / 1,593 windows, "
                f"{row['measured']['violations']} violations | "
                f"{row['first_pass']['windows_checked']} / 1,593, "
                f"{row['first_pass']['violations']} violations | {row['verdict']} |"
            )
        else:
            guard_lines.append(
                f"| {row['guard']} | {row['harmful_side']} "
                f"{'<=' if row['harmful_side'] == 'upper bound' else '>='} "
                f"{row['allowed_bound_pp']:+.5f} | {row['harmful_bound_pp']:+.5f} "
                f"(point {row['point_estimate_pp']:+.5f}) | "
                f"{row['first_pass_harmful_bound_pp']:+.5f} | {row['verdict']} |"
            )
    guard_lines += [
        "",
        "| primary leg | required | measured | disjoint from the PERSON null? | verdict |",
        "|---|---|---|---|---|",
    ]
    for leg, row in primary.items():
        guard_lines.append(
            f"| {leg} | LB > {row['threshold_pp']:+.5f} | "
            f"{row['point_estimate_pp']:+.3f} [{row['ci90_pp'][0]:+.3f}, "
            f"{row['ci90_pp'][1]:+.3f}] | "
            f"{'YES' if row['disjoint_from_the_person_null_interval'] else 'no'} | "
            f"{row['verdict']} |"
        )
    guard_lines += [
        "",
        "## The replication contrast -- first pass versus replicate, against the "
        "carrier's own null band",
        "",
        "| metric | replicate - first pass | CI90 | null band | inside? |",
        "|---|---:|---|---|---|",
    ]
    for row in replication_table:
        guard_lines.append(
            f"| {row['metric']} | {row['delta_replicate_minus_first_pass_pp']:+.5f} | "
            f"[{row['ci90_pp'][0]:+.5f}, {row['ci90_pp'][1]:+.5f}] | "
            f"[{row['null_interval_pp'][0]:+.5f}, {row['null_interval_pp'][1]:+.5f}] | "
            f"{'YES' if row['inside_the_null_band'] else 'NO'} |"
        )
    (args.out_dir / "guard-table.md").write_text(
        "\n".join(guard_lines) + "\n", encoding="utf-8"
    )

    call_lines = [
        "# Per call -- the stratum this carrier's bootstrap actually resamples",
        "",
        "The own-null replicate measured about a POINT of per-call corpus-WER "
        "replicate noise on this carrier (its verdict, section 5.1). No per-call "
        "movement below that is readable as an effect, and this table is published "
        "so no reader has to take that on trust.",
        "",
        "| call | roster | windows | comparator corpus | first pass corpus | "
        "replicate corpus | rep - first (corpus) | comparator PERSON | "
        "first pass PERSON | replicate PERSON | rep - first (PERSON) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    def _fmt(value, spec="+.3f"):
        return "--" if value is None else format(value, spec)

    for entry in per_call:
        call_lines.append(
            f"| `{entry['sample_id']}` | {entry['roster']} | {entry['windows']} | "
            f"{_fmt(entry['comparator_corpus_wer_percent'], '.4f')} | "
            f"{_fmt(entry['kc-e1f_corpus_wer_percent'], '.4f')} | "
            f"{_fmt(entry['kc-e1f-rep_corpus_wer_percent'], '.4f')} | "
            f"{_fmt(entry['replicate_minus_first_pass_corpus_pp'])} | "
            f"{_fmt(entry['comparator_person_entity_wer_percent'], '.4f')} | "
            f"{_fmt(entry['kc-e1f_person_entity_wer_percent'], '.4f')} | "
            f"{_fmt(entry['kc-e1f-rep_person_entity_wer_percent'], '.4f')} | "
            f"{_fmt(entry['replicate_minus_first_pass_person_pp'])} |"
        )
    call_lines += ["", "## The E5 halves, reported apart and descriptively", "",
                   roster_halves_note, "",
                   "| half | calls | windows | metric | comparator | first pass | replicate |",
                   "|---|---:|---:|---|---:|---:|---:|"]
    for label, half in roster_halves.items():
        for metric in ("corpus_wer", "entity_wer_PERSON", "entity_wer_ORG"):
            values = half[metric]
            call_lines.append(
                f"| {label} | {half['calls']} | {half['windows']} | {metric} | "
                f"{_fmt(values['comparator'], '.4f')} | "
                f"{_fmt(values['kc-e1f'], '.4f')} | "
                f"{_fmt(values['kc-e1f-rep'], '.4f')} |"
            )
    (args.out_dir / "per-call-table.md").write_text(
        "\n".join(call_lines) + "\n", encoding="utf-8"
    )
    print(f"\nVERDICT {verdict}", flush=True)
    for reason in reasons:
        print(f"  - {reason}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
