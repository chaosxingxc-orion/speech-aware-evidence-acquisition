#!/usr/bin/env python3
"""CLI: the Earnings-22 DEV over-generation analysis (model-free, zero contacts).

Exposure row ``SAEA-E22-MF-OVERGENERATION-ANALYSIS-V1`` (``model-free-check``),
registered before the first sealed byte was read.

I/O ONLY: every measurement and every receipt field lives in
``analysis.e22_overgeneration``. This script arms the offline guard, loads the
hash-pinned DEV10 reference layer, the DEV10 segment table, the sealed arm A
outputs and trace and the committed clip-boundary geometry table, hands them to
``build_receipts``, prints the headline and writes the receipt directory with
its ``MANIFEST.sha256``.

The six ESB TEST calls are unreachable from here: ``load_esb_references`` is
pinned to the dev10 receipt path alone, so ``e22-esb-test-references.jsonl`` is
never opened; the segment-table loader reads the dev10 extracted table only; and
the only run directory named is the sealed dev arm A attempt. No model,
tokenizer, embedder, network, GPU or audio contact.

Usage (WSL2)::

    python scripts/run_e22_overgeneration_analysis.py            # print only
    python scripts/run_e22_overgeneration_analysis.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    ARM_SOURCES,
    load_hypotheses,
    load_segment_table,
    outputs_path,
)
from speech_aware_evidence_acquisition.analysis.e22_overgeneration import (  # noqa: E402
    ARM,
    build_receipts,
    build_rows,
    load_clip_geometry,
    load_flight_tokens,
    trace_path,
)
from speech_aware_evidence_acquisition.core.roster import read_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

#: The reserved 1,500-row dev subset the three model-usage cells fly. Read for
#: its sample ids only, so the cap frontier can be projected onto the
#: population a cell would actually measure.
SUBSET_ROSTER_RELPATH = "docs/receipts/rosters/e22-dev-esb-1500-v1.json"

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition/2026-09-06-e22-overgeneration-analysis"
)


def write_manifest(directory: Path) -> None:
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()} *{path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "MANIFEST.sha256"
    ]
    (directory / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")


def headline(summary: dict) -> str:
    excess = summary["excess_distribution"]
    final = summary["sentence_final"]
    lines = [
        f"arm {summary['arm']}: {excess['rows']} rows, "
        f"corpus WER {summary['identity_gate']['corpus_wer_percent']:.4f} % "
        f"(identity gate {summary['identity_gate']['reproduced']})",
        f"  length ratio {excess['length_ratio']:.4f}; longer {excess['rows_longer']}, "
        f"equal {excess['rows_equal']}, shorter {excess['rows_shorter']}; "
        f"net excess {excess['net_excess_words']} words "
        f"(gross +{excess['gross_excess_words']} / -{excess['gross_deficit_words']})",
        f"  excess quantiles p50 {excess['quantiles']['p50']:.0f}, "
        f"p95 {excess['quantiles']['p95']:.0f}, p99 {excess['quantiles']['p99']:.0f}, "
        f"max {excess['quantiles']['max']:.0f}",
        f"  ends sentence-final {final['sentence_final']['rows']}, "
        f"runs on {final['run_on']['rows']}",
    ]
    for block in summary["excess_by_overlap"]:
        lines.append(
            f"  {block['label']}: {block['rows']} rows, ratio {block['length_ratio']:.4f}, "
            f"mean excess {block['mean_excess_words']:.2f} words, "
            f"WER {block['corpus_wer_percent']:.3f} %"
        )
    frontier = summary["cap_frontier"]
    lines.append(
        f"  cap constants: words/s p95 {frontier['words_per_second_p95']:.4f}, "
        f"tokens/word {frontier['tokens_per_word']:.4f}"
    )
    for rung in frontier["rungs"]:
        lines.append(
            f"  alpha {rung['alpha']:.2f}: capped {rung['rows_capped']}, "
            f"benefit {rung['benefit_rows']}, harm(realized) {rung['harm_rows_realized']}, "
            f"harm(cap<ref) {rung['harm_rows_cap_below_reference']}, "
            f"bleed rows cut {rung['tail_bleed_rows_capped']}/{rung['tail_bleed_rows_total']}, "
            f"WER {rung['corpus_wer_percent']:.4f} % "
            f"({rung['corpus_wer_delta_points']:+.4f})"
            + (
                f", agentic {rung['agentic']['agentic_error_rate_percent']:.4f} %"
                if "agentic" in rung
                else ""
            )
        )
    subset = summary.get("subset_projection")
    if subset:
        base = subset["baseline"]
        lines.append(
            f"  subset {subset['label']}: {subset['rows']} rows, uncapped WER "
            f"{base['corpus_wer_percent']:.4f} %"
            + (
                f", agentic {base['agentic']['agentic_error_rate_percent']:.4f} %"
                if "agentic" in base
                else ""
            )
        )
        for rung in subset["cap_frontier"]["rungs"]:
            agentic = rung.get("agentic", {}).get("agentic_error_rate_percent")
            lines.append(
                f"    alpha {rung['alpha']:.2f}: capped {rung['rows_capped']}, "
                f"benefit {rung['benefit_rows']}, harm {rung['harm_rows_realized']}, "
                f"bleed cut {rung['tail_bleed_rows_capped']}/{rung['tail_bleed_rows_total']}, "
                f"WER {rung['corpus_wer_percent']:.4f} % "
                f"({rung['corpus_wer_delta_points']:+.4f})"
                + (f", agentic {agentic:.4f} %" if agentic is not None else "")
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    parser.add_argument(
        "--no-subset",
        action="store_true",
        help="skip the E22-DEV-ESB-1500-V1 subset projection",
    )
    args = parser.parse_args()

    attempts = arm_offline_guard()
    root = Path(data_root())
    references = load_esb_references(
        root,
        repo_root=REPO_ROOT,
        receipt_relpaths=(ESB_DEV10_REFERENCE_RECEIPT_RELPATH,),
    )
    segments = load_segment_table(root, REPO_ROOT)
    hypotheses = load_hypotheses(outputs_path(root, ARM))
    flight_tokens = load_flight_tokens(trace_path(root, ARM))
    geometry = load_clip_geometry(REPO_ROOT)

    subset_ids = None
    subset_label = None
    if not args.no_subset:
        roster = read_roster(REPO_ROOT / SUBSET_ROSTER_RELPATH)
        subset_ids = [str(item["sample_id"]) for item in roster["items"]]
        subset_label = str(roster["roster_id"])

    rows = build_rows(
        references=references,
        hypotheses=hypotheses,
        flight_tokens=flight_tokens,
        geometry=geometry,
        segments=segments,
    )
    summary, per_row = build_receipts(
        rows=rows,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
        references=references,
        segments=segments,
        subset_ids=subset_ids,
        subset_label=subset_label,
    )
    summary["arm_source"] = dict(ARM_SOURCES[ARM])

    print(headline(summary))
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", summary)
    (OUT_DIR / "per-row-table.csv").write_text(per_row, encoding="utf-8", newline="\n")
    write_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
