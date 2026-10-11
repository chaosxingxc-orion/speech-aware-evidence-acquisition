#!/usr/bin/env python3
"""Model-free wire check WITH seal-and-score for one registered cell.

``core.flight.cli wire-check`` runs ``FlightRuntime.wire_check(seal_and_score=False)``; this driver runs the same
entry with ``seal_and_score=True`` so the manifest builder, bundle verifier (I7 trace coverage included), ledger-surface
validator and every registered scorer run over the wire-check transport's canned reply. No server, socket, GPU or model
is involved; every receipt reports ``model_contacts: 0``. The scores are meaningless by construction.

``wire_check`` writes under ``<data-root>/wire-check/`` and ``<data-root>/attempts/``: pass a TEMPORARY or
overlay-mounted data root, never the real ``SPEECHRL_DATA_DIR``. The study tree must be clean (a dirty tree refuses a
COMPLETED manifest by design).

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src python -B scripts/checks/wire_check_seal_and_score.py \
        --repo-root <repo> --data-root <temp-or-overlay> --runtime-root <temp> --lock-path <repo>/docs/datasets.lock.json \
        --experiment <experiment-fragment> [--cell <cell id>]
Exit status 0 only when the seal-and-score status is OK.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _scorer_receipts(seal: dict) -> dict:
    """Per registered scorer: the schema / version identifiers its receipt carries (never scores or text)."""

    out: dict = {}
    jobs = (seal.get("score_result") or {}).get("jobs") or ()
    manifest = seal.get("manifest_path")
    if not jobs or not manifest:
        return out
    path = Path(manifest).parent / "score-batch" / str(jobs[0].get("result_file"))
    if not path.is_file():
        return {"unreadable": str(path)}
    document = json.loads(path.read_text(encoding="utf-8"))
    out["_file_schema"] = document.get("schema") if isinstance(document, dict) else None
    scores = document.get("scores", document) if isinstance(document, dict) else {}
    for name, block in (scores.items() if isinstance(scores, dict) else ()):
        if isinstance(block, dict):
            out[name] = {key: block[key] for key in sorted(block) if key.endswith(("schema", "schema_id", "scorer_version", "version"))
                         and isinstance(block[key], (str, int))}
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--cell")
    parser.add_argument("--max-workers", type=int, default=1)
    args = parser.parse_args(argv)
    repo = Path(args.repo_root).resolve()
    sys.path.insert(0, str(repo / "src"))
    from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells
    from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

    cells = load_campaign_cells(repo, args.experiment)
    if args.cell:
        cells = tuple(cell for cell in cells if cell.document["cell_id"] == args.cell)
    if len(cells) != 1:
        parser.error("select exactly one cell with --cell")
    cell = cells[0]
    cell.assert_mode("wire-check")
    runtime = build_flight_runtime(
        repo, Path(args.data_root).resolve(), model=cell.document["model_fragment"],
        dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
        experiment=args.experiment, run_id=cell.run_id, attempt_id=cell.attempt_id,
        runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
    )
    receipt = runtime.wire_check(seal_and_score=True, max_workers=args.max_workers)
    summary = {key: receipt[key] for key in (
        "contact_count", "model_contacts", "sample_count", "attempt_aborted") if key in receipt}
    summary["seal_and_score"] = receipt["seal_and_score"]
    print("WIRE_SEAL_SCORE " + json.dumps(summary, sort_keys=True, default=str))
    print("SCORER_RECEIPTS " + json.dumps(_scorer_receipts(receipt["seal_and_score"]), sort_keys=True, default=str))
    return 0 if receipt["seal_and_score"].get("status") == "OK" and receipt.get("model_contacts") == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
