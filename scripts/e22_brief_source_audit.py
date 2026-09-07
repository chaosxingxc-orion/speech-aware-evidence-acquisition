#!/usr/bin/env python3
"""CLI: KC-E2's model-free brief-source audit.

Exposure row ``SAEA-E22-MF-BRIEF-SOURCE-AUDIT-V1`` (``model-free-check``),
registered before the first sealed byte is read.

I/O ONLY: every measurement lives in ``analysis.e22_brief_source_audit``. This
script arms the offline guard, loads the hash-pinned DEV10 ESB reference layer
(and ONLY that layer, so the six calibration-exposed ESB test calls are
unreachable from here), hands it to ``build_receipt``, prints the headline and
writes the receipt directory.

No model, tokenizer, embedder, retriever, network, GPU or audio contact, and no
media byte is opened. Usage (WSL2)::

    python scripts/e22_brief_source_audit.py [--write]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.e22_brief_source_audit import (  # noqa: E402
    build_receipt,
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

OUT_DIR = (
    REPO_ROOT
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-07-e22-brief-source-audit"
)


def headline(receipt: dict) -> str:
    pairing = receipt["pairing"]
    anchor = receipt["identity_anchor"]
    measurement = receipt["measurement"]
    distinctive = receipt["distinctive"]
    lines = [
        f"identity anchor: {anchor['reproduced']} "
        f"({anchor['measured_corpus_wer_percent']:.4f} % vs published "
        f"{anchor['published_corpus_wer_percent']:.4f} %, "
        f"{anchor['reference_words']} reference words)",
        f"pairing: {pairing['clips']} clips over {pairing['clusters']} call clusters",
        f"brief-term reference words: {measurement['brief_term_reference_words']} of "
        f"{measurement['reference_words']} "
        f"({100 * measurement['brief_term_share_of_reference_words']:.3f} %)",
        f"comparator recall on them: {100 * measurement['brief_term_recall']:.2f} % "
        f"({measurement['brief_term_hits']} hits, "
        f"{measurement['brief_term_substitutions']} S, "
        f"{measurement['brief_term_deletions']} D)",
        f"CEILING a perfect brief could move: "
        f"{measurement['ceiling_corpus_wer_points']:.4f} corpus-WER points",
        f"call-specific share of the term mass: "
        f"{100 * distinctive['call_specific_share']:.2f} % "
        f"({distinctive['call_specific_reference_words']} of "
        f"{distinctive['covered_reference_words']} words)",
    ]
    for field in measurement["per_field"]:
        lines.append(
            f"    {field['field']:<26} words {field['reference_words']:>6} "
            f"recall {100 * field['recall']:>6.2f} % "
            f"ceiling {field['ceiling_corpus_wer_points']:.4f} pts"
        )
    for entry in measurement["terms"]:
        if entry["own_call_reference_words"] == 0:
            continue
        lines.append(
            f"    term {entry['normalized']!r} ({entry['field']}): "
            f"own {entry['own_call_reference_words']} / other "
            f"{entry['other_call_reference_words']} "
            f"-> {'call-specific' if entry['call_specific'] else 'shared vocabulary'}"
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
    receipt = build_receipt(
        repo_root=REPO_ROOT,
        root=root,
        references=references,
        outbound_attempts=attempts.count,
        outbound_targets=list(attempts.targets),
    )
    print(headline(receipt))
    if not args.write:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json_artifact(OUT_DIR / "summary.json", receipt)
    (OUT_DIR / "per-call-table.csv").write_text(
        "call_id,clips,reference_words,brief_term_reference_words,hits,recall\n"
        + "".join(
            "%s,%d,%d,%d,%d,%.6f\n"
            % (
                row["call_id"],
                row["clips"],
                row["reference_words"],
                row["brief_term_reference_words"],
                row["hits"],
                row["recall"],
            )
            for row in receipt["measurement"]["per_call"]
        ),
        encoding="utf-8",
        newline="\n",
    )
    write_check_manifest(OUT_DIR)
    print(f"wrote {OUT_DIR}")
    print(json.dumps({"clusters": receipt["pairing"]["clusters"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
