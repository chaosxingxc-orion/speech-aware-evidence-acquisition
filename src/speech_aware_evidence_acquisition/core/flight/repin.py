"""Re-pin one registered flight package after the working tree moved under it.

Every registered cell binds (a) a model-free prepared Perception supply artifact
whose identity digest (``core.preparation.artifact_inputs``) pins the SHA-256 of
``rails.kb_policy``, ``rails.knowledge_provider``, ``rails.phase_supply``,
``rails.knowledge_stores`` and ``core.flight.runtime``, and (b) a composed config
hash / protocol hash derived from the four config fragments (model, dataset,
baseline, experiment) via :func:`speech_aware_evidence_acquisition.core.config
.compose` and :func:`speech_aware_evidence_acquisition.core.config.protocol_hash`.
Master moves between a cell's registration and its launch: a merge that touches
any of the five pinned files breaks the prepared artifact's identity
(``core.preparation.PreparationError: prepared artifact identity mismatch``), and
any change to a cell's config fragments -- including its own readiness block,
since ``compose()`` hashes the complete merged fragment set -- shifts the
composed config hash and, with it, the protocol hash and every document that
quotes them.

This module is the reviewed, tested replacement for doing that by hand (as the
2026-09-17 SLURP B0 review-off re-pin, commit ``72204ced``, did): it re-runs the
model-free ``prepare-supply`` step only when the prepared artifact would
actually mismatch, re-pins the new artifact into the baseline fragment and the
experiment's preparation readiness requirement, optionally applies a decision
readiness requirement and flips ``readiness.state`` to ``ready``, recomputes the
composed/protocol hashes and rewrites every dependent hash (the protocol
document, every plan file, the README, the preregistration note, and the
exposure-ledger notes for the package's run ids) in dependency order, then runs
``core.flight.cli check`` for every cell and asserts the runtime-derived hashes
agree.

Every step is model-free: the only contacts this module makes are the
:func:`default_prepare_supply` (``core.flight.cli prepare-supply``, itself
zero-model-contact) and :func:`default_run_check` (``core.flight.cli check``)
calls, both of which are dependency-injected so tests can exercise the
orchestration logic (hash rewriting, refusals, readiness edits) against a
synthetic package without touching a real carrier, model, or registered
package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import compose, protocol_hash as compute_protocol_hash
from .campaign import CampaignCell, CampaignError, load_campaign_cells

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^phase-supply-v(\d+)\.json$")
_PROTOCOL_DOCUMENT_SHA_PATTERN = re.compile(
    r'"protocol_document"\s*:\s*\{[^{}]*?"sha256"\s*:\s*"([0-9a-f]{64})"'
)
_PLAN_SHA_PATTERN = re.compile(r"Plan SHA256 ([0-9a-f]{64})")

_LEDGER_HEADER_RUN = "run/experiment id"
_LEDGER_HEADER_CONSUMED = "consumed"
_LEDGER_HEADER_ARTIFACTS = "artifacts"
_LEDGER_HEADER_NOTES = "notes"

_PROTOCOL_DOCUMENT_NAME = "protocol-registered-v1.json"


class RepinError(RuntimeError):
    """Refuse an inconsistent, unsafe, or incomplete re-pin request."""


@dataclass(frozen=True)
class ArtifactPin:
    """One ``{relpath, sha256}`` prepared-artifact pin."""

    relpath: str
    sha256: str

    @classmethod
    def from_mapping(cls, value: object) -> "ArtifactPin":
        if (
            not isinstance(value, Mapping)
            or set(value) != {"relpath", "sha256"}
            or not isinstance(value["relpath"], str)
            or not value["relpath"]
            or not isinstance(value["sha256"], str)
            or SHA256_PATTERN.fullmatch(value["sha256"]) is None
        ):
            raise RepinError(f"malformed artifact pin: {value!r}")
        return cls(value["relpath"], value["sha256"])

    def as_dict(self) -> dict[str, str]:
        return {"relpath": self.relpath, "sha256": self.sha256}


@dataclass(frozen=True)
class CellIdentity:
    """Everything derived from composing one registered cell's four fragments."""

    experiment: str
    cell_id: str
    run_id: str
    attempt_id: str
    model_fragment: str
    dataset_fragment: str
    baseline_fragment: str
    carrier_lock_key: str
    arm: str
    split_identity_hash: str
    config_hash: str
    protocol_hash: str
    prepared_phase_supply: ArtifactPin | None


PrepareSupplyFn = Callable[..., Mapping[str, object]]
RunCheckFn = Callable[..., Mapping[str, object]]


# --------------------------------------------------------------------------
# Config fragment paths and structural edits.
# --------------------------------------------------------------------------


def baseline_fragment_path(repo_root: Path, name: str) -> Path:
    return Path(repo_root) / "configs" / "baseline" / f"{name}.json"


def experiment_fragment_path(repo_root: Path, name: str) -> Path:
    return Path(repo_root) / "configs" / "experiment" / f"{name}.json"


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RepinError(f"cannot read {path}: {error}") from error


def _write_json(path: Path, document: object) -> None:
    path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def resolve_split_identity_hash(
    composed_values: Mapping[str, object], carrier_lock_key: str
) -> str:
    """Read the cell's split identity from its own composed ``population`` block.

    Never a hand-typed constant: the declared ``population.split_identity_hash``
    is cross-checked, when the fragment inlines ``populations[*].ids``, against a
    fresh hash over those same ids (:func:`speech_aware_evidence_acquisition.data
    .splits.split_identity_hash`), so a mismatch between the declared value and
    the roster it claims to summarize is refused rather than silently trusted.
    """

    population = composed_values.get("population")
    if not isinstance(population, Mapping) or not isinstance(
        population.get("split_identity_hash"), str
    ):
        raise RepinError(
            "composed experiment fragment has no population.split_identity_hash"
        )
    declared = population["split_identity_hash"]
    if SHA256_PATTERN.fullmatch(declared) is None:
        raise RepinError(
            f"population.split_identity_hash is not a lowercase 64-hex SHA-256: {declared!r}"
        )
    populations = composed_values.get("populations")
    ids: list[str] = []
    if isinstance(populations, list):
        for entry in populations:
            if isinstance(entry, Mapping) and isinstance(entry.get("ids"), list):
                ids.extend(str(item) for item in entry["ids"])
    if ids:
        from ...data.splits import prefixed, split_identity_hash as _compute

        recomputed = _compute(prefixed(carrier_lock_key, ids))
        if recomputed != declared:
            raise RepinError(
                "population.split_identity_hash does not match a fresh hash over "
                f"populations[*].ids: declared {declared!r}, recomputed {recomputed!r}"
            )
    return declared


def compute_cell_identity(repo_root: Path, experiment: str, cell: CampaignCell) -> CellIdentity:
    """Compose one cell's four fragments exactly as ``core.flight.cli`` does."""

    document = cell.document
    model = str(document["model_fragment"])
    dataset = str(document["dataset_fragment"])
    baseline = str(document["baseline_fragment"])
    composed = compose(Path(repo_root), model, dataset, baseline, experiment)
    values = composed.values
    carrier_lock_key = values.get("carrier_lock_key")
    if not isinstance(carrier_lock_key, str) or not carrier_lock_key:
        raise RepinError(f"composed cell {cell.document['cell_id']!r} has no carrier_lock_key")
    arm = values.get("arm")
    if not isinstance(arm, str) or not arm:
        raise RepinError(f"composed cell {cell.document['cell_id']!r} has no arm")
    split_identity_hash = resolve_split_identity_hash(values, carrier_lock_key)
    phash = compute_protocol_hash(composed.config_hash, arm, split_identity_hash)
    pin = values.get("prepared_phase_supply")
    return CellIdentity(
        experiment=experiment,
        cell_id=str(document["cell_id"]),
        run_id=cell.run_id,
        attempt_id=cell.attempt_id,
        model_fragment=model,
        dataset_fragment=dataset,
        baseline_fragment=baseline,
        carrier_lock_key=carrier_lock_key,
        arm=arm,
        split_identity_hash=split_identity_hash,
        config_hash=composed.config_hash,
        protocol_hash=phash,
        prepared_phase_supply=(ArtifactPin.from_mapping(pin) if pin is not None else None),
    )


def _next_artifact_version(directory: Path) -> int:
    if not directory.is_dir():
        return 1
    versions = [
        int(match.group(1))
        for path in directory.iterdir()
        if (match := _VERSION_PATTERN.match(path.name))
    ]
    return max(versions) + 1 if versions else 1


def _phase_supply_row_counts(output: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    if isinstance(output, Mapping):
        for key in ("facets", "values"):
            phases = output.get(key)
            total = 0
            if isinstance(phases, Mapping):
                for rows in phases.values():
                    if isinstance(rows, Mapping):
                        total += len(rows)
            counts[key] = total
    return counts


def _compare_artifact_output(
    *, old_path: Path | None, new_path: Path, allow_output_change: bool
) -> dict[str, object] | None:
    if old_path is None or not old_path.is_file():
        return None
    old_document = _read_json(old_path)
    new_document = _read_json(new_path)
    old_output = old_document.get("output") if isinstance(old_document, Mapping) else None
    new_output = new_document.get("output") if isinstance(new_document, Mapping) else None
    counts = {"old": _phase_supply_row_counts(old_output), "new": _phase_supply_row_counts(new_output)}
    if old_output != new_output and not allow_output_change:
        raise RepinError(
            "rebuilt phase-supply artifact selects a different output than the "
            f"previous artifact ({old_path}); row counts old={counts['old']} "
            f"new={counts['new']}; pass --allow-output-change to accept this deliberately"
        )
    return counts


# --------------------------------------------------------------------------
# Default (real) prepare-supply and check integrations. Both are
# dependency-injected so tests never need a real carrier/model/lock.
# --------------------------------------------------------------------------


def default_prepare_supply(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiment: str,
    cell_id: str,
    model_fragment: str,
    dataset_fragment: str,
    baseline_fragment: str,
    run_id: str,
    attempt_id: str,
    output_path: Path,
) -> Mapping[str, object]:
    """Run the real, model-free ``core.flight.cli prepare-supply`` path.

    Called with an EXISTING ``output_path`` this is a pure identity check
    (``FlightRuntime.prepare_phase_supply`` takes the warm-artifact branch,
    which never re-derives the selection): it raises
    ``core.preparation.PreparationError`` iff the artifact at that path no
    longer matches the current rails/config identity. Called with a path that
    does not yet exist, it actually derives and publishes a fresh artifact --
    the caller is responsible for having dropped any stale
    ``prepared_phase_supply`` pin from the baseline fragment first, since
    ``FlightRuntime._phase_supply_seeds`` only recomputes from scratch when no
    pin is configured.
    """

    from .factory import build_flight_runtime

    runtime = build_flight_runtime(
        repo_root,
        data_root,
        model=model_fragment,
        dataset=dataset_fragment,
        baseline=baseline_fragment,
        experiment=experiment,
        run_id=run_id,
        attempt_id=attempt_id,
        runtime_root=runtime_root,
        lock_path=lock_path,
    )
    return runtime.prepare_phase_supply(Path(output_path))


def default_run_check(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiment: str,
    cell_id: str,
    python: str,
) -> Mapping[str, object]:
    """Invoke ``core.flight.cli check`` for one cell out-of-process."""

    import os

    command = [
        python,
        "-B",
        "-m",
        "speech_aware_evidence_acquisition.core.flight.cli",
        "check",
        "--repo-root",
        str(repo_root),
        "--data-root",
        str(data_root),
        "--runtime-root",
        str(runtime_root),
        "--lock-path",
        str(lock_path),
        "--experiment",
        experiment,
        "--cell",
        cell_id,
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(Path(repo_root) / "src")
    completed = subprocess.run(
        command, cwd=str(repo_root), capture_output=True, text=True, check=False, env=env
    )
    if completed.returncode != 0:
        raise RepinError(
            f"core.flight.cli check failed for {experiment}/{cell_id}: exit "
            f"{completed.returncode}\nstdout: {completed.stdout}\nstderr: {completed.stderr}"
        )
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RepinError(
            f"core.flight.cli check for {experiment}/{cell_id} produced non-JSON stdout: {error}"
        ) from error


# --------------------------------------------------------------------------
# Step 1: ensure the prepared phase-supply artifact is pinned and current.
# --------------------------------------------------------------------------


def _drop_prepared_phase_supply(baseline_path: Path) -> None:
    document = _read_json(baseline_path)
    if not isinstance(document, dict):
        raise RepinError(f"baseline fragment {baseline_path} is not a JSON object")
    document.pop("prepared_phase_supply", None)
    _write_json(baseline_path, document)


def _set_prepared_phase_supply(baseline_path: Path, pin: ArtifactPin) -> None:
    document = _read_json(baseline_path)
    if not isinstance(document, dict):
        raise RepinError(f"baseline fragment {baseline_path} is not a JSON object")
    document["prepared_phase_supply"] = pin.as_dict()
    _write_json(baseline_path, document)


def _set_preparation_requirement(experiment_path: Path, *, cell_id: str, pin: ArtifactPin) -> None:
    document = _read_json(experiment_path)
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise RepinError(f"experiment fragment {experiment_path} has no cells list")
    found = False
    for cell_doc in document["cells"]:
        if not isinstance(cell_doc, Mapping) or cell_doc.get("cell_id") != cell_id:
            continue
        readiness = cell_doc.get("readiness")
        requirements = readiness.get("requirements") if isinstance(readiness, Mapping) else None
        if not isinstance(requirements, list):
            continue
        for entry in requirements:
            if isinstance(entry, dict) and entry.get("kind") == "preparation":
                entry["relpath"] = pin.relpath
                entry["sha256"] = pin.sha256
                found = True
    if not found:
        # A package registered before its supply could be prepared (the B1
        # exemplar cells, blocked by the E3 router guard) carries an empty
        # requirements list; the first successful preparation creates the
        # requirement instead of refusing, so the tool completes such a
        # registration rather than demanding a hand edit.
        for cell_doc in document["cells"]:
            if not isinstance(cell_doc, Mapping) or cell_doc.get("cell_id") != cell_id:
                continue
            readiness = cell_doc.get("readiness")
            if not isinstance(readiness, dict):
                continue
            requirements = readiness.setdefault("requirements", [])
            if isinstance(requirements, list):
                requirements.append({
                    "kind": "preparation",
                    "relpath": pin.relpath,
                    "sha256": pin.sha256,
                    "reason": "Model-free first-phase supply prepared by core.flight.repin on the launch commit; zero model, tokenizer or encoder contact.",
                })
                found = True
    if not found:
        raise RepinError(
            f"cell {cell_id!r} in {experiment_path} has no readiness block to carry a 'preparation' requirement"
        )
    _write_json(experiment_path, document)


def ensure_artifact_pinned(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiment: str,
    identity: CellIdentity,
    prepare_supply_fn: PrepareSupplyFn,
    allow_output_change: bool,
) -> dict[str, object]:
    """Re-run ``prepare-supply`` only if the pinned artifact would mismatch.

    Verifies the current pin first (a warm-artifact identity check, no writes):
    if it still matches, nothing is touched. Otherwise the stale pin is dropped
    from the baseline fragment (transiently -- restored verbatim on any
    failure), a fresh artifact is derived into a NEW, never-overwritten
    ``phase-supply-v<N+1>.json``, its ``output`` is asserted equal to the
    previous artifact's ``output`` when one exists, and only then is the new
    pin written into both the baseline fragment and the experiment's
    'preparation' readiness requirement.
    """

    baseline_path = baseline_fragment_path(repo_root, identity.baseline_fragment)
    experiment_path = experiment_fragment_path(repo_root, experiment)
    current_pin = identity.prepared_phase_supply
    existing_absolute: Path | None = None
    needs_rebuild = current_pin is None
    mismatch_reason = "no prepared_phase_supply pin is currently configured"
    if current_pin is not None:
        existing_absolute = (Path(data_root) / current_pin.relpath).resolve()
        if not existing_absolute.is_file():
            needs_rebuild = True
            mismatch_reason = f"pinned artifact is absent on disk: {current_pin.relpath}"
        else:
            try:
                prepare_supply_fn(
                    repo_root=repo_root,
                    data_root=data_root,
                    runtime_root=runtime_root,
                    lock_path=lock_path,
                    experiment=experiment,
                    cell_id=identity.cell_id,
                    model_fragment=identity.model_fragment,
                    dataset_fragment=identity.dataset_fragment,
                    baseline_fragment=identity.baseline_fragment,
                    run_id=identity.run_id,
                    attempt_id=identity.attempt_id,
                    output_path=existing_absolute,
                )
            except Exception as error:  # noqa: BLE001 -- any failure means the pin cannot be trusted
                needs_rebuild = True
                mismatch_reason = str(error)

    if not needs_rebuild:
        assert current_pin is not None
        return {"rebuilt": False, "pin": current_pin.as_dict()}

    directory = Path(data_root) / "prepared" / identity.run_id
    version = _next_artifact_version(directory)
    new_relpath = f"prepared/{identity.run_id}/phase-supply-v{version}.json"
    new_absolute = Path(data_root) / new_relpath
    if new_absolute.exists():
        raise RepinError(f"refusing to overwrite an existing artifact at {new_relpath}")

    original_baseline_text = baseline_path.read_text(encoding="utf-8")
    _drop_prepared_phase_supply(baseline_path)
    try:
        receipt = prepare_supply_fn(
            repo_root=repo_root,
            data_root=data_root,
            runtime_root=runtime_root,
            lock_path=lock_path,
            experiment=experiment,
            cell_id=identity.cell_id,
            model_fragment=identity.model_fragment,
            dataset_fragment=identity.dataset_fragment,
            baseline_fragment=identity.baseline_fragment,
            run_id=identity.run_id,
            attempt_id=identity.attempt_id,
            output_path=new_absolute,
        )
    except Exception:
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        raise
    new_sha256 = receipt.get("sha256") if isinstance(receipt, Mapping) else None
    if not isinstance(new_sha256, str) or SHA256_PATTERN.fullmatch(new_sha256) is None:
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        raise RepinError(f"prepare_supply_fn returned no valid sha256 for {new_relpath}")

    try:
        row_counts = _compare_artifact_output(
            old_path=existing_absolute, new_path=new_absolute, allow_output_change=allow_output_change
        )
    except RepinError:
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        raise

    new_pin = ArtifactPin(new_relpath, new_sha256)
    _set_prepared_phase_supply(baseline_path, new_pin)
    _set_preparation_requirement(experiment_path, cell_id=identity.cell_id, pin=new_pin)
    return {
        "rebuilt": True,
        "reason": mismatch_reason,
        "old_pin": current_pin.as_dict() if current_pin is not None else None,
        "new_pin": new_pin.as_dict(),
        "row_counts": row_counts,
    }


# --------------------------------------------------------------------------
# Step 2: decision readiness requirement and the ready flip.
# --------------------------------------------------------------------------


def _upsert_decision_requirement(
    readiness: dict, *, decision_id: str, relpath: str, sha256: str
) -> bool:
    requirements = readiness.setdefault("requirements", [])
    for entry in requirements:
        if (
            isinstance(entry, dict)
            and entry.get("kind") == "decision"
            and entry.get("expected_decision_id") == decision_id
        ):
            changed = entry.get("relpath") != relpath or entry.get("sha256") != sha256
            entry["relpath"] = relpath
            entry["sha256"] = sha256
            entry.setdefault("reason", f"Decision {decision_id} pinned by scripts/flights/repin_cell.py.")
            return changed
    requirements.insert(
        0,
        {
            "kind": "decision",
            "expected_decision_id": decision_id,
            "relpath": relpath,
            "sha256": sha256,
            "reason": f"Decision {decision_id} pinned by scripts/flights/repin_cell.py.",
        },
    )
    return True


def _set_ready(readiness: dict) -> bool:
    changed = readiness.get("state") != "ready"
    readiness["state"] = "ready"
    return changed


def apply_decision_and_readiness(
    *,
    repo_root: Path,
    data_root: Path,
    experiment: str,
    cell_id: str,
    decision: tuple[str, str] | None,
    set_ready: bool,
) -> bool:
    """Insert/update the decision requirement and/or flip readiness to ready."""

    if decision is None and not set_ready:
        return False
    experiment_path = experiment_fragment_path(repo_root, experiment)
    document = _read_json(experiment_path)
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise RepinError(f"experiment fragment {experiment_path} has no cells list")
    changed = False
    found = False
    for cell_doc in document["cells"]:
        if not isinstance(cell_doc, dict) or cell_doc.get("cell_id") != cell_id:
            continue
        found = True
        readiness = cell_doc.setdefault("readiness", {})
        if decision is not None:
            relpath, decision_id = decision
            decision_file = Path(data_root) / relpath
            if not decision_file.is_file():
                raise RepinError(f"decision receipt not found under data root: {relpath}")
            sha256 = hashlib.sha256(decision_file.read_bytes()).hexdigest()
            changed = (
                _upsert_decision_requirement(readiness, decision_id=decision_id, relpath=relpath, sha256=sha256)
                or changed
            )
        if set_ready:
            changed = _set_ready(readiness) or changed
    if not found:
        raise RepinError(f"cell {cell_id!r} not declared by experiment {experiment!r}")
    if changed:
        _write_json(experiment_path, document)
    return changed


# --------------------------------------------------------------------------
# Step 3: hash rewriting, in dependency order, plus the residue check.
# --------------------------------------------------------------------------


def _split_row_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if len(stripped) < 2 or not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_separator_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(not cell.strip("-: ") for cell in cells)


def apply_mapping_to_text(path: Path, mapping: Mapping[str, str]) -> int:
    """Replace every OLD->NEW pair in ``mapping`` across ``path``'s whole text.

    Returns the number of individual substring occurrences replaced.
    """

    if not mapping or not path.is_file():
        return 0
    text = path.read_text(encoding="utf-8")
    updated = text
    replaced = 0
    for old, new in mapping.items():
        if not old or old == new:
            continue
        occurrences = updated.count(old)
        if occurrences:
            updated = updated.replace(old, new)
            replaced += occurrences
    if updated != text:
        path.write_text(updated, encoding="utf-8", newline="\n")
    return replaced


def apply_mapping_to_files(paths: Iterable[Path], mapping: Mapping[str, str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for path in paths:
        count = apply_mapping_to_text(path, mapping)
        if count:
            result[str(path)] = count
    return result


def rewrite_ledger_notes(text: str, *, run_ids: set[str], mapping: Mapping[str, str]) -> tuple[str, int]:
    """Apply ``mapping`` to the ``notes`` cell only, of rows naming ``run_ids``.

    Ledger rows are recognized the same way as
    :func:`speech_aware_evidence_acquisition.contracts.ledger._parse_ledger_tables`
    (a table row immediately followed by a GFM separator row opens a header;
    the run/experiment id column identifies the contract table); this focused
    editor never rewrites any other column, and never any row outside
    ``run_ids``.
    """

    if not mapping:
        return text, 0
    lines = text.splitlines(keepends=True)
    n = len(lines)
    header: list[str] | None = None
    out: list[str] = []
    changed = 0
    i = 0
    while i < n:
        line = lines[i]
        cells = _split_row_cells(line)
        if cells is not None:
            next_cells = _split_row_cells(lines[i + 1]) if i + 1 < n else None
            if next_cells is not None and _is_separator_row(next_cells):
                lowered = [cell.lower() for cell in cells]
                header = lowered if _LEDGER_HEADER_RUN in lowered else None
                out.append(line)
                out.append(lines[i + 1])
                i += 2
                continue
            if header is not None and len(cells) == len(header):
                run_col = header.index(_LEDGER_HEADER_RUN)
                if _LEDGER_HEADER_NOTES in header and cells[run_col] in run_ids:
                    notes_col = header.index(_LEDGER_HEADER_NOTES)
                    new_notes = cells[notes_col]
                    for old, new in mapping.items():
                        if old and old != new:
                            new_notes = new_notes.replace(old, new)
                    if new_notes != cells[notes_col]:
                        changed += 1
                        new_cells = list(cells)
                        new_cells[notes_col] = new_notes
                        newline = "\n" if line.endswith("\n") else ""
                        out.append("| " + " | ".join(new_cells) + " |" + newline)
                        i += 1
                        continue
        out.append(line)
        i += 1
    return "".join(out), changed


def _foreign_ledger_row_mask(text: str, run_ids: set[str]) -> list[bool]:
    """One flag per line of ``text``: True when the line is a contract-table
    ROW whose run id is NOT in ``run_ids`` -- a row this re-pin must never
    touch, whatever hash it carries."""

    lines = text.splitlines(keepends=True)
    mask = [False] * len(lines)
    header: list[str] | None = None
    i = 0
    while i < len(lines):
        cells = _split_row_cells(lines[i])
        if cells is not None:
            next_cells = _split_row_cells(lines[i + 1]) if i + 1 < len(lines) else None
            if next_cells is not None and _is_separator_row(next_cells):
                lowered = [cell.lower() for cell in cells]
                header = lowered if _LEDGER_HEADER_RUN in lowered else None
                i += 2
                continue
            if header is not None and len(cells) == len(header):
                run_col = header.index(_LEDGER_HEADER_RUN)
                if cells[run_col] not in run_ids:
                    mask[i] = True
        i += 1
    return mask


def apply_mapping_to_ledger(ledger_path: Path, run_ids: set[str], mapping: Mapping[str, str]) -> int:
    """Rewrite the package's registration hashes in the ledger -- in its OWN
    rows and in the prose that introduces them, never in another row.

    A registration package writes its composed/protocol/plan hashes into the
    notes cells of its rows AND into the prose section that introduces them.
    Both are pre-contact registration text of an unflown package (the caller
    has already refused if any package row is consumed). A package DERIVED
    from a sealed package carries the parent's hashes until it is re-pinned,
    so a whole-file replace would also rewrite the PARENT's closed rows: that
    is exactly what happened to the B1r, B1-notool and B2 v3 rows before
    2026-09-21 (repaired at 35c4cc18). The second pass therefore skips every
    contract-table row whose run id is outside ``run_ids``; the notes-only
    pass runs first so its per-row change count is still reported.
    """
    text = ledger_path.read_text(encoding="utf-8")
    updated, changed = rewrite_ledger_notes(text, run_ids=run_ids, mapping=mapping)
    lines = updated.splitlines(keepends=True)
    foreign = _foreign_ledger_row_mask(updated, run_ids)
    for index, line in enumerate(lines):
        if foreign[index]:
            continue
        new_line = line
        for old, new in mapping.items():
            if old and old != new and old in new_line:
                changed += new_line.count(old)
                new_line = new_line.replace(old, new)
        lines[index] = new_line
    updated = "".join(lines)
    if updated != text:
        ledger_path.write_text(updated, encoding="utf-8", newline="\n")
    return changed


def _resolve_ledger_artifacts(ledger_text: str, run_ids: set[str]) -> dict[str, str]:
    from ...contracts.ledger import _parse_ledger_tables

    rows = _parse_ledger_tables(ledger_text)
    result: dict[str, str] = {}
    for row in rows:
        run_id = row.get(_LEDGER_HEADER_RUN)
        if run_id in run_ids and row.get(_LEDGER_HEADER_ARTIFACTS):
            result[run_id] = row[_LEDGER_HEADER_ARTIFACTS]
    missing = run_ids - set(result)
    if missing:
        raise RepinError(f"exposure ledger has no 'artifacts' entry for run ids: {sorted(missing)}")
    return result


def _collect_plan_hashes_from_notes(ledger_text: str, run_ids: set[str]) -> dict[str, str]:
    from ...contracts.ledger import _parse_ledger_tables

    rows = _parse_ledger_tables(ledger_text)
    result: dict[str, str] = {}
    for row in rows:
        run_id = row.get(_LEDGER_HEADER_RUN)
        if run_id not in run_ids:
            continue
        match = _PLAN_SHA_PATTERN.search(row.get(_LEDGER_HEADER_NOTES, ""))
        if match:
            result[run_id] = match.group(1)
    return result


def _collect_protocol_document_hashes(package_files: Sequence[Path], protocol_document_path: Path) -> set[str]:
    hashes: set[str] = set()
    for path in package_files:
        if path == protocol_document_path or path.suffix != ".json" or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        hashes.update(match.group(1) for match in _PROTOCOL_DOCUMENT_SHA_PATTERN.finditer(text))
    return hashes


def rewrite_dependent_hashes(
    *,
    repo_root: Path,
    readiness_dir: Path,
    preregistration_path: Path,
    exposure_ledger_path: Path,
    run_ids: set[str],
    mapping: Mapping[str, str],
) -> dict[str, int]:
    """Round 1 (config/protocol/artifact hashes), round 2 (protocol document
    sha256) and round 3 (registered plan sha256s), each depending on the
    previous round's rewritten bytes, applied across the package files and the
    exposure-ledger notes for ``run_ids``."""

    package_files = sorted(set(readiness_dir.glob("*.json")) | {preregistration_path})
    readme_path = readiness_dir / "README.md"
    if readme_path.is_file():
        package_files.append(readme_path)
    protocol_document_path = readiness_dir / _PROTOCOL_DOCUMENT_NAME

    rewritten: dict[str, int] = {}

    def _merge(update: Mapping[str, int]) -> None:
        for key, value in update.items():
            rewritten[key] = rewritten.get(key, 0) + value

    def _ledger(round_mapping: Mapping[str, str]) -> None:
        if not round_mapping:
            return
        count = apply_mapping_to_ledger(exposure_ledger_path, run_ids, round_mapping)
        if count:
            rewritten[str(exposure_ledger_path)] = rewritten.get(str(exposure_ledger_path), 0) + count

    # Round 1: composed/protocol hashes and artifact relpath/sha256.
    _merge(apply_mapping_to_files(package_files, mapping))
    _ledger(mapping)

    # Round 2: the protocol document's own sha256, referenced from every plan.
    if protocol_document_path.is_file():
        old_doc_hashes = _collect_protocol_document_hashes(package_files, protocol_document_path)
        new_doc_hash = hashlib.sha256(protocol_document_path.read_bytes()).hexdigest()
        doc_mapping = {old: new_doc_hash for old in old_doc_hashes if old and old != new_doc_hash}
        if doc_mapping:
            _merge(apply_mapping_to_files(package_files, doc_mapping))
            _ledger(doc_mapping)

    # Round 3: each registered plan's own sha256, resolved from the ledger's
    # own 'artifacts' column and referenced only from the ledger's notes.
    ledger_text = exposure_ledger_path.read_text(encoding="utf-8")
    artifacts_by_run = _resolve_ledger_artifacts(ledger_text, run_ids)
    old_plan_hashes = _collect_plan_hashes_from_notes(ledger_text, run_ids)
    plan_mapping: dict[str, str] = {}
    for run_id, relpath in artifacts_by_run.items():
        plan_path = Path(repo_root) / relpath
        if not plan_path.is_file():
            raise RepinError(f"exposure ledger artifact for {run_id} not found: {relpath}")
        new_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        old_hash = old_plan_hashes.get(run_id)
        if old_hash and old_hash != new_hash:
            plan_mapping[old_hash] = new_hash
    _ledger(plan_mapping)

    return rewritten


def assert_no_residue(
    repo_root: Path,
    old_values: Iterable[str],
    *,
    exposure_ledger_path: Path | None = None,
    run_ids: set[str] | None = None,
) -> None:
    """Refuse if any OLD hash string remains anywhere under ``docs/`` or
    ``configs/`` after rewriting.

    An OLD hash that lives in an exposure-ledger row OUTSIDE ``run_ids`` is
    not residue: it is another package's own registration (the sealed parent
    this package was derived from), and this re-pin neither rewrites it
    (:func:`apply_mapping_to_ledger`) nor may it demand that it disappear.
    """

    values = sorted({value for value in old_values if value})
    if not values:
        return
    ledger_resolved = Path(exposure_ledger_path).resolve() if exposure_ledger_path else None
    hits: list[str] = []
    for root_name in ("docs", "configs"):
        base = Path(repo_root) / root_name
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if ledger_resolved is not None and run_ids is not None and path.resolve() == ledger_resolved:
                lines = text.splitlines(keepends=True)
                foreign = _foreign_ledger_row_mask(text, run_ids)
                text = "".join(line for index, line in enumerate(lines) if not foreign[index])
            for value in values:
                if value in text:
                    hits.append(f"{path}: {value}")
    if hits:
        raise RepinError("old hash residue remains after rewriting:\n" + "\n".join(hits))


# --------------------------------------------------------------------------
# Pre-flight refusals: dirty tree and consumed exposure rows.
# --------------------------------------------------------------------------


def assert_clean_tree(repo_root: Path, expected_touched: Iterable[Path]) -> None:
    """Refuse if the tree has tracked modifications outside ``expected_touched``."""

    completed = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=True,
    )
    root = Path(repo_root).resolve()
    expected = {str(Path(path).resolve().relative_to(root)).replace("\\", "/") for path in expected_touched}
    offenders = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        relative = line[3:].strip()
        if " -> " in relative:
            relative = relative.split(" -> ", 1)[1]
        relative = relative.strip('"')
        if relative.replace("\\", "/") not in expected:
            offenders.append(line)
    if offenders:
        raise RepinError(
            "refusing to run: the working tree has tracked modifications outside "
            "the files this tool rewrites:\n" + "\n".join(offenders)
        )


def assert_rows_available(ledger_text: str, run_ids: set[str]) -> None:
    """Refuse if any target run id's exposure row is missing or already consumed."""

    from ...contracts.ledger import _parse_ledger_tables

    rows = _parse_ledger_tables(ledger_text)
    seen: set[str] = set()
    for row in rows:
        run_id = row.get(_LEDGER_HEADER_RUN)
        if run_id in run_ids:
            seen.add(run_id)
            if row.get(_LEDGER_HEADER_CONSUMED, "").strip().lower() == "yes":
                raise RepinError(
                    f"exposure ledger row {run_id!r} is already consumed = yes; refusing to re-pin"
                )
    missing = run_ids - seen
    if missing:
        raise RepinError(f"exposure ledger has no row for run ids: {sorted(missing)}")


def assert_current_pins_present(
    package_files: Sequence[Path], identity: CellIdentity
) -> None:
    """'Verifies the current pins': the freshly composed old hashes must
    already appear somewhere in the package before this tool starts rewriting,
    or the tool cannot safely know what to replace."""

    found_config = found_protocol = False
    for path in package_files:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found_config = found_config or identity.config_hash in text
        found_protocol = found_protocol or identity.protocol_hash in text
        if found_config and found_protocol:
            return
    raise RepinError(
        f"cell {identity.cell_id!r}: neither its freshly composed config_hash "
        f"({identity.config_hash}) nor protocol_hash ({identity.protocol_hash}) "
        "appears anywhere in the package files; refusing to guess what to rewrite"
    )


# --------------------------------------------------------------------------
# Top-level orchestration.
# --------------------------------------------------------------------------


def _resolve_under_repo(repo_root: Path, value: Path) -> Path:
    value = Path(value)
    return value if value.is_absolute() else Path(repo_root) / value


def _package_files_for(readiness_dir: Path, preregistration_path: Path) -> list[Path]:
    files = sorted(set(readiness_dir.glob("*.json")) | {preregistration_path})
    readme_path = readiness_dir / "README.md"
    if readme_path.is_file():
        files.append(readme_path)
    return files


def repin_package(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiments: Sequence[tuple[str, str | None]],
    readiness_dir: Path,
    preregistration_path: Path,
    exposure_ledger_path: Path | None = None,
    decision: tuple[str, str] | None = None,
    set_ready: bool = False,
    allow_output_change: bool = False,
    prepare_supply_fn: PrepareSupplyFn = default_prepare_supply,
    run_check_fn: RunCheckFn = default_run_check,
    python: str = sys.executable,
    package_name: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, object]:
    """Re-pin every cell named by ``experiments`` and rewrite its package.

    ``experiments`` is a sequence of ``(experiment_id, cell_id_or_None)`` pairs;
    ``cell_id_or_None`` selects a single cell out of that experiment's declared
    cells, or every declared cell when ``None``.
    """

    repo_root = Path(repo_root)
    data_root = Path(data_root)
    runtime_root = Path(runtime_root)
    lock_path = Path(lock_path)
    readiness_dir = _resolve_under_repo(repo_root, Path(readiness_dir))
    preregistration_path = _resolve_under_repo(repo_root, Path(preregistration_path))
    exposure_ledger_path = (
        _resolve_under_repo(repo_root, Path(exposure_ledger_path))
        if exposure_ledger_path is not None
        else repo_root / "docs" / "exposure-ledger.md"
    )
    if not readiness_dir.is_dir():
        raise RepinError(f"readiness dir does not exist: {readiness_dir}")
    if not preregistration_path.is_file():
        raise RepinError(f"preregistration file does not exist: {preregistration_path}")
    if not exposure_ledger_path.is_file():
        raise RepinError(f"exposure ledger not found: {exposure_ledger_path}")

    resolved: list[tuple[str, CampaignCell]] = []
    for experiment, cell_filter in experiments:
        try:
            cells = load_campaign_cells(repo_root, experiment)
        except CampaignError as error:
            raise RepinError(f"cannot load experiment {experiment!r}: {error}") from error
        if cell_filter is not None:
            cells = tuple(cell for cell in cells if cell.document["cell_id"] == cell_filter)
            if not cells:
                raise RepinError(f"cell {cell_filter!r} is not declared by experiment {experiment!r}")
        resolved.extend((experiment, cell) for cell in cells)
    if not resolved:
        raise RepinError("no cells resolved from the given experiment/cell selection")
    run_ids = {cell.run_id for _experiment, cell in resolved}
    if len(run_ids) != len(resolved):
        raise RepinError("duplicate run_id across the selected cells")

    package_name = package_name or readiness_dir.name

    baseline_paths = {
        baseline_fragment_path(repo_root, cell.document["baseline_fragment"]) for _e, cell in resolved
    }
    experiment_paths = {experiment_fragment_path(repo_root, experiment) for experiment, _c in resolved}
    package_files = _package_files_for(readiness_dir, preregistration_path)
    expected_touched = set(baseline_paths) | set(experiment_paths) | set(package_files) | {exposure_ledger_path}
    assert_clean_tree(repo_root, expected_touched)

    ledger_text = exposure_ledger_path.read_text(encoding="utf-8")
    assert_rows_available(ledger_text, run_ids)

    old_identities: dict[str, CellIdentity] = {}
    for experiment, cell in resolved:
        identity = compute_cell_identity(repo_root, experiment, cell)
        assert_current_pins_present(package_files, identity)
        old_identities[cell.run_id] = identity

    cell_reports: list[dict[str, object]] = []
    mapping: dict[str, str] = {}
    all_old_values: set[str] = set()
    new_identities: dict[str, CellIdentity] = {}
    for experiment, cell in resolved:
        old_identity = old_identities[cell.run_id]
        artifact_report = ensure_artifact_pinned(
            repo_root=repo_root,
            data_root=data_root,
            runtime_root=runtime_root,
            lock_path=lock_path,
            experiment=experiment,
            identity=old_identity,
            prepare_supply_fn=prepare_supply_fn,
            allow_output_change=allow_output_change,
        )
        apply_decision_and_readiness(
            repo_root=repo_root,
            data_root=data_root,
            experiment=experiment,
            cell_id=old_identity.cell_id,
            decision=decision,
            set_ready=set_ready,
        )
        new_identity = compute_cell_identity(repo_root, experiment, cell)
        new_identities[cell.run_id] = new_identity

        if artifact_report.get("rebuilt"):
            old_pin = artifact_report.get("old_pin")
            new_pin = artifact_report["new_pin"]
            if old_pin is not None:
                # Only a field that actually CHANGED counts as an old value to
                # rewrite/residue-check: a coincidentally identical relpath or
                # sha256 (e.g. a rebuilt artifact byte-identical to the stale
                # one) is not stale text left behind -- it is simply still
                # correct, and flagging it would be a false residue positive.
                if old_pin["relpath"] != new_pin["relpath"]:
                    mapping[old_pin["relpath"]] = new_pin["relpath"]
                    all_old_values.add(old_pin["relpath"])
                if old_pin["sha256"] != new_pin["sha256"]:
                    mapping[old_pin["sha256"]] = new_pin["sha256"]
                    all_old_values.add(old_pin["sha256"])
        if old_identity.config_hash != new_identity.config_hash:
            mapping[old_identity.config_hash] = new_identity.config_hash
            all_old_values.add(old_identity.config_hash)
        if old_identity.protocol_hash != new_identity.protocol_hash:
            mapping[old_identity.protocol_hash] = new_identity.protocol_hash
            all_old_values.add(old_identity.protocol_hash)

        cell_reports.append(
            {
                "experiment": experiment,
                "cell": old_identity.cell_id,
                "run_id": old_identity.run_id,
                "old": {"config_hash": old_identity.config_hash, "protocol_hash": old_identity.protocol_hash},
                "new": {"config_hash": new_identity.config_hash, "protocol_hash": new_identity.protocol_hash},
                "artifact": artifact_report,
            }
        )

    rewritten = rewrite_dependent_hashes(
        repo_root=repo_root,
        readiness_dir=readiness_dir,
        preregistration_path=preregistration_path,
        exposure_ledger_path=exposure_ledger_path,
        run_ids=run_ids,
        mapping=mapping,
    )
    assert_no_residue(
        repo_root,
        all_old_values,
        exposure_ledger_path=exposure_ledger_path,
        run_ids=run_ids,
    )

    check_reports = []
    if run_check_fn is not None:
        coordination_dir = Path(data_root) / "coordination" / package_name
        coordination_dir.mkdir(parents=True, exist_ok=True)
        timestamp = now().strftime("%Y%m%dT%H%M%SZ")
        for experiment, cell in resolved:
            identity = new_identities[cell.run_id]
            result = run_check_fn(
                repo_root=repo_root,
                data_root=data_root,
                runtime_root=runtime_root,
                lock_path=lock_path,
                experiment=experiment,
                cell_id=identity.cell_id,
                python=python,
            )
            receipt_path = coordination_dir / f"check-{identity.cell_id}-repin-{timestamp}.json"
            receipt_path.write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
            preflight = result.get("preflight") if isinstance(result, Mapping) else None
            measured_config = preflight.get("config_hash") if isinstance(preflight, Mapping) else None
            measured_protocol = preflight.get("protocol_hash") if isinstance(preflight, Mapping) else None
            if measured_config != identity.config_hash or measured_protocol != identity.protocol_hash:
                raise RepinError(
                    f"core.flight.cli check for {experiment}/{identity.cell_id} measured "
                    f"config_hash={measured_config!r} protocol_hash={measured_protocol!r}, "
                    f"expected {identity.config_hash!r} / {identity.protocol_hash!r}"
                )
            check_reports.append(
                {"experiment": experiment, "cell": identity.cell_id, "run_id": identity.run_id, "receipt": str(receipt_path)}
            )

    return {
        "schema": "saea-repin-summary-v1",
        "package": package_name,
        "readiness_dir": str(readiness_dir),
        "cells": cell_reports,
        "files_rewritten": rewritten,
        "checks": check_reports,
    }


# --------------------------------------------------------------------------
# CLI.
# --------------------------------------------------------------------------


class _RecordOrder(argparse.Action):
    """Append ``(dest, value)`` to a single shared list in CLI encounter order.

    Plain ``action='append'`` on two separate flags loses the interleaving
    needed to pair each ``--cell`` with the ``--experiment`` it immediately
    follows; this keeps that order so ``--experiment E1 --cell C1 --experiment
    E2`` pairs correctly regardless of how many pairs are given.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        ordered = getattr(namespace, "_ordered", None)
        if ordered is None:
            ordered = []
            namespace._ordered = ordered
        ordered.append((self.dest, values))


def _pair_experiments_and_cells(ordered: Sequence[tuple[str, str]]) -> list[tuple[str, str | None]]:
    pairs: list[tuple[str, str | None]] = []
    for kind, value in ordered:
        if kind == "experiment":
            pairs.append((value, None))
        elif kind == "cell":
            if not pairs:
                raise SystemExit("--cell must immediately follow an --experiment")
            experiment, existing = pairs[-1]
            if existing is not None:
                raise SystemExit(f"experiment {experiment!r} already has a --cell filter")
            pairs[-1] = (experiment, value)
    return pairs


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("repo-root", "data-root", "runtime-root", "lock-path"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--experiment", dest="experiment", action=_RecordOrder, required=True)
    parser.add_argument("--cell", dest="cell", action=_RecordOrder)
    parser.add_argument("--readiness-dir", required=True)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--decision", default=None, help="relpath under --data-root of a decision receipt")
    parser.add_argument("--decision-id", default=None)
    parser.add_argument("--set-ready", action="store_true")
    parser.add_argument("--allow-output-change", action="store_true")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--package-name", default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if bool(args.decision) != bool(args.decision_id):
        parser.error("--decision and --decision-id must be given together")
    pairs = _pair_experiments_and_cells(getattr(args, "_ordered", []))
    decision = (args.decision, args.decision_id) if args.decision else None
    try:
        summary = repin_package(
            repo_root=Path(args.repo_root),
            data_root=Path(args.data_root),
            runtime_root=Path(args.runtime_root),
            lock_path=Path(args.lock_path),
            experiments=pairs,
            readiness_dir=Path(args.readiness_dir),
            preregistration_path=Path(args.preregistration),
            decision=decision,
            set_ready=args.set_ready,
            allow_output_change=args.allow_output_change,
            python=args.python,
            package_name=args.package_name,
        )
    except RepinError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
