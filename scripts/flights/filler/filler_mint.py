#!/usr/bin/env python3
"""Mint a BATCH of filler chunks' root-admission receipts on the data root (owner decision 162: "minted
ahead in a batch"). Root's act, never an agent's.

For every chunk k of ``--chunks`` it copies ``docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-cKK-v1/
root-admission-draft-v1.json`` to ``$SPEECHRL_DATA_DIR/coordination/slurp-stage3-filler-fold-b-cKK-v1/
root-admission-v1.json``, sets ``status`` to ``decided``, stamps ``recorded_at_utc`` and the coordinator,
re-hashes every antecedent ``{"path", "sha256"}`` naming a repository file (the flip rewrites the package,
and the receipt pins the bytes current when it is minted), and refuses to overwrite an existing receipt.
The eligible run ids and the budget caps are the draft's; they are checked against
``filler_family.names`` and never edited here.

``--countersign`` additionally rewrites, in ``docs/exposure-ledger.md``, the DRAFT marker of every row
of the minted chunks (and of the family's model-free preparation row while it is still DRAFT) to the
countersigned form. That edit is a repository change the coordinator commits on its own (as
``c75ad044`` did) BEFORE ``filler_flip.sh``, which refuses a chunk whose rows still say DRAFT.

    python scripts/flights/filler/filler_mint.py --chunks 1-6 [--coordinator NAME] [--dry] [--countersign]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import filler_family as ff  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = Path(os.environ.get("SAEA_STUDY_ROOT", str(ff.REPO_ROOT)))
LEDGER = "docs/exposure-ledger.md"
DRAFT_MARK = "(DRAFT, root countersignature pending)"


def rehash(node, root: Path) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and (root / path).is_file():
            node["sha256"] = hashlib.sha256((root / path).read_bytes()).hexdigest()
            count += 1
        for value in node.values():
            count += rehash(value, root)
    elif isinstance(node, list):
        for value in node:
            count += rehash(value, root)
    return count


def expected_run_ids(k: int) -> list[str]:
    n = ff.names(k)
    ids = [n["run"], n["fit_run"]]
    if k == 1:
        s = ff.names(1, smoke=True)
        ids += [s["run"], s["fit_run"]]
    return ids


def mint_one(k: int, *, coordinator: str, dry: bool) -> dict:
    n = ff.names(k)
    draft_path = ROOT / n["readiness_dir"] / "root-admission-draft-v1.json"
    draft = json.loads(draft_path.read_text(encoding="utf-8"))
    if draft.get("decision_id") != n["decision_id"]:
        raise SystemExit(f"c{k:02d}: draft decision_id {draft.get('decision_id')!r} is not {n['decision_id']!r}")
    if draft.get("eligible_run_ids") != expected_run_ids(k):
        raise SystemExit(f"c{k:02d}: the draft's eligible_run_ids are not this chunk's run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = coordinator
    receipt["minted_from"] = {"template_receipt": str(draft_path.relative_to(ROOT)).replace("\\", "/"),
                              "tool": "scripts/flights/filler/filler_mint.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, ROOT)
    out = Path(DATA) / n["decision_relpath"]
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if dry:
        return {"chunk": k, "would_write": str(out), "rehashed_paths": rehashed, "eligible_run_ids": receipt["eligible_run_ids"]}
    if out.exists():
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    return {"chunk": k, "written": str(out), "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "decision_id": n["decision_id"], "eligible_run_ids": receipt["eligible_run_ids"], "rehashed_paths": rehashed}


def countersign(chunks: list[int], *, coordinator: str, stamp: str, dry: bool) -> dict:
    ledger = ROOT / LEDGER
    text = io.open(ledger, encoding="utf-8", newline="").read()
    chunk_of = {run: k for k in chunks for run in expected_run_ids(k)}
    targets = set(chunk_of) | {ff.PREPARE_ROW}
    lines = text.split("\n")
    signed = []
    for index, line in enumerate(lines):
        parts = line.split("|")
        if not (line.startswith("|") and len(parts) > 3 and parts[2].strip() in targets):
            continue
        if DRAFT_MARK not in line:
            continue
        run = parts[2].strip()
        decision = "" if run == ff.PREPARE_ROW else f"; decision receipt {ff.names(chunk_of[run])['decision_relpath']}"
        lines[index] = line.replace(
            DRAFT_MARK, f"(root countersigned {stamp} by the coordinator, {coordinator}, before contact{decision})", 1)
        signed.append(run)
    if not dry and signed:
        io.open(ledger, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return {"countersigned_rows": signed, "dry": dry}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--chunks", required=True, help="e.g. 1-6")
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print what would be minted / signed, write nothing")
    parser.add_argument("--countersign", action="store_true", help="also countersign the chunks' DRAFT ledger rows")
    args = parser.parse_args()
    chunks = ff.parse_chunks(args.chunks)
    minted = [mint_one(k, coordinator=args.coordinator, dry=args.dry) for k in chunks]
    report = {"minted": minted}
    if args.countersign:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        report["ledger"] = countersign(chunks, coordinator=args.coordinator, stamp=stamp, dry=args.dry)
        if not args.dry:
            report["next"] = ("commit docs/exposure-ledger.md on master (git commit -F <msg>), then "
                              f"scripts/flights/filler/filler_flip.sh {args.chunks}")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
