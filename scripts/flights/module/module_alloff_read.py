#!/usr/bin/env python3
"""The descriptive FORM read of a carrier's consumption-module ALL-OFF arm (design 2b.3; owner decision 196, direction 205).

MODEL-FREE. Refuses before opening anything unless the package's READ row is ROOT COUNTERSIGNED in
``docs/exposure-ledger.md`` (after the seal). Then, for the arm and the smoke: the sealed run manifest's composed
``config_hash`` must equal the registered one (the module-compiled all-off bytes flew), and the module byte proof
(``module_equivalence_proof.py --at a2t0 | e210``) is re-run on the tree. It reports ids and hashes only -- never an
utterance, transcript, gold label or model output -- and states no verdict: the all-off arm claims no benefit.

    python -B scripts/flights/module/module_alloff_read.py --carrier a2t|e21|e22
"""

from __future__ import annotations
import os

import argparse
import glob
import io
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(REPO_ROOT / "src"))

import module_equivalence_proof as proof  # noqa: E402

DATA = (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
STEMS = {"a2t": ("a2t-native-stage3-module-alloff-v1", "a2t0"), "e21": ("earnings21-native-stage3-module-alloff-v1", "e210"),
         "e22": ("earnings22-native-stage3-module-alloff-v1", "e220")}
#: Package directory per carrier (the Earnings-22 package carries its own date and stem).
PACKAGES = {"a2t": "2026-09-30-a2t-native-stage3-module-alloff-v1", "e21": "2026-09-30-earnings21-native-stage3-module-alloff-v1",
            "e22": "2026-10-11-earnings22-module-alloff-v1"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--carrier", choices=sorted(STEMS), required=True)
    args = parser.parse_args()
    stem, at = STEMS[args.carrier]
    package = REPO_ROOT / "docs" / "readiness" / PACKAGES[args.carrier]
    facts = json.loads(io.open(package / "registered-facts-v1.json", encoding="utf-8").read())
    read_run = facts["read_run_id"]
    rows = [line for line in io.open(REPO_ROOT / "docs" / "exposure-ledger.md", encoding="utf-8")
            if line.startswith(f"| ") and f"| {read_run} |" in line]
    if len(rows) != 1 or "root countersigned" not in rows[0]:
        raise SystemExit(f"refusing: the READ row {read_run} is not ROOT COUNTERSIGNED (found {len(rows)} row(s))")
    report = {"read_run_id": read_run, "cells": {}, "byte_proof_ok": proof.run_case(at, REPO_ROOT)["ok"]}
    for key, cell in facts["cells"].items():
        manifests = sorted(glob.glob(f"{DATA}/runs/{cell['run_id']}/*/{cell['run_id']}.run-manifest.json"))
        sealed = [json.loads(io.open(m, encoding="utf-8").read()) for m in manifests]
        hashes = [((s.get("config") or {}).get("config_hash")) for s in sealed]
        report["cells"][key] = {"run_id": cell["run_id"], "registered_config_hash": cell["composed_config_hash"],
                                "sealed_manifests": len(manifests), "sealed_config_hashes": hashes,
                                "flew_the_registered_bytes": bool(hashes) and all(h == cell["composed_config_hash"] for h in hashes)}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
