"""Root-only lease handoff for an already-ready attach-only worker."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Callable, Mapping, TextIO

from ..bundle.git_commit import require_clean_study_repo
from ..session.serving import assert_identity_matches, find_resident_session
from .campaign import CampaignCell, CampaignError, declared_readiness, load_campaign_cells
from .factory import build_flight_runtime
from .lease import GenerationLease


class LeaseHandoffError(RuntimeError):
    """Refuse to issue or release an ambiguous worker capability."""


def _confined_token_path(data_root: Path, raw: Path) -> Path:
    root = Path(data_root).resolve()
    path = Path(raw)
    if path.is_absolute():
        candidate = path.resolve()
    else:
        candidate = (root / path).resolve()
    coordination = (root / "coordination").resolve()
    if not candidate.is_relative_to(coordination) or candidate.name in {"", ".", ".."}:
        raise LeaseHandoffError("token output must be confined beneath data-root/coordination")
    return candidate


def _write_token(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(document, sort_keys=True) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise LeaseHandoffError(f"refusing to overwrite token file: {path}") from error
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _preserve(lease: GenerationLease) -> None:
    """Close this process's descriptor while preserving lease metadata."""
    lease.__exit__(LeaseHandoffError, LeaseHandoffError("handoff remains root-owned"), None)


def handoff_worker_lease(
    *,
    repo_root: Path,
    data_root: Path,
    runtime_root: Path,
    lock_path: Path,
    experiment: str,
    cell: CampaignCell,
    owner: str,
    expected_session_id: str,
    token_output: Path,
    stage: str = "worker",
    input_stream: TextIO = sys.stdin,
    output_stream: TextIO = sys.stdout,
    runtime_factory: Callable = build_flight_runtime,
    lease_factory: Callable = GenerationLease.acquire,
    resident_finder: Callable = find_resident_session,
    study_head_factory: Callable = require_clean_study_repo,
) -> int:
    """Issue a worker token, wait for explicit ``release``, then clear it.

    Any EOF, wrong input, exception, or interrupt preserves lease metadata and
    the token file. Only the exact root command ``release`` releases custody.
    """
    repo_root, data_root, runtime_root, lock_path = map(
        Path, (repo_root, data_root, runtime_root, lock_path)
    )
    if stage not in {"worker", "prepare-window-features", "prompt-fit"}:
        raise LeaseHandoffError(
            "lease handoff stage must be worker, prepare-window-features or prompt-fit"
        )
    token_path = _confined_token_path(data_root, Path(token_output))
    if not owner.strip() or not expected_session_id.strip():
        raise LeaseHandoffError("owner and expected session id must be nonempty")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", expected_session_id) is None:
        raise LeaseHandoffError("expected session id must be one plain path segment")
    try:
        cell.assert_mode(stage)
    except CampaignError as error:
        raise LeaseHandoffError(f"cell does not permit {stage} stage: {error}") from error
    readiness = declared_readiness(cell, data_root)
    if readiness.state != "ready":
        raise LeaseHandoffError(f"{stage} readiness is {readiness.state}: {readiness.reason}")
    if cell.dependencies():
        raise LeaseHandoffError(
            f"standalone {stage} handoff refuses declared flight dependencies"
        )
    if token_path.exists():
        raise LeaseHandoffError(f"refusing to overwrite token file: {token_path}")

    runtime = runtime_factory(
        repo_root, data_root, model=cell.document["model_fragment"],
        dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
        experiment=experiment, run_id=cell.run_id, attempt_id=cell.attempt_id,
        runtime_root=runtime_root, lock_path=lock_path,
    )
    required_identity = runtime.session_required_identity()
    resident = resident_finder(data_root)
    if resident is None:
        raise LeaseHandoffError("required resident session is absent; refusing to issue worker capability")
    _, session_document = resident
    if session_document.get("session_id") != expected_session_id:
        raise LeaseHandoffError("resident session differs from expected session")
    try:
        assert_identity_matches(session_document, required_identity)
    except Exception as error:  # noqa: BLE001 -- preserve exact identity refusal
        raise LeaseHandoffError(f"resident session identity mismatch: {error}") from error

    lease = lease_factory(
        data_root, owner=owner, run_id=cell.run_id, attempt_id=cell.attempt_id,
        session_id=expected_session_id, study_head=study_head_factory(repo_root),
    )
    token_document = {
        "schema": "saea-worker-lease-handoff-v1",
        "token": lease.token, "run_id": cell.run_id, "attempt_id": cell.attempt_id,
        "session_id": expected_session_id,
    }
    if stage != "worker":
        token_document["stage"] = stage
    ready_event = "worker-lease-ready" if stage == "worker" else f"{stage}-lease-ready"
    try:
        _write_token(token_path, token_document)
        output_stream.write(json.dumps({
            "event": ready_event, "run_id": cell.run_id,
            "attempt_id": cell.attempt_id, "session_id": expected_session_id,
            "token_path": str(token_path),
        }, sort_keys=True) + "\n")
        output_stream.flush()
        command = input_stream.readline()
        if command == "":
            _preserve(lease)
            output_stream.write(json.dumps({"event": f"{stage}-lease-preserved", "reason": "stdin EOF"}) + "\n")
            output_stream.flush()
            return 2
        if command not in {"release", "release\n", "release\r\n"}:
            _preserve(lease)
            output_stream.write(json.dumps({"event": f"{stage}-lease-preserved", "reason": "explicit release required"}) + "\n")
            output_stream.flush()
            return 2
        lease.release()
        token_path.unlink()
        output_stream.write(json.dumps({
            "event": f"{stage}-lease-released", "run_id": cell.run_id,
            "attempt_id": cell.attempt_id, "session_id": expected_session_id,
        }, sort_keys=True) + "\n")
        output_stream.flush()
        return 0
    except (KeyboardInterrupt, EOFError):
        _preserve(lease)
        return 2
    except BaseException:
        _preserve(lease)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=("worker", "prepare-window-features", "prompt-fit"), default="worker"
    )
    for name in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "cell", "owner", "expected-session-id", "token-output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    repo, data_root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    cells = load_campaign_cells(repo, args.experiment)
    selected = tuple(cell for cell in cells if cell.document["cell_id"] == args.cell)
    if len(selected) != 1:
        parser.error("--cell must select exactly one declared campaign cell")
    return handoff_worker_lease(
        repo_root=repo, data_root=data_root, runtime_root=Path(args.runtime_root),
        lock_path=Path(args.lock_path), experiment=args.experiment, cell=selected[0],
        owner=args.owner, expected_session_id=args.expected_session_id,
        token_output=Path(args.token_output), stage=args.stage,
    )


if __name__ == "__main__":
    raise SystemExit(main())
