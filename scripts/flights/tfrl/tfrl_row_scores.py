#!/usr/bin/env python3
"""Export the per-row official SLU-F1 of the lock and ace columns for the ACE counters (I-OBJ; design 4.2 step 3).

Output ``saea-tfrl-row-scores-v1``: ``{"arms": {"lock": {sample_id: slu_f1}, "ace": {...}}, "rows": {sample_id: {"scenarios": [...],
"slot_types": [...]}}}``. The sample ids stay in this analysis artefact only; ``tfrl_loop_lib.ace_credit_from_row_scores`` replaces
them with opaque digests before the credit reaches the curator. Gold is read through the governed TRAIN loader exactly as
``tfrl_contrast_tables.py`` does, for the scenario and slot-type annotation only; no text, filler or model output is read or written.

The lock column's per-row scores are the sealed delivered scores of the run (``<run>.scores.json``); the ace column's are the per-arm
file ``arm-ace-<scorer>-scores.json`` that ``stage3_rollout_score.py --mode supply-variants`` writes under ``<run dir>/supply-variants``.

    python -B scripts/flights/tfrl/tfrl_row_scores.py --run-id R --attempt A --out F [--data-root D] [--lock L]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import tfrl_family as tf  # noqa: E402

REPO_ROOT = tf.REPO_ROOT
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

SCHEMA = "saea-tfrl-row-scores-v1"
DEFAULT_LOCK = "/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json"
DEFAULT_DATA_ROOT = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")


def per_sample_scores(document: Mapping[str, Any], scorer: str) -> dict[str, float]:
    """``{sample_id: slu_f1_f1}`` from a scores file (top-level ``per_sample`` or the scorer's block)."""

    block = document.get(scorer, document)
    rows = block.get("per_sample") if isinstance(block, Mapping) else None
    if not isinstance(rows, list):
        raise ValueError("no per_sample list in the scores file")
    return {str(r["sample_id"]): float(r["slu_f1_f1"]) for r in rows}


def build_row_scores(lock_scores: Mapping[str, float], ace_scores: Mapping[str, float], annotations: Mapping[str, Mapping[str, Any]]) -> dict:
    if sorted(lock_scores) != sorted(ace_scores) or sorted(lock_scores) != sorted(annotations):
        raise ValueError("the lock and ace columns and the annotations do not cover the same rows")
    return {"schema": SCHEMA, "arms": {"lock": dict(sorted(lock_scores.items())), "ace": dict(sorted(ace_scores.items()))},
            "rows": {sid: {"scenarios": sorted({str(annotations[sid]["scenario"])}),
                           "slot_types": sorted({str(t) for t in annotations[sid]["slot_types"]})} for sid in sorted(annotations)}}


def gold_annotations(lock_path: Path, data_root: Path, ids: set[str]) -> dict[str, dict]:
    spec = importlib.util.spec_from_file_location("slurp_nx_postproc_v4_search", REPO_ROOT / "scripts/analysis/slurp_nx_postproc_v4_search.py")
    module = importlib.util.module_from_spec(spec)           # type: ignore[arg-type]
    sys.modules[spec.name] = module                          # type: ignore[union-attr]
    spec.loader.exec_module(module)                          # type: ignore[union-attr]
    from speech_aware_evidence_acquisition.data.lock import load_lock  # noqa: PLC0415

    gold = module.load_gold(load_lock(lock_path), data_root, "train")
    return {sid: {"scenario": gold[sid]["scenario"], "slot_types": [e.type for e in gold[sid]["entities"]]} for sid in ids}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--attempt", required=True)
    parser.add_argument("--scorer", default=tf.SCORER)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data-root", default=os.environ.get("SPEECHRL_DATA_DIR", DEFAULT_DATA_ROOT))
    parser.add_argument("--lock", default=DEFAULT_LOCK)
    args = parser.parse_args(argv)
    data_root = Path(args.data_root)
    run_dir = data_root / "runs" / args.run_id / args.attempt
    lock_scores = per_sample_scores(json.loads((run_dir / f"{args.run_id}.scores.json").read_text(encoding="utf-8")), args.scorer)
    ace_path = run_dir / "supply-variants" / f"arm-ace-{args.scorer}-scores.json"
    ace_scores = per_sample_scores(json.loads(ace_path.read_text(encoding="utf-8")), args.scorer)
    annotations = gold_annotations(Path(args.lock), data_root, set(lock_scores))
    document = build_row_scores(lock_scores, ace_scores, annotations)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"{out} exists (write-once)")
    out.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out} rows={len(lock_scores)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
