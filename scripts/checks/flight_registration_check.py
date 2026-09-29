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

#: owner decision 172, docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-
#: design.md section 4: the two designs whose cells must run their supply_variants arms fanned
#: out at the FIRST Solver visit only (section 2, gate finding ``arm-visits-not-first``). The
#: ``stage3_measurement`` key itself is read via ``stage3_effect_floor_check.MEASUREMENT_KEY``
#: (imported lazily, see ``_floor_gate_module``) so the two gates never drift on its spelling.
SUPPLY_VARIANT_INSTRUMENT_DESIGNS = ("same-flight-supply-variant", "offline-sealed-pool")

#: ``supply_variants.arm_visits`` default the parser keeps for byte-identical old forms
#: (``rails/supply_variants.py``, merge set B); an instrument cell must override it to "first".
SUPPLY_VARIANT_ARM_VISITS_DEFAULT = "every"
SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT = "first"

#: The path a ``supply_variants`` block is composed under in a baseline fragment (see
#: ``configs/baseline/*var2-supply-variants*.json``).
SUPPLY_VARIANT_PATH = ("native_episode", "roles", "solver", "supply_variants")

#: Registration fields a ``same-flight-supply-variant`` / ``offline-sealed-pool`` cell must carry
#: BESIDE ``measurement_design`` in the same ``stage3_measurement`` block (Q2 ruling): roster
#: receipt paths, the twin arm id, the declared cost, and the claim ceiling. Only ``variant_cost``
#: and ``claim`` are enforced by merge set A's gate findings; ``tuning_roster``, ``read_roster``
#: and ``aa_arm_id`` are parsed and reported here (the deeper cross-checks -- read-roster-mismatch,
#: roster-knowledge-overlap, aa-arm-missing -- need the snapshot's own contents beyond the roster
#: receipts and are not part of merge set A).
SUPPLY_VARIANT_CLAIM_CEILING = "nominated"

# --------------------------------------------------------------------------
# tuning/read roster split registration (item D3, docs/results/2026-09-27-verdict-
# reclassification.md: the AGREE agreement term was tuned on TRAIN Fold A gold and read on TRAIN
# Fold A -- a circular read; docs/readiness/2026-09-27-slurp-stage3-replan-v2.md section 3, row
# "Circular reads": "make the tuning roster and the read roster registered fields checked by the
# pre-launch gate"). Unlike the supply-variant fields above, these two apply to EVERY Stage-3 cell
# that declares a ``stage3_measurement`` block, whatever its ``measurement_design``.
# --------------------------------------------------------------------------

#: The literal ``tuning_roster`` value a cell writes when no weight, threshold, cap, template or
#: knowledge selection was tuned on any roster at all (nothing to check for overlap).
NO_TUNING_ROSTER = "none"

#: Where a roster's own disjointness receipt lives, keyed by its roster id (case-insensitive
#: filename match against ``roster_id`` inside the file when the slug itself does not resolve).
ROSTER_RECEIPTS_DIR = Path("docs/receipts/rosters")

_NORMALIZE_KEY = re.compile(r"[^a-z0-9]+")
_SHARED_WITH_KEY = re.compile(r"^sharedwith(.+?)(recordings|utterances)$")


class FlightRegistrationCheckError(RuntimeError):
    """The tree or the data root cannot be read; exit 2."""


@dataclass
class Finding:
    kind: str
    message: str
    run_id: str | None = None
    #: ``None`` (the default) inherits the cell's own :attr:`CellReport.severity` -- every finding
    #: kind before item D3 works this way. An explicit ``"advisory"`` here means the finding is
    #: reported but never blocks a launch on its own, even on an otherwise-blocking (ready,
    #: unflown) cell: ``tuning-roster-missing`` and ``tuning-roster-unverified`` are the two kinds
    #: that set it, because an unregistered or unverifiable roster split is a gap in provenance,
    #: not proof of a circular read.
    severity: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "message": self.message,
            "run_id": self.run_id,
            "severity": self.severity,
        }


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
    #: Set only for a cell whose ``stage3_measurement.measurement_design`` is one of
    #: :data:`SUPPLY_VARIANT_INSTRUMENT_DESIGNS` -- owner decision 172, section 4.
    supply_variant: dict[str, Any] | None = None
    #: Set only for a cell whose ``stage3_measurement.measurement_design`` is
    #: ``same-flight-perception-variant`` -- same-flight instrument, PHASE 2 (merge set C,
    #: design docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-
    #: variants-design.md section 4).
    perception_branch: dict[str, Any] | None = None
    #: Set for EVERY cell that declares a ``stage3_measurement`` block, whatever its design --
    #: item D3: ``{"tuning_roster": ..., "read_roster": ...}``, the raw values as registered.
    roster_split: dict[str, Any] | None = None

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
            "supply_variant": self.supply_variant,
            "perception_branch": self.perception_branch,
            "roster_split": self.roster_split,
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


# --------------------------------------------------------------------------
# supply-variant instrument registration (owner decision 172, docs/superpowers/specs/
# 2026-09-27-same-flight-supply-variant-instrument-design.md section 4, merge set A)
# --------------------------------------------------------------------------


def _floor_gate_module(repo_root: Path):
    """The effect-floor gate's declaration-file scanner, imported once.

    Both gates read the SAME ``stage3_measurement`` block in the SAME precedence
    (``docs/readiness/<package>/registered-facts-v*.json``, a ``*preregistration*.md`` fenced
    JSON block, then the experiment fragment's own top level); this gate reuses that scanner
    rather than re-implementing it, at the cost of reaching into two of its private helpers
    (``_declaration_files``, ``_block_for``) -- intentional, documented coupling to one sibling
    file in ``scripts/checks/``, the same pattern ``stage3_effect_floor_check.py`` itself uses to
    reuse ``stage3_algorithm_label_check.is_stage3_fragment``.
    """

    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    try:
        import stage3_effect_floor_check as floor_gate  # noqa: PLC0415
    except Exception as error:  # pragma: no cover - import environment problem
        raise FlightRegistrationCheckError(
            f"cannot import stage3_effect_floor_check from {here}: {error}"
        ) from error
    return floor_gate


def _measurement_block(
    floor_gate: Any, repo_root: Path, run_id: str, cell_id: str, fragment: dict[str, Any]
) -> Any:
    """The cell's raw ``stage3_measurement`` object, unparsed, or ``None``.

    Unlike ``floor_gate._find_declaration`` this returns the raw block rather than a
    ``Declaration``, because merge set A's registration fields (``variant_cost``, ``claim``,
    ``tuning_roster``, ``read_roster``, ``aa_arm_id``) live beside ``measurement_design`` in the
    same object and the floor gate's ``Declaration`` dataclass does not carry them.
    """

    for entry in floor_gate._declaration_files(repo_root):
        names_it = bool(run_id and run_id in entry.text) or bool(cell_id and cell_id in entry.text)
        if not names_it or entry.parse_error is not None:
            continue
        block = floor_gate._block_for(entry.blocks, run_id, cell_id)
        if block is not None:
            return block
    if floor_gate.MEASUREMENT_KEY in fragment:
        block = floor_gate._block_for(fragment[floor_gate.MEASUREMENT_KEY], run_id, cell_id)
        if block is not None:
            return block
    return None


def _supply_variants_block(baseline: dict[str, Any] | None) -> Any:
    """The cell's ``native_episode.roles.solver.supply_variants`` block, or ``None``."""

    node: Any = baseline
    for key in SUPPLY_VARIANT_PATH:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _check_supply_variant_registration(
    report: CellReport,
    fragment: dict[str, Any],
    baseline: dict[str, Any] | None,
    floor_gate: Any,
    repo_root: Path,
) -> None:
    """Section 4 registration fields and gate findings for a supply-variant instrument cell.

    A no-op when the declaration is absent or unreadable, when it names a design outside
    :data:`SUPPLY_VARIANT_INSTRUMENT_DESIGNS`, or when the cell declares no ``supply_variants``
    block at all. The second guard matters because ``offline-sealed-pool`` is NOT exclusive to
    this instrument: it is also the pre-existing, general design for an offline read over a
    sealed sample pool with no supply variation whatsoever (the real ROLL-1/ROLL-2/ROLL-3 and
    filler-chunk cells all declare it with no ``supply_variants`` anywhere in their baseline). A
    cross-flight cell may likewise still declare ``supply_variants`` in the closed VAR-2 shape
    (``configs/baseline/*var2-supply-variants*.json``); this gate must not invent a new
    requirement for either case.
    """

    block = _measurement_block(floor_gate, repo_root, report.run_id, report.cell_id, fragment)
    if not isinstance(block, dict):
        return
    design = block.get("measurement_design")
    if design not in SUPPLY_VARIANT_INSTRUMENT_DESIGNS:
        return
    supply_variants = _supply_variants_block(baseline)
    if not isinstance(supply_variants, dict):
        return

    arms = supply_variants.get("arms")
    arm_count = len(arms) if isinstance(arms, list) else None
    arm_visits = supply_variants.get("arm_visits", SUPPLY_VARIANT_ARM_VISITS_DEFAULT)

    report.supply_variant = {
        "measurement_design": design,
        "arm_visits": arm_visits,
        "arms": arm_count,
        "variant_cost": block.get("variant_cost"),
        "claim": block.get("claim"),
        "tuning_roster": block.get("tuning_roster"),
        "read_roster": block.get("read_roster"),
        "aa_arm_id": block.get("aa_arm_id"),
    }

    if arm_visits != SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT:
        where = (
            "supply_variants.arm_visits"
            if "arm_visits" in supply_variants
            else "supply_variants.arm_visits (absent, so the parser default 'every' applies)"
        )
        report.findings.append(Finding(
            "arm-visits-not-first",
            f"{report.run_id}: measurement_design {design!r} is a same-flight instrument design "
            f"(section 2 of the svinst design) but {where} is {arm_visits!r}, not 'first' -- "
            "under 'every' the VAR-2 failure recurs: arms fan out on every revision visit while "
            "max_supplied_items bounds only one",
            report.run_id,
        ))

    cost = block.get("variant_cost")
    expected_extra = arm_count - 1 if isinstance(arm_count, int) and arm_count >= 1 else None
    if not isinstance(cost, dict):
        report.findings.append(Finding(
            "variant-cost-mismatch",
            f"{report.run_id}: measurement_design {design!r} declares no variant_cost block; the "
            "package must declare variant_cost.extra_contacts_per_row and "
            "variant_cost.extra_audio_seconds, and the gate checks both against the arm list",
            report.run_id,
        ))
    else:
        extra_contacts = cost.get("extra_contacts_per_row")
        if expected_extra is not None and (
            isinstance(extra_contacts, bool)
            or not isinstance(extra_contacts, int)
            or extra_contacts != expected_extra
        ):
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_contacts_per_row is {extra_contacts!r}, but "
                f"the arm list ({arm_count} arms, twin included) makes it {expected_extra} "
                "(K - 1, K counting the twin)",
                report.run_id,
            ))
        extra_audio = cost.get("extra_audio_seconds")
        if (
            isinstance(extra_audio, bool)
            or not isinstance(extra_audio, (int, float))
            or extra_audio < 0
        ):
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_audio_seconds is {extra_audio!r}; it must be "
                "a non-negative number ((K - 1) * row audio, since every arm re-sends the speech "
                "packet at the first visit)",
                report.run_id,
            ))
        elif expected_extra == 0 and extra_audio != 0:
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_audio_seconds is {extra_audio!r} but the arm "
                "list carries no arm beyond the delivering one (extra_contacts_per_row 0)",
                report.run_id,
            ))
        elif expected_extra is not None and expected_extra > 0 and extra_audio == 0:
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_audio_seconds is 0 but "
                f"extra_contacts_per_row is {expected_extra}; every extra arm re-sends the row's "
                "speech packet, so the audio cost cannot be zero",
                report.run_id,
            ))

    claim = block.get("claim")
    if claim != SUPPLY_VARIANT_CLAIM_CEILING:
        report.findings.append(Finding(
            "variant-claim-not-nominated",
            f"{report.run_id}: measurement_design {design!r} may claim only "
            f"{SUPPLY_VARIANT_CLAIM_CEILING!r} (Q6 ruling: a Solver-local effect never supports a "
            f"system-level claim), but claim is {claim!r}",
            report.run_id,
        ))


# --------------------------------------------------------------------------
# tuning/read roster split registration (item D3; every Stage-3 cell, every design)

# --------------------------------------------------------------------------
# Perception-branch instrument registration (same-flight instrument, PHASE 2, merge set C,
# docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md
# section 4, "Registration")
# --------------------------------------------------------------------------

#: The one design whose cells declare a ``roles.perception.branches`` group. Phase 2 registers no
#: ``offline-sealed-pool``-style rollout use (design section 5's inner-loop use is a phase-1-only
#: concept); a phase-2 cell always names this one design.
PERCEPTION_VARIANT_INSTRUMENT_DESIGNS = ("same-flight-perception-variant",)

#: The path a Perception ``branches`` block is composed under in a baseline fragment (see
#: ``rails.native_episode_config``'s ``roles.perception.branches``).
PERCEPTION_BRANCH_PATH = ("native_episode", "roles", "perception", "branches")

#: Design section 8 (O1 ruling): never "admitted", whatever the level -- a level-1 result
#: nominates only into level 2; only a level-2 result nominates the full-system read.
PERCEPTION_BRANCH_CLAIM_CEILING = "nominated"


def _perception_branches_block(baseline: dict[str, Any] | None) -> Any:
    """The cell's ``native_episode.roles.perception.branches`` block, or ``None``."""

    node: Any = baseline
    for key in PERCEPTION_BRANCH_PATH:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _check_perception_branch_registration(
    report: CellReport,
    fragment: dict[str, Any],
    baseline: dict[str, Any] | None,
    floor_gate: Any,
    repo_root: Path,
) -> None:
    """Design section 4 registration fields and gate findings for a Perception-branch cell.

    A no-op when the declaration is absent or unreadable, when it names a design outside
    :data:`PERCEPTION_VARIANT_INSTRUMENT_DESIGNS`, or when the cell declares no
    ``roles.perception.branches`` block at all -- the same three-guard shape
    :func:`_check_supply_variant_registration` uses, for the same reason.

    Four findings: ``branch-level-missing``, ``aa-arm-missing`` (reused from phase 1: the
    required twin, T, is absent or its id disagrees with the registered ``aa_arm_id``),
    ``variant-claim-not-nominated`` (reused from phase 1 verbatim), and ``branch-seed-unpinned``
    (design section 4/5): every non-A, non-T (B) branch must declare a well-formed
    ``prepared_seed {relpath, sha256}`` (``rails.supply_variants.PerceptionBranch.prepared_seed``)
    before this cell may register -- read straight off the raw config a B branch's own
    ``prepared_seed`` key carries, which is as far as a static-config gate can check without the
    runtime's own prepared-artifact identity computation
    (``core.flight.runtime.FlightRuntime._perception_branch_seeds``); it does not re-verify that
    the pinned bytes actually reproduce that identity.
    """

    block = _measurement_block(floor_gate, repo_root, report.run_id, report.cell_id, fragment)
    if not isinstance(block, dict):
        return
    design = block.get("measurement_design")
    if design not in PERCEPTION_VARIANT_INSTRUMENT_DESIGNS:
        return
    branches_block = _perception_branches_block(baseline)
    if not isinstance(branches_block, dict):
        return

    branches = branches_block.get("branches")
    branch_count = len(branches) if isinstance(branches, list) else None
    declared_level = branches_block.get("level")

    report.perception_branch = {
        "measurement_design": design,
        "level": declared_level,
        "branches": branch_count,
        "variant_cost": block.get("variant_cost"),
        "claim": block.get("claim"),
        "tuning_roster": block.get("tuning_roster"),
        "read_roster": block.get("read_roster"),
        "aa_arm_id": block.get("aa_arm_id"),
    }

    if declared_level not in (1, 2):
        report.findings.append(Finding(
            "branch-level-missing",
            f"{report.run_id}: measurement_design {design!r} is the phase-2 Perception-branch "
            "instrument design (design section 3, 'Two levels'), but "
            f"roles.perception.branches.level is {declared_level!r}, not 1 or 2",
            report.run_id,
        ))

    twin_id = None
    if isinstance(branches, list):
        for row in branches:
            if isinstance(row, dict) and row.get("replicate_of") is not None:
                twin_id = row.get("branch_id")
                break
    aa_arm_id = block.get("aa_arm_id")
    if twin_id is None:
        report.findings.append(Finding(
            "aa-arm-missing",
            f"{report.run_id}: measurement_design {design!r} declares no twin (T) branch -- no "
            "branch row names replicate_of -- but design section 4 ('A/A = twin') requires "
            "exactly one on every same-flight-perception-variant read",
            report.run_id,
        ))
    elif aa_arm_id != twin_id:
        report.findings.append(Finding(
            "aa-arm-missing",
            f"{report.run_id}: stage3_measurement.aa_arm_id is {aa_arm_id!r}, but the branch "
            f"group's own twin (the branch naming replicate_of) is {twin_id!r}",
            report.run_id,
        ))

    claim = block.get("claim")
    if claim != PERCEPTION_BRANCH_CLAIM_CEILING:
        report.findings.append(Finding(
            "variant-claim-not-nominated",
            f"{report.run_id}: measurement_design {design!r} may claim only "
            f"{PERCEPTION_BRANCH_CLAIM_CEILING!r} (design section 8, O1 ruling: a level-1 result "
            "nominates only into level 2; only a level-2 result nominates the full-system read), "
            f"but claim is {claim!r}",
            report.run_id,
        ))

    if isinstance(branches, list):
        for row in branches:
            if (
                not isinstance(row, dict)
                or row.get("deliver") is True
                or row.get("replicate_of") is not None
            ):
                continue
            seed = row.get("prepared_seed")
            if (
                not isinstance(seed, dict)
                or set(seed) != {"relpath", "sha256"}
                or not isinstance(seed.get("relpath"), str) or not seed["relpath"]
                or not isinstance(seed.get("sha256"), str) or len(seed["sha256"]) != 64
                or any(
                    character not in "0123456789abcdef" for character in seed["sha256"]
                )
            ):
                report.findings.append(Finding(
                    "branch-seed-unpinned",
                    f"{report.run_id}: perception branch {row.get('branch_id')!r} (a B branch) "
                    "declares no well-formed pinned prepared_seed {relpath, sha256} -- design "
                    "section 5 requires every non-A, non-T branch's pre-flight seed to be pinned "
                    "as its own prepared artifact before this cell may register",
                    report.run_id,
                ))


# --------------------------------------------------------------------------
# tuning/read roster split registration (item D3; every Stage-3 cell, every design)
# --------------------------------------------------------------------------


def _roster_ids(value: Any) -> list[str]:
    """A ``tuning_roster`` / ``read_roster`` value as a list of roster id strings.

    The field may be one id, a list of ids (a cell tuned on several sealed pools), or absent.
    Anything else (a number, a bare object) is not a roster id and yields an empty list -- the
    overlap check below then has nothing to compare and is a no-op, which is correct: a malformed
    value is a different defect than an unregistered or overlapping one.
    """

    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _is_no_tuning(value: Any) -> bool:
    ids = _roster_ids(value)
    return len(ids) == 1 and ids[0].strip().lower() == NO_TUNING_ROSTER


def _normalize_roster_key(value: str) -> str:
    return _NORMALIZE_KEY.sub("", value.lower())


#: ``str(repo_root) -> {lookup key -> receipt document}``, built once per run by
#: :func:`_roster_receipt_index` and reused by every :func:`_load_roster_receipt` call. Every real
#: receipt file under ``ROSTER_RECEIPTS_DIR`` is read and parsed at most once per process, however
#: many cells or directions query it (2026-09-28 fix: a cell's tuning/read overlap check used to
#: reopen the same files on every call, and doubling the callers per cell -- item D3 -- made the
#: previously-latent cost visible as a full-minutes regression).
_ROSTER_RECEIPT_INDEX_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def _roster_receipt_index(repo_root: Path) -> dict[str, dict[str, Any]]:
    """Every roster receipt under ``ROSTER_RECEIPTS_DIR``, read once, keyed for lookup.

    Two keys point at the same document: its own filename slug (the convention every real receipt
    follows) and its internal ``roster_id`` field, lowercased -- the two disagree in case for
    several real receipts (``SLURP-DEV-2000-V1`` in ``slurp-dev-2000-v1.json``). Filename-slug keys
    are populated first and never overwritten, so a slug that matches one file's name always
    resolves to THAT file even if some other file's ``roster_id`` field also happens to match it --
    bit-for-bit the old function's "try the exact filename first" precedence. Among files whose own
    ``roster_id`` field ties on the fallback key, the first in sorted (filename) order wins, same as
    the old function's fallback scan.
    """

    key = str(repo_root)
    cached = _ROSTER_RECEIPT_INDEX_CACHE.get(key)
    if cached is not None:
        return cached
    directory = repo_root / ROSTER_RECEIPTS_DIR
    by_filename: dict[str, dict[str, Any]] = {}
    if directory.is_dir():
        for path in sorted(directory.glob("*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if isinstance(document, dict):
                by_filename[path.stem.strip().lower()] = document
    index: dict[str, dict[str, Any]] = dict(by_filename)
    for document in by_filename.values():
        roster_id_field = str(document.get("roster_id", "")).strip().lower()
        if roster_id_field:
            index.setdefault(roster_id_field, document)
    _ROSTER_RECEIPT_INDEX_CACHE[key] = index
    return index


def _load_roster_receipt(repo_root: Path, roster_id: str) -> dict[str, Any] | None:
    """The roster receipt naming ``roster_id``, or ``None`` when none can be found.

    Looks up the exact-slug filename first (``docs/receipts/rosters/<roster_id lowercased>.json``,
    the convention every real receipt in that directory follows), then falls back to the receipt
    whose own ``roster_id`` field matches (case-insensitive) -- see :func:`_roster_receipt_index`.
    Every receipt file is read from disk at most once per run, however many roster ids are looked
    up.
    """

    slug = roster_id.strip().lower()
    if not slug:
        return None
    return _roster_receipt_index(repo_root).get(slug)


def _extract_shared_count(value: Any) -> int | None:
    """The overlap count out of one ``disjointness_proof`` entry, or ``None`` when it carries none.

    An entry is either a bare number (the legacy ``shared_with_<slug>_recordings`` flat form) or an
    object carrying ``shared_recordings`` / ``shared_utterances`` (the ``construction_rosters_
    checked`` cross-reference form); the worse (larger) of the two counts when an object carries
    both, since either alone proves the two rosters are not disjoint.
    """

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        counts = [
            v for k, v in value.items()
            if k in ("shared_recordings", "shared_utterances")
            and isinstance(v, (int, float)) and not isinstance(v, bool)
        ]
        if counts:
            return int(max(counts))
    return None


def _disjointness_count(receipt: dict[str, Any], other_roster_id: str) -> int | None:
    """The overlap this receipt's own ``disjointness_proof`` declares against ``other_roster_id``.

    ``None`` means the proof says nothing about that roster (not that the two are disjoint) --
    the caller treats that as unverified, never as clear.
    """

    proof = receipt.get("disjointness_proof")
    if not isinstance(proof, dict):
        return None
    target = _normalize_roster_key(other_roster_id)
    if not target:
        return None
    best: int | None = None
    for key, value in proof.items():
        key_norm = _normalize_roster_key(str(key))
        matched = key_norm == target
        if not matched:
            fenced = _SHARED_WITH_KEY.match(key_norm)
            if fenced:
                slug = fenced.group(1)
                matched = bool(slug) and (slug in target or target in slug)
        if not matched:
            continue
        count = _extract_shared_count(value)
        if count is not None:
            best = count if best is None else max(best, count)
    return best


def _roster_overlap(repo_root: Path, tuning_id: str, read_id: str) -> int | None:
    """The larger of what either roster's own receipt proves shared with the other.

    ``None`` when neither receipt is found, or neither found receipt's disjointness proof says
    anything about the other roster -- both cases mean the split cannot be verified from what the
    tree carries today, not that it is safe.
    """

    counts: list[int] = []
    for this_id, other_id in ((tuning_id, read_id), (read_id, tuning_id)):
        receipt = _load_roster_receipt(repo_root, this_id)
        if receipt is None:
            continue
        count = _disjointness_count(receipt, other_id)
        if count is not None:
            counts.append(count)
    return max(counts) if counts else None


def _check_tuning_read_overlap(
    report: CellReport, repo_root: Path, tuning_roster: Any, read_roster: Any
) -> None:
    if _is_no_tuning(tuning_roster):
        return
    tuning_ids = _roster_ids(tuning_roster)
    read_ids = _roster_ids(read_roster)
    if not tuning_ids or not read_ids:
        return
    for tuning_id in tuning_ids:
        for read_id in read_ids:
            if _normalize_roster_key(tuning_id) == _normalize_roster_key(read_id):
                report.findings.append(Finding(
                    "tuning-read-overlap",
                    f"{report.run_id}: tuning_roster {tuning_id!r} names the read_roster "
                    f"{read_id!r} directly -- item D3's circular read (a weight, threshold, cap, "
                    "template or knowledge selection chosen on the same roster it is read on)",
                    report.run_id,
                ))
                continue
            overlap = _roster_overlap(repo_root, tuning_id, read_id)
            if overlap is None:
                report.findings.append(Finding(
                    "tuning-roster-unverified",
                    f"{report.run_id}: no roster receipt under {ROSTER_RECEIPTS_DIR.as_posix()}/ "
                    f"proves tuning_roster {tuning_id!r} disjoint from read_roster {read_id!r} "
                    "(no receipt found for one of them, or its disjointness_proof says nothing "
                    "about the other) -- reported, not blocked, until a receipt settles it",
                    report.run_id,
                    severity="advisory",
                ))
            elif overlap > 0:
                report.findings.append(Finding(
                    "tuning-read-overlap",
                    f"{report.run_id}: tuning_roster {tuning_id!r} shares {overlap} recording(s)/"
                    f"utterance(s) with read_roster {read_id!r} by its own disjointness_proof -- "
                    "item D3's circular read",
                    report.run_id,
                ))


def _check_roster_split_registration(
    report: CellReport,
    fragment: dict[str, Any],
    floor_gate: Any,
    repo_root: Path,
) -> None:
    """``tuning_roster`` / ``read_roster`` registration -- item D3, EVERY Stage-3 cell.

    A no-op when the cell declares no ``stage3_measurement`` block at all (it is then not a
    Stage-3 cell by this gate's own reading of that block). Unlike
    :func:`_check_supply_variant_registration` this does not gate on ``measurement_design``: the
    AGREE circular read that item D3 repairs was a plain cross-flight cell, not a supply-variant
    instrument one, so the split must be checked everywhere the block exists.
    """

    block = _measurement_block(floor_gate, repo_root, report.run_id, report.cell_id, fragment)
    if not isinstance(block, dict):
        return
    tuning_roster = block.get("tuning_roster")
    read_roster = block.get("read_roster")
    report.roster_split = {"tuning_roster": tuning_roster, "read_roster": read_roster}
    if tuning_roster is None or read_roster is None:
        missing = "tuning_roster" if tuning_roster is None else "read_roster"
        report.findings.append(Finding(
            "tuning-roster-missing",
            f"{report.run_id}: {floor_gate.MEASUREMENT_KEY} declares no {missing} (item D3: every "
            "Stage-3 cell names the roster(s) any weight, threshold, cap, template or knowledge "
            "selection was tuned on -- 'none' if nothing was tuned -- and the roster it is read "
            "on)",
            report.run_id,
            severity="advisory",
        ))
        return
    _check_tuning_read_overlap(report, repo_root, tuning_roster, read_roster)


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
    floor_gate = _floor_gate_module(index.repo_root)
    _check_supply_variant_registration(report, fragment, baseline, floor_gate, index.repo_root)
    _check_perception_branch_registration(report, fragment, baseline, floor_gate, index.repo_root)
    # Item D3's roster-split check still runs for a NAMED sealed/flown cell (a resume step
    # re-launching an already-consumed run id, gated the same as any other launch-mode cell --
    # see test_a_sealed_cell_is_never_blocked_by_tuning_read_overlap: the finding is reported,
    # never blocking, exactly as today). It is skipped for a cell reached only through tree-mode
    # bulk iteration (not named) that is already flown: that cell can never block regardless of
    # what this check would find, so this skips it without changing any pass/fail outcome.
    if report.named or report.consumed_by is None:
        _check_roster_split_registration(report, fragment, floor_gate, index.repo_root)

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


def _cell_blocks(report_severity: str, finding_severities: Iterable[str | None]) -> bool:
    """Whether a cell actually fails the gate.

    A cell whose OWN severity is not ``"blocking"`` (historical/flown, held preview, or
    stale-ready) never blocks, whatever its findings say -- unchanged from before item D3. A
    ``"blocking"`` cell blocks only when at least one of its findings is itself blocking: a
    finding with no explicit :attr:`Finding.severity` inherits the cell's own severity (every
    finding kind before item D3, so behaviour there is bit-for-bit unchanged), and an explicit
    ``"advisory"`` override (``tuning-roster-missing``, ``tuning-roster-unverified``) never blocks
    on its own even on an otherwise-blocking cell.
    """

    if report_severity != "blocking":
        return False
    return any((severity or report_severity) == "blocking" for severity in finding_severities)


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

    blocking = [
        r for r in reports if r.findings and _cell_blocks(r.severity, (f.severity for f in r.findings))
    ]
    advisory = [
        r for r in reports
        if r.findings and not _cell_blocks(r.severity, (f.severity for f in r.findings))
    ]
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
        blocking = _cell_blocks(cell["severity"], (f.get("severity") for f in cell["findings"]))
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
