#!/usr/bin/env python3
"""Model-free refusal gate for the COMP-1b TEST-SAMPLE milestone flip (owner decisions 151 and 202).

The flip (``comp1b_testsample_flip.sh``) and the mint (``comp1b_testsample_mint_receipt.py``) run this
first and stop on any refusal. It opens no media, no gold and no score; it reads committed configs,
the committed allowance and the package's registered facts, and (``--data-root``) checks that each
PENDING data-root artifact now exists.

Refusals, each one printed line:

* ``expectation-not-redeclared`` -- ``registered-facts-v1.json`` still reads
  ``redeclared_from_a2_read: false`` (root re-declares ``expected_effect_pp`` from the A2 read);
* ``fit-run-not-permitted`` -- a milestone cell's ``native_contact_fit.run_id`` is not among the
  ``permitted_run_ids`` of the allowance its fragment pins (v1 names none; a successor must);
* ``allowance-pin-mismatch`` / ``allowance-not-authorised`` -- the pinned bytes or status moved;
* ``read-run-not-a-read-id`` -- a milestone generation run id is not a ``read_run_ids`` entry;
* ``pending-pin`` -- a zero sha256 remains anywhere in a milestone baseline (knowledge-store
  sources, preparation receipts) or in a readiness requirement other than the cell's own
  first-phase supply (which the flip itself mints, item E16);
* ``pending-artifact-missing`` -- with ``--data-root``: a re-targeted data-root artifact is absent.

Exit 0 when nothing is refused, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE = "docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1"
CELLS = ("slurp-native-stage3-plan-testsample-milestone00-v1", "slurp-native-stage3-comp1b-testsample-v1")
ZERO = "0" * 64


def _zero_paths(node, path=""):
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _zero_paths(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _zero_paths(value, f"{path}[{index}]")
    elif node == ZERO:
        yield path


def refusals(repo_root: Path, data_root: Path | None) -> list[str]:
    out: list[str] = []
    facts = json.loads((repo_root / PACKAGE / "registered-facts-v1.json").read_text(encoding="utf-8"))
    if facts.get("redeclared_from_a2_read") is not True:
        out.append("expectation-not-redeclared: registered-facts redeclared_from_a2_read is not true; root re-declares "
                   "expected_effect_pp from the A2 read before the flip")
    for cell in CELLS:
        experiment = json.loads((repo_root / "configs/experiment" / f"{cell}.json").read_text(encoding="utf-8"))
        entry = experiment["cells"][0]
        baseline = json.loads((repo_root / "configs/baseline" / f"{entry['baseline_fragment']}.json").read_text(encoding="utf-8"))
        pin = experiment.get("owner_allowance") or {}
        allowance_path = repo_root / str(pin.get("path", ""))
        if not allowance_path.is_file():
            out.append(f"allowance-pin-mismatch: {cell} pins no readable allowance ({pin.get('path')!r})")
            continue
        raw = allowance_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin.get("sha256"):
            out.append(f"allowance-pin-mismatch: {cell} pins {pin.get('sha256')!r}, the committed bytes hash otherwise")
        allowance = json.loads(raw.decode("utf-8"))
        if allowance.get("status") != "authorised":
            out.append(f"allowance-not-authorised: {pin.get('path')} reads {allowance.get('status')!r}")
        if entry["run_id"] not in (allowance.get("read_run_ids") or []):
            out.append(f"read-run-not-a-read-id: {entry['run_id']} is not a read run id of {pin.get('path')}")
        fit_run = (baseline.get("native_contact_fit") or {}).get("run_id")
        if fit_run not in (allowance.get("permitted_run_ids") or []):
            out.append(f"fit-run-not-permitted: {fit_run} is not a permitted run id of {pin.get('path')} "
                       "(a successor allowance must name it; owner signature)")
        for path in _zero_paths(baseline):
            out.append(f"pending-pin: {entry['baseline_fragment']}:{path} is still 64 zeros")
        own_supply = f"prepared/{entry['run_id']}/phase-supply-v1.json"
        for requirement in entry["readiness"]["requirements"]:
            if requirement.get("sha256") == ZERO and requirement.get("relpath") != own_supply:
                out.append(f"pending-pin: {cell} readiness requirement {requirement.get('relpath')} is still 64 zeros")
            if data_root is not None and requirement.get("relpath") != own_supply:
                if not (data_root / str(requirement.get("relpath"))).is_file():
                    out.append(f"pending-artifact-missing: {requirement.get('relpath')} does not exist under the data root")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    found = refusals(args.repo_root, args.data_root)
    for line in found:
        print("REFUSED " + line)
    print(f"comp1b-testsample preflip: {len(found)} refusal(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
