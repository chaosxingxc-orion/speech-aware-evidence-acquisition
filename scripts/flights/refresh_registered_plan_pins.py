#!/usr/bin/env python3
"""Refresh the prepared-supply pin of registered plan copies from their cell baselines.

The launch gate ``registered-supply-binding`` (scripts/checks/flight_registration_check.py)
requires each ``docs/readiness/<package>/*plan-registered*.json`` that declares
``prepared_phase_supply`` to equal the cell baseline fragment's pin.  The flip loop
(``scripts/flights/repin_cell.py --set-ready``, item E16) mints that pin AFTER the package
writer ran, so the writer can only leave a placeholder.  This tool closes the gap: for every
registered plan in a package it resolves the plan's cell (plan ``experiment`` fragment ->
``cells[*].baseline_fragment``), reads the baseline's ``prepared_phase_supply`` and, when that
pin carries a real sha256, sets the plan's field to EXACTLY that dict.  Annotations the writer
had placed inside the pin (``note``, ``expected_output_sha256``, ...) move to the sibling key
``prepared_phase_supply_annotations``.  A baseline that still carries a placeholder leaves the
plan unchanged.  The tool is idempotent, model-free, and never touches the exposure ledger.

Usage: refresh_registered_plan_pins.py --package docs/readiness/<dir> [--cell <cell id> ...] [--dry]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_HEX64 = re.compile(r"[0-9a-f]{64}")
ANNOTATIONS_KEY = "prepared_phase_supply_annotations"
_PLAN_GLOB = "*plan-registered*.json"


class RefreshError(Exception):
    """A plan whose cell or baseline cannot be resolved; refused by name."""


def is_real_sha(value) -> bool:
    return isinstance(value, str) and bool(_HEX64.fullmatch(value)) and set(value) != {"0"}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def resolve_baseline(repo: Path, plan: dict, plan_name: str) -> tuple[str, dict]:
    cell_id = plan.get("cell")
    experiment = plan.get("experiment")
    if not (isinstance(cell_id, str) and isinstance(experiment, str)):
        raise RefreshError(f"{plan_name}: plan declares no string `cell` and `experiment`")
    fragment = repo / "configs" / "experiment" / f"{experiment}.json"
    if not fragment.is_file():
        raise RefreshError(f"{plan_name}: experiment fragment {fragment.name} not found")
    cells = [c for c in _load(fragment).get("cells", []) if isinstance(c, dict) and c.get("cell_id") == cell_id]
    if len(cells) != 1:
        raise RefreshError(f"{plan_name}: cell {cell_id} matches {len(cells)} cells in {fragment.name}")
    base = repo / "configs" / "baseline" / f"{cells[0].get('baseline_fragment')}.json"
    if not base.is_file():
        raise RefreshError(f"{plan_name}: baseline fragment for cell {cell_id} not found")
    return cell_id, _load(base)


def refresh_package(repo: Path, package: Path, cells: list[str] | None = None, dry: bool = False) -> list[dict]:
    results = []
    for path in sorted(package.glob(_PLAN_GLOB)):
        plan = _load(path)
        if not isinstance(plan, dict) or "prepared_phase_supply" not in plan:
            results.append({"file": path.name, "status": "skipped", "detail": "no prepared_phase_supply"})
            continue
        cell_id, baseline = resolve_baseline(repo, plan, path.name)
        if cells and cell_id not in cells:
            results.append({"file": path.name, "cell": cell_id, "status": "skipped", "detail": "cell not selected"})
            continue
        pin = baseline.get("prepared_phase_supply")
        if not (isinstance(pin, dict) and is_real_sha(pin.get("sha256"))):
            results.append({"file": path.name, "cell": cell_id, "status": "unchanged",
                            "detail": "baseline pin is a placeholder or absent"})
            continue
        declared = plan["prepared_phase_supply"]
        if declared == pin:
            results.append({"file": path.name, "cell": cell_id, "status": "unchanged", "detail": "already equal"})
            continue
        annotations = {k: v for k, v in (declared.items() if isinstance(declared, dict) else [])
                       if k not in pin}
        before = declared.get("sha256") if isinstance(declared, dict) else None
        plan["prepared_phase_supply"] = dict(pin)
        if annotations:
            merged = dict(plan.get(ANNOTATIONS_KEY) or {})
            merged.update(annotations)
            plan[ANNOTATIONS_KEY] = merged
        if not dry:
            path.write_text(_dump(plan), encoding="utf-8", newline="\n")
        results.append({"file": path.name, "cell": cell_id, "status": "refreshed",
                        "before": before, "after": pin["sha256"], "annotations_moved": sorted(annotations)})
    return results


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--package", required=True, help="docs/readiness/<package> directory")
    ap.add_argument("--cell", action="append", help="restrict to this cell id (repeatable)")
    ap.add_argument("--dry", action="store_true", help="print only; write nothing")
    ap.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args(argv)
    repo = Path(args.repo_root)
    package = Path(args.package)
    if not package.is_absolute():
        package = repo / package
    if not package.is_dir():
        print(f"refused: package directory {package} not found", file=sys.stderr)
        return 2
    try:
        results = refresh_package(repo, package, args.cell, args.dry)
    except RefreshError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    for r in results:
        line = f"{r['status']:9} {r['file']}"
        if r["status"] == "refreshed":
            line += f"  {r['before']} -> {r['after']}" + (f"  (annotations moved: {', '.join(r['annotations_moved'])})" if r["annotations_moved"] else "")
        elif r.get("detail"):
            line += f"  ({r['detail']})"
        print(line)
    if args.dry:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
