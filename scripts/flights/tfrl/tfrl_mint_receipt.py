#!/usr/bin/env python3
"""Mint a loop iteration's root-admission decision receipt on the data root from the package's DRAFT.

Root's act, never an agent's, and never the loop driver's. Copies ``<package>/root-admission-draft-v1.json`` to
``$SPEECHRL_DATA_DIR/coordination/<decision dir>/root-admission-v1.json``, sets ``status`` to ``decided`` and ``recorded_at_utc`` to now,
re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file, and refuses to overwrite an existing receipt. The
eligible run ids and the budget caps are the draft's and are not edited here.

    python scripts/flights/tfrl/tfrl_mint_receipt.py --iteration 1 --kind column [--coordinator "Fable5.1"] [--dry]

SMOKE RECOVERY (rec1, ``tfrl_family.SMOKE_RECOVERIES``): a recovery changes attempt ids and the smoke's run-cumulative budget, never the run ids, so a
receipt already minted from the earlier draft is neither overwritten (this tool refuses) nor re-minted; the regenerated draft lists the
``eligible_attempt_ids`` (rec1) and the ``superseded_attempt_ids`` for the record, and eligibility is keyed by run id.

``--kind construction`` mints ``slurp-tfrl-construction-lock-r01c-admission-v1`` for the construction-source lock column and its smoke (the
typed loop's proposer / reflector material source on R01C; ``--iteration`` is ignored). ``--kind column`` mints ``slurp-tfrl-loop-i<t>-admission-v1`` for the column cell and its smoke; ``--kind proposers`` mints
``slurp-tfrl-proposers-i<t>-admission-v1`` for the text-only typed proposer and ACE reflector cells (two eligible run ids, no FIT identity: text-only).
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

import tfrl_family as tf  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get("SAEA_STUDY_ROOT", str(tf.REPO_ROOT))


def rehash(node, root: str) -> int:
    count = 0
    if isinstance(node, dict):
        path = node.get("path")
        if isinstance(path, str) and os.path.isfile(os.path.join(root, path)):
            node["sha256"] = hashlib.sha256(io.open(os.path.join(root, path), "rb").read()).hexdigest()
            count += 1
        for value in node.values():
            count += rehash(value, root)
    elif isinstance(node, list):
        for value in node:
            count += rehash(value, root)
    return count


def identities(iteration: int, kind: str) -> dict:
    if kind == "construction":
        arm, smoke = tf.const_names("arm"), tf.const_names("smoke")
        return {"decision_id": arm["decision_id"], "decision_dir": Path(arm["decision_path"]).parent.name, "package": tf.CONST_PACKAGE_DIR,
                "eligible": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]}
    if kind == "column":
        arm, smoke = tf.names(iteration, "arm"), tf.names(iteration, "smoke")
        return {"decision_id": f"slurp-tfrl-loop-i{iteration}-admission-v1", "decision_dir": f"slurp-tfrl-loop-i{iteration}-v1",
                "package": f"docs/readiness/{tf.DATE}-slurp-tfrl-loop-i{iteration}-fold-b-v1",
                "eligible": [arm["run_id"], arm["fit_run_id"], smoke["run_id"], smoke["fit_run_id"]]}
    typed, ace = tf.names(iteration, "typed"), tf.names(iteration, "ace")
    return {"decision_id": f"slurp-tfrl-proposers-i{iteration}-admission-v1", "decision_dir": f"slurp-tfrl-proposers-i{iteration}-v1",
            "package": f"docs/readiness/{tf.DATE}-slurp-tfrl-loop-i{iteration}-proposers-v1",
            "eligible": [typed["run_id"], ace["run_id"]]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--iteration", type=int, default=1, choices=tf.ITERATIONS, help="ignored for --kind construction")
    parser.add_argument("--kind", choices=("column", "proposers", "construction"), default="column")
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args(argv)
    ident = identities(args.iteration, args.kind)
    root = ROOT.rstrip("/")
    draft_path = f"{ident['package']}/root-admission-draft-v1.json"
    full = os.path.join(root, draft_path)
    if not os.path.isfile(full):
        raise SystemExit(f"no DRAFT at {draft_path}: run the registration writer first")
    draft = json.loads(io.open(full, encoding="utf-8").read())
    if draft.get("decision_id") != ident["decision_id"]:
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {ident['decision_id']!r}")
    if draft.get("eligible_run_ids") != ident["eligible"]:
        raise SystemExit("the draft's eligible_run_ids are not this cell's run ids")
    receipt = json.loads(json.dumps(draft))
    receipt["status"] = "decided"
    receipt["recorded_at_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["coordinator"] = args.coordinator
    receipt["minted_from"] = {"template_receipt": draft_path, "tool": "scripts/flights/tfrl/tfrl_mint_receipt.py"}
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out = os.path.join(DATA, "coordination", ident["decision_dir"], "root-admission-v1.json")
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "decision_id": ident["decision_id"],
                      "eligible_run_ids": ident["eligible"], "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
