#!/usr/bin/env python3
"""Mint the root-admission decision receipt of a carrier's consumption-module ALL-OFF arm (design 2b.3 carrier admission
gate; owner decision 196, direction 205) on the data root from the package's draft.

Root's act, never an agent's, and ONLY after the owner reopens the carrier (decision 187 keeps the GPU on SLURP until the
SLURP lock). Copies ``<package>/root-admission-draft-v1.json`` (``PACKAGES``) to
``$SPEECHRL_DATA_DIR/coordination/<stem>/root-admission-v1.json``, sets ``status`` to ``decided`` and
``recorded_at_utc`` to now, re-hashes every antecedent ``{"path": ..., "sha256": ...}`` that names a repository file,
and refuses to overwrite an existing receipt. It refuses unless every run's registered ``stage3_measurement`` is the
form proof (``claims_benefit`` false) the package declared.

    python scripts/flights/module/module_alloff_mint_receipt.py --carrier a2t|e21|e22 [--coordinator "Fable5.1"] [--dry]
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
from datetime import datetime, timezone

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
ROOT = os.environ.get("SAEA_STUDY_ROOT", "/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition")
STEMS = {"a2t": "a2t-native-stage3-module-alloff-v1", "e21": "earnings21-native-stage3-module-alloff-v1",
         "e22": "earnings22-native-stage3-module-alloff-v1"}
#: Package directory per carrier (a2t / e21 registered 2026-09-30; the Earnings-22 package carries its own date and stem).
PACKAGES = {"a2t": "docs/readiness/2026-09-30-a2t-native-stage3-module-alloff-v1",
            "e21": "docs/readiness/2026-09-30-earnings21-native-stage3-module-alloff-v1",
            "e22": "docs/readiness/2026-10-11-earnings22-module-alloff-v1"}


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carrier", choices=sorted(STEMS), required=True)
    parser.add_argument("--coordinator", default="Fable5.1")
    parser.add_argument("--dry", action="store_true", help="print the receipt, write nothing")
    args = parser.parse_args()
    root = ROOT.rstrip("/")
    stem = STEMS[args.carrier]
    package = PACKAGES[args.carrier]
    facts = json.loads(io.open(os.path.join(root, package, "registered-facts-v1.json"), encoding="utf-8").read())
    for run_id, block in facts["stage3_measurement"].items():
        if block.get("measurement_design") != "form-proof" or block.get("claims_benefit") is not False:
            raise SystemExit(f"refusing to mint: {run_id} is not registered as a form proof with claims_benefit false")
    draft = json.loads(io.open(os.path.join(root, package, "root-admission-draft-v1.json"), encoding="utf-8").read())
    if draft.get("decision_id") != f"{stem}-admission-v1":
        raise SystemExit(f"draft decision_id is {draft.get('decision_id')!r}, expected {stem}-admission-v1")
    expected = sorted(r for c in facts["cells"].values() for r in (c["run_id"], c.get("fit_run_id")) if r)
    if sorted(draft.get("eligible_run_ids", [])) != expected:
        raise SystemExit("the draft's eligible_run_ids are not the package's run ids")
    receipt = json.loads(json.dumps(draft))
    receipt.update({"status": "decided", "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                    "coordinator": args.coordinator,
                    "minted_from": {"template_receipt": f"{package}/root-admission-draft-v1.json",
                                    "tool": "scripts/flights/module/module_alloff_mint_receipt.py"}})
    receipt.pop("_draft_note", None)
    rehashed = rehash(receipt, root)
    out_dir = os.path.join(DATA, "coordination", stem)
    out = os.path.join(out_dir, "root-admission-v1.json")
    text = json.dumps(receipt, indent=2, ensure_ascii=False) + "\n"
    if args.dry:
        print(text)
        print(f"(dry) would write {out}; re-hashed {rehashed} antecedent path(s)")
        return 0
    if os.path.exists(out):
        raise SystemExit(f"refusing to overwrite an existing receipt: {out}")
    os.makedirs(out_dir, exist_ok=True)
    io.open(out, "w", encoding="utf-8", newline="\n").write(text)
    print(json.dumps({"written": out, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "eligible_run_ids": expected, "rehashed_paths": rehashed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
