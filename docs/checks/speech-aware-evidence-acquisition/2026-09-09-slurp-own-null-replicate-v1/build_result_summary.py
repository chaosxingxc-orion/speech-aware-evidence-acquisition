#!/usr/bin/env python3
"""Assemble the machine form of the SLURP own-null verdict.

Reads nothing but ``verdict/read.json`` and ``flight-1000/falsifier.json``, and
writes ``verdict/result-summary.json``, ``verdict/null-table.md`` and
``verdict/per-scenario-table.md``. **Zero contacts of any kind.**
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA = "saea-slurp-own-null-replicate-v1-result-summary-v1"

MICRO_ROWS = (
    ("entities_strict", "entities strict F1 (micro)"),
    ("word_f1", "Word-F1 (micro)"),
    ("char_f1", "Char-F1 (micro)"),
    ("slu_f1", "SLU-F1 (micro)"),
)
ROW_LABELS = (
    ("scenario_action_exact", "intent (scenario+action)"),
    ("scenario_exact", "scenario"),
    ("action_exact", "action"),
    ("slot_f1_exact_f1", "entities strict F1 (per row)"),
    ("slu_f1_word_f1", "Word-F1 (per row)"),
    ("slu_f1_char_f1", "Char-F1 (per row)"),
    ("slu_f1_f1", "SLU-F1 (per row)"),
)


def fmt(interval):
    return "[%+.4f, %+.4f]" % (interval[0], interval[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", required=True, type=Path)
    parser.add_argument("--falsifier", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    read = json.loads(args.read.read_text(encoding="utf-8"))
    falsifier = json.loads(args.falsifier.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    micro = read["null_table_micro_official"]
    per_row = read["null_table_per_row_official"]
    micro_norm = read["null_table_micro_normalized"]
    per_row_norm = read["null_table_per_row_normalized"]

    lines = ["# The null table — SLURP's own greedy replicate", ""]
    lines.append(
        "Signed **replicate minus comparator**. 10,000 replicates, seed 20260903, CI90. "
        "The speaker-clustered family is the honest one; the scenario-stratified family is "
        "beside it. **The half-width is the margin.**"
    )
    lines.append("")
    lines.append("## Paper-facing micro (pooled) metrics")
    lines.append("")
    lines.append(
        "| metric | comparator | replicate | delta | speaker-clustered CI90 | "
        "**half-width** | scenario-stratified CI90 | half-width |"
    )
    lines.append("|---|---:|---:|---:|---|---:|---|---:|")
    for key, label in MICRO_ROWS:
        row = micro[key]
        lines.append(
            "| %s | %.4f | %.4f | **%+.4f** | %s | **%.4f** | %s | %.4f |"
            % (
                label,
                row["comparator_pct"],
                row["replicate_pct"],
                row["delta_pp"],
                fmt(row["clustered_by_speaker_ci90_pp"]),
                row["clustered_by_speaker_half_width_pp"],
                fmt(row["stratified_by_scenario_ci90_pp"]),
                row["stratified_by_scenario_half_width_pp"],
            )
        )
    lines.append("")
    lines.append("## Per-row metrics")
    lines.append("")
    lines.append(
        "| metric | comparator | replicate | delta | speaker-clustered CI90 | "
        "**half-width** | scenario-stratified CI90 | saves | harms | ties | sign p |"
    )
    lines.append("|---|---:|---:|---:|---|---:|---|---:|---:|---:|---:|")
    for key, label in ROW_LABELS:
        row = per_row[key]
        lines.append(
            "| %s | %.4f | %.4f | **%+.4f** | %s | **%.4f** | %s | %d | %d | %d | %.4g |"
            % (
                label,
                row["comparator_pct"],
                row["replicate_pct"],
                row["delta_pp"],
                fmt(row["clustered_by_speaker_ci90_pp"]),
                row["clustered_by_speaker_half_width_pp"],
                fmt(row["stratified_by_scenario_ci90_pp"]),
                row["saves"],
                row["harms"],
                row["ties"],
                row["sign_test_p"],
            )
        )
    lines.append("")
    lines.append("## The normalized secondary, same rows")
    lines.append("")
    lines.append("| metric | official delta | normalized delta | official half-width | normalized half-width |")
    lines.append("|---|---:|---:|---:|---:|")
    for key, label in MICRO_ROWS:
        lines.append(
            "| %s | %+.4f | %+.4f | %.4f | %.4f |"
            % (
                label,
                micro[key]["delta_pp"],
                micro_norm[key]["delta_pp"],
                micro[key]["clustered_by_speaker_half_width_pp"],
                micro_norm[key]["clustered_by_speaker_half_width_pp"],
            )
        )
    for key, label in ROW_LABELS:
        lines.append(
            "| %s | %+.4f | %+.4f | %.4f | %.4f |"
            % (
                label,
                per_row[key]["delta_pp"],
                per_row_norm[key]["delta_pp"],
                per_row[key]["clustered_by_speaker_half_width_pp"],
                per_row_norm[key]["clustered_by_speaker_half_width_pp"],
            )
        )
    lines.append("")
    (args.out_dir / "null-table.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
    )

    # ---- per scenario -------------------------------------------------
    strata_intent = per_row["scenario_action_exact"]["per_stratum"]
    strata_slu = per_row["slu_f1_f1"]["per_stratum"]
    flips = read["flip_rates"]["per_scenario"]
    scen = ["# Per gold scenario — the null, scenario by scenario", ""]
    scen.append(
        "Signed replicate minus comparator, on the same 1,000 paired rows. Descriptive: this "
        "cell has no factor, so a scenario that moves is measuring the decoder, not a mechanism."
    )
    scen.append("")
    scen.append(
        "| scenario | n | intent comparator | intent replicate | intent delta | saves | harms | "
        "SLU-F1 (per row) delta | raw text flip rate | projected-intent flips |"
    )
    scen.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name in sorted(strata_intent, key=lambda key: strata_intent[key]["delta_pp"]):
        row = strata_intent[name]
        slu = strata_slu[name]
        flip = flips.get(name, {})
        scen.append(
            "| `%s` | %d | %.2f | %.2f | **%+.4f** | %d | %d | %+.4f | %.1f %% | %d |"
            % (
                name,
                row["n"],
                row["comparator_pct"],
                row["replicate_pct"],
                row["delta_pp"],
                row["saves"],
                row["harms"],
                slu["delta_pp"],
                flip.get("raw_flip_rate_pct", 0.0),
                flip.get("projected_intent_flips", 0),
            )
        )
    scen.append("")
    (args.out_dir / "per-scenario-table.md").write_text(
        "\n".join(scen) + "\n", encoding="utf-8", newline="\n"
    )

    # ---- per speaker cluster ------------------------------------------
    clusters = read["per_cluster"]
    cl = ["# Per speaker cluster - the unit the honest interval resamples", ""]
    cl.append(
        "All %d clusters, signed replicate minus comparator on the same 1,000 paired rows. "
        "%d clusters moved on intent and %d on per-row SLU-F1, with NOTHING changed. Small "
        "clusters carry enormous per-cluster noise, which is exactly why a per-speaker reading "
        "on this carrier is inadmissible without its own replicate."
        % (
            clusters["clusters"],
            clusters["clusters_moved"]["scenario_action_exact"],
            clusters["clusters_moved"]["slu_f1_f1"],
        )
    )
    cl.append("")
    cl.append("| cluster | n | intent delta | SLU-F1 (per row) delta |")
    cl.append("|---|---:|---:|---:|")
    for row in sorted(clusters["rows"], key=lambda r: r["scenario_action_exact_delta_pp"]):
        cl.append(
            "| `%s` | %d | %+.4f | %+.4f |"
            % (
                row["cluster"],
                row["n"],
                row["scenario_action_exact_delta_pp"],
                row["slu_f1_f1_delta_pp"],
            )
        )
    cl.append("")
    (args.out_dir / "per-cluster-table.md").write_text(
        "\n".join(cl) + "\n", encoding="utf-8", newline="\n"
    )

    summary = {
        "schema": SCHEMA,
        "row": read["row"],
        "preregistration": read["preregistration"],
        "there_is_no_verdict": read["there_is_no_verdict"],
        "contacts": read["contacts"],
        "falsifier": {
            "passed": falsifier["passed"],
            "rows_paired": falsifier["rows_paired"],
            "rows_missing": len(falsifier["rows_missing"]),
            "rows_extra": len(falsifier["rows_extra"]),
            "disagreeing_row_count": falsifier["disagreeing_row_count"],
            "checks_passed_per_row": falsifier["checks_passed_per_row"],
            "prompt_token_delta_histogram": falsifier["prompt_token_delta_histogram"],
            "prompt_tokens_total": falsifier["prompt_tokens_total"],
            "manifest_cost_checks": falsifier["manifest_cost_checks"],
        },
        "identity_gate": read["identity_gate"],
        "identity_gate_passed": read["identity_gate_passed"],
        "official": read["official"],
        "normalized": read["normalized"],
        "population": read["population"],
        "flip_rates": {
            key: value
            for key, value in read["flip_rates"].items()
            if key != "per_scenario"
        },
        "null_table_micro_official": micro,
        "null_table_per_row_official": {
            key: {
                field: value
                for field, value in row.items()
                if field != "per_stratum"
            }
            for key, row in per_row.items()
        },
        "margins": read["margins"],
        "per_cluster": {
            key: value for key, value in read["per_cluster"].items() if key != "rows"
        },
        "silence_tail_reread": read["silence_tail_reread"],
        "manifests": read["manifests"],
        "score_batch": read["score_batch"],
    }
    (args.out_dir / "result-summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("wrote result-summary.json, null-table.md, per-scenario-table.md, per-cluster-table.md -> %s" % args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
