"""Config-driven campaign custody on the existing FlightQueue and FlightRuntime.

Only the coordinator acquires a generation lease. Workers attach to its named
resident session. A missing or mismatching profile stays held for an explicit
root service switch through the existing serving-session owner; no campaign
worker has a service start/stop fallback.
"""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..bundle.git_commit import require_clean_study_repo
from ..session.serving import assert_identity_matches, find_resident_session
from .lease import GenerationLease, WorkerExecutionPolicy
from .queue import FlightDependency, FlightQueue, FlightReadiness
from .runtime import FlightRuntime


EXECUTION_STAGES = frozenset({"check", "wire-check", "prepare-supply", "prompt-fit", "worker", "campaign"})


class CampaignError(ValueError):
    """A campaign is missing explicit identity, readiness or ownership."""


@dataclass(frozen=True)
class CampaignCell:
    document: Mapping[str, object]

    @classmethod
    def from_document(cls, document: Mapping[str, object]) -> CampaignCell:
        required = {
            "cell_id", "model_fragment", "dataset_fragment", "baseline_fragment",
            "run_id", "attempt_id",
        }
        if any(not isinstance(document.get(name), str) or not document[name] for name in required):
            raise CampaignError(f"campaign cell required fields: {sorted(required)}")
        readiness = document.get("readiness")
        if not isinstance(readiness, Mapping) or readiness.get("state") not in {
            "ready", "held", "preparation-pending",
        }:
            raise CampaignError("campaign cell requires explicit scientific readiness")
        stages = document.get("allowed_execution_stages")
        if stages is not None and (
            not isinstance(stages, list) or not stages
            or any(not isinstance(stage, str) for stage in stages)
            or len(stages) != len(set(stages)) or not set(stages) <= EXECUTION_STAGES
        ):
            raise CampaignError("allowed execution stages must be unique known modes")
        return cls(dict(document))

    def assert_mode(self, mode: str) -> None:
        """Enforce declared stage custody before any runtime or session work."""
        if mode not in self.document.get("allowed_execution_stages", EXECUTION_STAGES):
            raise CampaignError(
                f"cell {self.document['cell_id']} does not permit execution stage {mode}"
            )

    @property
    def run_id(self) -> str:
        return str(self.document["run_id"])

    @property
    def attempt_id(self) -> str:
        return str(self.document["attempt_id"])

    def dependencies(self) -> tuple[FlightDependency, ...]:
        return tuple(
            FlightDependency(item["run_id"], item.get("required_state", "scored"))
            for item in self.document["readiness"].get("depends_on", ())
        )


def load_campaign_cells(repo_root: Path, experiment: str) -> tuple[CampaignCell, ...]:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", experiment) is None:
        raise CampaignError("experiment must be a plain fragment id")
    path = Path(repo_root) / "configs/experiment" / f"{experiment}.json"
    document = json.loads(path.read_text(encoding="utf-8"))
    cells = tuple(CampaignCell.from_document(item) for item in document.get("cells", ()))
    if not cells:
        raise CampaignError("campaign experiment must declare cells")
    for name in ("cell_id", "run_id"):
        if len({cell.document[name] for cell in cells}) != len(cells):
            raise CampaignError(f"campaign repeats {name}")
    return cells


def declared_readiness(cell: CampaignCell, data_root: Path) -> FlightReadiness:
    readiness = cell.document["readiness"]
    if readiness["state"] != "ready":
        return FlightReadiness(readiness["state"], str(readiness.get("reason", "")))
    root = Path(data_root).resolve()
    for item in readiness.get("requirements", ()):
        if item.get("kind") not in {"preparation", "decision"}:
            raise CampaignError("readiness requirements must be preparation or decision receipts")
        relative, digest = item.get("relpath"), item.get("sha256")
        if not isinstance(relative, str) or not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            raise CampaignError("readiness requirements need a relative path and SHA-256")
        path = root / relative
        if Path(relative).is_absolute() or "\\" in relative or ".." in Path(relative).parts or not path.resolve().is_relative_to(root):
            raise CampaignError("readiness requirement path must be confined beneath data root")
        state = "preparation-pending" if item["kind"] == "preparation" else "held"
        reason = str(item.get("reason", f"{item['kind']} receipt required"))
        if not path.is_file():
            return FlightReadiness(state, f"{reason}: missing {relative}")
        with path.open("rb") as handle:
            actual = hashlib.file_digest(handle, "sha256").hexdigest()
        if actual != digest:
            return FlightReadiness(state, f"{reason}: hash mismatch for {relative}")
    return FlightReadiness.ready()


def run_campaign(
    flights: Sequence[FlightRuntime], *, cells: Sequence[CampaignCell],
    repo_root: Path, data_root: Path, owner: str, expected_session_id: str,
    resident_finder=find_resident_session,
) -> Mapping[str, object]:
    """Run ready workers serially; overlap full-manifest scoring between leases."""
    if not owner.strip() or not expected_session_id.strip():
        raise CampaignError("coordinator owner and expected resident session must be explicit")
    by_run = {cell.run_id: cell for cell in cells}
    if len(by_run) != len(cells) or {flight.run_id for flight in flights} != set(by_run):
        raise CampaignError("campaign runtime roster differs from declared cell identities")

    def readiness(flight):
        cell = by_run[flight.run_id]
        try:
            cell.assert_mode("campaign")
        except CampaignError as error:
            return FlightReadiness("held", str(error))
        if flight.attempt_id != cell.attempt_id:
            raise CampaignError("runtime attempt differs from the registered campaign cell")
        state = declared_readiness(cell, data_root)
        if state.state != "ready":
            return state
        resident = resident_finder(data_root)
        if resident is None:
            return FlightReadiness("held", "resident session absent; root must start the pinned profile")
        _, document = resident
        if document.get("session_id") != expected_session_id:
            return FlightReadiness("held", "resident session differs from the coordinator session")
        try:
            assert_identity_matches(document, flight.session_required_identity())
        except Exception as error:  # noqa: BLE001 -- identity refusal must stay visible
            return FlightReadiness("held", f"root profile switch required: {error}")
        return FlightReadiness.ready()

    @contextmanager
    def custody(flight):
        with GenerationLease.acquire(
            data_root, owner=owner, run_id=flight.run_id, attempt_id=flight.attempt_id,
            session_id=expected_session_id, study_head=require_clean_study_repo(repo_root),
        ) as lease:
            flight.bind_execution_policy(WorkerExecutionPolicy(expected_session_id, lease.token))
            yield

    queue = FlightQueue(
        flights, readiness=readiness,
        dependencies={cell.run_id: cell.dependencies() for cell in cells},
        execution_context_factory=custody, include_per_sample=True,
    )
    try:
        while queue.pending:
            completed = queue.run()
            queue.drain_scores()
            if not completed:
                break
        return {
            "schema": "saea-campaign-status-v1",
            "states": {key: asdict(value) for key, value in queue.states.items()},
            "pending": [flight.run_id for flight in queue.pending],
            "completed": [entry.flight.run_id for entry in queue.completed],
        }
    finally:
        queue.shutdown()
