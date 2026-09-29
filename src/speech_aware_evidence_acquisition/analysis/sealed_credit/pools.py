"""Pool manifest for the sealed-credit inner loop (design spec 2026-09-29, task 1).

A pool manifest (``configs/analysis/sealed-credit-pools-v1.json``) names every sealed
run this inner loop's credit table is built from, its ROW-STATE kind (see
``analysis.sealed_credit.row_states``), the roster it was flown on, and whether it is
a TUNING pool, a READ pool, a never-tuning pool (ROLL-3 / DEV), or a purely
DESCRIPTIVE one (the filler pools -- decision 186: a policy built from Fold-B
rollouts may not be read on Fold B, so the filler pools enter neither as tuning nor
as this run's read roster).

Leakage discipline (design spec section 3) is enforced here, before any row is read:

* every roster id the manifest names (``tuning_roster``, every ``read_rosters``
  value, and every pool's own ``roster``) must resolve to a receipt under
  ``docs/receipts/rosters/`` -- ``missing-roster-receipt`` otherwise;
* no ``read_rosters`` value may equal, or overlap (by either roster's own
  ``disjointness_proof``), any ``tuning_roster`` id -- ``tuning-read-overlap``;
  an unresolvable overlap (neither receipt speaks to the other) is
  ``tuning-roster-unverified`` (advisory, matching ``flight_registration_check.py``'s
  own severity for the same finding);
* a pool marked ``"use": "tuning"`` whose own roster IS a ``read_rosters`` value is
  refused outright (``dev-as-tuning`` / ``read-roster-as-tuning``) -- the run 1
  design's own rule that ROLL-3 (DEV-2000-ADDED) never enters tuning, generalised to
  any pool that tries to tune on the roster this run will read.

The roster overlap arithmetic itself is NOT reimplemented here: ``_roster_overlap``
below re-reads it from ``scripts/checks/flight_registration_check.py`` (item D3's own
reader, ``_roster_overlap`` / ``_load_roster_receipt`` / ``_is_no_tuning`` /
``_roster_ids``), loaded the same way every ``scripts/analysis/*.py`` driver in this
repository loads a sibling script (``importlib`` from a file path) -- one law, read
once, never copied into a second implementation that could drift from the gate's own.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[5]

SCHEMA = "saea-sealed-credit-pools-v1"
POOL_KINDS = ("single-sample-arm", "grouped-multi-sample")
POOL_USES = ("tuning", "read", "never-tuning", "descriptive")
REQUIRED_POOL_KEYS = frozenset({"label", "run_id", "kind", "roster", "use", "scorer"})
OPTIONAL_POOL_KEYS = frozenset({"attempt", "phases_attempt", "samples_per_row", "note", "program"})
REQUIRED_MANIFEST_KEYS = frozenset({"schema", "tuning_roster", "read_rosters", "pools"})


class PoolManifestError(RuntimeError):
    """The pool manifest is malformed, or a leakage rule it must satisfy fails closed."""


def _fail(message: str) -> None:
    raise PoolManifestError(message)


def load_manifest(path: Path) -> dict[str, Any]:
    """Parse and shape-validate the pool manifest. Raises :class:`PoolManifestError`
    on any structural defect; does not touch roster receipts or sealed bytes."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PoolManifestError(f"cannot read pool manifest {path}: {error}") from error
    if not isinstance(document, Mapping):
        _fail(f"{path}: pool manifest must be a JSON object")
    missing = sorted(REQUIRED_MANIFEST_KEYS - set(document))
    if missing:
        _fail(f"{path}: pool manifest is missing key(s) {missing}")
    if document.get("schema") != SCHEMA:
        _fail(f"{path}: schema must be {SCHEMA!r}, got {document.get('schema')!r}")
    tuning_roster = document.get("tuning_roster")
    if not isinstance(tuning_roster, list) or not all(isinstance(r, str) and r for r in tuning_roster):
        _fail(f"{path}: tuning_roster must be a non-empty list of roster id strings")
    read_rosters = document.get("read_rosters")
    if not isinstance(read_rosters, Mapping) or not read_rosters:
        _fail(f"{path}: read_rosters must be a non-empty {{design: roster_id}} object")
    for design, roster_id in read_rosters.items():
        if not isinstance(design, str) or not isinstance(roster_id, str) or not roster_id:
            _fail(f"{path}: read_rosters entry {design!r} must map to a non-empty roster id string")
    pools = document.get("pools")
    if not isinstance(pools, list) or not pools:
        _fail(f"{path}: pools must be a non-empty list")
    labels = set()
    for entry in pools:
        if not isinstance(entry, Mapping):
            _fail(f"{path}: every pool entry must be an object, got {type(entry).__name__}")
        entry_missing = sorted(REQUIRED_POOL_KEYS - set(entry))
        if entry_missing:
            _fail(f"{path}: pool {entry.get('label')!r} is missing key(s) {entry_missing}")
        unknown = sorted(set(entry) - REQUIRED_POOL_KEYS - OPTIONAL_POOL_KEYS)
        if unknown:
            _fail(f"{path}: pool {entry['label']!r} carries unknown key(s) {unknown}")
        if entry["kind"] not in POOL_KINDS:
            _fail(f"{path}: pool {entry['label']!r}: kind {entry['kind']!r} is not one of {POOL_KINDS}")
        if entry["use"] not in POOL_USES:
            _fail(f"{path}: pool {entry['label']!r}: use {entry['use']!r} is not one of {POOL_USES}")
        if entry["label"] in labels:
            _fail(f"{path}: duplicate pool label {entry['label']!r}")
        labels.add(entry["label"])
        if entry["kind"] == "grouped-multi-sample":
            spr = entry.get("samples_per_row")
            if not isinstance(spr, int) or isinstance(spr, bool) or spr < 2:
                _fail(f"{path}: grouped pool {entry['label']!r} must declare samples_per_row >= 2")
    return dict(document)


# ---------------------------------------------------------------------------
# roster overlap (item D3's own reader, reused not reimplemented)


def _import_path(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    # Registered in sys.modules BEFORE exec: a module defining a ``@dataclass`` needs
    # ``sys.modules[cls.__module__]`` to resolve its own annotations during class
    # creation (Python's dataclasses._is_type), which fails with a bare AttributeError
    # otherwise -- flight_registration_check.py defines several.
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _flight_registration_check(repo_root: Path):
    checks_dir = repo_root / "scripts" / "checks"
    if str(checks_dir) not in sys.path:
        sys.path.insert(0, str(checks_dir))
    return _import_path(checks_dir / "flight_registration_check.py", "flight_registration_check")


def roster_findings(manifest: Mapping[str, Any], repo_root: Path | None = None) -> list[dict[str, str]]:
    """Every leakage finding the manifest's rosters raise, item D3's own way.

    Each finding is ``{"code": ..., "severity": "blocking"|"advisory", "message": ...}``.
    An empty list means every declared roster resolves and no tuning roster overlaps
    (or is identical to) any read roster. This function reads roster RECEIPTS only
    (``docs/receipts/rosters/``); it never opens a sealed run.
    """

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    frc = _flight_registration_check(root)
    findings: list[dict[str, str]] = []

    tuning_roster: list[str] = list(manifest["tuning_roster"])
    read_rosters: dict[str, str] = dict(manifest["read_rosters"])
    every_roster_id = sorted(set(tuning_roster) | set(read_rosters.values()) |
                             {entry["roster"] for entry in manifest["pools"]})
    for roster_id in every_roster_id:
        if frc._load_roster_receipt(root, roster_id) is None:  # noqa: SLF001
            findings.append({
                "code": "missing-roster-receipt", "severity": "blocking",
                "message": f"no roster receipt under docs/receipts/rosters/ resolves {roster_id!r}",
            })

    for design, read_id in read_rosters.items():
        for tuning_id in tuning_roster:
            if frc._normalize_roster_key(tuning_id) == frc._normalize_roster_key(read_id):  # noqa: SLF001
                findings.append({
                    "code": "tuning-read-overlap", "severity": "blocking",
                    "message": f"read design {design!r} roster {read_id!r} is also a tuning_roster entry",
                })
                continue
            overlap = frc._roster_overlap(root, tuning_id, read_id)  # noqa: SLF001
            if overlap is None:
                findings.append({
                    "code": "tuning-roster-unverified", "severity": "advisory",
                    "message": (
                        f"no roster receipt proves tuning_roster {tuning_id!r} disjoint from "
                        f"read design {design!r} roster {read_id!r}"
                    ),
                })
            elif overlap > 0:
                findings.append({
                    "code": "tuning-read-overlap", "severity": "blocking",
                    "message": (
                        f"tuning_roster {tuning_id!r} shares {overlap} recording(s)/utterance(s) with "
                        f"read design {design!r} roster {read_id!r}"
                    ),
                })

    read_roster_ids = {frc._normalize_roster_key(r) for r in read_rosters.values()}  # noqa: SLF001
    for entry in manifest["pools"]:
        if entry["use"] == "tuning" and frc._normalize_roster_key(entry["roster"]) in read_roster_ids:  # noqa: SLF001
            findings.append({
                "code": "read-roster-as-tuning", "severity": "blocking",
                "message": (
                    f"pool {entry['label']!r} declares use=tuning but its own roster {entry['roster']!r} "
                    "is one of this manifest's read_rosters -- item D3's circular read"
                ),
            })
    return findings


def validate_manifest(manifest: Mapping[str, Any], repo_root: Path | None = None) -> None:
    """Raise :class:`PoolManifestError` on the first BLOCKING roster finding.

    Advisory findings (``tuning-roster-unverified``) are returned by
    :func:`roster_findings` for the caller to report, never raised.
    """

    blocking = [f for f in roster_findings(manifest, repo_root) if f["severity"] == "blocking"]
    if blocking:
        lines = "; ".join(f"[{f['code']}] {f['message']}" for f in blocking)
        raise PoolManifestError(f"pool manifest refused: {lines}")


# ---------------------------------------------------------------------------
# pool resolution (locating the sealed attempt directory)


def pools_by_use(manifest: Mapping[str, Any], use: str) -> list[dict[str, Any]]:
    return [dict(entry) for entry in manifest["pools"] if entry["use"] == use]


def pool_by_label(manifest: Mapping[str, Any], label: str) -> dict[str, Any]:
    for entry in manifest["pools"]:
        if entry["label"] == label:
            return dict(entry)
    raise PoolManifestError(f"no pool named {label!r} in this manifest")


def attempt_dir(data_root: Path, run_id: str, attempt: str | None = None) -> Path:
    """The sealed attempt directory carrying ``<run_id>.phases.json``.

    Mirrors ``scripts/analysis/slurp_reviewer_credit_table.py``'s own ``attempt_dir``:
    globs ``runs/<run_id>/*/`` for the one attempt that carries the phases file, unless
    ``attempt`` names it directly.
    """

    base = Path(data_root) / "runs" / run_id
    if attempt is not None:
        candidate = base / attempt
        if not (candidate / f"{run_id}.phases.json").is_file():
            raise PoolManifestError(f"{run_id}: attempt {attempt!r} carries no phases file")
        return candidate
    hits = sorted(base.glob(f"*/{run_id}.phases.json"))
    if len(hits) != 1:
        raise PoolManifestError(f"{run_id}: expected exactly one attempt carrying phases, found {len(hits)}")
    return hits[0].parent


__all__ = [
    "SCHEMA", "POOL_KINDS", "POOL_USES", "PoolManifestError",
    "load_manifest", "roster_findings", "validate_manifest",
    "pools_by_use", "pool_by_label", "attempt_dir",
]
