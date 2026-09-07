#!/usr/bin/env python3
"""CLI: the paired verdict of the two Earnings-22 model-usage cells.

Exposure row ``SAEA-E22-MF-USAGE-CELLS-VERDICT-V1`` (``model-free-check``),
registered before the first sealed score file was read.

I/O ONLY: every measurement lives in ``analysis.e22_usage_cells``. This script
arms the offline guard, hard-codes the six identity anchors, loads the
hash-pinned DEV10 reference layer and segment table, hands them to
``build_receipts``, prints the two decisions and writes the receipt directory.

**The six anchors below are the gate, not decoration.** They are the raw pairs
the two flight rows and the preregistration published, and ``build_receipts``
refuses to compute a single contrast unless every one of them reproduces.

The six ESB TEST calls are unreachable from here: ``load_esb_references`` is
pinned to the dev10 receipt alone and the segment-table loader reads the dev10
extracted table only. No model, tokenizer, embedder, network, GPU or audio
contact. Usage (WSL2): ``python scripts/e22_usage_cells_read.py [--write]``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    load_segment_table,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (  # noqa: E402
    build_receipts,
    write_check_manifest,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

#: The three raw pairs, hard-coded: arm A is the preregistration's own published
#: subset baseline (section 0), the two cells are their flight rows' sealed
#: numbers, and no contrast is computed until all six reproduce.
IDENTITY_ANCHORS = {
    "A": {"corpus_wer_percent": 17.4012, "agentic_error_rate_percent": 1.9161},
    "Q8": {"corpus_wer_percent": 16.9708, "agentic_error_rate_percent": 1.8552},
    "STOPCAP": {"corpus_wer_percent": 17.2603, "agentic_error_rate_percent": 1.9009},
}

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-06-e22-dev-usage-cells/verdict"
)


def _interval(stat: dict, key: str) -> str:
    return f"{stat[key]['point_estimate']:+.4f} [{stat[key]['ci_low']:+.4f}, {stat[key]['ci_high']:+.4f}]"


def headline(summary: dict) -> str:
    lines = [f"identity gate: {summary['identity_gate']['reproduced']} (6 pairs)"]
    for arm, block in sorted(summary["contrasts"].items()):
        decision = block["decision"]
        verdict = "ADMITTED" if decision["admitted"] else "NOT ADMITTED"
        lines.append(f"cell {block['cell']} {arm}: {verdict}")
        for name, key in (("corpus WER", "corpus_wer_delta_points"),
                          ("agentic   ", "agentic_delta_points")):
            stat = block[key]
            lines.append(
                f"    {name} stratified {_interval(stat, 'stratified')} | "
                f"clustered {_interval(stat, 'clustered')}"
            )
        row = block["per_row_wer"]
        lines.append(
            f"    clause 1 {decision['clause_1_corpus_wer_improves_with_ci90_upper_below_zero']}"
            f" | clause 2 {decision['clause_2_agentic_ci90_upper_below_margin']}"
            f" | saves {row['saves']} harms {row['harms']} ties {row['ties']}"
            f" sign p {row['sign_test_p']:.4g}"
        )
    check = summary["prediction_check_cell_b"]
    got, want = check["measured"], check["predicted"]
    lines.append(
        f"prediction check (b): bitten {got['rows_the_cap_bit']} vs "
        f"{want['rows_the_cap_bites']}; benefit {got['benefit_rows']} vs {want['benefit_rows']}; "
        f"harm {got['harm_rows']} vs {want['harm_rows']}"
    )
    null = check["cap_inert_null"]
    lines.append(
        f"    cap-inert null on {null['rows']} rows: "
        f"{_interval(null, 'pooled_delta_on_own_denominator')}"
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt directory")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    root = Path(data_root())
    references = load_esb_references(
        root,
        repo_root=REPO_ROOT,
        receipt_relpaths=(ESB_DEV10_REFERENCE_RECEIPT_RELPATH,),
    )
    segments = load_segment_table(root, REPO_ROOT)

    summary, per_call = build_receipts(
        repo_root=REPO_ROOT,
        root=root,
        references=references,
        segments=segments,
        anchors=IDENTITY_ANCHORS,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )

    print(headline(summary))
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", summary)
    (OUT_DIR / "per-call-table.csv").write_text(per_call, encoding="utf-8", newline="\n")
    write_check_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
