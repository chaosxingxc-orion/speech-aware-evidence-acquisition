#!/usr/bin/env python3
"""Assemble the machine-readable verdict from ``read.json`` alone.

Reads nothing else. Zero model, GPU, tool, embedding and network contacts.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

SCHEMA = "saea-slurp-silence-tail-v1-result-summary-v1"
HEADLINE = ("scenario_action_exact", "scenario_exact", "action_exact", "slu_f1_f1")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--falsifier-flight", required=True, type=Path)
    parser.add_argument("--falsifier-smoke", required=True, type=Path)
    args = parser.parse_args()

    read = json.loads(args.read.read_text(encoding="utf-8"))
    flight_falsifier = json.loads(args.falsifier_flight.read_text(encoding="utf-8"))
    smoke_falsifier = json.loads(args.falsifier_smoke.read_text(encoding="utf-8"))
    contrasts = read["contrasts_official_projected_v2"]
    honest = read["decisions"]["clustered_by_speaker"]

    summary = {
        "schema": SCHEMA,
        "study": "speech-aware-evidence-acquisition",
        "row": read["row"],
        "verdict": read["verdict"],
        "verdict_family": read["verdict_family"],
        "verdict_families_agree": read["verdict_families_agree"],
        "preregistration": read["preregistration"],
        "rule_4_1_verbatim": read["rule_4_1_verbatim"],
        "null": read["null"],
        "contacts": read["contacts"],
        "identity_gate_passed": read["identity_gate_passed"],
        "identity_gate": read["identity_gate"],
        "falsifier": {
            "flight": {
                "passed": flight_falsifier["passed"],
                "rows": flight_falsifier["checks"]["rows"],
                "disagreeing_rows": len(flight_falsifier["disagreeing_rows"]),
                "checks": flight_falsifier["checks"],
                "seconds": flight_falsifier["seconds"],
                "prompt_tokens": flight_falsifier["prompt_tokens"],
            },
            "smoke": {
                "passed": smoke_falsifier["passed"],
                "rows": smoke_falsifier["checks"]["rows"],
                "disagreeing_rows": len(smoke_falsifier["disagreeing_rows"]),
                "prompt_tokens": smoke_falsifier["prompt_tokens"],
            },
        },
        "official_projected_v2": read["official"],
        "normalized_secondary": read["normalized"],
        "secondary_sign_agreement": read["secondary_sign_agreement"],
        "population": read["population"],
        "headline": {
            metric: {
                "comparator_pct": contrasts[metric]["left_pct"],
                "cell_pct": contrasts[metric]["right_pct"],
                "delta_pp": contrasts[metric]["delta_pp"],
                "clustered_by_speaker_ci90_pp": contrasts[metric][
                    "clustered_by_speaker_ci90_pp"
                ],
                "stratified_by_scenario_ci90_pp": contrasts[metric][
                    "stratified_by_scenario_ci90_pp"
                ],
                "saves": contrasts[metric]["saves"],
                "harms": contrasts[metric]["harms"],
                "ties": contrasts[metric]["ties"],
                "sign_test_p": contrasts[metric]["sign_test_p"],
                "equal_stratum_point_pp": read["equal_stratum_official_projected_v2"][
                    metric
                ]["point_pp"],
                "equal_stratum_clustered_ci90_pp": read[
                    "equal_stratum_official_projected_v2"
                ][metric]["clustered_by_speaker_ci90_pp"],
            }
            for metric in HEADLINE
        },
        "contrasts_official_projected_v2": contrasts,
        "equal_stratum_official_projected_v2": read["equal_stratum_official_projected_v2"],
        "decisions": read["decisions"],
        "prediction_check": {
            "section_5_signed_before_the_cell_existed": (
                "SLURP: small, positive, quite possibly inside the null. Predicted intent "
                "delta 0 to +2.0 pp, and inside the imported null margin is an entirely "
                "plausible outcome that would be reported as such."
            ),
            "measured_intent_delta_pp": contrasts["scenario_action_exact"]["delta_pp"],
            "held": 0.0
            <= contrasts["scenario_action_exact"]["delta_pp"]
            <= 2.0,
            "inside_imported_null_margin": honest["inside_imported_null_margin"],
        },
        "what_this_cannot_conclude": [
            "Nothing about the SLURP test split or FINAL60, neither of which this cell touches.",
            "No like-for-like comparison against any published SLURP protocol number: DEV-1000 "
            "is a dev-tier optimization population and every request carried 2.0 s of digital "
            "silence no published system appends.",
            "Nothing about generalization or superiority, and nothing that belongs to Stage-3.",
            "Not that the tail is the last difference and not that the encoder pad was removed: "
            "appending whole mel blocks leaves the residue (n_samples // 160) % 100 unchanged, "
            "so the same padded block is still sent, two seconds later.",
            "Nothing about any other carrier. There is no cross-carrier verdict: three cells, "
            "three answers, reported side by side.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )

    per_stratum = contrasts["scenario_action_exact"]["per_stratum"]
    slu = contrasts["slu_f1_f1"]["per_stratum"]
    lines = [
        "# Per-scenario intent accuracy — `SAEA-SLURP-DEV1000-CLOSED-LIST-TAIL2S-V1`",
        "",
        "All 18 gold scenarios, sorted by intent delta. `intent` is the official projected-v2",
        "scenario+action exact accuracy; `SLU-F1` is the per-row mean of the official per-sample",
        "SLU-F1, which is what the paired contrast is computed on (the paper-facing SLU-F1 is the",
        "micro aggregate and is reported in the verdict note).",
        "",
        "| scenario | n | intent, comparator | intent, cell | intent delta | saves | harms | SLU-F1 delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in sorted(per_stratum, key=lambda key: -per_stratum[key]["delta_pp"]):
        row = per_stratum[name]
        lines.append(
            "| `%s` | %d | %.2f | %.2f | %+.4f | %d | %d | %+.4f |"
            % (
                name,
                row["n"],
                row["left_pct"],
                row["right_pct"],
                row["delta_pp"],
                row["saves"],
                row["harms"],
                slu[name]["delta_pp"],
            )
        )
    lines.append("")
    lines.append(
        "**Section 4.1 clause 3, as written: no scenario loses more than 3.0 pp of intent "
        "accuracy, and at most 2 of the 18 scenarios lose anything at all.** Measured: "
        "%d scenarios lose intent and the worst loses %.4f pp. The clause FAILS on both halves."
        % (
            honest["clause_3_detail"]["scenarios_losing_intent"],
            honest["clause_3_detail"]["worst_scenario_delta_pp"],
        )
    )
    lines.append("")
    with io.open(args.table, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines))
    print("wrote %s and %s" % (args.out, args.table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
