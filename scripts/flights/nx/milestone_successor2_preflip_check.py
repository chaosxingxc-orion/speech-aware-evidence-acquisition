#!/usr/bin/env python3
"""Model-free refusal gate for the SLURP test-sample SUCCESSOR-2 composed cell (owner decisions 233, 241, 250 A, 251 A).

The mint (``milestone_successor2_mint_receipt.py``), the flip (``milestone_successor2_flip.sh``) and the launch chain
(``batch_chain_milestone_successor2.sh``) run this first and stop on any refusal. It opens no media, no gold and no score; it reads
committed fragments, the committed allowance and (``--data-root``) checks that each pending data-root artifact exists and that
neither run id has an attempt.

Refusals, each one printed line:

* ``allowance-pin-mismatch`` -- the fragment's ``owner_allowance`` does not hash to the committed allowance bytes;
* ``allowance-not-authorised`` -- the pinned allowance is not ``authorised``;
* ``run-not-a-read-id`` / ``fit-run-not-permitted`` -- the cell's run id is not a read id, or its FIT id is not a preparation id,
  of the pinned allowance;
* ``smoke-registered`` -- ANY smoke fragment, smoke run id or smoke campaign member exists for the cell (the allowance lists
  ``test-sample smoke`` as not authorised; a smoke under the read id would consume its one attempt);
* ``pending-pin`` -- a zero sha256 remains in the cell's baseline or in a readiness requirement other than the cell's own
  first-phase supply (which the flip itself mints, item E16);
* ``pending-artifact-missing`` -- with ``--data-root``: a re-targeted data-root artifact is absent;
* ``attempt-exists`` -- with ``--data-root``: an attempt directory already exists for the run or FIT id (ONE attempt, ever).

Exit 0 when nothing is refused, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CELL = "slurp-milestone-successor2-composed-v1"
RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1"
FIT_RUN = "SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-FIT-V1"
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
    experiment = json.loads((repo_root / "configs/experiment" / f"{CELL}.json").read_text(encoding="utf-8"))
    entry = experiment["cells"][0]
    baseline = json.loads((repo_root / "configs/baseline" / f"{entry['baseline_fragment']}.json").read_text(encoding="utf-8"))
    pin = experiment.get("owner_allowance") or {}
    allowance_path = repo_root / str(pin.get("path", ""))
    if not allowance_path.is_file():
        out.append(f"allowance-pin-mismatch: {CELL} pins no readable allowance ({pin.get('path')!r})")
    else:
        raw = allowance_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin.get("sha256"):
            out.append(f"allowance-pin-mismatch: {CELL} pins {pin.get('sha256')!r}, the committed bytes hash otherwise")
        allowance = json.loads(raw.decode("utf-8"))
        if allowance.get("status") != "authorised":
            out.append(f"allowance-not-authorised: {pin.get('path')} reads {allowance.get('status')!r}")
        if entry["run_id"] != RUN or entry["run_id"] not in (allowance.get("read_run_ids") or []):
            out.append(f"run-not-a-read-id: {entry['run_id']} is not the read run id {RUN} of {pin.get('path')}")
        fit_run = (baseline.get("native_contact_fit") or {}).get("run_id")
        if fit_run != FIT_RUN or fit_run not in (allowance.get("preparation_run_ids") or []):
            out.append(f"fit-run-not-permitted: {fit_run} is not the preparation run id {FIT_RUN} of {pin.get('path')}")
    smokes = [str(p.relative_to(repo_root)) for p in (repo_root / "configs").rglob("*successor2*smoke*")]
    if smokes:
        out.append(f"smoke-registered: {smokes} (the allowance authorises no test-sample smoke)")
    campaign = json.loads((repo_root / "configs/campaign" / f"{CELL}.json").read_text(encoding="utf-8"))
    if [c["cell"] for c in campaign["cells"]] != [CELL]:
        out.append("smoke-registered: the campaign plan is not exactly the one cell")
    for path in _zero_paths(baseline):
        out.append(f"pending-pin: {entry['baseline_fragment']}:{path} is still 64 zeros")
    own_supply = f"prepared/{entry['run_id']}/phase-supply-v1.json"
    for requirement in entry["readiness"]["requirements"]:
        if requirement.get("sha256") == ZERO and requirement.get("relpath") != own_supply:
            out.append(f"pending-pin: {CELL} readiness requirement {requirement.get('relpath')} is still 64 zeros")
        if data_root is not None and requirement.get("relpath") != own_supply:
            if not (data_root / str(requirement.get("relpath"))).is_file():
                out.append(f"pending-artifact-missing: {requirement.get('relpath')} does not exist under the data root")
    if data_root is not None:
        for run in (RUN, FIT_RUN):
            attempts = data_root / "attempts" / run
            if attempts.is_dir() and any(attempts.iterdir()):
                out.append(f"attempt-exists: {attempts} is not empty (ONE attempt, ever; never re-launch)")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--data-root", type=Path, default=None)
    args = parser.parse_args(argv)
    found = refusals(args.repo_root, args.data_root)
    for line in found:
        print("REFUSED " + line)
    print(f"milestone-successor2 preflip: {len(found)} refusal(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
