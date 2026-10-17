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

Not every registered cell HAS a prepared phase-supply artifact. A program
without a supplied first phase (the direct-only comparators, item E38) and a
construction-visible text arm (item E42 -- ``run_phases`` dispatches it through
``FlightRuntime._dispatch_fixed_policy``, so it builds no knowledge snapshot,
no speech packet binding and no phase supply at all) both re-pin WITHOUT one:
the preparation step says so by name, the summary records the skip and its
reason, and no ``prepared_phase_supply`` pin or 'preparation' readiness
requirement is created for them.

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
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..config import compose, protocol_hash as compute_protocol_hash
from .campaign import CampaignCell, CampaignError, load_campaign_cells

#: The preparation runtime's own message for a program without a supplied first phase (item E38).
NO_SUPPLIED_PHASE_MESSAGE = "program has no supplied first phase to prepare"

#: The preparation runtime's own message for a CONSTRUCTION-VISIBLE arm, which
#: is dispatched text-only and builds no phase supply at any point of a real
#: flight, so no prepared supply artifact exists for it to verify or pin (item
#: E42). Mirrors ``core.flight.runtime.NO_CONSTRUCTION_PHASE_SUPPLY_MESSAGE``
#: exactly as the line above mirrors the runtime's E38 literal; the mirror is
#: asserted by ``tests/unit/test_flight_repin.py``.
NO_CONSTRUCTION_SUPPLY_MESSAGE = (
    "a construction-visible text arm has no prepared phase supply to prepare"
)

#: Every preparation message that means "this cell HAS no prepared phase-supply
#: artifact", mapped to the reason the re-pin summary records beside it. A cell
#: whose preparation answers one of these is re-pinned WITHOUT an artifact: no
#: derivation, no ``prepared_phase_supply`` pin, and no 'preparation' readiness
#: requirement is created or rewritten for it.
NO_ARTIFACT_REASONS: Mapping[str, str] = {
    NO_SUPPLIED_PHASE_MESSAGE: (
        "the program declares no supplied phase, so no prepared artifact exists for this cell"
    ),
    NO_CONSTRUCTION_SUPPLY_MESSAGE: (
        "the cell composes a construction-visible text arm with no knowledge store and no "
        "phase supply, so no prepared artifact exists for this cell"
    ),
}


def no_prepared_artifact_reason(error: BaseException) -> str | None:
    """The :data:`NO_ARTIFACT_REASONS` key ``error`` announces, or ``None``.

    Matched on the message rather than the exception type for the same reason
    item E38 already did: ``prepare_supply_fn`` is a dependency-injected seam,
    so the failure that reaches here may be the real
    ``core.preparation.PreparationError``, a subprocess-shaped re-raise, or a
    test double's ``RuntimeError`` carrying the same sentence.
    """

    message = str(error)
    for candidate in NO_ARTIFACT_REASONS:
        if candidate in message:
            return candidate
    return None


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
    #: The ONE shared pin every B branch of ``native_episode.roles.perception.
    #: branches`` carries (design section 5 item 4; the item-4 GAP), or
    #: ``None`` for a cell with no branch group, or one whose B branches carry
    #: no pin yet. Every B branch shares the same artifact
    #: (:func:`branch_seed_pin` refuses if they disagree), so one pin covers
    #: the whole cell.
    perception_branch_seed_pin: ArtifactPin | None = None
    #: Whether this cell declares ``native_episode.roles.perception.branches``
    #: AT ALL -- read straight off the composed config
    #: (:func:`_perception_branches_list`), never by attempting a prepare and
    #: pattern-matching its refusal message. ``ensure_branch_seeds_pinned``
    #: uses this to skip the overwhelming majority of cells (every one
    #: written before phase 2) WITHOUT ever building a runtime for them --
    #: unlike ``prepared_phase_supply``, whose "no supplied phase" and
    #: "construction-visible arm" skips are cheap only because a program
    #: object already exists by the time they are discovered; a Perception
    #: branch group is cheaper to rule out from the raw config than to reach
    #: by building a whole runtime first.
    has_perception_branch_group: bool = False


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


# --------------------------------------------------------------------------
# Perception branch-seed pins (design section 5 item 4; the item-4 GAP).
# One shared artifact per cell, one shared pin across every B branch of its
# ``native_episode.roles.perception.branches.branches`` list -- the SAME
# nested location :func:`compute_cell_identity` and
# :func:`ensure_branch_seeds_pinned` both read/write, structurally the twin
# of ``prepared_phase_supply``'s own top-level pin above.
# --------------------------------------------------------------------------


def _perception_branches_list(document: Mapping) -> list | None:
    """The declared ``native_episode.roles.perception.branches.branches``
    list, or ``None`` when the cell declares no Perception branch group at
    all (every cell written before phase 2)."""

    native_episode = document.get("native_episode") if isinstance(document, Mapping) else None
    roles = native_episode.get("roles") if isinstance(native_episode, Mapping) else None
    perception = roles.get("perception") if isinstance(roles, Mapping) else None
    branches_block = perception.get("branches") if isinstance(perception, Mapping) else None
    branches = branches_block.get("branches") if isinstance(branches_block, Mapping) else None
    return branches if isinstance(branches, list) else None


def _b_branch_ids(branches: list) -> list[str]:
    """Every non-A, non-T (B) branch id in declaration order."""

    return [
        row["branch_id"] for row in branches
        if isinstance(row, Mapping) and row.get("deliver") is not True
        and row.get("replicate_of") is None and isinstance(row.get("branch_id"), str)
    ]


def branch_seed_pin(document: Mapping) -> ArtifactPin | None:
    """The one ``prepared_seed`` pin every B branch of ``document`` shares.

    ``None`` when the cell declares no branch group, when it declares one
    with no B branch, or when no B branch carries a pin yet. Refuses
    (:class:`RepinError`) if two B branches of the SAME cell disagree --
    design section 3 states plainly they share one artifact, so a
    disagreement is a malformed cell, not a value to silently pick one of.
    """

    branches = _perception_branches_list(document)
    if not branches:
        return None
    b_ids = _b_branch_ids(branches)
    if not b_ids:
        return None
    pins: dict[str, ArtifactPin | None] = {}
    for row in branches:
        if isinstance(row, Mapping) and row.get("branch_id") in b_ids:
            seed = row.get("prepared_seed")
            pins[row["branch_id"]] = None if seed is None else ArtifactPin.from_mapping(seed)
    distinct = set(pins.values())
    if len(distinct) > 1:
        raise RepinError(
            f"perception branch group's B branches disagree on prepared_seed: {pins}"
        )
    return next(iter(distinct)) if distinct else None


def _drop_perception_branch_seed_pins(baseline_path: Path) -> None:
    document = _read_json(baseline_path)
    if not isinstance(document, dict):
        raise RepinError(f"baseline fragment {baseline_path} is not a JSON object")
    branches = _perception_branches_list(document)
    if not branches:
        return
    changed = False
    for row in branches:
        if isinstance(row, dict) and row.pop("prepared_seed", None) is not None:
            changed = True
    if changed:
        _write_json(baseline_path, document)


def _set_perception_branch_seed_pins(baseline_path: Path, pin: ArtifactPin) -> int:
    """Point every B branch's ``prepared_seed`` at ``pin``. Returns the count updated."""

    document = _read_json(baseline_path)
    if not isinstance(document, dict):
        raise RepinError(f"baseline fragment {baseline_path} is not a JSON object")
    branches = _perception_branches_list(document)
    if not branches:
        raise RepinError(f"baseline fragment {baseline_path} declares no Perception branch group")
    b_ids = set(_b_branch_ids(branches))
    if not b_ids:
        raise RepinError(f"baseline fragment {baseline_path} declares no B branch to pin")
    updated = 0
    for row in branches:
        if isinstance(row, dict) and row.get("branch_id") in b_ids:
            row["prepared_seed"] = pin.as_dict()
            updated += 1
    _write_json(baseline_path, document)
    return updated


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
        perception_branch_seed_pin=branch_seed_pin(values),
        has_perception_branch_group=_perception_branches_list(values) is not None,
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
    # M8 (read-only by DEFAULT since 2026-10-17): a check never needs its one data-root write. Opt-in
    # read-only let the NX-T R1 rec2 flip (no env set) write <run dir>/resume-declaration.json at
    # 08:47Z / 08:53Z, and the chain's "rec2 attempt not yet opened" precondition then refused the
    # launch. SAEA_REPIN_CHECK_READONLY=0 restores the writing check (nothing in the repo needs it).
    if os.environ.get("SAEA_REPIN_CHECK_READONLY", "1") != "0":
        command.append("--read-only")
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


#: The relpath shape :func:`ensure_artifact_pinned` mints for a cell's own
#: prepared phase-supply artifact: ``prepared/<run_id>/phase-supply-v<N>.json``.
_OWN_SUPPLY_RELPATH_PATTERN = re.compile(r"prepared/(?P<run_id>[^/]+)/phase-supply-v\d+\.json")

#: The ``reason`` written on a 'preparation' requirement this tool creates.
_CREATED_REQUIREMENT_REASON = (
    "Model-free first-phase supply prepared by core.flight.repin on the launch commit; "
    "zero model, tokenizer or encoder contact."
)


def is_own_supply_requirement(entry: object, *, run_id: str, previous_relpath: str | None) -> bool:
    """Whether ``entry`` is the readiness requirement for the cell's OWN prepared supply.

    A readiness requirement's identity is its ``relpath``: it is the only key
    ``core.flight.campaign.declared_readiness`` locates and verifies the
    artifact by (a requirement carries no run-id or role field). An entry
    names the cell's own supply when it is a 'preparation' requirement whose
    relpath is either

    * the pin this re-pin supersedes -- the baseline's current
      ``prepared_phase_supply``, which for a cell that inherited a sibling's
      supply verbatim (B8b from B7r) lives under the SIBLING's run id -- or
    * a phase-supply artifact under the cell's own run-id directory, in the
      exact ``prepared/<run_id>/phase-supply-v<N>.json`` shape this tool mints
      (:func:`ensure_artifact_pinned`); this also covers a cell registered
      before its supply was prepared and therefore carrying no baseline pin
      yet (the AGREE family).

    Matching on ``kind`` alone was the 2026-09-26 defect: a cell may carry
    other 'preparation' requirements (the AGREE cells' pre-computed
    exemplar-intent agreement table, under a different run id), and those are
    never this cell's supply, so a flip must not rewrite them.
    """

    if not isinstance(entry, Mapping) or entry.get("kind") != "preparation":
        return False
    relpath = entry.get("relpath")
    if not isinstance(relpath, str) or not relpath:
        return False
    if previous_relpath is not None and relpath == previous_relpath:
        return True
    match = _OWN_SUPPLY_RELPATH_PATTERN.fullmatch(relpath)
    return match is not None and match.group("run_id") == run_id


def _set_preparation_requirement(
    experiment_path: Path,
    *,
    cell_id: str,
    run_id: str,
    previous_pin: ArtifactPin | None,
    pin: ArtifactPin,
) -> dict[str, int]:
    """Point the cell's OWN 'preparation' readiness requirement at ``pin``.

    Rewrites every requirement :func:`is_own_supply_requirement` accepts (a
    cell registered with the same own-supply entry twice keeps both, both
    updated -- sixteen committed Stage-3 cells carry that duplicate), leaves
    every other 'preparation' requirement untouched byte-for-byte, and appends
    exactly one new requirement when nothing matches. Returns ``{"updated",
    "appended", "kept"}`` counts for the re-pin summary.
    """

    document = _read_json(experiment_path)
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise RepinError(f"experiment fragment {experiment_path} has no cells list")
    previous_relpath = previous_pin.relpath if previous_pin is not None else None
    own_cells = [
        cell_doc
        for cell_doc in document["cells"]
        if isinstance(cell_doc, Mapping) and cell_doc.get("cell_id") == cell_id
    ]
    updated = kept = 0
    for cell_doc in own_cells:
        readiness = cell_doc.get("readiness")
        requirements = readiness.get("requirements") if isinstance(readiness, Mapping) else None
        if not isinstance(requirements, list):
            continue
        for entry in requirements:
            if is_own_supply_requirement(entry, run_id=run_id, previous_relpath=previous_relpath):
                entry["relpath"] = pin.relpath
                entry["sha256"] = pin.sha256
                updated += 1
            elif isinstance(entry, Mapping) and entry.get("kind") == "preparation":
                kept += 1
    appended = 0
    if updated == 0:
        # A package registered before its supply could be prepared (the B1
        # exemplar cells, blocked by the E3 router guard; the CONV probe)
        # carries no own-supply requirement -- an empty list, or only foreign
        # 'preparation' requirements; the first successful preparation creates
        # the requirement instead of refusing, so the tool completes such a
        # registration rather than demanding a hand edit.
        for cell_doc in own_cells:
            readiness = cell_doc.get("readiness")
            if not isinstance(readiness, dict):
                continue
            requirements = readiness.setdefault("requirements", [])
            if isinstance(requirements, list):
                requirements.append({
                    "kind": "preparation",
                    "relpath": pin.relpath,
                    "sha256": pin.sha256,
                    "reason": _CREATED_REQUIREMENT_REASON,
                })
                appended = 1
                break
    if updated == 0 and appended == 0:
        raise RepinError(
            f"cell {cell_id!r} in {experiment_path} has no readiness block to carry a 'preparation' requirement"
        )
    _write_json(experiment_path, document)
    return {"updated": updated, "appended": appended, "kept": kept}


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
    'preparation' readiness requirement for the cell's OWN supply -- matched
    by artifact identity (:func:`is_own_supply_requirement`), never by
    ``kind`` alone, so any other 'preparation' requirement the cell carries
    (the AGREE family's pre-computed agreement table) stays byte-for-byte
    intact.

    A cell that HAS no prepared phase supply -- a program without a supplied
    first phase (item E38), or a construction-visible text arm (item E42) --
    is reported as ``{"rebuilt": False, "pin": None, "skipped": <message>,
    "reason": ...}``: nothing is derived, nothing is pinned, and the cell's own
    'preparation' readiness requirement (which for such a cell names a sibling
    deliverable rather than a phase-supply artifact) is left untouched.
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
    except Exception as error:  # noqa: BLE001 -- the baseline is restored verbatim on every failure
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        skipped = no_prepared_artifact_reason(error)
        if skipped is not None and current_pin is None:
            # Item E38: a program with no supplied first phase (the direct-only
            # comparators). Item E42: a construction-visible TEXT arm, which
            # ``run_phases`` dispatches through ``_dispatch_fixed_policy`` and
            # which therefore builds no knowledge snapshot, no speech packet
            # binding and no phase supply. Either way there is nothing to
            # prepare and nothing to pin: the cell is flipped on its decision
            # requirement alone; no artifact, no 'preparation' readiness
            # requirement, no baseline change.
            return {
                "rebuilt": False,
                "pin": None,
                "skipped": skipped,
                "reason": NO_ARTIFACT_REASONS[skipped],
            }
        if skipped == NO_CONSTRUCTION_SUPPLY_MESSAGE and current_pin is not None:
            raise RepinError(
                f"cell {identity.cell_id!r} composes the construction-visible arm "
                f"{identity.arm!r}, which has no derivable prepared phase supply, yet its "
                f"baseline fragment {identity.baseline_fragment!r} pins "
                f"prepared_phase_supply {current_pin.relpath!r}; that combination is "
                "undefined -- remove the pin by hand and re-run"
            ) from error
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
    requirement_edit = _set_preparation_requirement(
        experiment_path,
        cell_id=identity.cell_id,
        run_id=identity.run_id,
        previous_pin=current_pin,
        pin=new_pin,
    )
    return {
        "rebuilt": True,
        "reason": mismatch_reason,
        "old_pin": current_pin.as_dict() if current_pin is not None else None,
        "new_pin": new_pin.as_dict(),
        "row_counts": row_counts,
        "readiness_requirement": requirement_edit,
    }


# --------------------------------------------------------------------------
# Perception branch-seed re-pin (design section 5 item 4; the item-4 GAP).
# Structurally :func:`ensure_artifact_pinned`'s twin: same verify-or-rebuild
# shape, over the branch-seed artifact instead of the phase-supply one, and
# over the nested ``native_episode.roles.perception.branches.branches`` pin
# location instead of the baseline's top-level ``prepared_phase_supply`` key.
# No 'preparation' readiness requirement bookkeeping: the registration gate
# (``scripts/checks/flight_registration_check.py``) reads the branch's own
# ``prepared_seed`` field directly, so none is needed here.
# --------------------------------------------------------------------------

#: The preparation runtime's own message for a cell with no declared
#: Perception branch group at all (every cell written before phase 2).
NO_BRANCH_GROUP_MESSAGE = (
    "cell declares no roles.perception.branches; there is no Perception branch seed to prepare"
)

_BRANCH_SEED_VERSION_PATTERN = re.compile(r"^perception-branch-seeds-v(\d+)\.json$")


def default_prepare_branch_seeds(
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
    """Run the real, model-free ``core.flight.cli prepare-branch-seeds`` path.

    Mirrors :func:`default_prepare_supply` exactly: called with an existing
    ``output_path`` this is a pure identity check; called with a path that
    does not yet exist, it derives and publishes a fresh artifact.
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
    return runtime.prepare_perception_branch_seeds(Path(output_path))


def _next_branch_seed_version(directory: Path) -> int:
    if not directory.is_dir():
        return 1
    versions = [
        int(match.group(1))
        for path in directory.iterdir()
        if (match := _BRANCH_SEED_VERSION_PATTERN.match(path.name))
    ]
    return max(versions) + 1 if versions else 1


def _branch_seed_row_counts(output: object) -> dict[str, int]:
    counts: dict[str, int] = {}
    if isinstance(output, Mapping):
        branches = output.get("branches")
        if isinstance(branches, Mapping):
            for branch_id, rows in branches.items():
                counts[str(branch_id)] = len(rows) if isinstance(rows, Mapping) else 0
    return counts


def _compare_branch_seed_output(
    *, old_path: Path | None, new_path: Path, allow_output_change: bool
) -> dict[str, object] | None:
    if old_path is None or not old_path.is_file():
        return None
    old_document = _read_json(old_path)
    new_document = _read_json(new_path)
    old_output = old_document.get("output") if isinstance(old_document, Mapping) else None
    new_output = new_document.get("output") if isinstance(new_document, Mapping) else None
    counts = {"old": _branch_seed_row_counts(old_output), "new": _branch_seed_row_counts(new_output)}
    if old_output != new_output and not allow_output_change:
        raise RepinError(
            "rebuilt perception branch-seed artifact selects a different output than the "
            f"previous artifact ({old_path}); row counts old={counts['old']} "
            f"new={counts['new']}; pass --allow-output-change to accept this deliberately"
        )
    return counts


def ensure_branch_seeds_pinned(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiment: str,
    identity: CellIdentity,
    prepare_branch_seeds_fn: PrepareSupplyFn = default_prepare_branch_seeds,
    allow_output_change: bool = False,
) -> dict[str, object]:
    """Re-run ``prepare-branch-seeds`` only if the pinned artifact would mismatch.

    Every B branch of one cell shares ONE artifact (design section 3), so
    this verifies (or rebuilds) it once and writes the SAME new pin onto
    every B branch (:func:`_set_perception_branch_seed_pins`). A cell that
    declares no Perception branch group at all is reported as ``{"rebuilt":
    False, "pin": None, "skipped": NO_BRANCH_GROUP_MESSAGE}``: nothing is
    derived, nothing is pinned -- the overwhelming majority of registered
    cells, written before phase 2. That case is caught HERE, off
    ``identity.has_perception_branch_group`` (read straight off the composed
    config), before ``prepare_branch_seeds_fn`` is ever called -- unlike
    ``ensure_artifact_pinned``, this never needs to build a runtime just to
    rule a cell out, so a synthetic test cell with no real carrier (most of
    ``tests/unit/test_flight_repin.py``'s own fixtures) is unaffected by this
    mechanism entirely.
    """

    if not identity.has_perception_branch_group and identity.perception_branch_seed_pin is None:
        return {"rebuilt": False, "pin": None, "skipped": NO_BRANCH_GROUP_MESSAGE}

    baseline_path = baseline_fragment_path(repo_root, identity.baseline_fragment)
    current_pin = identity.perception_branch_seed_pin
    existing_absolute: Path | None = None
    needs_rebuild = current_pin is None
    mismatch_reason = "no prepared_seed pin is currently configured on the B branch(es)"
    if current_pin is not None:
        existing_absolute = (Path(data_root) / current_pin.relpath).resolve()
        if not existing_absolute.is_file():
            needs_rebuild = True
            mismatch_reason = f"pinned artifact is absent on disk: {current_pin.relpath}"
        else:
            try:
                prepare_branch_seeds_fn(
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
    version = _next_branch_seed_version(directory)
    new_relpath = f"prepared/{identity.run_id}/perception-branch-seeds-v{version}.json"
    new_absolute = Path(data_root) / new_relpath
    if new_absolute.exists():
        raise RepinError(f"refusing to overwrite an existing artifact at {new_relpath}")

    original_baseline_text = baseline_path.read_text(encoding="utf-8")
    _drop_perception_branch_seed_pins(baseline_path)
    try:
        receipt = prepare_branch_seeds_fn(
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
    except Exception as error:  # noqa: BLE001 -- the baseline is restored verbatim on every failure
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        if NO_BRANCH_GROUP_MESSAGE in str(error) and current_pin is None:
            # No branch group at all: nothing to prepare, nothing to pin --
            # the overwhelming majority of registered cells.
            return {"rebuilt": False, "pin": None, "skipped": NO_BRANCH_GROUP_MESSAGE}
        raise
    new_sha256 = receipt.get("sha256") if isinstance(receipt, Mapping) else None
    if not isinstance(new_sha256, str) or SHA256_PATTERN.fullmatch(new_sha256) is None:
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        raise RepinError(f"prepare_branch_seeds_fn returned no valid sha256 for {new_relpath}")

    try:
        row_counts = _compare_branch_seed_output(
            old_path=existing_absolute, new_path=new_absolute, allow_output_change=allow_output_change
        )
    except RepinError:
        baseline_path.write_text(original_baseline_text, encoding="utf-8", newline="\n")
        raise

    new_pin = ArtifactPin(new_relpath, new_sha256)
    updated = _set_perception_branch_seed_pins(baseline_path, new_pin)
    return {
        "rebuilt": True,
        "reason": mismatch_reason,
        "old_pin": current_pin.as_dict() if current_pin is not None else None,
        "new_pin": new_pin.as_dict(),
        "row_counts": row_counts,
        "branches_updated": updated,
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


#: The exact marker ``docs/exposure-ledger.md`` carries on a donor package's
#: own row(s) once a cell registered under it is carried forward into a new
#: package (commit 1099a19c, the COMP-1 DEV-2000-ADDED placeholder -> cell
#: A2/COMP-1b): ``SUPERSEDED 2026-09-29 by cell A2
#: (docs/readiness/2026-09-29-slurp-stage3-comp1b-dev2000-added-v1, owner
#: decision 198: ...)``. Group 1 is the superseding package's own directory
#: name -- compared against the CURRENT re-pin's own ``readiness_dir.name``,
#: never matched loosely, so a package superseded in favor of some OTHER
#: package is never exempted here.
_SUPERSEDED_BY_PACKAGE = re.compile(r"SUPERSEDED\s+\d{4}-\d{2}-\d{2}\s+by\s+cell\s+\S+\s+\(docs/readiness/([A-Za-z0-9._-]+)")


def _superseded_donor_ledger_row_mask(text: str, *, own_package_name: str) -> list[bool]:
    """One flag per line of ``text``: True when the line is a contract-table
    ROW whose ``notes`` column carries :data:`_SUPERSEDED_BY_PACKAGE` naming
    ``own_package_name`` -- a donor cell's own sealed record (E26), frozen
    even on the rare row whose run id might otherwise fall inside the
    current re-pin's own ``run_ids`` (in the ordinary case such a row is
    already masked by :func:`_foreign_ledger_row_mask`, since a truly
    superseded donor cell keeps its own, different run id; this is the
    narrower defensive twin for the case where it does not). Every entry is
    False when ``own_package_name`` is empty (no ``readiness_dir`` given)."""

    if not own_package_name:
        return []
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
            if header is not None and len(cells) == len(header) and _LEDGER_HEADER_NOTES in header:
                notes = cells[header.index(_LEDGER_HEADER_NOTES)]
                match = _SUPERSEDED_BY_PACKAGE.search(notes)
                if match and match.group(1) == own_package_name:
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


def _is_within(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def _collect_run_id_values(document: object) -> set[str]:
    """Every string found under a JSON key literally named ``run_id``, at any
    nesting depth -- the identifier every registered cell's own fragments and
    packages record for themselves (``cells[].run_id``, ``execution_plan.
    run_id``, ``cell.run_id``, ``abort.run_id`` and so on; item: the REC
    protocol document's own ``parent_protocol`` block and the experiment
    fragment's ``cells`` array both carry a sibling's or a parent's run id
    beside the current cell's own)."""

    found: set[str] = set()

    def _walk(node: object) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if key == "run_id" and isinstance(value, str):
                    found.add(value)
                _walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                _walk(item)

    _walk(document)
    return found


def _is_foreign_readiness_package(path: Path, *, readiness_root: Path, run_ids: set[str], text: str) -> bool:
    """True when ``path`` sits inside SOME package directory directly under
    ``docs/readiness/`` (at least one directory level below it) that is not
    the cell's own -- the caller has already excluded the cell's own package
    and own config fragments before calling this -- and the file does not
    itself name one of ``run_ids`` (which would make it suspect rather than a
    plain sealed record of a different run).

    Item: the 2026-09-28 COMP-1 -REC recovery cell, derived from the sealed
    COMP-1 arm, inherited that parent's own hash-pinned prepared-supply pin
    and quoted the parent's protocol document under its own ``parent_protocol``
    field; the parent's OWN ``docs/readiness/2026-09-27-...-comp-1-fold-a-v1/``
    package must never be rewritten, and a residue scan that does not know
    this is a different, sealed package's own directory falsely refuses on
    it.
    """

    try:
        relative = path.relative_to(readiness_root)
    except ValueError:
        return False
    if len(relative.parts) < 2:
        # A loose file directly under docs/readiness/, not inside any
        # package directory -- treated the same as any other stray doc.
        return False
    if any(run_id in text for run_id in run_ids):
        return False
    return True


def _is_foreign_config(path: Path, *, run_ids: set[str]) -> bool:
    """True when ``path`` is a ``configs/`` fragment -- the caller has already
    excluded this re-pin's OWN fragments -- whose own declared ``run_id``
    value(s) are read from the JSON and found disjoint from ``run_ids``: a
    baseline or experiment fragment that names some OTHER cell(s) only. A
    fragment with no ``run_id`` field anywhere (for example a model or
    dataset fragment) is never exempted this way; the scan stays strict on it.
    """

    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    file_run_ids = _collect_run_id_values(document)
    return bool(file_run_ids) and file_run_ids.isdisjoint(run_ids)


def _resume_parent_attempt_ids(resolved: Sequence[tuple[str, CampaignCell]]) -> set[str]:
    """Every predecessor attempt id named by a resolved cell's own
    ``resume_from`` declaration(s) (:mod:`core.flight.resume`) -- the sealed
    or aborted arm(s) a resume/seal-only completion is built on. Empty for an
    ordinary cell that declares no ``resume_from`` at all.
    """

    from .resume import resume_declarations_from_document  # noqa: PLC0415

    attempt_ids: set[str] = set()
    for _experiment, cell in resolved:
        resume = cell.resume_from
        if resume is None:
            continue
        for declaration in resume_declarations_from_document(resume):
            attempt_ids.add(declaration.attempt_id)
    return attempt_ids


def _resume_parent_config_paths(repo_root: Path, attempt_ids: set[str]) -> set[Path]:
    """The parent cell's own experiment fragment and baseline fragment paths,
    for every cell declared anywhere under ``configs/experiment/`` whose OWN
    ``attempt_id`` is named by ``attempt_ids`` -- a resume/seal-only cell's
    own ``resume_from`` chain.

    Item E4-1 (2026-09-29): unlike a ``docs/readiness/`` package (identified
    by directory and exempted by :func:`_is_foreign_readiness_package` /
    :func:`_is_sealed_package_record`), a parent cell's ``configs/`` fragments
    carry no directory boundary of their own, and ``resume_from`` names only
    an attempt id and a trace sha256 -- no experiment or cell id -- so the
    parent's own fragment paths must be found by searching every experiment
    fragment for the matching attempt id, the same way a plan document's own
    ``execution_plan.attempt_id`` identifies it in
    :func:`_is_earlier_attempt_plan_document`.

    A resume/seal-only cell's own ``attempt_id`` is never named by its own
    ``resume_from`` (:meth:`CampaignCell.from_document` refuses that), so
    calling this with the current re-pin's ``attempt_ids`` would safely find
    nothing; the caller only ever passes the PARENT chain's attempt ids.
    """

    if not attempt_ids:
        return set()
    experiment_dir = Path(repo_root) / "configs" / "experiment"
    if not experiment_dir.is_dir():
        return set()
    paths: set[Path] = set()
    for path in sorted(experiment_dir.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        cells = document.get("cells") if isinstance(document, Mapping) else None
        if not isinstance(cells, list):
            continue
        for cell in cells:
            if not isinstance(cell, Mapping):
                continue
            attempt_id = cell.get("attempt_id")
            if not (isinstance(attempt_id, str) and attempt_id in attempt_ids):
                continue
            paths.add(path.resolve())
            baseline_fragment = cell.get("baseline_fragment")
            if isinstance(baseline_fragment, str) and baseline_fragment:
                paths.add(baseline_fragment_path(repo_root, baseline_fragment).resolve())
    return paths


#: The exact pattern ``scripts/checks/flight_registration_check.py`` uses for its
#: own ``PACKAGE_REF``: a ``docs/readiness/<package>/`` directory reference
#: inside a flight row's ``artifacts`` column. Reused here verbatim (item E4-2)
#: rather than inventing a second mapping from run id to package directory.
_READINESS_PACKAGE_REF = re.compile(r"docs/readiness/([A-Za-z0-9._\-]+)/")


def _resume_parent_package_dirs(
    repo_root: Path, exposure_ledger_path: Path, run_ids: set[str]
) -> set[Path]:
    """The ``docs/readiness/<package>/`` directory the CURRENT exposure-ledger
    row(s) for ``run_ids`` name in their ``artifacts`` column -- resolved the
    same way the registration gate's own fallback resolves a cell's package
    (``scripts/checks/flight_registration_check.py::resolve_package``'s FIRST
    strategy, "the flight row's ``artifacts`` column"; :data:`_READINESS_PACKAGE_REF`
    is that same ``PACKAGE_REF`` pattern), never a hand-rolled cell-id-to-
    directory guess.

    Item E4-2 (2026-09-29, the P-SV-1 seal-only flip): a resume/seal-only cell
    shares its parent's run id (the resume-recovery clause: "the same run id,
    a fresh attempt id"), and one run id has exactly one exposure-ledger row.
    That row's ``artifacts`` column is set once, at the run id's FIRST
    registration, and is never rewritten to a new package afterward --
    :func:`apply_mapping_to_ledger` only ever substitutes specific pinned
    hash/relpath VALUES the current re-pin's ``mapping`` names, never the
    column's own relpath -- so for a resume this reads back the PARENT's own
    package directory even though the resume's own re-pin targets a brand
    new ``docs/readiness/<...>-resume-v1/`` directory (a DIFFERENT directory
    from the one this returns; the caller's own ``readiness_dir`` is exempted
    separately, by :func:`assert_no_residue`'s ``own_files``/``readiness_dir``
    handling, not by this).

    Read fresh from disk (never the ``ledger_text`` a caller may have read
    earlier in the same :func:`repin_package` call): by the time this is
    called, :func:`rewrite_dependent_hashes` has already rewritten the ledger
    on disk, and a stale in-memory copy would not reflect that.

    Caller-gated: only meaningful, and only ever called, when the current
    re-pin's own ``resume_from`` chain is non-empty. For an ordinary cell
    (no resume) this would simply resolve back to the cell's own package --
    already exempt by other means -- so callers skip it entirely rather than
    rely on that coincidence.
    """

    if not run_ids or not exposure_ledger_path.is_file():
        return set()
    from ...contracts.ledger import _parse_ledger_tables  # noqa: PLC0415

    ledger_text = exposure_ledger_path.read_text(encoding="utf-8")
    rows = _parse_ledger_tables(ledger_text)
    dirs: set[Path] = set()
    for row in rows:
        run_id = row.get(_LEDGER_HEADER_RUN)
        if run_id not in run_ids:
            continue
        artifacts = row.get(_LEDGER_HEADER_ARTIFACTS)
        if not artifacts:
            continue
        match = _READINESS_PACKAGE_REF.search(artifacts)
        if match:
            dirs.add((Path(repo_root) / "docs" / "readiness" / match.group(1)).resolve())
    return dirs


def _superseded_donor_package_dirs(
    repo_root: Path, exposure_ledger_path: Path, readiness_dir: Path
) -> set[Path]:
    """The ``docs/readiness/<package>/`` directory of every OTHER package the
    exposure ledger explicitly records as superseded BY the current re-pin's
    own package (``readiness_dir``): scans EVERY row in the ledger (not only
    rows naming the current run ids -- a donor's own superseded rows
    ordinarily carry a DIFFERENT run id, so :func:`_resume_parent_package_dirs`'s
    current-run-id-only scan would never find them) for a ``notes`` column
    matching :data:`_SUPERSEDED_BY_PACKAGE` whose captured package name is
    this cell's own ``readiness_dir.name``; that row's OWN ``artifacts``
    column then names the donor package to exempt.

    Item (2026-09-29, cell A2/COMP-1b on DEV-2000-ADDED, owner decision 198):
    the in-chain A/A cell was carried forward from the COMP-1 DEV-2000-ADDED
    placeholder package into this one; commit 1099a19c marked the
    placeholder's own rows (the arm, its FIT identity, the four-row smoke,
    its FIT identity, and the paired-analysis row) SUPERSEDED with this exact
    marker and left the placeholder's bytes untouched (E26: never rewrite
    another cell's own record) -- so the placeholder package's own copies of
    the carried-over A/A cell's registered plan and facts documents
    (``aa-generation-plan-registered-v1.json``, ``registered-facts-v1.json``,
    ``root-admission-draft-v1.json``) are the donor's own sealed record, not
    residue, but ONLY because the ledger itself says so, by name, for THIS
    package; a package superseded in favor of some OTHER package, or merely
    described as superseded in prose without the exact marker, is not found
    here and stays exempt by no rule at all -- ``assert_no_residue`` refuses
    on it exactly as before this item.
    """

    if not exposure_ledger_path.is_file():
        return set()
    from ...contracts.ledger import _parse_ledger_tables  # noqa: PLC0415

    own_package_name = Path(readiness_dir).name
    ledger_text = exposure_ledger_path.read_text(encoding="utf-8")
    rows = _parse_ledger_tables(ledger_text)
    dirs: set[Path] = set()
    for row in rows:
        notes = row.get(_LEDGER_HEADER_NOTES, "")
        match = _SUPERSEDED_BY_PACKAGE.search(notes)
        if not match or match.group(1) != own_package_name:
            continue
        artifacts = row.get(_LEDGER_HEADER_ARTIFACTS)
        if not artifacts:
            continue
        ref = _READINESS_PACKAGE_REF.search(artifacts)
        if ref:
            dirs.add((Path(repo_root) / "docs" / "readiness" / ref.group(1)).resolve())
    return dirs


def _is_resume_parent_readiness_record(
    path: Path, *, readiness_root: Path, resume_parent_package_dirs: set[Path]
) -> bool:
    """True when ``path`` sits inside one of the current re-pin's own
    ``resume_from`` chain's PARENT readiness packages
    (:func:`_resume_parent_package_dirs`), or is that same package's sibling
    preregistration note (``docs/readiness/<package-name>-preregistration*.md``,
    a file adjacent to -- never inside -- the package directory).

    Every file under the parent's own package directory is exempted, not only
    ``*.json``/``README.md``: the parent's readiness package (README, every
    registered plan, the protocol document, ``registered-facts-v1.json``, the
    root-admission draft) legitimately quotes the parent's own frozen pins
    (a branch-seed relpath and sha256, a phase-supply pin) and must stay
    byte-identical (rule E26) -- the exact old value a resume/seal-only cell's
    first re-pin supersedes is, legitimately, still the frozen parent's own
    current pin.
    """

    if not resume_parent_package_dirs:
        return False
    resolved = path.resolve()
    for package_dir in resume_parent_package_dirs:
        if _is_within(resolved, package_dir):
            return True
        if (
            resolved.parent == readiness_root
            and resolved.suffix == ".md"
            and resolved.name.startswith(f"{package_dir.name}-preregistration")
        ):
            return True
    return False


def _is_superseded_donor_readiness_record(
    path: Path, *, readiness_root: Path, superseded_donor_package_dirs: set[Path]
) -> bool:
    """True when ``path`` sits inside one of the packages the exposure ledger
    marks SUPERSEDED by the current re-pin's own package
    (:func:`_superseded_donor_package_dirs`), or is that donor package's
    sibling preregistration note -- the same shape as
    :func:`_is_resume_parent_readiness_record`, for a package related by
    supersession (a cell carried FORWARD into the current package) rather
    than by ``resume_from`` (a cell built on top of a still-live sealed
    parent).

    The caller only ever reaches this check for a file that has already
    failed :func:`_is_foreign_readiness_package` -- i.e., the file already
    names one of the current run ids -- so this can never widen a residue
    exemption beyond a cell the current package itself now declares: the
    donor package's own record of some OTHER, still-superseded cell (one the
    current package does not carry) never reaches here, because it never
    names one of ``run_ids`` in the first place and so is already exempted,
    correctly, by :func:`_is_foreign_readiness_package`.
    """

    if not superseded_donor_package_dirs:
        return False
    resolved = path.resolve()
    for package_dir in superseded_donor_package_dirs:
        if _is_within(resolved, package_dir):
            return True
        if (
            resolved.parent == readiness_root
            and resolved.suffix == ".md"
            and resolved.name.startswith(f"{package_dir.name}-preregistration")
        ):
            return True
    return False


def _plan_document_attempt_id(document: object) -> str | None:
    """The attempt one registered plan document names.

    Every registered fit/generation plan under ``docs/readiness/`` (e.g.
    ``fit-plan-registered-v1.json``, ``generation-plan-registered-v1.json``,
    their ``aa-`` and ``smoke-`` siblings) names its own attempt the same
    way: ``execution_plan.attempt_id``. A document with no such field is not
    a plan document this rule recognizes.
    """

    if not isinstance(document, Mapping):
        return None
    execution_plan = document.get("execution_plan")
    if isinstance(execution_plan, Mapping) and isinstance(execution_plan.get("attempt_id"), str):
        return execution_plan["attempt_id"]
    return None


def _is_earlier_attempt_plan_document(text: str, *, attempt_ids: set[str]) -> bool:
    """True when ``text`` is a registered plan document naming an attempt
    that is NOT one being re-pinned now -- a sealed record of an earlier
    (e.g. aborted) attempt of the same run id. A document this tool cannot
    read an attempt out of (malformed JSON, or simply not a plan document)
    is never exempted this way: the scan stays strict on it.
    """

    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return False
    attempt = _plan_document_attempt_id(document)
    return attempt is not None and attempt not in attempt_ids


def _package_pins_own_digest(path: Path, *, repo_root: Path, package_dir: Path) -> bool:
    """True when some OTHER json file inside ``package_dir`` pins ``path``'s
    OWN current bytes by sha256 under a ``{"relpath"|"path": ..., "sha256":
    ...}`` block -- the admission draft's ``attribution_classes`` pin, or the
    registered facts' ``source`` pin, over an analysis file such as
    ``attribution-classes-v1.json``. Rewriting ``path`` would silently break
    that external pin, so a superseded value frozen inside it at derivation
    time is not residue -- it is exactly what was sealed.
    """

    try:
        own_relpath = str(path.resolve().relative_to(Path(repo_root).resolve())).replace("\\", "/")
    except ValueError:
        return False
    try:
        own_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False

    def _pins_this_file(node: object) -> bool:
        if isinstance(node, Mapping):
            relvalue = node.get("relpath")
            if not isinstance(relvalue, str):
                relvalue = node.get("path")
            if (
                isinstance(relvalue, str)
                and relvalue == own_relpath
                and node.get("sha256") == own_sha256
            ):
                return True
            return any(_pins_this_file(value) for value in node.values())
        if isinstance(node, (list, tuple)):
            return any(_pins_this_file(item) for item in node)
        return False

    if not package_dir.is_dir():
        return False
    for sibling in sorted(package_dir.glob("*.json")):
        if sibling.resolve() == path.resolve():
            continue
        try:
            document = json.loads(sibling.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if _pins_this_file(document):
            return True
    return False


def _is_sealed_package_record(
    path: Path, *, readiness_root: Path, repo_root: Path, attempt_ids: set[str], text: str
) -> bool:
    """True when ``path`` sits inside SOME package directory under
    ``docs/readiness/`` (the caller has already excluded the cell's own
    files) and is a sealed record this re-pin must never be asked to alter,
    even though the package also names one of the current run ids (so
    :func:`_is_foreign_readiness_package` no longer exempts it):

    * a registered plan document naming an attempt other than the one being
      re-pinned (:func:`_is_earlier_attempt_plan_document`) -- the 2026-09-28
      COMP-1 RESUME shares its parent arm's run id, so the parent's own
      ``fit-plan-registered-v1.json`` (attempt
      ``attempt-slurp-native-stage3-comp1-fold-a-fit-v1``, not the resume's)
      legitimately still carries the aborted attempt's supply pin; or
    * a file whose own current bytes are pinned by sha256 from a sibling
      document in the same package directory
      (:func:`_package_pins_own_digest`) -- the parent's
      ``attribution-classes-v1.json``, hash-pinned by its
      ``root-admission-draft-v1.json`` and ``registered-facts-v1.json``.

    Never exempts the re-pinned attempt's own plan documents or a
    registered-facts/analysis-recipe block describing the CURRENT attempt:
    both name an attempt in ``attempt_ids`` and so fail the first test, and
    neither is the pin TARGET of a sibling's ``attribution_classes``-shaped
    block, so the second test never fires for them either.
    """

    try:
        relative = path.relative_to(readiness_root)
    except ValueError:
        return False
    if len(relative.parts) < 2 or path.suffix != ".json":
        return False
    if _is_earlier_attempt_plan_document(text, attempt_ids=attempt_ids):
        return True
    package_dir = readiness_root / relative.parts[0]
    return _package_pins_own_digest(path, repo_root=repo_root, package_dir=package_dir)


def assert_no_residue(
    repo_root: Path,
    old_values: Iterable[str],
    *,
    exposure_ledger_path: Path | None = None,
    run_ids: set[str] | None = None,
    attempt_ids: set[str] | None = None,
    readiness_dir: Path | None = None,
    own_files: Iterable[Path] | None = None,
    own_config_paths: Iterable[Path] | None = None,
    resume_parent_config_paths: Iterable[Path] | None = None,
    resume_parent_package_dirs: Iterable[Path] | None = None,
    superseded_donor_package_dirs: Iterable[Path] | None = None,
    explain: bool = False,
    file_cache: dict | None = None,
) -> None:
    """Refuse if any OLD hash string remains anywhere under ``docs/`` or
    ``configs/`` after rewriting.

    An OLD hash that lives in an exposure-ledger row OUTSIDE ``run_ids`` is
    not residue: it is another package's own registration (the sealed parent
    this package was derived from), and this re-pin neither rewrites it
    (:func:`apply_mapping_to_ledger`) nor may it demand that it disappear.

    Six further exemptions follow the same principle, active only when
    ``readiness_dir`` and ``run_ids`` are given (the only production call, from
    :func:`repin_package`), and only for files that are NOT this cell's own
    (``own_files``, ``own_config_paths``, or anywhere inside ``readiness_dir``
    itself -- those stay exactly as strict as before):

    * a file inside some OTHER package directory directly under
      ``docs/readiness/`` is a different, sealed package's own record, not
      residue, unless it also names one of ``run_ids`` (see
      :func:`_is_foreign_readiness_package`);
    * failing that (a RESUME shares its parent's run id, so the parent's own
      package legitimately names it), a sealed record of an earlier attempt
      or a sha256-pinned table within that same package is still not
      residue (see :func:`_is_sealed_package_record`; ``attempt_ids`` names
      the attempt(s) actually being re-pinned now);
    * failing BOTH of those too (the parent's package can carry a live,
      non-JSON file such as its own ``README.md``, which neither rule above
      reaches -- ``_is_foreign_readiness_package`` declines because the
      package names the shared run id, and ``_is_sealed_package_record``
      never considers a non-``.json`` file at all), every file inside a
      package named in ``resume_parent_package_dirs`` -- the ``docs/
      readiness/<package>/`` directory the CURRENT re-pin's own exposure-
      ledger row(s) name in their ``artifacts`` column (see
      :func:`_resume_parent_package_dirs`) -- is the parent's own sealed
      record, not residue (item E4-2, 2026-09-29: the P-SV-1 seal-only flip's
      parent package legitimately quotes the parent's own frozen branch-seed
      and phase-supply pins in its README and ``registered-facts-v1.json``).
      The package's sibling preregistration note (``docs/readiness/
      <package>-preregistration*.md``) is exempted the same way (see
      :func:`_is_resume_parent_readiness_record`);
    * failing all three of those (a cell CARRIED FORWARD into this package
      from a now-superseded donor package -- the mirror image of a resume:
      the donor did not build this cell on a still-live parent, it GAVE this
      cell up), every file inside a package named in
      ``superseded_donor_package_dirs`` -- a package whose exposure-ledger
      row(s) carry the exact marker ``SUPERSEDED <date> by cell <id>
      (docs/readiness/<this-package>, ...)`` naming THIS package by name
      (see :func:`_superseded_donor_package_dirs`) -- is the donor's own
      sealed record, not residue (item 2026-09-29, cell A2/COMP-1b on
      DEV-2000-ADDED: the in-chain A/A cell was carried forward from the
      COMP-1 DEV-2000-ADDED placeholder package, whose own
      ``aa-generation-plan-registered-v1.json``, ``registered-facts-v1.json``
      and ``root-admission-draft-v1.json`` legitimately still carry the A/A's
      pre-repin pin). The donor package's sibling preregistration note is
      exempted the same way (see :func:`_is_superseded_donor_readiness_record`).
      This is explicit-marker-gated, not name-symmetric with a resume: a
      package merely described as superseded in prose, or superseded in
      favor of some OTHER package, is not exempted;
    * a ``configs/`` fragment whose own declared ``run_id`` value(s) are
      disjoint from ``run_ids`` belongs to a different cell, not residue (see
      :func:`_is_foreign_config`);
    * failing THAT too (a resume/seal-only cell shares its parent's run id,
      so the parent's own ``configs/`` fragments are never disjoint either),
      a ``configs/`` fragment named in ``resume_parent_config_paths`` -- the
      specific experiment and baseline fragment(s) of the cell(s) the current
      re-pin's own ``resume_from`` chain names (see
      :func:`_resume_parent_config_paths`) -- is the parent's own sealed
      record, not residue (item E4-1, 2026-09-29): a resume/seal-only cell's
      FIRST re-pin inherits its parent's supply pin byte for byte, so the
      exact old value being superseded is still, legitimately, the frozen
      parent's own current pin. This never widens to every config quoting a
      shared run id (a genuinely foreign cell that happens to quote the old
      hash must still refuse); it names only the specific parent chain's own
      files.

    Both parent-chain exemptions (``resume_parent_config_paths`` and
    ``resume_parent_package_dirs``) name only the specific parent(s) the
    current re-pin's own ``resume_from`` points at; ``superseded_donor_package_dirs``
    names only the specific donor(s) the exposure ledger itself says were
    superseded BY this cell's own package. A genuinely foreign package or
    config that happens to quote the same old value, or the resume cell's
    OWN package (``readiness_dir``/``own_files``, scanned as strictly as
    ever), must still refuse.

    ``explain=True`` prints, to stderr, one line per file that still hits an
    old value: which of the rules above were considered for that file and
    what each one decided, so a refusal is diagnosable without re-deriving
    the exemption logic by hand.

    ``file_cache`` (optional, owner decision 270 A) lets several calls over the
    SAME unchanged tree -- the one-pass package re-pin runs this once per cell --
    share one directory listing and one read of every file. A file that carries
    none of the old values can never be a hit, so its exemption rules are not
    evaluated at all (the ledger is the one exception: it is always row-filtered).
    """

    cache = file_cache if file_cache is not None else {}
    values = sorted({value for value in old_values if value})
    if not values:
        return
    ledger_resolved = Path(exposure_ledger_path).resolve() if exposure_ledger_path else None
    readiness_dir_resolved = Path(readiness_dir).resolve() if readiness_dir is not None else None
    readiness_root_resolved = Path(repo_root).resolve() / "docs" / "readiness"
    attempt_ids = attempt_ids or set()
    own_resolved = {Path(p).resolve() for p in (own_files or ())} | {
        Path(p).resolve() for p in (own_config_paths or ())
    }
    resume_parent_resolved = {Path(p).resolve() for p in (resume_parent_config_paths or ())}
    resume_parent_package_resolved = {
        Path(p).resolve() for p in (resume_parent_package_dirs or ())
    }
    superseded_donor_package_resolved = {
        Path(p).resolve() for p in (superseded_donor_package_dirs or ())
    }
    own_package_name = readiness_dir_resolved.name if readiness_dir_resolved is not None else ""
    hits: list[str] = []
    for root_name in ("docs", "configs"):
        base = Path(repo_root) / root_name
        if not base.is_dir():
            continue
        listing_key = ("listing", str(base))
        if listing_key not in cache:
            cache[listing_key] = [item for item in sorted(base.rglob("*")) if item.is_file()]
        for path in cache[listing_key]:
            if path not in cache:
                try:
                    cache[path] = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    cache[path] = None
            text = cache[path]
            if text is None:
                continue
            is_ledger = (
                ledger_resolved is not None
                and run_ids is not None
                and path.name == ledger_resolved.name
                and path.resolve() == ledger_resolved
            )
            if not is_ledger and not any(value in text for value in values):
                continue
            resolved = path.resolve()
            is_own = resolved in own_resolved or (
                readiness_dir_resolved is not None and _is_within(resolved, readiness_dir_resolved)
            )
            scan_text = text
            considered: list[tuple[str, bool]] = []
            exempt = False
            if ledger_resolved is not None and run_ids is not None and resolved == ledger_resolved:
                lines = text.splitlines(keepends=True)
                foreign = _foreign_ledger_row_mask(text, run_ids)
                superseded_rows = _superseded_donor_ledger_row_mask(text, own_package_name=own_package_name)
                stripped = [
                    foreign[index] or (index < len(superseded_rows) and superseded_rows[index])
                    for index in range(len(lines))
                ]
                scan_text = "".join(line for index, line in enumerate(lines) if not stripped[index])
                considered.append(("ledger-foreign-rows-stripped", True))
            elif is_own:
                considered.append(("own", True))
            elif run_ids and root_name == "docs":
                foreign_package = _is_foreign_readiness_package(
                    resolved, readiness_root=readiness_root_resolved, run_ids=run_ids, text=text
                )
                considered.append(("foreign-readiness-package", foreign_package))
                if foreign_package:
                    exempt = True
                else:
                    sealed = _is_sealed_package_record(
                        resolved,
                        readiness_root=readiness_root_resolved,
                        repo_root=Path(repo_root),
                        attempt_ids=attempt_ids,
                        text=text,
                    )
                    considered.append(("sealed-package-record", sealed))
                    if sealed:
                        exempt = True
                    else:
                        resume_parent_package = _is_resume_parent_readiness_record(
                            resolved,
                            readiness_root=readiness_root_resolved,
                            resume_parent_package_dirs=resume_parent_package_resolved,
                        )
                        considered.append(("resume-parent-readiness-package", resume_parent_package))
                        if resume_parent_package:
                            exempt = True
                        else:
                            superseded_donor = _is_superseded_donor_readiness_record(
                                resolved,
                                readiness_root=readiness_root_resolved,
                                superseded_donor_package_dirs=superseded_donor_package_resolved,
                            )
                            considered.append(("superseded-donor-readiness-package", superseded_donor))
                            exempt = superseded_donor
            elif run_ids and root_name == "configs":
                foreign_config = _is_foreign_config(resolved, run_ids=run_ids)
                considered.append(("foreign-config", foreign_config))
                if foreign_config:
                    exempt = True
                else:
                    resume_parent_config = resolved in resume_parent_resolved
                    considered.append(("resume-parent-config", resume_parent_config))
                    exempt = resume_parent_config
            if exempt:
                continue
            for value in values:
                if value in scan_text:
                    hits.append(f"{path}: {value}")
                    if explain:
                        rule_summary = ", ".join(f"{name}={result}" for name, result in considered) or "no rule applicable (scanned strictly)"
                        print(f"[explain-residue] {path}: value {value} -- {rule_summary}", file=sys.stderr)
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
    prepare_branch_seeds_fn: PrepareSupplyFn = default_prepare_branch_seeds,
    run_check_fn: RunCheckFn = default_run_check,
    python: str = sys.executable,
    package_name: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    explain_residue: bool = False,
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
        # Item-4 GAP close (design section 5 item 4): the SAME verify-or-
        # rebuild treatment for a cell's Perception branch-seed artifact,
        # AFTER the phase supply above (a branch's own bootstrap reads
        # whatever prepared_phase_supply pin now stands, so ordering
        # matters). A no-op (skipped) for the overwhelming majority of
        # cells, which declare no Perception branch group at all.
        branch_seed_report = ensure_branch_seeds_pinned(
            repo_root=repo_root,
            data_root=data_root,
            runtime_root=runtime_root,
            lock_path=lock_path,
            experiment=experiment,
            identity=old_identity,
            prepare_branch_seeds_fn=prepare_branch_seeds_fn,
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
        if branch_seed_report.get("rebuilt"):
            old_pin = branch_seed_report.get("old_pin")
            new_pin = branch_seed_report["new_pin"]
            if old_pin is not None:
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
                "branch_seeds": branch_seed_report,
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
    attempt_ids = {identity.attempt_id for identity in old_identities.values()}
    resume_parent_attempt_ids = _resume_parent_attempt_ids(resolved)
    resume_parent_config_paths = _resume_parent_config_paths(repo_root, resume_parent_attempt_ids)
    # Item E4-2: only meaningful for a resume/seal-only cell -- for an
    # ordinary cell this would just resolve back to its own package, which is
    # already exempt by other means, so it is never resolved otherwise.
    resume_parent_package_dirs = (
        _resume_parent_package_dirs(repo_root, exposure_ledger_path, run_ids)
        if resume_parent_attempt_ids
        else set()
    )
    # Unconditional (unlike the resume-chain lookups above, which are only
    # meaningful for a resume/seal-only cell): a cell carried forward from a
    # superseded donor package is not signalled by anything this cell's own
    # config declares (unlike resume_from) -- only by the ledger marker on
    # the DONOR's own rows -- so this always scans the ledger for a marker
    # naming this cell's own package. Cheap (one ledger read, already parsed
    # elsewhere in this function) and a no-op whenever no such marker exists.
    superseded_donor_package_dirs = _superseded_donor_package_dirs(
        repo_root, exposure_ledger_path, readiness_dir
    )
    assert_no_residue(
        repo_root,
        all_old_values,
        exposure_ledger_path=exposure_ledger_path,
        run_ids=run_ids,
        attempt_ids=attempt_ids,
        readiness_dir=readiness_dir,
        own_files=package_files,
        own_config_paths=set(baseline_paths) | set(experiment_paths),
        resume_parent_config_paths=resume_parent_config_paths,
        resume_parent_package_dirs=resume_parent_package_dirs,
        superseded_donor_package_dirs=superseded_donor_package_dirs,
        explain=explain_residue,
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
    parser.add_argument(
        "--explain-residue",
        action="store_true",
        help=(
            "on a residue refusal, print to stderr which exemption rule(s) were "
            "considered for each hit file and what each one decided"
        ),
    )
    return parser


NINE_P_REFUSAL_EXIT = 64


def nine_p_refusal(repo_root: Path) -> str | None:
    """One-line refusal when ``repo_root`` resolves under ``/mnt/`` (9p), else ``None``.

    Owner 2026-10-12: hot paths (re-pin/flip loops, git-heavy tooling) run on Linux-native ext4. The data root
    is not affected. ``SAEA_ALLOW_9P_FLIP=1`` is the explicit escape hatch for the one-time migration.
    """

    if os.environ.get("SAEA_ALLOW_9P_FLIP") == "1":
        return None
    resolved = Path(repo_root).resolve().as_posix()
    if resolved == "/mnt" or resolved.startswith("/mnt/"):
        return (
            f"refusing: repo root {resolved} is on /mnt (9p); run from an ext4 worktree "
            "(scripts/flights/batch/flip_in_ext4.sh) or set SAEA_ALLOW_9P_FLIP=1"
        )
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if bool(args.decision) != bool(args.decision_id):
        parser.error("--decision and --decision-id must be given together")
    refusal = nine_p_refusal(Path(args.repo_root))
    if refusal is not None:
        print(refusal, file=sys.stderr)
        return NINE_P_REFUSAL_EXIT
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
            explain_residue=args.explain_residue,
        )
    except RepinError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
