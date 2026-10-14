#!/usr/bin/env python3
"""Model-free refusal gate for the SUCCESSOR-3 cell (the Thinking system on the signed test sample; owner ruling 301 A).

The mint (``successor3_thinking_mint_receipt.py``), the flip (``successor3_thinking_flip.sh``) and the launch chain (``batch_chain_successor3_thinking.sh``) run this
first and stop on any refusal. It opens no media, no gold and no score; it reads committed fragments, the committed allowance and (``--data-root``) checks that each
pending data-root artifact and the Thinking sample promotion receipt exist and that neither run id has an attempt.

Refusals, each one printed line:

* ``allowance-pin-mismatch`` -- the fragment's ``owner_allowance`` does not hash to the committed allowance bytes;
* ``allowance-not-authorised`` -- the pinned allowance is not ``authorised``;
* ``run-not-a-read-id`` / ``fit-run-not-permitted`` -- the cell's run id is not a read id, or its FIT id is not a preparation id, of the pinned allowance;
* ``smoke-registered`` -- ANY smoke or twin fragment, run id or campaign member exists for the cell (no smoke, no twin on the sample);
* ``pending-pin`` -- a zero sha256 remains in the cell's baseline (the Thinking packet-receipt pin included) or in a readiness requirement other than the cell's own
  first-phase supply and the decision receipt (which the flip itself mints / pins);
* ``packets-receipt-missing`` / ``pending-artifact-missing`` -- with ``--data-root``: the Thinking sample promotion receipt or a re-targeted artifact is absent;
* ``attempt-exists`` -- with ``--data-root``: an attempt directory already exists for the run or FIT id (ONE attempt, ever).

Exit 0 when nothing is refused, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import successor3_thinking_family as fam  # noqa: E402

REPO_ROOT = fam.REPO_ROOT
ZERO = fam.ZERO


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
    experiment = json.loads((repo_root / "configs/experiment" / f"{fam.CELL}.json").read_text(encoding="utf-8"))
    entry = experiment["cells"][0]
    baseline = json.loads((repo_root / "configs/baseline" / f"{entry['baseline_fragment']}.json").read_text(encoding="utf-8"))
    pin = experiment.get("owner_allowance") or {}
    allowance_path = repo_root / str(pin.get("path", ""))
    if not allowance_path.is_file():
        out.append(f"allowance-pin-mismatch: {fam.CELL} pins no readable allowance ({pin.get('path')!r})")
    else:
        raw = allowance_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin.get("sha256"):
            out.append(f"allowance-pin-mismatch: {fam.CELL} pins {pin.get('sha256')!r}, the committed bytes hash otherwise")
        allowance = json.loads(raw.decode("utf-8"))
        if allowance.get("status") != "authorised":
            out.append(f"allowance-not-authorised: {pin.get('path')} reads {allowance.get('status')!r}")
        if entry["run_id"] != fam.RUN or entry["run_id"] not in (allowance.get("read_run_ids") or []):
            out.append(f"run-not-a-read-id: {entry['run_id']} is not the read run id {fam.RUN} of {pin.get('path')}")
        fit_run = (baseline.get("native_contact_fit") or {}).get("run_id")
        if fit_run != fam.FIT_RUN or fit_run not in (allowance.get("preparation_run_ids") or []):
            out.append(f"fit-run-not-permitted: {fit_run} is not the preparation run id {fam.FIT_RUN} of {pin.get('path')}")
    extras = [str(p.relative_to(repo_root)) for p in (repo_root / "configs").rglob("*successor3*")
              if p.name not in (f"{fam.CELL}.json", f"{fam.BASELINE}.json")]
    if extras:
        out.append(f"smoke-registered: {sorted(extras)} (no smoke, no twin on the sample)")
    campaign = json.loads((repo_root / fam.CAMPAIGN_PLAN).read_text(encoding="utf-8"))
    if [c["cell"] for c in campaign["cells"]] != [fam.CELL]:
        out.append("smoke-registered: the campaign plan is not exactly the one cell")
    for path in _zero_paths(baseline):
        out.append(f"pending-pin: {entry['baseline_fragment']}:{path} is still 64 zeros")
    own_supply = f"prepared/{entry['run_id']}/phase-supply-v1.json"
    for requirement in entry["readiness"]["requirements"]:
        relpath = requirement.get("relpath")
        if requirement.get("sha256") == ZERO and relpath not in (own_supply, fam.DECISION_RELPATH):
            out.append(f"pending-pin: {fam.CELL} readiness requirement {relpath} is still 64 zeros")
        if data_root is not None and relpath not in (own_supply, fam.DECISION_RELPATH):
            if not (data_root / str(relpath)).is_file():
                out.append(f"pending-artifact-missing: {relpath} does not exist under the data root")
    if data_root is not None:
        receipt = Path(baseline.get("speech_packet_promotion_receipt", ""))
        if not receipt.is_file():
            out.append(f"packets-receipt-missing: {receipt} does not exist (run the packets window first)")
        for run in (fam.RUN, fam.FIT_RUN):
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
    print(f"milestone-successor3 preflip: {len(found)} refusal(s)")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
