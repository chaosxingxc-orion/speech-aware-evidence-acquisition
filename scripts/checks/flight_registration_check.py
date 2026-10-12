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
context-read-scope / context-read-row-duplicate
    A declared saea-context-learning-analysis-v1 recipe must already have one
    zero-call, model-free-check, discovery READ row naming that exact recipe.
    This matches the existing offline reader scope without signing or reading it.
    Other recipe schemas and historical report-only handling remain unchanged.

For a cell that declares ``resume_from`` (owner ruling after the COMP-1 resume attempt 3 seal
abort -- a four-row smoke cannot see seal-time checks on kept rows):

``resume-replay-unproven``
    the package's own ``*plan-registered*.json`` carries no ``resume_replay_proof`` block naming
    every field of :data:`RESUME_REPLAY_PROOF_FIELDS` (rows checked / failing / sealed-twice /
    checker sha256 / code commit), or the block it carries reports a failing or sealed-twice row.
    Advisory in tree mode; BLOCKING at launch for a live, unflown resume cell -- see
    ``scripts/checks/resume_prelaunch_gate_check.py``, the live form of the same check, which
    ``scripts/flights/batch/batch_driver.sh`` runs automatically right before any resume cell
    flies.

**Scope and severity.**

* Whole-tree mode (no ``--cell``): every cell of ``configs/experiment/*.json`` whose
  ``readiness.state`` is ``ready`` (``--include-held`` adds ``held`` cells as a PREVIEW, never
  blocking). A cell declaring ``attempt_id`` is historical only when its own attempt record
  or non-empty ``runs/<run id>/<attempt id>/`` / ``prepared/<run id>/<attempt id>/`` exists.
  Another attempt, a run-level receipt or a consumed ledger row never waives a new attempt.
  For legacy cells without ``attempt_id``, a generation run id is already CONSUMED by a non-empty
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
  named unflown cell that is not ``ready`` is refused (``not-ready``). Historical cells are
  reported only under the attempt-aware rule above; a new recovery attempt receives full
  launch checks even when its run id was consumed. The runtime separately enforces attempt
  lifecycle and recovery authority. This is the mode
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
GPU_COLUMN = "gpu hours"
SUPERSEDED_ROW = re.compile(r"\bsuperseded\b", re.IGNORECASE)

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

# --------------------------------------------------------------------------
# resume-replay proof (coordinator, after the COMP-1 resume attempt 3 seal abort): a four-row
# smoke cannot see seal-time checks on kept rows, so a cell that declares resume_from must carry
# proof, in its OWN readiness package, that scripts/analysis/replay_seal_consistency.py already
# replayed every predecessor attempt under the current code with zero failing rows and nothing
# sealed twice -- see scripts/checks/resume_prelaunch_gate_check.py (the checker's live, at-launch
# form) and scripts/flights/batch/README.md.
# --------------------------------------------------------------------------

#: The fields a ``resume_replay_proof`` block must name (kept as one tuple shared with
#: ``resume_prelaunch_gate_check.py`` so the two can never drift apart on the spelling).
RESUME_REPLAY_PROOF_FIELDS = (
    "rows_checked", "rows_failing", "sealed_twice", "checker_sha256", "code_commit",
)


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
    #: Set only for a cell whose ``stage3_measurement.measurement_design`` is
    #: ``same-flight-node-column`` -- the NX node-template column (instrument E1; design
    #: docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md section 7).
    node_column: dict[str, Any] | None = None
    #: Set only for a cell whose ``stage3_measurement.measurement_design`` is
    #: ``same-flight-shadow-relisten`` -- owner decision 185, design docs/superpowers/specs/
    #: 2026-09-28-e4-core-native-targeted-relisten-design.md section 8 rulings 2 and 7.
    relisten: dict[str, Any] | None = None
    #: Set for EVERY cell that declares a ``stage3_measurement`` block, whatever its design --
    #: item D3: ``{"tuning_roster": ..., "read_roster": ...}``, the raw values as registered.
    roster_split: dict[str, Any] | None = None
    #: Set only for a cell that declares ``resume_from``: the ``resume_replay_proof`` block found
    #: in its readiness package's ``*plan-registered*.json``, or ``None`` when none was found.
    resume_replay_proof: dict[str, Any] | None = None

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
            "node_column": self.node_column,
            "relisten": self.relisten,
            "roster_split": self.roster_split,
            "resume_replay_proof": self.resume_replay_proof,
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


def consumption(
    data_root: Path, run_id: str, rows: list[dict[str, str]], *, attempt_id: str | None = None,
) -> str | None:
    """Identify historical evidence for this attempt, or legacy run-only cells.

    A new attempt sharing a run id must not inherit a predecessor's waiver.
    Historical classification does not establish completion, sealing or score validity.
    """

    if attempt_id is not None:
        if not isinstance(attempt_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", attempt_id) is None:
            raise FlightRegistrationCheckError("attempt_id must be a plain non-empty identifier")
        record = data_root / "attempts" / run_id / f"{attempt_id}.json"
        if record.is_file():
            try:
                payload = json.loads(record.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise FlightRegistrationCheckError(f"cannot read attempt record {record}: {error}") from error
            if not isinstance(payload, dict) or payload.get("run_id") != run_id or payload.get("attempt_id") != attempt_id:
                raise FlightRegistrationCheckError(f"attempt record identity mismatch: {record}")
            return f"attempts/{run_id}/{attempt_id}.json"
        for kind in ("runs", "prepared"):
            path = data_root / kind / run_id / attempt_id
            if path.is_dir() and any(path.iterdir()):
                return f"{kind}/{run_id}/{attempt_id}"
        return None

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
    *,
    data_root: Path | None = None,
) -> None:
    """Design section 4 registration fields and gate findings for a Perception-branch cell.

    Fifth finding (2026-09-30, the ``key_source`` axis): ``key-source-unpinned`` -- a B branch's
    ``key_source`` swaps a pin that is not a well-formed ``{relpath, sha256}``-bearing source,
    or (when ``data_root`` is given) whose file is missing under the data root or does not hash
    to its pinned sha256. The runtime refuses the same thing at seed preparation
    (``FlightRuntime._apply_key_source``); this surfaces it at registration.

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
            key_source = row.get("key_source")
            if key_source is None:
                continue
            for problem in _key_source_pin_problems(key_source, data_root):
                report.findings.append(Finding(
                    "key-source-unpinned",
                    f"{report.run_id}: perception branch {row.get('branch_id')!r} key_source "
                    f"{problem}",
                    report.run_id,
                ))


# --------------------------------------------------------------------------
# Node-template column registration (NX programme instrument E1, 2026-10-09)
# --------------------------------------------------------------------------

#: The one design whose cells declare a ``roles.<node>.template_variants`` group.
NODE_COLUMN_DESIGNS = ("same-flight-node-column",)

#: Where the Solver's ``template_variants`` block is composed in a baseline fragment
#: (``rails.supply_variants.TEMPLATE_VARIANT_NODES``; Solver first).
NODE_COLUMN_PATH = ("native_episode", "roles", "solver", "template_variants")

#: A node column, like every same-flight instrument design, may claim only a nomination.
NODE_COLUMN_CLAIM_CEILING = "nominated"


def _node_column_block(baseline: dict[str, Any] | None) -> Any:
    node: Any = baseline
    for key in NODE_COLUMN_PATH:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _check_node_column_registration(
    report: CellReport,
    fragment: dict[str, Any],
    baseline: dict[str, Any] | None,
    floor_gate: Any,
    repo_root: Path,
) -> None:
    """Registration findings for a ``same-flight-node-column`` cell (the three the instrument README
    listed as not done): ``aa-arm-missing``, ``variant-cost-mismatch`` and ``variant-claim-not-nominated``,
    plus ``template-summary-mismatch`` (the declared ``template_variants`` summary must agree with the
    arm list). A no-op when the declaration is absent, names another design, or the cell declares no
    ``template_variants`` block -- the same three-guard shape the supply-variant check uses. The arm
    group itself is parsed, and refused by name, by the rails at config load; this surfaces the
    REGISTRATION half of the contract before launch.
    """

    block = _measurement_block(floor_gate, repo_root, report.run_id, report.cell_id, fragment)
    if not isinstance(block, dict) or block.get("measurement_design") not in NODE_COLUMN_DESIGNS:
        return
    group = _node_column_block(baseline)
    if not isinstance(group, dict):
        return
    arms = group.get("arms")
    arm_rows = [a for a in arms if isinstance(a, dict)] if isinstance(arms, list) else []
    twin_ids = [a.get("arm_id") for a in arm_rows if a.get("replicate_of") is not None]
    candidates = [a for a in arm_rows if a.get("instruction_template") is not None]
    report.node_column = {
        "measurement_design": block.get("measurement_design"),
        "arms": len(arm_rows),
        "candidate_arms": len(candidates),
        "twin": twin_ids[0] if twin_ids else None,
        "variant_cost": block.get("variant_cost"),
        "claim": block.get("claim"),
        "tuning_roster": block.get("tuning_roster"),
        "read_roster": block.get("read_roster"),
        "aa_arm_id": block.get("aa_arm_id"),
    }
    aa_arm_id = block.get("aa_arm_id")
    if not twin_ids:
        report.findings.append(Finding(
            "aa-arm-missing",
            f"{report.run_id}: measurement_design 'same-flight-node-column' declares no twin arm -- no arm "
            "names replicate_of -- but the node-column read needs its in-chain A/A (the twin of the delivering arm)",
            report.run_id,
        ))
    elif aa_arm_id != twin_ids[0]:
        report.findings.append(Finding(
            "aa-arm-missing",
            f"{report.run_id}: stage3_measurement.aa_arm_id is {aa_arm_id!r}, but the arm group's own twin "
            f"(the arm naming replicate_of) is {twin_ids[0]!r}",
            report.run_id,
        ))
    cost = block.get("variant_cost")
    expected_extra = len(arm_rows) - 1 if arm_rows else None
    if not isinstance(cost, dict):
        report.findings.append(Finding(
            "variant-cost-mismatch",
            f"{report.run_id}: measurement_design 'same-flight-node-column' declares no variant_cost block; the "
            "package must declare variant_cost.extra_contacts_per_row and variant_cost.extra_audio_seconds",
            report.run_id,
        ))
    else:
        extra_contacts = cost.get("extra_contacts_per_row")
        if expected_extra is not None and (
            isinstance(extra_contacts, bool) or not isinstance(extra_contacts, int)
            or extra_contacts != expected_extra
        ):
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_contacts_per_row is {extra_contacts!r}, but the arm list "
                f"({len(arm_rows)} arms, twin and delivering arm included) makes it {expected_extra} (K - 1)",
                report.run_id,
            ))
        extra_audio = cost.get("extra_audio_seconds")
        if isinstance(extra_audio, bool) or not isinstance(extra_audio, (int, float)) or extra_audio < 0:
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_audio_seconds is {extra_audio!r}; it must be a "
                "non-negative number ((K - 1) * row audio: every arm re-sends the speech packet)",
                report.run_id,
            ))
        elif expected_extra is not None and expected_extra > 0 and extra_audio == 0:
            report.findings.append(Finding(
                "variant-cost-mismatch",
                f"{report.run_id}: variant_cost.extra_audio_seconds is 0 but extra_contacts_per_row is "
                f"{expected_extra}; every extra arm re-sends the row's speech packet",
                report.run_id,
            ))
    summary = block.get("template_variants")
    if not isinstance(summary, dict) or summary.get("candidate_arms") != len(candidates) or bool(
        summary.get("twin")
    ) != bool(twin_ids):
        report.findings.append(Finding(
            "template-summary-mismatch",
            f"{report.run_id}: stage3_measurement.template_variants is {summary!r}, but the arm list has "
            f"{len(candidates)} candidate arm(s) and {'a' if twin_ids else 'no'} twin",
            report.run_id,
        ))
    claim = block.get("claim")
    if claim != NODE_COLUMN_CLAIM_CEILING:
        report.findings.append(Finding(
            "variant-claim-not-nominated",
            f"{report.run_id}: measurement_design 'same-flight-node-column' may claim only "
            f"{NODE_COLUMN_CLAIM_CEILING!r} (a node-local effect never supports a system-level claim), "
            f"but claim is {claim!r}",
            report.run_id,
        ))


#: The three retrieval-key pins a ``key_source`` branch may swap
#: (``rails.native_episode_receipt.PERCEPTION_BRANCH_KEY_SOURCE_FIELDS``, restated so this
#: gate imports nothing from the package).
KEY_SOURCE_FIELDS = ("facet_source", "query_source", "agreement_source")


def _key_source_pin_problems(key_source: Any, data_root: Path | None) -> list[str]:
    """Why a raw ``key_source`` block's pins are not registrable, one line each (``[]`` = fine)."""

    if not isinstance(key_source, dict) or set(key_source) != {"store_id", *KEY_SOURCE_FIELDS}:
        return ["is not exactly {store_id, facet_source, query_source, agreement_source}"]
    problems: list[str] = []
    swapped = 0
    for name in KEY_SOURCE_FIELDS:
        pin = key_source.get(name)
        if pin is None:
            continue
        swapped += 1
        relpath = pin.get("relpath") if isinstance(pin, dict) else None
        sha = pin.get("sha256") if isinstance(pin, dict) else None
        if (
            not isinstance(relpath, str) or not relpath
            or not isinstance(sha, str) or len(sha) != 64
            or any(character not in "0123456789abcdef" for character in sha)
        ):
            problems.append(f"{name} carries no well-formed pinned {{relpath, sha256}}")
            continue
        if data_root is None:
            continue
        path = data_root / relpath
        if not path.is_file():
            problems.append(f"{name} pin {relpath!r} is missing under the data root")
        elif _sha256(path) != sha:
            problems.append(f"{name} pin {relpath!r} does not hash to its pinned sha256 {sha}")
    if not swapped:
        problems.append("swaps zero retrieval-key pins")
    return problems


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


# --------------------------------------------------------------------------
# E4 targeted-relisten registration (owner decision 185, design docs/
# superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-design.md
# section 8 coordinator rulings 2 and 7)
# --------------------------------------------------------------------------

#: The one design whose cells must carry this section's three fields beside
#: ``measurement_design`` (ruling 7: "the bar is the twin/shadow null").
RELISTEN_INSTRUMENT_DESIGNS = ("same-flight-shadow-relisten",)

#: The path a ``relisten`` block is composed under in a baseline fragment
#: (``rails.native_episode_config``'s ``native_episode.relisten``).
RELISTEN_PATH = ("native_episode", "relisten")

#: Ruling 7 / the same-flight-supply-variant precedent (Q6 ruling this
#: design copies): a post-accept shadow effect never supports a
#: system-level claim.
RELISTEN_CLAIM_CEILING = "nominated"

#: The exact two shadow-column ids ruling 2 registers
#: (``rails.relisten.SHADOW_COLUMNS``, restated here as a literal so this
#: gate reads its own name set from source, the same discipline
#: ``register_phase_programs_v1`` uses).
RELISTEN_SHADOW_COLUMNS = ("relisten-replace-only", "relisten-replace-drop-unheard")


def _relisten_block(baseline: dict[str, Any] | None) -> Any:
    """The cell's ``native_episode.relisten`` block, or ``None``."""

    node: Any = baseline
    for key in RELISTEN_PATH:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _check_relisten_registration(
    report: CellReport,
    fragment: dict[str, Any],
    baseline: dict[str, Any] | None,
    floor_gate: Any,
    repo_root: Path,
) -> None:
    """Ruling 2/7 registration fields and gate findings for an E4 cell.

    A no-op when the declaration is absent or unreadable, when it names a
    design outside :data:`RELISTEN_INSTRUMENT_DESIGNS`, or when the cell
    declares no ``relisten`` block at all -- the same three-guard shape
    :func:`_check_supply_variant_registration` uses, for the same reason.

    Three findings: ``relisten-claim-not-nominated`` (the claim ceiling,
    ruling 7), ``relisten-not-shadow-delivery`` (ruling 5: the delivered
    answer is never changed in flight -- v1 admits no other mode), and
    ``relisten-columns-missing`` (ruling 2: both shadow columns, and only
    those two, must be declared by id).
    """

    block = _measurement_block(floor_gate, repo_root, report.run_id, report.cell_id, fragment)
    if not isinstance(block, dict):
        return
    design = block.get("measurement_design")
    if design not in RELISTEN_INSTRUMENT_DESIGNS:
        return
    relisten_block = _relisten_block(baseline)
    if not isinstance(relisten_block, dict):
        return

    columns = block.get("columns")
    report.relisten = {
        "measurement_design": design,
        "max_slots_per_row": relisten_block.get("max_slots_per_row"),
        "shadow_delivery": block.get("shadow_delivery"),
        "columns": columns,
        "claim": block.get("claim"),
        "tuning_roster": block.get("tuning_roster"),
        "read_roster": block.get("read_roster"),
    }

    claim = block.get("claim")
    if claim != RELISTEN_CLAIM_CEILING:
        report.findings.append(Finding(
            "relisten-claim-not-nominated",
            f"{report.run_id}: measurement_design {design!r} may claim only "
            f"{RELISTEN_CLAIM_CEILING!r} (ruling 7: a post-accept shadow effect never "
            f"supports a system-level claim), but claim is {claim!r}",
            report.run_id,
        ))

    if block.get("shadow_delivery") is not True:
        report.findings.append(Finding(
            "relisten-not-shadow-delivery",
            f"{report.run_id}: measurement_design {design!r} requires "
            "stage3_measurement.shadow_delivery true (ruling 5: 'Shadow delivery, on "
            "TRAIN Fold A first' -- the delivered answer is never changed in flight in "
            f"v1), but shadow_delivery is {block.get('shadow_delivery')!r}",
            report.run_id,
        ))

    if (
        not isinstance(columns, list)
        or sorted(columns) != sorted(RELISTEN_SHADOW_COLUMNS)
    ):
        report.findings.append(Finding(
            "relisten-columns-missing",
            f"{report.run_id}: measurement_design {design!r} requires "
            f"stage3_measurement.columns to name exactly the two shadow columns "
            f"{sorted(RELISTEN_SHADOW_COLUMNS)} (ruling 2), but columns is {columns!r}",
            report.run_id,
        ))


def _resume_replay_proof_block(
    index: PackageIndex, package: str, run_id: str, cell_id: str | None = None
) -> dict[str, Any] | None:
    """The ``resume_replay_proof`` block from the cell's own registered-plan facts.

    A resume-recovery flies under the ARM's run id, so the package :func:`resolve_package` finds
    from the arm's ledger row is the arm's ORIGINAL package, while the resume cell's own registered
    plan (the one that carries this block) lives in the recovery package (COMP-1: the ``-resume-v1``
    package beside the parent ``2026-09-27`` one, which is never edited). So a registered plan that
    names BOTH this run id and this ``cell_id`` is preferred, in the resolved package first and then
    in every package whose registered plan names the run id; failing that, the resolved package's
    first plan naming the run id is used, exactly as before.

    ``None`` when no candidate names this run id at all; ``{}`` when the chosen plan carries no
    block. Never raises: an unreadable or malformed registered-plan file is skipped, exactly like
    :meth:`PackageIndex.packages_registering`.
    """

    candidates = [package] + [name for name in index.packages_registering(run_id) if name != package]
    fallback: dict[str, Any] | None = None
    for name in candidates:
        directory = index.repo_root / READINESS / name
        for path in sorted(directory.glob("*plan-registered*.json")):
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            if not isinstance(document, dict):
                continue
            execution_plan = document.get("execution_plan")
            named_run_id = document.get("run_id") or (
                execution_plan.get("run_id") if isinstance(execution_plan, dict) else None
            )
            if named_run_id != run_id:
                continue
            block = document.get("resume_replay_proof")
            block = block if isinstance(block, dict) else {}
            if cell_id is not None and document.get("cell") == cell_id:
                return block
            if name == package and fallback is None:
                fallback = block
    return fallback


def _check_resume_replay_proof(
    report: CellReport, cell: dict[str, Any], index: PackageIndex, package: str
) -> None:
    """``resume-replay-unproven`` -- a cell declaring ``resume_from`` must carry proof, in its own
    package, that the offline replay already ran clean under the current code (owner ruling after
    the COMP-1 resume attempt 3 seal abort: a four-row smoke cannot see seal-time checks on kept
    rows).

    Advisory in tree mode (a whole-tree scan reports the gap without failing the tree over
    paperwork not yet done); BLOCKING at launch (``--cell`` / ``--campaign-plan``, what
    ``batch_driver.sh`` runs) for a live, unflown resume cell -- inherits the cell's own severity,
    which is only ``"blocking"`` there. A no-op for a cell that declares no ``resume_from`` at
    all, and skipped for a cell reached only through tree-mode bulk iteration of an already-flown
    run id (never blocking either way, so checking it would only add noise -- the same scope
    :func:`check_cell` already applies to the roster-split check).
    """

    if cell.get("resume_from") is None:
        return
    if not (report.named or report.consumed_by is None):
        return
    severity = None if report.named else "advisory"
    block = _resume_replay_proof_block(index, package, report.run_id, cell.get("cell_id"))
    report.resume_replay_proof = block
    fields = RESUME_REPLAY_PROOF_FIELDS
    if block is None:
        report.findings.append(Finding(
            "resume-replay-unproven",
            f"{report.run_id}: no *plan-registered*.json under {report.package} names this run id "
            "with a resume_replay_proof block (scripts/analysis/replay_seal_consistency.py, run "
            "offline over every resume_from predecessor under the current code, before this "
            "resume launches)",
            report.run_id, severity=severity,
        ))
        return
    missing = [name for name in fields if name not in block]
    if missing:
        report.findings.append(Finding(
            "resume-replay-unproven",
            f"{report.run_id}: {report.package}'s resume_replay_proof is missing {missing} (must "
            f"name all of {list(fields)})",
            report.run_id, severity=severity,
        ))
        return
    if int(block.get("rows_failing") or 0) != 0 or int(block.get("sealed_twice") or 0) != 0:
        report.findings.append(Finding(
            "resume-replay-unproven",
            f"{report.run_id}: {report.package}'s resume_replay_proof reports "
            f"{block.get('rows_failing')} row(s) failing and {block.get('sealed_twice')} sealed "
            "twice -- the replay did not prove this resume safe to launch",
            report.run_id, severity=severity,
        ))


def _check_system_text_binding(report, cell, baseline, recipe, repo_root, data_root):
    """Bind fixed-pool comparison roles to the policy declared by its registration."""
    from speech_aware_evidence_acquisition.rails.system_text_policy import (
        _read_pin, require, verify_system_text_binding,
    )
    family = str(recipe.get("family_id", ""))
    context = "context_learning_registration" in recipe or family.startswith("context-initial4-")
    fixed = family.startswith("fixed400-context")
    panel = (family.startswith("fixed400-text-") or "system_panel_registration" in recipe
             or report.run_id.startswith("SAEA-SLURP-SYSTEM-TEXT-FIXED400-ROUND"))
    if not context and not fixed and not panel and "system_text_policy_binding" not in cell:
        return
    from speech_aware_evidence_acquisition.core.config import ConfigError, compose
    try:
        registration = {}
        binding = cell.get("system_text_policy_binding")
        require(binding is not None, "declared system text policy binding is missing")
        if context:
            from speech_aware_evidence_acquisition.rails.system_context_learning import _validate_scope
            require(not panel and not fixed and "pilot_registration" not in recipe,
                    "ambiguous context learning registration")
            registration = json.loads(_read_pin(recipe["context_learning_registration"], repo_root))
            protocol = json.loads(_read_pin(registration["protocol"], repo_root))
            _validate_scope(recipe, registration, protocol, root=repo_root)
            members = [m for m in registration["member_bindings"].values()
                       if m["run_id"] == report.run_id]
            require(len(members) == 1 and members[0]["bundle_id"] == binding["bundle_id"]
                    and members[0]["attempt_id"] == cell.get("attempt_id"),
                    "cell differs from the registered context member")
        elif panel:
            from speech_aware_evidence_acquisition.rails.hashing import content_hash
            require(not fixed and "pilot_registration" not in recipe,
                    "ambiguous legacy and panel registrations")
            registration = json.loads(_read_pin(recipe["system_panel_registration"], repo_root))
            from speech_aware_evidence_acquisition.rails.system_optimization import SUCCESSOR_REGISTRATION
            successor = registration.get("schema") == SUCCESSOR_REGISTRATION
            if successor:
                from speech_aware_evidence_acquisition.analysis import system_text_panel
                supplement = json.loads(_read_pin(recipe["successor_panel_scope"], repo_root))
                owner = json.loads(_read_pin(supplement["owner_decision"], repo_root))
                require(supplement.get("schema") == "saea-successor-panel-source-scope-v1",
                        "successor prelaunch needs its complete analysis scope")
                scope = system_text_panel.load_scope(registration, owner, supplement, repo_root=repo_root, recipe=recipe)
                system_text_panel.validate_definition(recipe, registration, owner, **scope)
            require(registration.get("schema") in {"saea-fixed400-system-panel-registration-v1", SUCCESSOR_REGISTRATION}
                    and registration.get("family_id") == family
                    and registration.get("registration_sha256") == content_hash(
                        {k: v for k, v in registration.items() if k != "registration_sha256"}),
                    "panel registration identity or hash differs")
            members = [m for m in registration["member_bindings"].values()
                       if m["run_id"] == report.run_id]
            require(len(members) == 1 and members[0]["bundle_id"] == binding["bundle_id"]
                    and cell.get("attempt_id")
                    and members[0]["attempt_id"] == cell["attempt_id"],
                    "cell policy or attempt differs from the registered panel member")
        elif fixed:
            registration = json.loads(_read_pin(recipe["pilot_registration"], repo_root))
            members = [m for m in registration["member_bindings"].values()
                       if m["run_id"] == report.run_id]
            require(len(members) == 1 and members[0]["bundle_id"] == binding["bundle_id"],
                    "cell policy differs from the registered comparison member")
        # Verify what the shared runtime consumes, including options declared in
        # model, dataset or experiment fragments instead of the baseline.
        composed = compose(repo_root, model=cell["model_fragment"],
                            dataset=cell["dataset_fragment"],
                            baseline=cell["baseline_fragment"],
                            experiment=report.experiment)
        effective = composed.values
        if context:
            require(members[0]["config_hash"] == composed.config_hash,
                    "context member configuration differs from registration")
            if "experiment_population" in protocol:
                from speech_aware_evidence_acquisition.rails.experiment_population import (
                    load_population_config, require_population_binding,
                )
                population_pin = protocol["experiment_population"]
                population = load_population_config(population_pin, repo_root=repo_root)
                cohort = require_population_binding(population, population_pin,
                    protocol["population_cohort"], cell, effective)
                require(all(effective.get("decoding_params", {}).get(k) == v
                            for k, v in population["sampling"].items()),
                        "runtime sampling differs from experiment population config")
                limits = population["contact_limits"]
                require(effective.get("native_contact_fit", {}).get("contact_cap") ==
                        len(cohort["sample_ids"]) * limits["model_per_trajectory"] * limits["fit_endpoints_per_model_contact"],
                        "runtime FIT cap differs from experiment population config")
        verify_system_text_binding(effective, binding, repo_root=repo_root, data_root=data_root)
        # Compare prospective measurement custody before spending model contacts.
        profile = recipe.get("measurement_profile")
        require((not (context or panel or fixed) or registration.get("measurement_profile") == profile)
                and effective.get("system_search_measurement") == profile,
                "registered measurement profile differs from runtime or read recipe")
        if profile is not None:
            from speech_aware_evidence_acquisition.rails.system_search_measurement import runtime_options
            from speech_aware_evidence_acquisition.rails.adapters.runtime_view import configured_geometry
            require(type(effective.get("serving_slots")) is int
                    and type(effective.get("serving_slot_tokens")) is int,
                    "measured runtime geometry must be explicit")
            geometry = configured_geometry(effective, defaults=(0, 0, 0))
            runtime_options(effective, slot_count=geometry["slots"])

    except (ConfigError, ValueError, TypeError, KeyError, OSError) as error:
        report.findings.append(Finding(
            "system-text-policy-binding", f"{report.run_id}: {error}", report.run_id
        ))


def _check_declared_carrier_binding(report, document, run_id, ledger):
    """Check the exact declared carrier token before the heavier runtime gate.

    Reuse runtime ledger tokenization without case folding or substring matching.
    Legacy plans without a carrier declaration retain their existing behavior.
    Runtime still resolves the key against the authoritative dataset inventory and
    rejects captions naming additional known carriers; this early check does not
    replace execution-plan, scope, exposure or dataset-lock admission.
    """
    from speech_aware_evidence_acquisition.contracts.ledger import (
        _CARRIER_CELL_TOKEN_SPLIT, _EXPOSURE_CARRIER_COLUMN,
    )

    plan = document.get("execution_plan")
    if (run_id not in report.run_ids.values() or not isinstance(plan, dict)
            or "carrier_lock_key" not in plan):
        return
    rows = ledger.get(run_id, [])
    if len(rows) != 1:
        return  # The existing missing/duplicate-row check already refuses this run.
    carrier = plan["carrier_lock_key"]
    caption = rows[0].get(_EXPOSURE_CARRIER_COLUMN, "")
    tokens = [token for token in _CARRIER_CELL_TOKEN_SPLIT.split(caption) if token]
    if (not isinstance(carrier, str) or not carrier or carrier.strip() != carrier
            or tokens.count(carrier) != 1):
        report.findings.append(Finding(
            "registered-carrier-binding",
            f"{run_id}: exposure carrier caption {caption!r} must contain the plan's "
            f"exact nonempty carrier key {carrier!r} once; do not case-fold or use "
            "a substring. Runtime dataset-lock admission remains required.",
            run_id,
        ))


def _report_authorized_joint_overlap(report, stage):
    """Retain overlaps visibly only after exact canonical joint authentication."""
    for finding in report.findings:
        if finding.kind == "tuning-read-overlap" and finding.run_id == report.run_id:
            finding.kind = "authorized-adaptive-joint-roster-overlap"
            finding.severity = "advisory"
            finding.message += (f"; exact owner227 complete joint {stage} basis authorizes adaptive discovery "
                                "on this original roster; no benefit, independent-validation, "
                                "adoption or learner-export claim")


_HEX64 = re.compile(r"[0-9a-f]{64}")
#: Annotation-only members of a registered ``prepared_phase_supply`` declaration. They describe
#: the pin (provenance note, the minted artifact's output hash) and are never part of its identity.
_SUPPLY_PIN_ANNOTATIONS = ("note", "output_sha256")


def _supply_pins_agree(declared: Any, expected: Any) -> bool:
    """Whether a registered plan's ``prepared_phase_supply`` names the cell baseline's supply.

    A plan registered BEFORE the flip cannot carry the minted hash: it declares the artifact's
    ``relpath`` with an explicit placeholder (``"0" * 64`` or ``MINTED_AT_THE_FLIP``), and the flip
    later writes the real pin into the baseline. Annotation members (``note``, ``output_sha256``)
    never identify the pin. So the identity compared is the ``relpath`` always, and the ``sha256``
    only when the plan declares a real (64 lowercase hex, non-zero) one. A sibling's relpath or a
    real, different hash is still a disagreement.
    """

    if not isinstance(declared, dict) or not isinstance(expected, dict):
        return declared == expected

    def identity(pin: dict[str, Any]) -> dict[str, Any]:
        view = {k: v for k, v in pin.items() if k not in _SUPPLY_PIN_ANNOTATIONS}
        sha = view.get("sha256")
        if not (isinstance(sha, str) and _HEX64.fullmatch(sha) and set(sha) != {"0"}):
            view.pop("sha256", None)
        return view

    declared_view = identity(declared)
    if "sha256" not in declared_view:
        expected_view = {k: v for k, v in identity(expected).items() if k != "sha256"}
        return declared_view == expected_view
    return declared_view == identity(expected)


def _check_registered_supply_binding(report, baseline, index, package, ledger, *, cell=None, fragment=None,
                                     data_root=None):
    """Refuse a plan that declares another member's prepared supply envelope.

    Legacy plans without this optional declaration retain their old behavior.
    Runtime preparation still verifies the actual artifact and source hashes.
    """
    expected = (baseline or {}).get("prepared_phase_supply")
    natural = (cell is not None and cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker"]
               and ("architecture_member" in (fragment or {}) or "architecture_member" in (baseline or {})))
    manual_n20 = (cell is not None
                  and cell.get("allowed_execution_stages") == ["check", "prepare-supply", "worker", "campaign"]
                  and ("architecture_member" in (fragment or {}) or "architecture_member" in (baseline or {})))
    natural_plans = []
    for path in sorted((index.repo_root / READINESS / package).glob("*plan-registered*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(document, dict):
            continue
        plan = document.get("execution_plan")
        run_id = document.get("run_id") or (plan.get("run_id") if isinstance(plan, dict) else None)
        _check_declared_carrier_binding(report, document, run_id, ledger)
        if run_id in report.run_ids.values() and "experiment_population" in (baseline or {}):
            if natural or manual_n20:
                natural_plans.append(document)
            try:
                from speech_aware_evidence_acquisition.rails.experiment_population import (
                    load_population_config, require_population_binding,
                    require_architecture_capacity_registration,
                )
                from speech_aware_evidence_acquisition.rails.system_text_policy import require
                if natural or manual_n20:
                    pass  # Validate the complete generation/FIT pair after collecting it.
                elif "architecture_member" in (fragment or {}) or "architecture_member" in baseline:
                    from speech_aware_evidence_acquisition.core.config import compose
                    effective = compose(index.repo_root, cell["model_fragment"], cell["dataset_fragment"],
                                        cell["baseline_fragment"], report.experiment)
                    require_architecture_capacity_registration(effective.values, cell, document,
                                                              repo_root=index.repo_root,
                        **({"data_root":data_root} if effective.values.get("joint_role_basis") is not None else {}))
                    if effective.values.get("joint_role_basis") is not None:
                        _report_authorized_joint_overlap(report, "capacity")
                else:
                    population_pin = baseline["experiment_population"]
                    population = load_population_config(population_pin, repo_root=index.repo_root)
                    cohort = require_population_binding(population, population_pin,
                        baseline["population_cohort"], document)
                    cap = len(cohort["sample_ids"]) * population["contact_limits"]["model_per_trajectory"]
                    if run_id != report.run_ids["generation"]:
                        cap *= population["contact_limits"]["fit_endpoints_per_model_contact"]
                    require(isinstance(plan, dict) and plan.get("planned_model_calls") == cap,
                            "registered plan contact cap differs from config")
            except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:  # RuntimeError: BundleError (unreadable source custody) is a finding, never a gate crash
                report.findings.append(Finding("population-config-binding", f"{run_id}: {error}", run_id))
        if (run_id in report.run_ids.values() and "prepared_phase_supply" in document
                and not _supply_pins_agree(document["prepared_phase_supply"], expected)):
            report.findings.append(Finding(
                "registered-supply-binding",
                f"{run_id}: {path.name} declares a prepared supply different from its cell baseline "
                f"(remedy: python scripts/flights/refresh_registered_plan_pins.py --package {READINESS}/{package}, "
                f"after the flip loop minted the baseline pin)",
                run_id,
            ))
    if natural or manual_n20:
        try:
            from speech_aware_evidence_acquisition.core.config import compose
            from speech_aware_evidence_acquisition.rails.architecture_natural_registration import (
                require_architecture_natural_registration, require_architecture_n20_registration,
            )
            effective = compose(index.repo_root, cell["model_fragment"], cell["dataset_fragment"],
                                cell["baseline_fragment"], report.experiment)
            if manual_n20:
                from speech_aware_evidence_acquisition.rails.architecture_audio_budget import require_manual_architecture_audio_budget
                require_manual_architecture_audio_budget(effective.values)
            validator = require_architecture_n20_registration if manual_n20 else require_architecture_natural_registration
            validator(effective.values, cell, natural_plans,
                                                     repo_root=index.repo_root, data_root=data_root)
            if effective.values.get("joint_role_basis") is not None:
                _report_authorized_joint_overlap(report, "generation" if manual_n20 else "natural")
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as error:  # RuntimeError: BundleError (unreadable source custody) is a finding, never a gate crash
            report.findings.append(Finding("population-config-binding", str(error), report.run_id))


def planned_gpu_hours_of(fragment: dict[str, Any]) -> float | None:
    """The GPU hours the cell's execution plan will claim at the exposure gate (``execution_plan.planned_gpu_hours``)."""

    plan = fragment.get("execution_plan")
    value = plan.get("planned_gpu_hours") if isinstance(plan, dict) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def gpu_row_findings(role: str, run_id: str, rows: list[dict[str, str]], planned: float | None) -> list[Finding]:
    """A live ledger row whose ``gpu hours`` cell is below the plan's claim.

    The exposure gate (``contracts.gate_exposure``) refuses a model touch when the plan claims more GPU hours than the matched
    row pre-registered, and the live phase-fit run id has a row of its own: amending only the generation row leaves the FIT row
    short and the arm aborts before contact (266-E Thinking arm, 2026-10-12). Consumed and superseded rows are history and skipped.
    """

    if planned is None:
        return []
    out: list[Finding] = []
    for row in rows:
        if row_consumed(row) or SUPERSEDED_ROW.search(row_text(row)) or GPU_COLUMN not in row:
            continue
        try:
            registered = float(str(row[GPU_COLUMN]).replace("*", "").strip())
        except ValueError:
            continue
        if registered < planned:
            out.append(Finding(
                "row-gpu-under-plan",
                f"{run_id} ({role}): the exposure-ledger row pre-registers {registered:g} gpu hours but the plan claims "
                f"{planned:g}; the exposure gate would refuse the model touch",
                run_id,
            ))
    return out


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
    _check_perception_branch_registration(
        report, fragment, baseline, floor_gate, index.repo_root, data_root=data_root,
    )
    _check_node_column_registration(report, fragment, baseline, floor_gate, index.repo_root)
    _check_relisten_registration(report, fragment, baseline, floor_gate, index.repo_root)
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
    planned_gpu = planned_gpu_hours_of(fragment)
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
        report.findings.extend(gpu_row_findings(role, run_id, rows, planned_gpu))
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
    _check_registered_supply_binding(report, baseline, index, package, ledger, cell=cell, fragment=fragment,
                                     data_root=data_root)
    _check_resume_replay_proof(report, cell, index, package)
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
    if isinstance(recipe, dict):
        _check_system_text_binding(report, cell, baseline, recipe, index.repo_root, data_root)
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
    _check_context_read_scope(report, recipe, read_rows)


def _check_context_read_scope(
    report: CellReport, recipe: dict[str, Any], read_rows: list[dict[str, str]],
) -> None:
    """Match the context reader's offline scope without authorizing a READ.

    Draft READ signatures are intentional before sealing. Only the declared
    context-learning recipe uses this contract; other readers keep their own
    scope checks. Historical findings retain the caller's report-only severity.
    """
    if recipe.get("schema") != "saea-context-learning-analysis-v1":
        return
    if len(read_rows) != 1:
        report.findings.append(Finding(
            "context-read-row-duplicate",
            "The context reader requires exactly one READ registration.",
            report.read_run_id,
        ))
        return
    row = read_rows[0]
    expected = {
        "execution profile": "model-free-check",
        "split role": "discovery",
        "calls": "0",
        ARTIFACTS_COLUMN: report.recipe,
    }
    mismatches = [
        key for key, value in expected.items()
        if (row.get(key, "").strip("`") if key == ARTIFACTS_COLUMN
            else row.get(key)) != value
    ]
    if mismatches:
        report.findings.append(Finding(
            "context-read-scope",
            "Context READ registration differs from its zero-contact offline "
            "reader contract: " + ", ".join(mismatches)
            + ". Correct the prospective registration; root READ countersignature "
            "still waits for the complete sealed family.",
            report.read_run_id,
        ))


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


def _ledger_completed_sole_attempt(
    cell: dict[str, Any], run_id: str, rows: list[dict[str, str]], registered_attempts: set[str],
) -> str | None:
    """Tree-mode historical evidence for a spend that leaves no ``attempts/``/``runs/`` record.

    Tokenizer-only and zero-generation diagnostics (capacity and fit measurements) are spent
    without ever creating an attempt directory, so the attempt-aware :func:`consumption` finds
    nothing for them. Their evidence of record is the exposure-ledger row, closed
    ``consumed = yes`` and a recorded ``COMPLETED`` / ``Verdict:`` disposition. That row waives the cell ONLY in whole-tree
    mode and ONLY while this cell is the sole attempt registered for the run id anywhere in
    ``configs/experiment``: a second attempt sharing the run id is a new attempt and never inherits
    the waiver, and a named (launch-mode) cell is always gated in full.
    """

    attempt_id = cell.get("attempt_id")
    if not isinstance(attempt_id, str) or registered_attempts != {attempt_id}:
        return None
    if any(row_consumed(row) and re.search(r"\b(?:completed|verdict:)", row_text(row), re.IGNORECASE) for row in rows):
        return "ledger consumed=yes + COMPLETED (sole registered attempt, no attempt record)"
    return None


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

    attempts_by_run: dict[str, set[str]] = {}
    for entry in fragments.values():
        for member in entry.fragment["cells"]:
            if isinstance(member, dict) and member.get("run_id"):
                attempts_by_run.setdefault(str(member["run_id"]).strip(), set()).add(
                    str(member.get("attempt_id") or "")
                )

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
        report.consumed_by = consumption(data_root, run_id, rows, attempt_id=cell.get("attempt_id"))
        if report.consumed_by is None and not named:
            report.consumed_by = _ledger_completed_sole_attempt(
                cell, run_id, rows, attempts_by_run.get(run_id, set())
            )
        baseline = entry.baseline
        if baseline is None and cell.get("baseline_fragment") is not None:
            # A multi-member family may intentionally use different policy bundles.
            # Resolve this member's baseline instead of silently omitting every
            # member's FIT and native-tool registration requirements.
            name = cell["baseline_fragment"]
            if not isinstance(name, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name) is None:
                raise FlightRegistrationCheckError("cell baseline must be a plain fragment name")
            try:
                baseline = json.loads((repo_root / BASELINE_DIR / f"{name}.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise FlightRegistrationCheckError(f"cannot read baseline {name}: {error}") from error
            if not isinstance(baseline, dict):
                raise FlightRegistrationCheckError(f"baseline {name} must be an object")
        check_cell(report, cell, entry.fragment, baseline, ledger, data_root, index, receipt_cache)

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
