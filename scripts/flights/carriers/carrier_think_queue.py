#!/usr/bin/env python3
"""Batch-driver queue steps, close ids and sealed-state probes of the carrier base chain, from the family (no id is typed in a shell script).

    carrier_think_queue.py steps   --carrier a2t --phase smoke|arms --out /home/chao/batch-queue.json
    carrier_think_queue.py ids     --carrier a2t [--phase smoke|all]            # run ids to close after a sealed segment, space separated
    carrier_think_queue.py state   --carrier a2t --data-root DIR               # prints sealed | opened | none for the carrier's smoke
    carrier_think_queue.py arm-state --carrier a2t --data-root DIR             # prints sealed | opened | none for the carrier's all-off arm
    carrier_think_queue.py carriers                                            # the carriers in the owner's order

Model-free. Reads the data root only for ``state`` / ``arm-state`` (the run manifest and the attempt record).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import carrier_think_family as fam  # noqa: E402


def step(order: int, short: str, key: str, *, kind: str, expected_rows: int, contacts_per_row: int, ceiling_per_row: int) -> dict:
    s = fam.CELLS[key]
    base = {"order": order, "short": short, "kind": kind, "experiment": s["cell"], "cell": s["cell"], "smoke_experiment": None, "smoke_cell": None,
            "campaign_plan": s["campaign"], "run_id": s["run"], "fit_run_id": s["fit_run"], "gen_attempt_id": s["attempt"], "smoke_run_id": None, "smoke_attempt_id": None,
            "expected_rows": expected_rows, "contacts_per_row": contacts_per_row, "ceiling_per_row": ceiling_per_row, "notool": True, "owner": f"root-{s['cell']}"}
    if kind == "engineering":
        # An `engineering` step runs only its registered four-row smoke through the worker and the structural inspector; arm and smoke identifiers are equal and no
        # campaign plan exists (batch_driver.sh).
        base.update({"smoke_experiment": s["cell"], "smoke_cell": s["cell"], "campaign_plan": None, "smoke_run_id": s["run"], "smoke_attempt_id": s["attempt"]})
    return base


def queue_steps(carrier: str, phase: str) -> list[dict]:
    b = fam.CARRIER_SPEC[carrier]["batch"]
    if phase == "smoke":
        key = fam.cell_key(carrier, "smoke")
        form = b["smoke_form"]
        if form not in ("engineering", "cell"):
            raise ValueError(f"unknown smoke form {form!r}")
        return [step(1, f"carrierthink-{carrier}-smoke", key, kind=form, expected_rows=b["smoke_expected_rows"], contacts_per_row=b["smoke_contacts_per_row"],
                     ceiling_per_row=b["ceiling_per_row"])]
    if phase == "arms":
        return [step(n, f"carrierthink-{carrier}-{kind}", fam.cell_key(carrier, kind), kind="cell", expected_rows=b["expected_rows"], contacts_per_row=b["contacts_per_row"],
                     ceiling_per_row=b["ceiling_per_row"]) for n, kind in enumerate(fam.ARM_KINDS, 1)]
    raise ValueError("phase must be smoke or arms")


def close_ids(carrier: str, phase: str = "all") -> list[str]:
    kinds = ("smoke",) if phase == "smoke" else fam.KINDS
    out: list[str] = []
    for kind in kinds:
        s = fam.CELLS[fam.cell_key(carrier, kind)]
        out.append(s["run"])
        if s["fit_run"]:
            out.append(s["fit_run"])
    return out


def sealed_state(key: str, data_root: str) -> str:
    s = fam.CELLS[key]
    manifest = os.path.join(data_root, "runs", s["run"], s["attempt"], s["run"] + ".run-manifest.json")
    attempt = os.path.join(data_root, "attempts", s["run"], s["attempt"] + ".json")
    try:
        sealed = json.load(open(manifest, encoding="utf-8")).get("status") == "COMPLETED"
    except (OSError, ValueError):
        sealed = False
    return "sealed" if sealed else ("opened" if os.path.exists(attempt) else "none")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    p.add_argument("cmd", choices=("steps", "ids", "state", "arm-state", "carriers"))
    p.add_argument("--carrier", choices=fam.CARRIERS)
    p.add_argument("--phase", default="all", choices=("smoke", "arms", "all"))
    p.add_argument("--out")
    p.add_argument("--data-root", default=os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR"))
    a = p.parse_args(argv)
    if a.cmd == "carriers":
        print(" ".join(fam.CARRIERS))
        return 0
    if a.carrier is None:
        p.error("--carrier is required")
    if a.cmd == "steps":
        if a.phase not in ("smoke", "arms") or not a.out:
            p.error("steps needs --phase smoke|arms and --out")
        Path(a.out).write_text(json.dumps(queue_steps(a.carrier, a.phase), indent=1) + "\n", encoding="utf-8", newline="\n")
        return 0
    if a.cmd == "ids":
        print(" ".join(close_ids(a.carrier, "smoke" if a.phase == "smoke" else "all")))
        return 0
    if not a.data_root:
        p.error("--data-root is required")
    print(sealed_state(fam.cell_key(a.carrier, "smoke" if a.cmd == "state" else "alloff"), a.data_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
