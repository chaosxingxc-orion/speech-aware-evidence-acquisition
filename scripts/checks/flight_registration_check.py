#!/usr/bin/env python3
"""Pre-launch gate: a cell flies only when its registration is complete.

Owner decision 163 (2026-09-27, engineering track): "the flight-row countersignature and READ-row
registration enforced by a gate before launch". Two process defects slipped through the day
before, and this gate exists so neither can recur silently:

* cell ROLL-3's four flight rows flew while ``docs/exposure-ledger.md`` still read
  ``(draft, root countersignature pending)`` -- the decision receipt had been minted before
  contact, but the ledger countersignature had not been written (disclosed in place at
  ``96482ddc``);
* cells AGREE, KPROBE and ROLL-3 had no READ row registered in their packages, so the
  coordinator registered each read row after the seal (``c2623782``, ``d1e2c61a``,
  ``e2822b2b``).

**What a cell must carry before launch.** For every run id the cell spends -- its generation run
id (``cells[].run_id``) and every FIT spend identity its fragments declare
(``native_contact_fit.run_id``, ``live_phase_fit.run_id``, ``prompt_fit.run_id``, read from the
experiment fragment and then from its ``baseline_fragment``):

``missing-row`` / ``duplicate-row``
    exactly one exposure-ledger row, parsed with the repository's own ledger parser
    (``contracts._parse_ledger_tables``, the parser the runtime gate uses);
``row-not-countersigned``
    the row's notes carry ``root countersigned`` -- a row that still reads ``DRAFT`` /
    ``root countersignature pending`` is a draft, and a draft never authorises contact;
``no-decision-receipt`` / ``receipt-missing`` / ``receipt-unreadable`` /
``receipt-not-decided`` / ``receipt-hash-mismatch`` / ``receipt-decision-id-mismatch`` /
``receipt-disagrees-with-readiness`` / ``run-not-eligible``
    the decision receipt the countersigned row names (a ``coordination/...json`` path in its
    notes; the cell's own ``readiness.requirements`` decision pin when the row names none) exists
    under the data root (``$SPEECHRL_DATA_DIR``), reads ``status: decided``, matches the
    readiness pin's sha256 and decision id when the readiness block pins one, and lists the run
    id in ``eligible_run_ids``.

And for the cell's readiness package (the ``docs/readiness/<package>/`` directory the flight row's
artifacts column points at; else the decision receipt's antecedents; else the package whose
``*plan-registered*.json`` names the run id):

``no-package`` / ``no-analysis-recipe`` / ``ambiguous-analysis-recipe``
    the package carries one analysis recipe for this cell (``*analysis-recipe*.json``; when a
    package carries several, the one whose text names the cell's run id);
``no-read-run-id``
    the recipe DECLARES its READ run id -- ``read_run_id`` at top level or ``run_ids.read`` --
    so the read is registered with the flight, not invented after the seal;
``read-row-missing``
    that READ run id has its own exposure-ledger row. It may still be a DRAFT until the seal
    (the read row is countersigned after the seal and before any number is read), but it must
    exist.

**Scope and severity.**

* Whole-tree mode (no ``--cell``): every cell of ``configs/experiment/*.json`` whose
  ``readiness.state`` is ``ready`` (``--include-held`` adds ``held`` cells as a PREVIEW, never
  blocking). A cell whose generation run id is already CONSUMED -- a non-empty
  ``runs/<run id>/`` or ``attempts/<run id>/`` on the data root, a ``prepared/<run id>/attempt*``
  FIT receipt directory, or a ledger row whose ``consumed`` column reads ``yes`` -- is
  HISTORICAL: its findings are reported and never block (this repository never rewrites sealed
  bytes or their registrations). A ready, unflown cell BLOCKS when its registration date (the
  ledger row's ``date``, else the fragment's ``date``) is on or after ``--strict-from``
  (default :data:`STRICT_FROM_DEFAULT`, the day the Stage-3 flight packages -- and both defects
  above -- began); an older ready-but-unflown cell is a STALE-READY advisory: it is reported,
  it does not fail the tree, and it still cannot pass the launch gate below.
* Launch mode (``--cell [EXPERIMENT:]CELL``, repeatable, and ``--campaign-plan PATH``, which
  adds every cell of that plan): every named cell is gated whatever its registration date. A
  named cell that is not ``ready`` is refused (``not-ready``); a named cell whose run id is
  already consumed is reported and passes (a resume step re-enters a consumed run id under the
  one-recovery rule, and the runtime's own gate judges it). This is the mode
  ``scripts/flights/batch/batch_driver.sh`` runs in ``prelaunch`` for every queue step.

Exit 0 when no blocking finding remains (advisory lines are still printed); exit 1 on a
blocking finding; exit 2 when the tree or the data root cannot be read.

Zero model, tokenizer, encoder, scorer, server, GPU and network contacts. It opens nothing for
writing. Flags: ``--repo-root``, ``--data-root``, ``--ledger``, ``--cell``, ``--campaign-plan``,
``--include-held``, ``--strict-from``, ``--json``, ``--verbose``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT_DEFAULT = Path(__file__).resolve().parents[2]

EXPOSURE_LEDGER = Path("docs/exposure-ledger.md")
EXPERIMENT_DIR = Path("configs/experiment")
BASELINE_DIR = Path("configs/baseline")
READINESS = Path("docs/readiness")

#: The Stage-3 flight packages began on 2026-09-26 (the measurement instrument note, the
#: countersign-by-coordinator practice, and both defects this gate exists for).
STRICT_FROM_DEFAULT = dt.date(2026, 9, 26)

RUN_COLUMN = "run/experiment id"
CONSUMED_COLUMN = "consumed"
DATE_COLUMN = "date"
NOTES_COLUMN = "notes"
ARTIFACTS_COLUMN = "artifacts"

COUNTERSIGNED = re.compile(r"\broot\s+countersigned\b", re.IGNORECASE)
PENDING = re.compile(r"countersignature\s+pending", re.IGNORECASE)
RECEIPT_REF = re.compile(r"coordination/[A-Za-z0-9._/\-]+?\.json")
PACKAGE_REF = re.compile(r"docs/readiness/([A-Za-z0-9._\-]+)/")
DATE_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

#: Fragment keys whose ``run_id`` is a FIT spend identity of the cell.
FIT_KEYS = ("native_contact_fit", "live_phase_fit", "prompt_fit")

GATED_STATES = ("ready",)
PREVIEW_STATES = ("held",)


class FlightRegistrationCheckError(RuntimeError):
    """The tree or the data root cannot be read; exit 2."""


@dataclass
class Finding:
    kind: str
    message: str
    run_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "message": self.message, "run_id": self.run_id}


@dataclass
class CellReport:
    experiment: str
    cell_id: str
    run_id: str
    state: str
    named: bool
    consumed_by: str | None = None
    registration_date: str | None = None
    severity: str = "blocking"
    scope_note: str = ""
    run_ids: dict[str, str] = field(default_factory=dict)
    package: str | None = None
    recipe: str | None = None
    read_run_id: str | None = None
    read_row_countersigned: bool | None = None
    receipts: dict[str, str] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "experiment": self.experiment,
            "cell_id": self.cell_id,
            "run_id": self.run_id,
            "state": self.state,
            "named": self.named,
            "consumed_by": self.consumed_by,
            "registration_date": self.registration_date,
            "severity": self.severity,
            "scope_note": self.scope_note,
            "run_ids": dict(self.run_ids),
            "package": self.package,
            "recipe": self.recipe,
            "read_run_id": self.read_run_id,
            "read_row_countersigned": self.read_row_countersigned,
            "receipts": dict(self.receipts),
            "findings": [finding.as_dict() for finding in self.findings],
        }


# --------------------------------------------------------------------------
# reading the tree
# --------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FlightRegistrationCheckError(f"cannot read {label}: {error}") from error


def _sha256(path: Path) -> str:
    measured = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            measured.update(chunk)
    return measured.hexdigest()


def parse_ledger(repo_root: Path, ledger: Path) -> dict[str, list[dict[str, str]]]:
    """``{run id: [rows]}`` with the repository's own exposure-ledger parser."""

    src = repo_root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    try:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            _parse_ledger_tables,
        )
    except Exception as error:  # pragma: no cover - import environment problem
        raise FlightRegistrationCheckError(
            f"cannot import the repository's exposure-ledger parser from {src}: {error}"
        ) from error
    path = repo_root / ledger
    if not path.is_file():
        raise FlightRegistrationCheckError(f"missing {ledger.as_posix()}")
    try:
        parsed = _parse_ledger_tables(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as error:
        raise FlightRegistrationCheckError(f"cannot parse {ledger.as_posix()}: {error}") from error
    rows: dict[str, list[dict[str, str]]] = {}
    for row in parsed:
        run_id = str(row.get(RUN_COLUMN, "")).strip()
        if run_id:
            rows.setdefault(run_id, []).append(dict(row))
    return rows


def row_text(row: dict[str, str]) -> str:
    """The notes cell, where the countersignature and the receipt are written; the whole row when
    the governing table has no notes column."""

    if NOTES_COLUMN in row:
        return str(row[NOTES_COLUMN])
    return " | ".join(str(value) for value in row.values())


def is_countersigned(row: dict[str, str]) -> bool:
    return bool(COUNTERSIGNED.search(row_text(row)))


def row_consumed(row: dict[str, str]) -> bool:
    cell = str(row.get(CONSUMED_COLUMN, "")).replace("*", "").strip().lower()
    return cell.split(";")[0].split("(")[0].strip() == "yes"


def date_in(text: Any) -> dt.date | None:
    match = DATE_PREFIX.search(str(text or ""))
    if match is None:
        return None
    try:
        return dt.date(int(match[1]), int(match[2]), int(match[3]))
    except ValueError:
        return None


def _fragment_value(fragment: dict[str, Any], baseline: dict[str, Any] | None, key: str) -> Any:
    if key in fragment:
        return fragment[key]
    if baseline is not None:
        return baseline.get(key)
    return None


def fit_run_ids(fragment: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in FIT_KEYS:
        block = _fragment_value(fragment, baseline, key)
        if isinstance(block, dict):
            run_id = block.get("run_id")
            if isinstance(run_id, str) and run_id.strip():
                out[key] = run_id.strip()
    return out


def consumption(data_root: Path, run_id: str, rows: list[dict[str, str]]) -> str | None:
    """Why ``run_id`` counts as already flown, or ``None``."""

    for kind in ("runs", "attempts"):
        path = data_root / kind / run_id
        if path.is_dir() and any(path.iterdir()):
            return f"{kind}/{run_id}"
    prepared = data_root / "prepared" / run_id
    if prepared.is_dir() and any(
        child.is_dir() and child.name.startswith("attempt") for child in prepared.iterdir()
    ):
        return f"prepared/{run_id}/attempt*"
    if any(row_consumed(row) for row in rows):
        return "ledger consumed=yes"
    return None


def decision_requirement(cell: dict[str, Any]) -> dict[str, Any] | None:
    readiness = cell.get("readiness")
    if not isinstance(readiness, dict):
        return None
    for requirement in readiness.get("requirements") or ():
        if isinstance(requirement, dict) and requirement.get("kind") == "decision":
            return requirement
    return None


def readiness_state(cell: dict[str, Any]) -> str:
    readiness = cell.get("readiness")
    if isinstance(readiness, dict) and isinstance(readiness.get("state"), str):
        return readiness["state"]
    return "<no readiness block>"


# --------------------------------------------------------------------------
# packages and recipes
# --------------------------------------------------------------------------


class PackageIndex:
    """Lazily reads ``docs/readiness/*/`` once."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self._plan_texts: list[tuple[str, str]] | None = None

    def package_exists(self, name: str) -> bool:
        return (self.repo_root / READINESS / name).is_dir()

    def recipes(self, name: str) -> list[Path]:
        return sorted((self.repo_root / READINESS / name).glob("*analysis-recipe*.json"))

    def packages_registering(self, run_id: str) -> list[str]:
        if self._plan_texts is None:
            texts: list[tuple[str, str]] = []
            root = self.repo_root / READINESS
            for path in sorted(root.glob("*/*plan-registered*.json")):
                try:
                    texts.append((path.parent.name, path.read_text(encoding="utf-8", errors="replace")))
                except OSError:
                    continue
            self._plan_texts = texts
        return sorted({name for name, text in self._plan_texts if f'"{run_id}"' in text})


def read_run_id_of(recipe: dict[str, Any]) -> str | None:
    value = recipe.get("read_run_id")
    if isinstance(value, str) and value.strip():
        return value.strip()
    run_ids = recipe.get("run_ids")
    if isinstance(run_ids, dict):
        for key in ("read", "read_run_id"):
            value = run_ids.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def resolve_package(
    index: PackageIndex,
    rows: Iterable[dict[str, str]],
    receipt: dict[str, Any] | None,
    run_id: str,
) -> tuple[str | None, str]:
    """The cell's readiness package and how it was found."""

    for row in rows:
        for match in PACKAGE_REF.finditer(str(row.get(ARTIFACTS_COLUMN, ""))):
            if index.package_exists(match[1]):
                return match[1], "the flight row's artifacts column"
    if isinstance(receipt, dict):
        antecedents = receipt.get("antecedents") or {}
        for key in ("analysis_recipe", "readiness_readme", "protocol"):
            entry = antecedents.get(key) if isinstance(antecedents, dict) else None
            path = entry.get("path") if isinstance(entry, dict) else None
            match = PACKAGE_REF.search(str(path or ""))
            if match and index.package_exists(match[1]):
                return match[1], f"the decision receipt's antecedents.{key}"
    registering = index.packages_registering(run_id)
    if len(registering) == 1:
        return registering[0], "the package whose registered plan names the run id"
    return None, (
        f"{len(registering)} packages register a plan naming the run id"
        if registering else "no package names the run id"
    )


# --------------------------------------------------------------------------
# the checks
# --------------------------------------------------------------------------


def _check_receipt(
    report: CellReport,
    data_root: Path,
    run_id: str,
    row: dict[str, str],
    requirement: dict[str, Any] | None,
    cache: dict[str, Any],
) -> dict[str, Any] | None:
    named = RECEIPT_REF.findall(row_text(row))
    pinned = requirement.get("relpath") if isinstance(requirement, dict) else None
    admission = [ref for ref in named if "admission" in ref] or named
    relpath = admission[0] if admission else pinned
    if not relpath:
        report.findings.append(Finding(
            "no-decision-receipt",
            f"{run_id}: the ledger row names no coordination/...json decision receipt and the "
            "cell's readiness block pins none",
            run_id,
        ))
        return None
    if pinned and relpath != pinned:
        report.findings.append(Finding(
            "receipt-disagrees-with-readiness",
            f"{run_id}: the countersigned row names {relpath}, the readiness block pins {pinned}",
            run_id,
        ))
    report.receipts[run_id] = relpath
    path = data_root / relpath
    if relpath not in cache:
        if not path.is_file():
            cache[relpath] = None
        else:
            try:
                cache[relpath] = (json.loads(path.read_text(encoding="utf-8")), _sha256(path))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                cache[relpath] = error
    loaded = cache[relpath]
    if loaded is None:
        report.findings.append(Finding(
            "receipt-missing", f"{run_id}: decision receipt {relpath} does not exist on the data root", run_id
        ))
        return None
    if isinstance(loaded, Exception):
        report.findings.append(Finding(
            "receipt-unreadable", f"{run_id}: decision receipt {relpath} is unreadable: {loaded}", run_id
        ))
        return None
    document, sha = loaded
    if not isinstance(document, dict):
        report.findings.append(Finding(
            "receipt-unreadable", f"{run_id}: decision receipt {relpath} is not a JSON object", run_id
        ))
        return None
    if document.get("status") != "decided":
        report.findings.append(Finding(
            "receipt-not-decided",
            f"{run_id}: decision receipt {relpath} has status {document.get('status')!r}, not 'decided'",
            run_id,
        ))
    if isinstance(requirement, dict) and relpath == pinned:
        if requirement.get("sha256") and requirement["sha256"] != sha:
            report.findings.append(Finding(
                "receipt-hash-mismatch",
                f"{run_id}: decision receipt {relpath} hashes to {sha[:12]}..., the readiness pin is "
                f"{str(requirement['sha256'])[:12]}...",
                run_id,
            ))
        expected = requirement.get("expected_decision_id")
        if expected and document.get("decision_id") != expected:
            report.findings.append(Finding(
                "receipt-decision-id-mismatch",
                f"{run_id}: decision receipt {relpath} carries decision id "
                f"{document.get('decision_id')!r}, the readiness pin expects {expected!r}",
                run_id,
            ))
    eligible = document.get("eligible_run_ids")
    if not isinstance(eligible, list) or run_id not in eligible:
        report.findings.append(Finding(
            "run-not-eligible",
            f"{run_id}: not in eligible_run_ids of decision receipt {relpath}",
            run_id,
        ))
    return document


def check_cell(
    report: CellReport,
    cell: dict[str, Any],
    fragment: dict[str, Any],
    baseline: dict[str, Any] | None,
    ledger: dict[str, list[dict[str, str]]],
    data_root: Path,
    index: PackageIndex,
    receipt_cache: dict[str, Any],
) -> None:
    run_ids = {"generation": report.run_id, **fit_run_ids(fragment, baseline)}
    report.run_ids = run_ids
    requirement = decision_requirement(cell)
    first_receipt: dict[str, Any] | None = None
    for role, run_id in run_ids.items():
        rows = ledger.get(run_id, [])
        if not rows:
            report.findings.append(Finding(
                "missing-row", f"{run_id} ({role}): no exposure-ledger row", run_id
            ))
            continue
        if len(rows) > 1:
            report.findings.append(Finding(
                "duplicate-row", f"{run_id} ({role}): {len(rows)} exposure-ledger rows", run_id
            ))
        signed = [row for row in rows if is_countersigned(row)]
        if not signed:
            state = "a DRAFT (root countersignature pending)" if any(
                PENDING.search(row_text(row)) for row in rows
            ) else "not countersigned"
            report.findings.append(Finding(
                "row-not-countersigned",
                f"{run_id} ({role}): the exposure-ledger row is {state}; a draft never authorises "
                "contact",
                run_id,
            ))
        document = _check_receipt(
            report, data_root, run_id, (signed or rows)[0], requirement, receipt_cache
        )
        if first_receipt is None and document is not None:
            first_receipt = document

    generation_rows = ledger.get(report.run_id, [])
    package, how = resolve_package(index, generation_rows, first_receipt, report.run_id)
    if package is None:
        report.findings.append(Finding(
            "no-package", f"{report.run_id}: no readiness package resolved ({how})", report.run_id
        ))
        return
    report.package = f"{READINESS.as_posix()}/{package}"
    recipes = index.recipes(package)
    if not recipes:
        report.findings.append(Finding(
            "no-analysis-recipe",
            f"{report.package} (found via {how}) carries no *analysis-recipe*.json",
            report.run_id,
        ))
        return
    if len(recipes) > 1:
        naming = [path for path in recipes if report.run_id in path.read_text(encoding="utf-8", errors="replace")]
        if len(naming) != 1:
            report.findings.append(Finding(
                "ambiguous-analysis-recipe",
                f"{report.package} carries {len(recipes)} analysis recipes and {len(naming)} name "
                f"{report.run_id}",
                report.run_id,
            ))
            return
        recipe_path = naming[0]
    else:
        recipe_path = recipes[0]
    report.recipe = recipe_path.relative_to(index.repo_root).as_posix()
    try:
        recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        report.findings.append(Finding(
            "no-analysis-recipe", f"{report.recipe} is unreadable: {error}", report.run_id
        ))
        return
    read_run_id = read_run_id_of(recipe) if isinstance(recipe, dict) else None
    if read_run_id is None:
        report.findings.append(Finding(
            "no-read-run-id",
            f"{report.recipe} declares no READ run id (read_run_id or run_ids.read): the read must "
            "be registered with the flight, never after the seal",
            report.run_id,
        ))
        return
    report.read_run_id = read_run_id
    read_rows = ledger.get(read_run_id, [])
    if not read_rows:
        report.findings.append(Finding(
            "read-row-missing",
            f"READ run id {read_run_id} (declared by {report.recipe}) has no exposure-ledger row; "
            "it may stay a draft until the seal, but it must exist before launch",
            read_run_id,
        ))
        return
    report.read_row_countersigned = any(is_countersigned(row) for row in read_rows)


# --------------------------------------------------------------------------
# scope
# --------------------------------------------------------------------------


@dataclass
class FragmentEntry:
    experiment: str
    fragment: dict[str, Any]
    baseline: dict[str, Any] | None


def load_fragments(repo_root: Path) -> dict[str, FragmentEntry]:
    out: dict[str, FragmentEntry] = {}
    baselines: dict[str, dict[str, Any] | None] = {}
    for path in sorted((repo_root / EXPERIMENT_DIR).glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
            continue
        baseline: dict[str, Any] | None = None
        names = {
            cell.get("baseline_fragment") for cell in document["cells"]
            if isinstance(cell, dict) and isinstance(cell.get("baseline_fragment"), str)
        }
        if len(names) == 1:
            name = names.pop()
            if name not in baselines:
                baseline_path = repo_root / BASELINE_DIR / f"{name}.json"
                try:
                    loaded = json.loads(baseline_path.read_text(encoding="utf-8"))
                    baselines[name] = loaded if isinstance(loaded, dict) else None
                except (OSError, UnicodeError, json.JSONDecodeError):
                    baselines[name] = None
            baseline = baselines[name]
        out[path.stem] = FragmentEntry(path.stem, document, baseline)
    return out


def named_cells(
    fragments: dict[str, FragmentEntry], cells: list[str], plans: list[Path]
) -> list[tuple[str, str]]:
    """``[(experiment, cell id)]`` for ``--cell`` and ``--campaign-plan``."""

    wanted: list[tuple[str | None, str]] = []
    for spec in cells:
        experiment, _, cell_id = spec.rpartition(":")
        wanted.append((experiment or None, cell_id))
    for plan_path in plans:
        plan = _read_json(plan_path, f"campaign plan {plan_path}")
        for entry in plan.get("cells") or () if isinstance(plan, dict) else ():
            if isinstance(entry, dict):
                wanted.append((entry.get("experiment"), str(entry.get("cell"))))
    resolved: list[tuple[str, str]] = []
    for experiment, cell_id in wanted:
        if experiment:
            if experiment not in fragments:
                raise FlightRegistrationCheckError(
                    f"experiment fragment {EXPERIMENT_DIR.as_posix()}/{experiment}.json not found"
                )
            candidates = [experiment]
        else:
            candidates = [
                name for name, entry in fragments.items()
                if any(isinstance(c, dict) and c.get("cell_id") == cell_id for c in entry.fragment["cells"])
            ]
            if len(candidates) != 1:
                raise FlightRegistrationCheckError(
                    f"cell {cell_id!r} resolves to {len(candidates)} experiment fragments; pass "
                    "--cell EXPERIMENT:CELL"
                )
        pair = (candidates[0], cell_id)
        if pair not in resolved:
            resolved.append(pair)
    return resolved


def evaluate(
    repo_root: Path,
    data_root: Path,
    ledger_path: Path,
    *,
    cells: list[str] | None = None,
    plans: list[Path] | None = None,
    include_held: bool = False,
    strict_from: dt.date = STRICT_FROM_DEFAULT,
) -> dict[str, Any]:
    if not data_root.is_dir():
        raise FlightRegistrationCheckError(
            f"data root {data_root} is not a directory (decision receipts and run directories live there)"
        )
    ledger = parse_ledger(repo_root, ledger_path)
    fragments = load_fragments(repo_root)
    index = PackageIndex(repo_root)
    receipt_cache: dict[str, Any] = {}
    launch_mode = bool(cells or plans)

    targets: list[tuple[str, dict[str, Any], bool]] = []
    if launch_mode:
        for experiment, cell_id in named_cells(fragments, list(cells or ()), list(plans or ())):
            entry = fragments[experiment]
            match = [c for c in entry.fragment["cells"] if isinstance(c, dict) and c.get("cell_id") == cell_id]
            if len(match) != 1:
                raise FlightRegistrationCheckError(
                    f"cell {cell_id!r} appears {len(match)} times in {experiment}.json"
                )
            targets.append((experiment, match[0], True))
    else:
        for experiment, entry in fragments.items():
            for cell in entry.fragment["cells"]:
                if not isinstance(cell, dict):
                    continue
                state = readiness_state(cell)
                if state in GATED_STATES or (include_held and state in PREVIEW_STATES):
                    targets.append((experiment, cell, False))

    reports: list[CellReport] = []
    for experiment, cell, named in targets:
        entry = fragments[experiment]
        run_id = str(cell.get("run_id") or "").strip()
        report = CellReport(
            experiment=experiment,
            cell_id=str(cell.get("cell_id")),
            run_id=run_id,
            state=readiness_state(cell),
            named=named,
        )
        reports.append(report)
        if not run_id:
            report.findings.append(Finding("missing-row", "the cell declares no run_id"))
            continue
        rows = ledger.get(run_id, [])
        registered = next((date_in(row.get(DATE_COLUMN)) for row in rows if date_in(row.get(DATE_COLUMN))), None)
        registered = registered or date_in(entry.fragment.get("date"))
        report.registration_date = registered.isoformat() if registered else None
        report.consumed_by = consumption(data_root, run_id, rows)
        check_cell(report, cell, entry.fragment, entry.baseline, ledger, data_root, index, receipt_cache)

        if report.consumed_by is not None:
            report.severity = "advisory"
            report.scope_note = f"historical: already flown ({report.consumed_by}); reported only"
        elif named:
            if report.state not in GATED_STATES:
                report.findings.insert(0, Finding(
                    "not-ready", f"readiness.state is {report.state!r}, not 'ready'", run_id
                ))
            report.severity = "blocking"
            report.scope_note = "launch gate: named cell, ready and unflown"
        elif report.state in PREVIEW_STATES:
            report.severity = "advisory"
            report.scope_note = "preview: held, unflown (what the gate would say at the flip)"
        elif registered is not None and registered >= strict_from:
            report.severity = "blocking"
            report.scope_note = "ready and unflown"
        else:
            report.severity = "advisory"
            report.scope_note = (
                f"stale-ready: ready and unflown, registered {report.registration_date or 'on an unknown date'} "
                f"before {strict_from.isoformat()}; reported only here, refused at launch"
            )

    blocking = [r for r in reports if r.severity == "blocking" and r.findings]
    advisory = [r for r in reports if r.severity == "advisory" and r.findings]
    return {
        "schema": "saea-flight-registration-check-v1",
        "mode": "launch" if launch_mode else "tree",
        "strict_from": strict_from.isoformat(),
        "data_root": str(data_root),
        "cells": [r.as_dict() for r in reports],
        "blocking_cells": [r.cell_id for r in blocking],
        "advisory_cells": [r.cell_id for r in advisory],
        "passed": not blocking,
        "contacts": {"model": 0, "tokenizer": 0, "encoder": 0, "scorer": 0, "server": 0, "network": 0},
    }


def render(data: dict[str, Any], *, verbose: bool = False) -> list[str]:
    """Blocking cells in full; advisory cells one line each (every finding with ``--verbose``)."""

    lines: list[str] = []
    for cell in data["cells"]:
        if not cell["findings"]:
            continue
        blocking = cell["severity"] == "blocking"
        label = "FAIL" if blocking else "advisory"
        head = f"flight registration check: {label}: {cell['experiment']}:{cell['cell_id']} ({cell['scope_note']})"
        if blocking or verbose:
            lines.append(head)
            for finding in cell["findings"]:
                lines.append(f"    [{finding['kind']}] {finding['message']}")
        else:
            kinds = sorted({finding["kind"] for finding in cell["findings"]})
            lines.append(f"{head}: {', '.join(kinds)}")
    ok = [c for c in data["cells"] if not c["findings"]]
    for cell in ok:
        if cell["named"]:
            note = "" if cell["read_row_countersigned"] is None else (
                f"; READ row {cell['read_run_id']} "
                + ("countersigned" if cell["read_row_countersigned"] else "registered (draft until the seal)")
            )
            lines.append(
                f"flight registration check: ok: {cell['experiment']}:{cell['cell_id']} "
                f"({cell['scope_note']}){note}"
            )
    blocking = len(data["blocking_cells"])
    summary = (
        f"{len(data['cells'])} cell(s) in scope ({data['mode']} mode), {len(ok)} clean, "
        f"{blocking} blocking, {len(data['advisory_cells'])} advisory; blocking from "
        f"{data['strict_from']} in tree mode"
    )
    lines.append(
        f"flight registration check: {'PASS' if data['passed'] else 'FAIL'} ({summary})"
    )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT_DEFAULT)
    parser.add_argument("--data-root", type=Path, default=None,
                        help="default: $SPEECHRL_DATA_DIR")
    parser.add_argument("--ledger", type=Path, default=EXPOSURE_LEDGER)
    parser.add_argument("--cell", action="append", default=[], metavar="[EXPERIMENT:]CELL",
                        help="gate one named cell (repeatable); launch mode")
    parser.add_argument("--campaign-plan", action="append", default=[], type=Path,
                        help="gate every cell of a campaign plan (repeatable); launch mode")
    parser.add_argument("--include-held", action="store_true",
                        help="tree mode: preview held cells as well (never blocking)")
    parser.add_argument("--strict-from", default=STRICT_FROM_DEFAULT.isoformat(), metavar="YYYY-MM-DD")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true",
                        help="print every finding of advisory cells too")
    args = parser.parse_args(argv)

    strict_from = date_in(args.strict_from)
    if strict_from is None:
        print(f"flight registration check: ERROR: --strict-from {args.strict_from!r} is not a date",
              file=sys.stderr)
        return 2
    data_root = args.data_root
    if data_root is None:
        raw = os.environ.get("SPEECHRL_DATA_DIR", "").strip()
        if not raw:
            print("flight registration check: ERROR: no --data-root and SPEECHRL_DATA_DIR is unset",
                  file=sys.stderr)
            return 2
        data_root = Path(raw)
    try:
        data = evaluate(
            args.repo_root.resolve(), data_root, args.ledger,
            cells=args.cell, plans=args.campaign_plan,
            include_held=args.include_held, strict_from=strict_from,
        )
    except FlightRegistrationCheckError as error:
        print(f"flight registration check: ERROR: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for line in render(data, verbose=args.verbose):
            print(line)
    return 0 if data["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
