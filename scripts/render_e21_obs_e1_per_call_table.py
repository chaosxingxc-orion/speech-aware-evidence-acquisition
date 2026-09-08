#!/usr/bin/env python3
"""Render the OBS-E1 per-call table from the verdict's own result-summary.json.

usage: render_per_call_table.py <result-summary.json> <out.md>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fmt(value, digits=4):
    if value is None:
        return "--"
    return f"{value:.{digits}f}"


def main() -> int:
    document = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = Path(sys.argv[2])
    lines: list[str] = []
    lines.append("# OBS-E1 — the per-call table, all 44 calls\n")
    lines.append(
        "Cell `SAEA-E21-OBS-E1-SPEAKER-TURN-UNITS-V1` against the sealed comparator\n"
        "`SAEA-E21-FULL44-DIRECT-BASELINE-V2`. `impr` is signed so that POSITIVE means the\n"
        "cell is better; it is `comparator - cell` for the error rates and `cell -\n"
        "comparator` for numeric-value accuracy. Units, cut seconds and delivered seconds\n"
        "are the pinned v2 plan's own, fixed model-free before any score existed.\n"
    )
    header = (
        "| call | units | windows | cut s | delivered s | mean unit s | dominated | "
        "WER comp | WER cell | WER impr | PERSON comp | PERSON cell | PERSON impr | "
        "PERSON ref w | ORG impr | numeric impr |"
    )
    lines.append(header)
    lines.append("|" + "---|" * 16)
    for row in sorted(document["per_call"], key=lambda r: r["sample_id"]):
        wer = row["corpus_wer_percent"]
        person = row["conec_person_wer_percent"]
        org = row["conec_org_wer_percent"]
        numeric = row["numeric_value_accuracy_percent"]
        lines.append(
            "| {call} | {units} | {windows} | {cut} | {delivered} | {mean} | {dom} | "
            "{wc} | {wl} | {wi} | {pc} | {pl} | {pi} | {pr} | {oi} | {ni} |".format(
                call=row["sample_id"],
                units=row["units"],
                windows=row["windows"],
                cut=fmt(row["cut_seconds"], 3),
                delivered=fmt(row["delivered_seconds"], 3),
                mean=fmt(row["unit_seconds_mean"], 2),
                dom=f"{row['dominated_units']}/{row['units']}",
                wc=fmt(wer["comparator"]),
                wl=fmt(wer["cell"]),
                wi=("%+.4f" % wer["improvement"]) if wer["improvement"] is not None else "--",
                pc=fmt(person["comparator"]),
                pl=fmt(person["cell"]),
                pi=("%+.4f" % person["improvement"])
                if person["improvement"] is not None
                else "--",
                pr=person["reference_words"],
                oi=("%+.4f" % org["improvement"]) if org["improvement"] is not None else "--",
                ni=("%+.4f" % numeric["improvement"])
                if numeric["improvement"] is not None
                else "--",
            )
        )
    lines.append("")
    lines.append("## Pooled over all 44 calls\n")
    lines.append("| metric | comparator | cell | improvement | CI90 | own-null half-width |")
    lines.append("|---|---:|---:|---:|---|---:|")
    for name, block in sorted(document["metrics"].items()):
        half = block.get("own_null_half_width")
        lines.append(
            "| `{n}` | {c:.5f} | {l:.5f} | {i:+.4f} | [{lo:+.4f}, {hi:+.4f}] | {hw} |".format(
                n=name,
                c=block["comparator"],
                l=block["cell"],
                i=block["improvement_point"],
                lo=block["improvement_ci90_low"],
                hi=block["improvement_ci90_high"],
                hw=("%.5f" % half) if half is not None else "--",
            )
        )
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote", out, len(document["per_call"]), "calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
