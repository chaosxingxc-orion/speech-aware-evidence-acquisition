"""One-pass package re-pin (owner decision 270 A, 2026-10-12).

The iterative flip (``scripts/flights/batch/flip_package_ext4.sh`` in its default
``iterate`` mode) converges a registered package by repetition: every cell's
``core.flight.repin`` call rewrites files that every OTHER cell's documents pin --
the package protocol document (whose sha256 every plan quotes), the plans (whose
sha256 the exposure-ledger notes quote), the preregistration and the ledger rows
-- commits, and the next cell's call changes those shared bytes again. Each cell
therefore needs two or three inner passes, the package two outer passes and a
pins-refresh round in between.

Nothing in that chain is genuinely circular. The dependency graph is a DAG::

    fragments (baseline pin, readiness block, decision requirement)
        -> composed config hash C_k and protocol hash Q_k of every cell k
        -> text of the protocol document, the plans, the README, the preregistration
        -> sha256 D of the protocol document            (quoted by every plan)
        -> baseline pin copied into the plans (refresh_registered_plan_pins)
        -> sha256 S_k of each plan                       (quoted by ledger row k only)

so the fixed point can be computed in one forward sweep over all cells together.
:func:`repin_package_one_pass` does exactly that, model-free:

1. refusals (clean tree, rows available, current pins present) exactly as
   :func:`~speech_aware_evidence_acquisition.core.flight.repin.repin_package`;
2. phase A -- the fragment fixed point: ``ensure_artifact_pinned``,
   ``ensure_branch_seeds_pinned`` and ``apply_decision_and_readiness`` for every
   cell, repeated ONLY for cells whose fragments changed in the previous round
   (bounded; this is the one part that stays iterative, see below);
3. phase B -- the text fixed point: every cell's old->new mapping is applied once
   to the package files, the protocol document sha D is recomputed once and
   propagated, the registered-plan pins are refreshed from the final baselines,
   and each plan sha S_k is propagated into its own ledger row (the ledger is
   always scoped per cell, as in the iterative path);
4. the residue check, per cell with that cell's own exemption parameters, over one
   shared read of the tree;
5. ONE commit of every touched path;
6. ``core.flight.cli check`` once per cell on the committed tree, asserting the
   measured config and protocol hashes (``core.flight.cli check`` refuses a dirty
   tree, so the check follows the commit; a failing check leaves the commit on the
   ext4 flip branch and the flip wrapper then never fast-forwards master).

What stays iterative (a true fixed point is impossible or not provable offline):

* a prepared artifact whose identity binds the configuration that contains its own
  pin: ``ensure_artifact_pinned`` drops the pin while it builds, then verifies the
  artifact against the final configuration; phase A re-verifies every cell whose
  fragments changed, up to :data:`MAX_FRAGMENT_ROUNDS` rounds, and refuses by name
  if the fragments do not settle;
* any document that quotes the git commit that will contain it: a commit id cannot
  be known before the commit, so such a quote cannot be a fixed point of a single
  commit (the registered packages carry the all-zero placeholder instead, and the
  flight-commit files outside git record HEAD afterwards);
* a protocol document that quoted its own sha256 (none does; the sha is held by the
  plans that sit downstream of the document).

Hash semantics are unchanged: only the existing helpers of
:mod:`~speech_aware_evidence_acquisition.core.flight.repin` rewrite bytes, so the
converged tree is byte-identical to the iterative mode's.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from .campaign import CampaignCell, CampaignError, load_campaign_cells
from .repin import (
    NINE_P_REFUSAL_EXIT,
    CellIdentity,
    PrepareSupplyFn,
    RepinError,
    RunCheckFn,
    _collect_plan_hashes_from_notes,
    _collect_protocol_document_hashes,
    _package_files_for,
    _PROTOCOL_DOCUMENT_NAME,
    _RecordOrder,
    _pair_experiments_and_cells,
    _resolve_ledger_artifacts,
    _resolve_under_repo,
    _resume_parent_attempt_ids,
    _resume_parent_config_paths,
    _resume_parent_package_dirs,
    _superseded_donor_package_dirs,
    apply_decision_and_readiness,
    apply_mapping_to_files,
    apply_mapping_to_ledger,
    assert_clean_tree,
    assert_current_pins_present,
    assert_no_residue,
    assert_rows_available,
    baseline_fragment_path,
    compute_cell_identity,
    default_prepare_branch_seeds,
    default_prepare_supply,
    default_run_check,
    ensure_artifact_pinned,
    ensure_branch_seeds_pinned,
    experiment_fragment_path,
    nine_p_refusal,
)

#: Upper bound on phase-A rounds. Round 1 mints pins and flips readiness; round 2 re-verifies the cells
#: round 1 changed and is normally the last. A third round is only reached when a rebuild itself changed
#: the fragments; four rounds without settling means the identity is genuinely self-referential.
MAX_FRAGMENT_ROUNDS = 4

RefreshFn = Callable[[Path, Path], list[dict]]


def _extend_chain(chain: dict[str, str], old: str, new: str) -> None:
    """Record ``old -> new`` and compress earlier links so every key points at the CURRENT value."""

    if not old or old == new:
        return
    for key, value in list(chain.items()):
        if value == old:
            chain[key] = new
    chain[old] = new


def _chain_pairs(chain: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in chain.items() if key != value}


def _fragment_bytes(repo_root: Path, experiment: str, identity: CellIdentity) -> tuple[bytes, bytes]:
    return (
        baseline_fragment_path(repo_root, identity.baseline_fragment).read_bytes(),
        experiment_fragment_path(repo_root, experiment).read_bytes(),
    )


def load_refresh_fn(repo_root: Path) -> RefreshFn:
    """Bind ``refresh_registered_plan_pins.refresh_package`` (a script, not a package module).

    The repository's own copy is preferred so a worktree uses the tool it was checked out with; the copy
    beside this module is the fallback for a synthetic repository."""

    candidates = [
        Path(repo_root) / "scripts" / "flights" / "refresh_registered_plan_pins.py",
        Path(__file__).resolve().parents[4] / "scripts" / "flights" / "refresh_registered_plan_pins.py",
    ]
    for candidate in candidates:
        if candidate.is_file():
            spec = importlib.util.spec_from_file_location("saea_refresh_registered_plan_pins", candidate)
            assert spec is not None and spec.loader is not None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            def refresh(repo: Path, package: Path, _module=module) -> list[dict]:
                try:
                    return _module.refresh_package(repo, package, None, False)
                except _module.RefreshError as error:
                    raise RepinError(f"plan pin refresh refused: {error}") from error

            return refresh
    raise RepinError("refresh_registered_plan_pins.py not found in the repository or beside the tool")


def _git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=str(repo_root), capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise RepinError(f"git {' '.join(args)} failed: {completed.stderr.strip() or completed.stdout.strip()}")
    return completed.stdout


def _tracked_dirt(repo_root: Path) -> list[str]:
    return [line for line in _git(repo_root, "status", "--porcelain", "--untracked-files=no").splitlines() if line.strip()]


def repin_package_one_pass(
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
    run_check_fn: RunCheckFn | None = default_run_check,
    python: str = sys.executable,
    package_name: str | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    explain_residue: bool = False,
    refresh_pins: bool = True,
    refresh_fn: RefreshFn | None = None,
    commit_message_file: Path | None = None,
    ready_receipt_cells: Sequence[str] = (),
    max_fragment_rounds: int = MAX_FRAGMENT_ROUNDS,
) -> dict[str, object]:
    """Re-pin every selected cell of ONE package in a single forward sweep and commit once.

    ``experiments`` is the union of every ``(experiment_id, cell_id_or_None)`` pair the iterative flip would
    re-pin one call at a time. ``commit_message_file`` names the single commit's message; without it nothing
    is committed and ``run_check_fn`` must be ``None`` (the flight check needs a committed, clean tree).
    ``ready_receipt_cells`` names the cells whose check result is also written as
    ``coordination/<package>/check-<cell>-ready-v1.json`` (the ``ARM=1`` receipt of ``repin_cell_generic.sh``).
    """

    timings: dict[str, float] = {}
    started = time.monotonic()

    def tick(name: str) -> None:
        nonlocal started
        current = time.monotonic()
        timings[name] = round(current - started, 3)
        started = current

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
    if run_check_fn is not None and commit_message_file is None:
        raise RepinError("a flight check needs a committed, clean tree: pass commit_message_file (or run_check_fn=None)")
    if commit_message_file is not None and not Path(commit_message_file).is_file():
        raise RepinError(f"commit message file does not exist: {commit_message_file}")

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
    tick("preflight")

    # ---- phase A: the fragment fixed point (the only iterative part) -----------------------------------
    current = dict(old_identities)
    chains: dict[str, dict[str, str]] = {cell.run_id: {} for _e, cell in resolved}
    artifact_reports: dict[str, list[dict]] = {cell.run_id: [] for _e, cell in resolved}
    branch_reports: dict[str, list[dict]] = {cell.run_id: [] for _e, cell in resolved}
    active = list(resolved)
    rounds = 0
    while active:
        if rounds >= max_fragment_rounds:
            raise RepinError(
                f"fragments of {sorted(c.run_id for _e, c in active)} did not settle after {max_fragment_rounds} "
                "rounds: a prepared artifact identity that depends on the configuration holding its own pin "
                "has no one-pass fixed point; use --mode iterate"
            )
        rounds += 1
        changed: list[tuple[str, CampaignCell]] = []
        for experiment, cell in active:
            identity = current[cell.run_id]
            before = _fragment_bytes(repo_root, experiment, identity)
            artifact_report = ensure_artifact_pinned(
                repo_root=repo_root,
                data_root=data_root,
                runtime_root=runtime_root,
                lock_path=lock_path,
                experiment=experiment,
                identity=identity,
                prepare_supply_fn=prepare_supply_fn,
                allow_output_change=allow_output_change,
            )
            branch_seed_report = ensure_branch_seeds_pinned(
                repo_root=repo_root,
                data_root=data_root,
                runtime_root=runtime_root,
                lock_path=lock_path,
                experiment=experiment,
                identity=identity,
                prepare_branch_seeds_fn=prepare_branch_seeds_fn,
                allow_output_change=allow_output_change,
            )
            apply_decision_and_readiness(
                repo_root=repo_root,
                data_root=data_root,
                experiment=experiment,
                cell_id=identity.cell_id,
                decision=decision,
                set_ready=set_ready,
            )
            new_identity = compute_cell_identity(repo_root, experiment, cell)
            chain = chains[cell.run_id]
            for report in (artifact_report, branch_seed_report):
                if report.get("rebuilt"):
                    old_pin = report.get("old_pin")
                    new_pin = report["new_pin"]
                    if old_pin is not None:
                        _extend_chain(chain, old_pin["relpath"], new_pin["relpath"])
                        _extend_chain(chain, old_pin["sha256"], new_pin["sha256"])
            _extend_chain(chain, identity.config_hash, new_identity.config_hash)
            _extend_chain(chain, identity.protocol_hash, new_identity.protocol_hash)
            artifact_reports[cell.run_id].append(artifact_report)
            branch_reports[cell.run_id].append(branch_seed_report)
            current[cell.run_id] = new_identity
            if _fragment_bytes(repo_root, experiment, new_identity) != before:
                changed.append((experiment, cell))
        active = changed
    tick("fragments")

    # ---- phase B: the text fixed point ------------------------------------------------------------------
    union_mapping: dict[str, str] = {}
    for chain in chains.values():
        union_mapping.update(_chain_pairs(chain))
    package_files = sorted(set(readiness_dir.glob("*.json")) | {preregistration_path})
    readme_path = readiness_dir / "README.md"
    if readme_path.is_file():
        package_files.append(readme_path)
    protocol_document_path = readiness_dir / _PROTOCOL_DOCUMENT_NAME
    rewritten: dict[str, int] = {}

    def merge(update: Mapping[str, int]) -> None:
        for key, value in update.items():
            rewritten[key] = rewritten.get(key, 0) + value

    def ledger_per_cell(per_run_mapping: Mapping[str, Mapping[str, str]]) -> None:
        for run_id, mapping in per_run_mapping.items():
            if not mapping:
                continue
            count = apply_mapping_to_ledger(exposure_ledger_path, {run_id}, mapping)
            if count:
                key = str(exposure_ledger_path)
                rewritten[key] = rewritten.get(key, 0) + count

    # round 1: composed/protocol hashes and artifact pins (package files: every cell's mapping; ledger: per cell)
    merge(apply_mapping_to_files(package_files, union_mapping))
    ledger_per_cell({run_id: _chain_pairs(chain) for run_id, chain in chains.items()})

    # round 2: the protocol document's own sha256, computed ONCE, quoted by every plan
    if protocol_document_path.is_file():
        old_doc_hashes = _collect_protocol_document_hashes(package_files, protocol_document_path)
        new_doc_hash = hashlib.sha256(protocol_document_path.read_bytes()).hexdigest()
        doc_mapping = {old: new_doc_hash for old in old_doc_hashes if old and old != new_doc_hash}
        if doc_mapping:
            merge(apply_mapping_to_files(package_files, doc_mapping))
            ledger_per_cell({run_id: doc_mapping for run_id in run_ids})

    # the plan pins refresh (the iterative path ran it between its two flip loops)
    refresh_results: list[dict] = []
    if refresh_pins:
        refresh = refresh_fn if refresh_fn is not None else load_refresh_fn(repo_root)
        refresh_results = refresh(repo_root, readiness_dir)

    # round 3: each registered plan's own sha256 (after the refresh rewrote the plans), ledger row of the cell only
    ledger_text = exposure_ledger_path.read_text(encoding="utf-8")
    artifacts_by_run = _resolve_ledger_artifacts(ledger_text, run_ids)
    old_plan_hashes = _collect_plan_hashes_from_notes(ledger_text, run_ids)
    plan_mapping: dict[str, dict[str, str]] = {}
    for run_id, relpath in artifacts_by_run.items():
        plan_path = Path(repo_root) / relpath
        if not plan_path.is_file():
            raise RepinError(f"exposure ledger artifact for {run_id} not found: {relpath}")
        new_hash = hashlib.sha256(plan_path.read_bytes()).hexdigest()
        old_hash = old_plan_hashes.get(run_id)
        if old_hash and old_hash != new_hash:
            plan_mapping[run_id] = {old_hash: new_hash}
    ledger_per_cell(plan_mapping)
    tick("rewrite")

    # ---- residue, per cell, over one shared read of the tree ------------------------------------------------
    file_cache: dict = {}
    superseded_donor_package_dirs = _superseded_donor_package_dirs(repo_root, exposure_ledger_path, readiness_dir)
    for experiment, cell in resolved:
        identity = old_identities[cell.run_id]
        parent_attempts = _resume_parent_attempt_ids([(experiment, cell)])
        assert_no_residue(
            repo_root,
            set(_chain_pairs(chains[cell.run_id])),
            exposure_ledger_path=exposure_ledger_path,
            run_ids={cell.run_id},
            attempt_ids={identity.attempt_id},
            readiness_dir=readiness_dir,
            own_files=_package_files_for(readiness_dir, preregistration_path),
            own_config_paths={
                baseline_fragment_path(repo_root, cell.document["baseline_fragment"]),
                experiment_fragment_path(repo_root, experiment),
            },
            resume_parent_config_paths=_resume_parent_config_paths(repo_root, parent_attempts),
            resume_parent_package_dirs=(
                _resume_parent_package_dirs(repo_root, exposure_ledger_path, {cell.run_id}) if parent_attempts else set()
            ),
            superseded_donor_package_dirs=superseded_donor_package_dirs,
            explain=explain_residue,
            file_cache=file_cache,
        )
    tick("residue")

    # ---- ONE commit ----------------------------------------------------------------------------------------
    commit_sha: str | None = None
    if commit_message_file is not None:
        if _tracked_dirt(repo_root):
            paths = sorted(
                {str(Path(p).resolve().relative_to(repo_root.resolve())).replace("\\", "/") for p in expected_touched}
            )
            _git(repo_root, "add", "--", *paths)
            leftover = [
                line for line in _git(repo_root, "status", "--porcelain", "--untracked-files=no").splitlines()
                if line[1:2].strip()
            ]
            if leftover:
                raise RepinError("tracked changes outside the paths this tool rewrites:\n" + "\n".join(leftover))
            _git(repo_root, "commit", "-q", "-F", str(commit_message_file))
        commit_sha = _git(repo_root, "rev-parse", "HEAD").strip()
    tick("commit")

    # ---- the per-cell check, once, on the committed tree ---------------------------------------------------
    check_reports: list[dict[str, object]] = []
    if run_check_fn is not None:
        coordination_dir = Path(data_root) / "coordination" / package_name
        coordination_dir.mkdir(parents=True, exist_ok=True)
        timestamp = now().strftime("%Y%m%dT%H%M%SZ")
        for experiment, cell in resolved:
            identity = current[cell.run_id]
            result = run_check_fn(
                repo_root=repo_root,
                data_root=data_root,
                runtime_root=runtime_root,
                lock_path=lock_path,
                experiment=experiment,
                cell_id=identity.cell_id,
                python=python,
            )
            payload = json.dumps(result, indent=2, sort_keys=True, default=str) + "\n"
            receipt_path = coordination_dir / f"check-{identity.cell_id}-repin-{timestamp}.json"
            receipt_path.write_text(payload, encoding="utf-8")
            preflight = result.get("preflight") if isinstance(result, Mapping) else None
            measured_config = preflight.get("config_hash") if isinstance(preflight, Mapping) else None
            measured_protocol = preflight.get("protocol_hash") if isinstance(preflight, Mapping) else None
            if measured_config != identity.config_hash or measured_protocol != identity.protocol_hash:
                raise RepinError(
                    f"core.flight.cli check for {experiment}/{identity.cell_id} measured "
                    f"config_hash={measured_config!r} protocol_hash={measured_protocol!r}, "
                    f"expected {identity.config_hash!r} / {identity.protocol_hash!r}"
                )
            report = {"experiment": experiment, "cell": identity.cell_id, "run_id": identity.run_id, "receipt": str(receipt_path)}
            if identity.cell_id in set(ready_receipt_cells):
                ready_path = coordination_dir / f"check-{identity.cell_id}-ready-v1.json"
                ready_path.write_text(payload, encoding="utf-8")
                report["ready_receipt"] = str(ready_path)
            check_reports.append(report)
    tick("check")

    cell_reports = []
    for experiment, cell in resolved:
        old, new = old_identities[cell.run_id], current[cell.run_id]
        cell_reports.append(
            {
                "experiment": experiment,
                "cell": old.cell_id,
                "run_id": old.run_id,
                "old": {"config_hash": old.config_hash, "protocol_hash": old.protocol_hash},
                "new": {"config_hash": new.config_hash, "protocol_hash": new.protocol_hash},
                "artifact": artifact_reports[cell.run_id][-1] if artifact_reports[cell.run_id] else {},
                "artifact_rounds": artifact_reports[cell.run_id],
                "branch_seeds": branch_reports[cell.run_id][-1] if branch_reports[cell.run_id] else {},
            }
        )
    return {
        "schema": "saea-repin-one-pass-summary-v1",
        "package": package_name,
        "readiness_dir": str(readiness_dir),
        "mode": "one-pass",
        "fragment_rounds": rounds,
        "cells": cell_reports,
        "files_rewritten": rewritten,
        "plan_pins_refreshed": [r for r in refresh_results if r.get("status") == "refreshed"],
        "commit": commit_sha,
        "checks": check_reports,
        "timings_seconds": timings,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
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
    parser.add_argument("--explain-residue", action="store_true")
    parser.add_argument("--no-refresh-pins", action="store_true", help="skip the registered-plan pins refresh")
    parser.add_argument("--commit-message-file", default=None, help="commit once with this message, then check")
    parser.add_argument("--ready-receipt", action="append", default=[], help="cell id whose check is also written as check-<cell>-ready-v1.json")
    parser.add_argument(
        "--flight-commit-file", action="append", default=[], help="write the final HEAD sha to this file (repeatable)"
    )
    parser.add_argument("--no-check", action="store_true", help="skip core.flight.cli check (tests / dry staging only)")
    return parser


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
        summary = repin_package_one_pass(
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
            prepare_branch_seeds_fn=default_prepare_branch_seeds,
            run_check_fn=None if args.no_check else default_run_check,
            python=args.python,
            package_name=args.package_name,
            explain_residue=args.explain_residue,
            refresh_pins=not args.no_refresh_pins,
            commit_message_file=Path(args.commit_message_file) if args.commit_message_file else None,
            ready_receipt_cells=tuple(args.ready_receipt),
        )
    except RepinError as error:
        print(json.dumps({"error": str(error)}, indent=2), file=sys.stderr)
        return 1
    head = _git(Path(args.repo_root), "rev-parse", "HEAD").strip()
    for path in args.flight_commit_file:
        Path(path).write_text(head + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
