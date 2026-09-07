#!/usr/bin/env python3
"""CLI: the paired verdict of the three Earnings-22 encoding probe cells.

Exposure row ``SAEA-E22-MF-ENCODING-PROBES-VERDICT-V1`` (``model-free-check``),
registered before the first sealed score file is read.

I/O ONLY: every measurement lives in ``analysis.e22_encoding_probes``, which is
itself a thin derivation over ``analysis.e22_usage_cells``. This script arms the
offline guard, hard-codes the four identity anchors, loads the hash-pinned DEV10
reference layer and segment table, hands them to ``build_receipts``, prints the
three decisions and writes the receipt directory.

**The four raw TRIPLES below are the gate, not decoration.** Arm A's triple is
the 2026-09-06 usage-cells verdict's own sealed numbers on these 1,500 rows;
each cell's triple is what its own flight receipt published. ``build_receipts``
refuses to compute a single contrast unless all twelve numbers reproduce, and it
runs the section 4.1 ``prompt_tokens`` falsifier of every cell before it opens a
score at all.

The six ESB TEST calls are unreachable from here: ``load_esb_references`` is
pinned to the dev10 receipt alone and the segment-table loader reads the dev10
extracted table only. No model, tokenizer, embedder, network, GPU or audio
contact, and no media byte is opened. Usage (WSL2):
``python scripts/e22_encoding_probes_read.py [--write]``.
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
from speech_aware_evidence_acquisition.analysis.e22_encoding_probes import (  # noqa: E402
    build_receipts,
)
from speech_aware_evidence_acquisition.analysis.e22_error_taxonomy import (  # noqa: E402
    load_segment_table,
)
from speech_aware_evidence_acquisition.analysis.e22_usage_cells import (  # noqa: E402
    write_check_manifest,
)
from speech_aware_evidence_acquisition.data.lock import data_root  # noqa: E402
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.esb_reference import (  # noqa: E402
    ESB_DEV10_REFERENCE_RECEIPT_RELPATH,
    load_esb_references,
)

#: The four raw triples, hard-coded: corpus WER under the Whisper normalizer,
#: the agentic error rate, and the boundary block in WER points. Arm A is the
#: 2026-09-06 usage-cells verdict section 4.5; each cell is its own flight
#: receipt's ``flight-read.json``. No contrast is computed until all twelve
#: numbers reproduce.
IDENTITY_ANCHORS = {
    "A": {
        "corpus_wer_percent": 17.4012,
        "agentic_error_rate_percent": 1.9161,
        "boundary_block_wer_points": 8.2778,
    },
    "BX": {
        "corpus_wer_percent": 14.3537,
        "agentic_error_rate_percent": 1.8971,
        "boundary_block_wer_points": 5.4969,
    },
    "TAIL2S": {
        "corpus_wer_percent": 9.4054,
        "agentic_error_rate_percent": 1.7599,
        "boundary_block_wer_points": 1.1085,
    },
    "PAD30S": {
        "corpus_wer_percent": 9.3254,
        "agentic_error_rate_percent": 1.7752,
        "boundary_block_wer_points": 0.9295,
    },
}

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-dev-encoding-probes/verdict"
)


def _interval(stat: dict, key: str) -> str:
    block = stat[key]
    return f"{block['point_estimate']:+.4f} [{block['ci_low']:+.4f}, {block['ci_high']:+.4f}]"


def headline(summary: dict) -> str:
    lines = [f"identity gate: {summary['identity_gate']['reproduced']} (12 numbers, 4 arms)"]
    for arm in ("BX", "TAIL2S", "PAD30S"):
        block = summary["contrasts"][arm]
        decision = block["decision"]
        verdict = "ADMITTED" if decision["admitted"] else "NOT ADMITTED"
        lines.append(f"cell {block['cell']} {block['variant']} ({arm}): {verdict}")
        for name, key in (
            ("corpus WER", "corpus_wer_delta_points"),
            ("agentic   ", "agentic_delta_points"),
            ("boundary  ", "boundary_delta_points"),
        ):
            stat = block[key]
            lines.append(
                f"    {name} stratified {_interval(stat, 'stratified')} | "
                f"clustered {_interval(stat, 'clustered')}"
            )
        row = block["per_row_wer"]
        lines.append(
            f"    clause 1 {decision['clause_1_corpus_wer_improves_with_ci90_upper_below_zero']}"
            f" | clause 2 {decision['clause_2_agentic_ci90_upper_below_margin']}"
            f" | clause 3 {decision['clause_3_boundary_block_falls_by_at_least_points']}"
            f" | saves {row['saves']} harms {row['harms']} ties {row['ties']}"
            f" sign p {row['sign_test_p']:.4g}"
        )
    for name, block in summary["pairwise_contrasts"].items():
        lines.append(
            f"pairwise {name}: corpus WER "
            f"{_interval(block['corpus_wer_delta_points'], 'stratified')}, boundary "
            f"{_interval(block['boundary_delta_points'], 'stratified')}, audio tokens x"
            f"{block['audio_token_ratio']}"
        )
    closing = summary["closing_rule"]
    lines.append(
        f"closing rule fires: {closing['fires']}; admitted {closing['cells_admitted']}; "
        f"clause 3 cleared by {closing['cells_clearing_clause_3']}"
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
