#!/usr/bin/env python3
"""The v2 RE-DECISION of the sealed KC-E1f pair under MEASURED non-inferiority margins.

Exposure row `SAEA-E21-KC-E1F-VERDICT-V2` (`model-free-check`), registered and
committed before the first number was recomputed.  Zero model, GPU, tool, embedder,
tokenizer, network, audio-decode and paid-API contacts: no arm is re-flown and this
script produces no model bytes.  Owner Decision 9 of 2026-09-08, item 1 (re-decide the
sealed pair) and item 3 (the family rule: every "not worse" guard is a non-inferiority
test with a margin fixed from the carrier's own null).

The rule this script implements is stated in English, in full, and BEFORE any number
existed, in `docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md` section
2.  This file is that rule in executable form and is committed in the same commit,
before it is ever run.

What it does NOT do
-------------------
It computes no contrast of its own for the pair.  Every KC-E1f / KU-E1fc / comparator
number is recomputed by the FIXED v1 instrument -- `scripts/e21_window_pairing_read.py`
then `scripts/e21_kc_e1f_verdict_read.py`, identity anchors first, 44 call clusters,
seed 20260903, 10,000 replicates, CI90, both weightings -- and this script reads that
instrument's output.  It then:

1. proves the recomputation moved NO NUMBER against the committed v1 receipt, decision
   block field by field (`--v1-summary`);
2. computes the ONE quantity v2 needs and v1 never had -- the null replicate's own
   call-clustered CI90 on `insertions / reference words` -- from the null replicate's
   per-window rows, through the same `analysis.paired.resampled_statistic` draws, and
   refuses to go on unless the same two row files reproduce the null verdict's OWN
   published corpus-WER interval to the digit (the identity anchor of this step);
3. applies the v2 rule and writes the guard table.

Margins are read from the null verdict's committed `result-summary.json`, never
retyped: the margin's authority is that cell's receipt, not this script's source.
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

RESULT_SCHEMA = "saea-e21-kc-e1f-v2-redecision-v1"
EXPOSURE_ROW = "SAEA-E21-KC-E1F-VERDICT-V2"
NULL_ROW = "SAEA-E21-FULL44-NULL-REPLICATE-V1"
V1_ROW = "SAEA-E21-KC-E1F-VERDICT-V1"

#: The owner record that authorizes this re-decision and states the family rule.
OWNER_DECISION = (
    "umbrella owner record Decision 9 of 2026-09-08, item 1 (re-decide the sealed "
    "KC-E1f pair under non-inferiority guards whose margins come from the Earnings-21 "
    "own-null replicate, with the v1 REJECTED verdict left standing beside it) and "
    "item 3 (every 'not worse' guard is a non-inferiority test with a margin fixed "
    "from the carrier's own null)"
)

#: guard name in the recomputed v1-form decision block -> how v2 reads it.
#:
#: ``harmful_bound`` is the CI90 bound on the side where the arm would be WORSE.
#: ``margin_key`` names the metric in the null verdict's own ``null_table`` whose
#: measured half-width is this guard's margin; ``None`` means the margin is computed
#: here (over-generation) or that the guard does not gate.
GUARD_PLAN: dict[str, dict[str, object]] = {
    "delivery integrity (construction)": {
        "harmful_bound": None,
        "margin_key": None,
        "gates": True,
        "v2_test": (
            "UNCHANGED from v1: a construction guarantee has no margin. For every "
            "window the delivered raw text equals the sealed predecessor outside the "
            "accepted substitution spans and carries the identical whitespace-token "
            "count; it ABORTS THE READ rather than producing a number"
        ),
    },
    "corpus WER non-inferiority": {
        "harmful_bound": "ci_high",
        "margin_key": "corpus_wer_percent",
        "gates": True,
        "v2_test": (
            "call-clustered CI90 UPPER bound on (KC-E1f - comparator) corpus WER "
            "<= +delta, delta = the Earnings-21 own-null replicate's measured "
            "call-clustered CI90 half-width on corpus WER"
        ),
    },
    "numeric-value accuracy not worse (call-pooled)": {
        "harmful_bound": "ci_low",
        "margin_key": "numeric_value_accuracy_percent",
        "gates": True,
        "v2_test": (
            "call-clustered CI90 LOWER bound on (KC-E1f - comparator) call-pooled "
            "numeric-value accuracy >= -delta, delta = the Earnings-21 own-null "
            "replicate's measured call-clustered CI90 half-width on numeric-value "
            "accuracy"
        ),
    },
    "over-generation not worse": {
        "harmful_bound": "ci_high",
        "margin_key": None,
        "gates": True,
        "v2_test": (
            "call-clustered CI90 UPPER bound on (KC-E1f - comparator) insertions per "
            "reference word <= +delta_ins, delta_ins = the half-width of the null "
            "replicate's OWN call-clustered CI90 on the SAME quantity, computed from "
            "its per-window rows through this same instrument"
        ),
    },
    "negation-critical rate not worse": {
        "harmful_bound": None,
        "margin_key": "semantic_high_impact_error_rate_percent",
        "gates": False,
        "v2_test": (
            "STAYS ADVISORY, now for a measured reason: this metric's own same-request "
            "null EXCLUDES ZERO, so no 'does not rise' clause is answerable on this "
            "carrier at any margin"
        ),
    },
}

#: The metric whose null half-width is reported beside the primary. It gates nothing.
PRIMARY_REFERENCE_METRIC = "conec_person_wer_percent"

SCALE = 100.0  # percentage points, the null table's own convention


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def window_rows(path: Path) -> dict[str, dict]:
    """`{window_id: row}` from either per-window row dialect on this carrier.

    The window-pairing runner writes a `saea-e21-window-pairing-v1` document whose
    `rows` is a LIST keyed by each row's own `window_id`; the null cell cached a
    plain mapping. Both carry the three operation counts and `reference_words`, so
    the pooled corpus-WER numerator is derived here rather than trusted from either
    file, and section 2's anchor proves the two dialects agree.
    """

    document = load_json(path)
    if isinstance(document, dict) and isinstance(document.get("rows"), list):
        raw = {str(row["window_id"]): row for row in document["rows"]}
    else:
        raw = {str(key): value for key, value in document.items()}
    out: dict[str, dict] = {}
    for key, row in raw.items():
        row = dict(row)
        row["__wer_errors"] = (
            row["substitutions"] + row["deletions"] + row["insertions"]
        )
        out[key] = row
    return out


def pooled(rows: dict[str, dict], ids, numerator: str, denominator: str) -> float:
    top = sum(rows[i][numerator] for i in ids)
    bottom = sum(rows[i][denominator] for i in ids)
    return (SCALE * top / bottom) if bottom else 0.0


def band(
    left: dict[str, dict],
    right: dict[str, dict],
    ids,
    numerator: str,
    denominator: str,
) -> dict:
    """`right - left` on the pooled ratio, call-clustered, under the frozen draws."""

    ids = list(ids)

    def statistic(resampled) -> float:
        return pooled(right, resampled, numerator, denominator) - pooled(
            left, resampled, numerator, denominator
        )

    result = paired.resampled_statistic(
        sample_ids=ids,
        statistic=statistic,
        seed=wp.E21_WINDOW_SEED,
        n_replicates=wp.E21_WINDOW_REPLICATES,
        ci_level=wp.E21_WINDOW_CI_LEVEL,
        cluster_of=wp.call_of,
    )
    return {
        # `point` is the null cell's own key for this field and the anchor in
        # section 2 compares against that cell's published block verbatim.
        "point": result.point_estimate,
        "point_estimate": result.point_estimate,
        "ci_low": result.ci_low,
        "ci_high": result.ci_high,
        "sigma_hat": result.sigma_hat,
        "n": len(ids),
        "replicates": wp.E21_WINDOW_REPLICATES,
        "seed": wp.E21_WINDOW_SEED,
        "ci_level": wp.E21_WINDOW_CI_LEVEL,
        "ci90_half_width": (result.ci_high - result.ci_low) / 2.0,
    }


def _numbers(node, prefix: str = "") -> dict[str, float]:
    """Every numeric leaf of a JSON subtree, keyed by its dotted path."""

    out: dict[str, float] = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(_numbers(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            out.update(_numbers(value, f"{prefix}[{index}]"))
    elif isinstance(node, bool):
        pass
    elif isinstance(node, (int, float)):
        out[prefix] = float(node)
    return out


def no_number_moved(v1_decision: dict, v2_decision: dict) -> dict:
    """v2 changes the guard WORDING and each margin's SOURCE. It must move no number.

    Compared field by field on the numeric leaves of the decision block: the primary's
    two intervals and every guard's measured interval.
    """

    left, right = _numbers(v1_decision), _numbers(v2_decision)
    shared = sorted(set(left) & set(right))
    moved = [
        {"field": key, "v1": left[key], "v2": right[key]}
        for key in shared
        if left[key] != right[key]
    ]
    return {
        "numeric_fields_compared": len(shared),
        "fields_only_in_v1": sorted(set(left) - set(right)),
        "fields_only_in_v2": sorted(set(right) - set(left)),
        "fields_that_moved": moved,
        "verdict": "PASS" if not moved else "FAIL",
        "note": (
            "the v1 receipt's own decision block against the freshly recomputed one; "
            "identical draws, identical rows, identical estimator -- a single moved "
            "digit here would mean the recomputation is not the v1 read"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verdict-summary",
        type=Path,
        required=True,
        help="the FRESHLY RECOMPUTED v1-form result-summary.json of the pair",
    )
    parser.add_argument(
        "--v1-summary",
        type=Path,
        required=True,
        help="the committed v1 receipt's result-summary.json, for the no-number-moved proof",
    )
    parser.add_argument(
        "--null-summary",
        type=Path,
        required=True,
        help="the committed null replicate verdict's result-summary.json (the margins)",
    )
    parser.add_argument(
        "--comparator-window-rows",
        type=Path,
        required=True,
        help="the comparator's per-window rows (this read's own, freshly regenerated)",
    )
    parser.add_argument(
        "--null-window-rows",
        type=Path,
        required=True,
        help="the null replicate's per-window rows, under SPEECHRL_DATA_DIR",
    )
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    started = time.time()
    recomputed = load_json(args.verdict_summary)
    v1 = load_json(args.v1_summary)
    null = load_json(args.null_summary)
    decision = recomputed["decision"]

    # ---- 1. the recomputation moved no number -----------------------------
    identity = {
        "no_number_moved": no_number_moved(v1["decision"], decision),
        "recomputed_summary": {
            "path": str(args.verdict_summary),
            "sha256": sha256(args.verdict_summary),
        },
        "v1_summary": {"path": str(args.v1_summary), "sha256": sha256(args.v1_summary)},
        "null_summary": {
            "path": str(args.null_summary),
            "sha256": sha256(args.null_summary),
            "exposure_row": null["exposure_row"],
        },
        "arm_identity_anchors": {
            slug: {
                "run_id": anchor["source_run_id"],
                "attempt_id": anchor["source_attempt_id"],
                "verdict": anchor["verdict"],
                "checks_total": anchor["checks_total"],
                "checks_failed": anchor["checks_failed"],
            }
            for slug, anchor in recomputed["identity_anchors"].items()
        },
    }
    if identity["no_number_moved"]["verdict"] == "FAIL":
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "result-summary.json").write_text(
            json.dumps({"schema": RESULT_SCHEMA, "identity": identity}, indent=1) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(json.dumps(identity["no_number_moved"], indent=1))
        return 1
    if any(
        anchor["verdict"] != "PASS" or anchor["checks_failed"]
        for anchor in recomputed["identity_anchors"].values()
    ):
        raise SystemExit("an arm's identity anchor is not PASS; refusing to decide")

    # ---- 2. the over-generation margin, computed here ---------------------
    comparator_rows = window_rows(args.comparator_window_rows)
    null_rows = window_rows(args.null_window_rows)
    shared = sorted(set(comparator_rows) & set(null_rows))
    # A window's reference-word ATTRIBUTION follows the alignment, so it moves when
    # the hypothesis moves; what may not move is the CALL's own reference length,
    # because the call is the bootstrap cluster and the reference is fixed. Gate on
    # the call, report the window churn.
    moved_windows = [
        wid
        for wid in shared
        if comparator_rows[wid]["reference_words"] != null_rows[wid]["reference_words"]
    ]
    per_call: dict[str, list[int]] = {}
    for wid in shared:
        call = wp.call_of(wid)
        totals = per_call.setdefault(call, [0, 0])
        totals[0] += comparator_rows[wid]["reference_words"]
        totals[1] += null_rows[wid]["reference_words"]
    mismatched_calls = sorted(call for call, (a, b) in per_call.items() if a != b)
    gate = {
        "comparator_rows": {
            "path": str(args.comparator_window_rows),
            "sha256": sha256(args.comparator_window_rows),
            "windows": len(comparator_rows),
        },
        "null_rows": {
            "path": str(args.null_window_rows),
            "sha256": sha256(args.null_window_rows),
            "windows": len(null_rows),
        },
        "windows_paired": len(shared),
        "calls": len(per_call),
        "calls_whose_reference_word_total_moved": mismatched_calls,
        "windows_whose_reference_word_attribution_moved": len(moved_windows),
        "corpus_reference_words": {
            "comparator": sum(row["reference_words"] for row in comparator_rows.values()),
            "null_replicate": sum(row["reference_words"] for row in null_rows.values()),
        },
        "note": (
            "the per-window reference-word attribution follows the alignment and "
            "moves when the hypothesis moves; the per-CALL total is the reference's "
            "own length and may not move, and the call is the bootstrap cluster"
        ),
    }
    if (
        len(shared) != len(comparator_rows)
        or len(shared) != len(null_rows)
        or mismatched_calls
        or gate["corpus_reference_words"]["comparator"]
        != gate["corpus_reference_words"]["null_replicate"]
    ):
        raise SystemExit(f"the null band's row gate failed: {json.dumps(gate)}")

    published = null["windows"]["corpus_wer_window_level_clustered_by_call_ci90"]
    reproduced = band(
        comparator_rows, null_rows, shared, "__wer_errors", "reference_words"
    )
    anchor_fields = ("point", "ci_low", "ci_high", "sigma_hat", "ci90_half_width")
    anchor_rows = [
        {
            "field": field,
            "published_by_the_null_cell": published[field],
            "reproduced_here": reproduced[field],
            "verdict": "PASS"
            if abs(published[field] - reproduced[field]) <= 1e-12
            else "FAIL",
        }
        for field in anchor_fields
    ]
    gate["null_instrument_anchor"] = {
        "checks": anchor_rows,
        "verdict": "FAIL" if any(r["verdict"] == "FAIL" for r in anchor_rows) else "PASS",
        "note": (
            "the same two row files, through this same instrument, must reproduce the "
            "null cell's OWN published corpus-WER interval to the digit before the "
            "over-generation band computed from them may be used as a margin"
        ),
    }
    if gate["null_instrument_anchor"]["verdict"] == "FAIL":
        raise SystemExit(f"null instrument anchor FAILED: {json.dumps(gate, indent=1)}")

    over_generation_null = band(
        comparator_rows, null_rows, shared, "insertions", "reference_words"
    )
    delta_ins = over_generation_null["ci90_half_width"]
    over_generation_null["comparator_insertions"] = sum(
        comparator_rows[w]["insertions"] for w in shared
    )
    over_generation_null["replicate_insertions"] = sum(
        null_rows[w]["insertions"] for w in shared
    )
    over_generation_null["reference_words"] = sum(
        comparator_rows[w]["reference_words"] for w in shared
    )

    # ---- 3. the margins, read from the null cell's own receipt ------------
    null_table = null["null_table"]
    margins = {
        "corpus_wer_percent": {
            "margin": null_table["corpus_wer_percent"]["ci90_half_width"],
            "null_interval": [
                null_table["corpus_wer_percent"]["call_clustered_ci90"]["ci_low"],
                null_table["corpus_wer_percent"]["call_clustered_ci90"]["ci_high"],
            ],
            "source": f"{NULL_ROW} null table, corpus WER",
        },
        "numeric_value_accuracy_percent": {
            "margin": null_table["numeric_value_accuracy_percent"]["ci90_half_width"],
            "null_interval": [
                null_table["numeric_value_accuracy_percent"]["call_clustered_ci90"]["ci_low"],
                null_table["numeric_value_accuracy_percent"]["call_clustered_ci90"]["ci_high"],
            ],
            "source": f"{NULL_ROW} null table, numeric-value accuracy",
        },
        "insertions_per_reference_word": {
            "margin": delta_ins,
            "null_interval": [
                over_generation_null["ci_low"],
                over_generation_null["ci_high"],
            ],
            "source": (
                f"computed here from {NULL_ROW}'s own per-window rows, through the "
                "same instrument; v1 had no margin for this quantity and the null "
                "cell's published table does not carry it"
            ),
        },
        PRIMARY_REFERENCE_METRIC: {
            "margin": null_table[PRIMARY_REFERENCE_METRIC]["ci90_half_width"],
            "null_interval": [
                null_table[PRIMARY_REFERENCE_METRIC]["call_clustered_ci90"]["ci_low"],
                null_table[PRIMARY_REFERENCE_METRIC]["call_clustered_ci90"]["ci_high"],
            ],
            "source": f"{NULL_ROW} null table, ConEC PERSON -- REPORTED, GATES NOTHING",
        },
        "semantic_high_impact_error_rate_percent": {
            "margin": null_table["semantic_high_impact_error_rate_percent"]["ci90_half_width"],
            "null_interval": [
                null_table["semantic_high_impact_error_rate_percent"]["call_clustered_ci90"]["ci_low"],
                null_table["semantic_high_impact_error_rate_percent"]["call_clustered_ci90"]["ci_high"],
            ],
            "excludes_zero_under_the_null": null_table[
                "semantic_high_impact_error_rate_percent"
            ]["excludes_zero"],
            "source": (
                f"{NULL_ROW} null table, semantic high-impact rate -- NOT USED AS A "
                "MARGIN: its own null excludes zero, so the guard stays advisory"
            ),
        },
    }

    # ---- 4. apply the rule ------------------------------------------------
    guards: list[dict] = []
    failed: list[str] = []
    for row in decision["guards"]:
        name = row["guard"]
        plan = GUARD_PLAN[name]
        entry: dict[str, object] = {
            "guard": name,
            "v1_test": row["test"],
            "v1_verdict": row["verdict"],
            "v2_test": plan["v2_test"],
            "gates": plan["gates"],
            "measured": row["measured"],
        }
        bound_key = plan["harmful_bound"]
        if bound_key is None:
            entry["v2_verdict"] = row["verdict"] if plan["gates"] else "ADVISORY"
            if plan["margin_key"] is not None:
                entry["margin_source"] = margins[plan["margin_key"]]
            # A construction guard gates without a margin: it either held on every
            # window or the read should already have aborted upstream.
            if plan["gates"] and entry["v2_verdict"] != "PASS":
                failed.append(name)
        else:
            margin_key = plan["margin_key"] or "insertions_per_reference_word"
            margin = margins[margin_key]["margin"]
            # The recomputed decision block carries fractions; the margins are in
            # percentage points, the null table's own convention.
            bound_pp = SCALE * float(row["measured"][bound_key])
            point_pp = SCALE * float(row["measured"]["point_estimate"])
            allowed = +margin if bound_key == "ci_high" else -margin
            passes = bound_pp <= allowed if bound_key == "ci_high" else bound_pp >= allowed
            entry.update(
                {
                    "harmful_side": "upper bound" if bound_key == "ci_high" else "lower bound",
                    "point_estimate_pp": point_pp,
                    "harmful_bound_pp": bound_pp,
                    "margin_pp": margin,
                    "allowed_bound_pp": allowed,
                    "margin_source": margins[margin_key],
                    "slack_pp": (allowed - bound_pp)
                    if bound_key == "ci_high"
                    else (bound_pp - allowed),
                    "v2_verdict": "PASS" if passes else "FAIL",
                }
            )
            if not passes:
                failed.append(name)
        guards.append(entry)

    primary = {}
    person_margin = margins[PRIMARY_REFERENCE_METRIC]["margin"]
    for leg, key in (("vs_comparator", "vs_comparator"), ("vs_ku_e1fc", "vs_ku_e1fc")):
        measured = decision["primary"][key]["measured"]
        low_pp = SCALE * float(measured["ci_low"])
        primary[leg] = {
            "required": "call-clustered CI90 lower bound > 0 -- UNCHANGED from v1",
            "measured": measured,
            "point_estimate_pp": SCALE * float(measured["point_estimate"]),
            "ci90_pp": [low_pp, SCALE * float(measured["ci_high"])],
            "verdict": "MET" if measured["ci_low"] > 0.0 else "NOT MET",
            "person_null_half_width_pp": person_margin,
            "lower_bound_exceeds_the_person_null_half_width": low_pp > person_margin,
            "lower_bound_in_person_null_half_widths": low_pp / person_margin,
            "note": (
                "the multiple of the null half-width is REPORTED, never a threshold: "
                "the primary's own bar is unchanged at zero"
            ),
        }

    primary_met = all(row["verdict"] == "MET" for row in primary.values())
    if not primary_met:
        verdict = "NULL"
    elif failed:
        verdict = "REJECTED"
    else:
        verdict = "ADMITTED"

    result = {
        "schema": RESULT_SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "exposure_row": EXPOSURE_ROW,
        "supersedes_nothing": (
            f"{V1_ROW} stays on record; this is a SECOND decision of the SAME sealed "
            "bytes under a different rule, not an amendment of the first"
        ),
        "owner_decision": OWNER_DECISION,
        "decides": recomputed["decides"],
        "arms": recomputed["arms"],
        "rule": {
            "primary": (
                "UNCHANGED: call-clustered CI90 lower bound on the PERSON entity-WER "
                "reduction > 0 against the sealed comparator AND against KU-E1fc"
            ),
            "guards": (
                "every 'not worse' guard becomes a non-inferiority test: the CI90 bound "
                "on the HARMFUL side must not exceed that metric's margin, and the "
                "margin is the half-width of the Earnings-21 own-null replicate's own "
                "call-clustered CI90 on the same metric"
            ),
            "verdict_map": (
                "ADMITTED iff the primary is met on both legs and every gating guard "
                "holds; NULL if either primary lower bound includes zero; REJECTED if "
                "any gating guard fails"
            ),
            "unchanged": [
                "roster: all 44 discovery calls",
                "pairing unit: the fixed 90-second window (1,593)",
                "bootstrap cluster: the call (44)",
                "estimator: the pooled ratio sum(numerator)/sum(denominator)",
                "seed 20260903, 10,000 replicates, CI90",
                "both weightings reported: natural mixture and equal stratum",
            ],
            "stated_before_any_number": (
                "docs/readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md "
                "section 2, committed before this script was first run"
            ),
        },
        "identity": identity,
        "null_band_gate": gate,
        "over_generation_null_band": over_generation_null,
        "margins": margins,
        "primary": primary,
        "guards": guards,
        "failed_guards": failed,
        "verdict": verdict,
        "pairing": recomputed["pairing"],
        "zero_contact": (
            "no model, GPU, tool, embedding, tokenizer, network, audio-decode or "
            "paid-API contact; no arm re-flown and no reference transcript opened here"
        ),
        "elapsed_seconds": round(time.time() - started, 1),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "result-summary.json").write_text(
        json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "| guard | v1 bound | v1 | **v2 margin** | v2 bound vs margin | **v2** |",
        "|---|---|---|---:|---|---|",
    ]
    for row in guards:
        if "harmful_bound_pp" not in row:
            lines.append(
                f"| {row['guard']} | {row['v1_test']} | {row['v1_verdict']} | -- | -- "
                f"| **{row['v2_verdict']}** |"
            )
            continue
        sense = "<=" if row["harmful_side"] == "upper bound" else ">="
        lines.append(
            f"| {row['guard']} | {row['harmful_bound_pp']:+.5f} pp ({row['harmful_side']}) "
            f"| {row['v1_verdict']} | {row['margin_pp']:.5f} "
            f"| {row['harmful_bound_pp']:+.5f} {sense} {row['allowed_bound_pp']:+.5f} "
            f"| **{row['v2_verdict']}** |"
        )
    (args.out_dir / "guard-table.md").write_text(
        f"# KC-E1f v2 — the guard table under measured margins\n\n**{verdict}**\n\n"
        + "\n".join(lines)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"V2 VERDICT {verdict}")
    print(f"no number moved: {identity['no_number_moved']['verdict']} "
          f"({identity['no_number_moved']['numeric_fields_compared']} numeric fields)")
    print(f"null instrument anchor: {gate['null_instrument_anchor']['verdict']}")
    print(
        f"delta_ins = {delta_ins:.6f} pp  "
        f"(null insertions {over_generation_null['comparator_insertions']} -> "
        f"{over_generation_null['replicate_insertions']}, "
        f"point {over_generation_null['point_estimate']:+.6f} pp, "
        f"[{over_generation_null['ci_low']:+.6f}, {over_generation_null['ci_high']:+.6f}])"
    )
    for leg, row in primary.items():
        print(
            f"primary {leg:14} {row['verdict']:8} {row['point_estimate_pp']:+.3f} pp "
            f"[{row['ci90_pp'][0]:+.3f}, {row['ci90_pp'][1]:+.3f}]  "
            f"= {row['lower_bound_in_person_null_half_widths']:.2f} PERSON null half-widths at the LB"
        )
    for row in guards:
        print(f"guard {row['v2_verdict']:9} {row['guard']}")
    print(f"elapsed {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
