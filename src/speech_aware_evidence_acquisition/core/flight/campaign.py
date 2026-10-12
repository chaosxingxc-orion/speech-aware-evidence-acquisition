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
from typing import TYPE_CHECKING, Mapping, Sequence

from ..bundle.git_commit import require_clean_study_repo
from ..session.serving import assert_identity_matches, find_resident_session
from .lease import GenerationLease, WorkerExecutionPolicy
from .queue import FlightDependency, FlightQueue, FlightReadiness
from .receipts import persist_flight_receipts
from .resume import ResumeRecoveryError, resume_declarations_from_document

if TYPE_CHECKING:  # annotations only; keeps the re-pin / light paths off the runtime stack
    from .runtime import FlightRuntime


EXECUTION_STAGES = frozenset({
    "check",
    "wire-check",
    "prepare-supply",
    "prepare-phase-recall",
    "prepare-branch-seeds",
    "prepare-window-inventory",
    "prepare-speech-observation-sources",
    "prepare-window-features",
    "prompt-fit",
    "worker",
    "campaign",
    "node-panel",
    "node-panel-worker",
    # E10d (2026-09-29): a cell whose declared predecessor(s) already cover
    # its whole roster seals with zero contacts -- no serving requirement, no
    # lease. See core.flight.cli's "seal-only" mode.
    "seal-only",
})


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
        # E10 (owner decision 22, 2026-09-18): a recovery cell may declare the
        # aborted attempt of its OWN run id whose complete rows it resumes.
        # E10d (2026-09-29): or a LIST of several pinned predecessor attempts
        # (core.flight.resume.MergedPredecessors) whose union it resumes,
        # possibly covering the whole roster (a seal-only cell). Validated
        # here so a malformed declaration refuses at cell load -- before a
        # runtime, a lease or a session exists.
        resume = document.get("resume_from")
        if resume is not None:
            try:
                declarations = resume_declarations_from_document(resume)
            except ResumeRecoveryError as error:
                raise CampaignError(f"cell resume_from is invalid: {error}") from error
            self_named = [
                declaration.attempt_id for declaration in declarations
                if declaration.attempt_id == document["attempt_id"]
            ]
            if self_named:
                raise CampaignError(
                    "cell resume_from names this recovery's own attempt_id as one "
                    "of its predecessors; every predecessor must be an ABORTED "
                    "attempt, never this recovery attempt"
                )
        return cls(dict(document))

    def assert_mode(self, mode: str) -> None:
        """Enforce declared stage custody before any runtime or session work."""
        stages = self.document.get("allowed_execution_stages")
        if mode in {"prepare-window-inventory", "prepare-window-features", "prepare-speech-observation-sources", "node-panel", "node-panel-worker"} and stages is None:
            raise CampaignError(
                f"cell {self.document['cell_id']} must explicitly permit "
                f"execution stage {mode}"
            )
        if mode not in (stages if stages is not None else EXECUTION_STAGES):
            raise CampaignError(
                f"cell {self.document['cell_id']} does not permit execution stage {mode}"
            )

    @property
    def run_id(self) -> str:
        return str(self.document["run_id"])

    @property
    def attempt_id(self) -> str:
        return str(self.document["attempt_id"])

    @property
    def resume_from(self) -> Mapping[str, object] | list[Mapping[str, object]] | None:
        """The aborted attempt(s) this recovery cell resumes, or ``None``.

        A single mapping for the original one-predecessor shape; a LIST of
        mappings for E10d's multi-predecessor form -- returned as a genuine
        ``list`` (never coerced through ``dict()``, which would refuse a
        list of more than two mappings with a confusing "too many values to
        unpack" instead of this module's own validation).
        """

        resume = self.document.get("resume_from")
        if resume is None:
            return None
        if isinstance(resume, list):
            return [dict(item) for item in resume]
        return dict(resume)

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
        if item.get("kind") == "decision" and (
            not isinstance(item.get("expected_decision_id"), str)
            or not item["expected_decision_id"].strip()
        ):
            raise CampaignError("decision readiness requirements need expected_decision_id")
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
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            return FlightReadiness(state, f"{reason}: hash mismatch for {relative}")
        if item["kind"] == "decision":
            try:
                receipt = json.loads(raw.decode("utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                return FlightReadiness("held", f"{reason}: invalid decision receipt {relative}: {error}")
            if not isinstance(receipt, Mapping):
                return FlightReadiness("held", f"{reason}: decision receipt {relative} must be an object")
            if receipt.get("schema") != "saea-campaign-decision-v1":
                return FlightReadiness("held", f"{reason}: decision receipt schema is not saea-campaign-decision-v1")
            decision_id = receipt.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id.strip():
                return FlightReadiness("held", f"{reason}: decision receipt has no nonempty decision_id")
            if decision_id != item["expected_decision_id"]:
                return FlightReadiness(
                    "held",
                    f"{reason}: expected decision {item['expected_decision_id']!r}, got {decision_id!r}",
                )
            if receipt.get("status") != "decided":
                return FlightReadiness("held", f"{reason}: decision status is {receipt.get('status')!r}, not 'decided'")
            eligible = receipt.get("eligible_run_ids")
            if (
                not isinstance(eligible, list)
                or not eligible
                or any(not isinstance(run_id, str) or not run_id.strip() for run_id in eligible)
                or len(set(eligible)) != len(eligible)
            ):
                return FlightReadiness("held", f"{reason}: eligible_run_ids must be unique nonempty strings")
            if cell.run_id not in eligible:
                return FlightReadiness("held", f"{reason}: run {cell.run_id!r} is not eligible in decision receipt")
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
    receipt_refs: dict[str, Mapping[str, str]] = {}

    def persist_receipts(flight: FlightRuntime) -> None:
        reference = persist_flight_receipts(
            data_root,
            run_id=flight.run_id,
            attempt_id=flight.attempt_id,
            receipts=flight.receipts,
        )
        if reference is not None:
            receipt_refs[flight.run_id] = reference

    def persist_all(primary_error: BaseException | None = None) -> None:
        for flight in flights:
            try:
                persist_receipts(flight)
            except Exception as error:  # noqa: BLE001 -- preserve the primary campaign failure
                if primary_error is None:
                    raise
                primary_error.add_note(
                    "Campaign could not preserve the live flight receipts for "
                    f"{flight.run_id!r}: {type(error).__name__}: {error}"
                )

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
            try:
                yield
            except BaseException as error:
                try:
                    persist_receipts(flight)
                except Exception as receipt_error:  # preserve the generation failure
                    error.add_note(
                        "Campaign could not preserve the live flight receipts: "
                        f"{type(receipt_error).__name__}: {receipt_error}"
                    )
                raise
            else:
                persist_receipts(flight)

    queue = FlightQueue(
        flights, readiness=readiness,
        dependencies={cell.run_id: cell.dependencies() for cell in cells},
        execution_context_factory=custody, include_per_sample=True,
    )
    try:
        while queue.pending:
            completed = queue.run()
            try:
                queue.drain_scores()
            except BaseException as error:
                persist_all(error)
                raise
            else:
                persist_all()
            if not completed:
                break
    except BaseException as error:
        try:
            queue.shutdown()
        except Exception as shutdown_error:  # preserve the campaign failure
            error.add_note(
                "Campaign queue shutdown also failed: "
                f"{type(shutdown_error).__name__}: {shutdown_error}"
            )
        persist_all(error)
        raise
    else:
        try:
            queue.shutdown()
        except BaseException as error:
            persist_all(error)
            raise
        persist_all()
        return {
            "schema": "saea-campaign-status-v1",
            "states": {key: asdict(value) for key, value in queue.states.items()},
            "pending": [flight.run_id for flight in queue.pending],
            "completed": [entry.flight.run_id for entry in queue.completed],
            "flight_receipts": dict(receipt_refs),
        }



def run_node_panel(
    flights: Sequence[FlightRuntime], *, cells: Sequence[CampaignCell], members,
    panel_id: str, repo_root: Path, data_root: Path, owner: str,
    expected_session_id: str, resident_finder=find_resident_session,
    mode: str = "node-panel",
) -> Mapping[str, object]:
    """Coordinate registered independent native flights under one node-stage lease.

    Reuse each FlightRuntime stage and the existing official scorer. No sibling
    may require a score from this still-unrun panel; prepare those dependencies
    before admission. All generation settles before any member is sealed, and
    scoring remains serial with no replay after failure. Explicit node-panel-worker
    mode writes the same complete generation artifacts and prepared score specification,
    then leaves the attempt OPENED without executing official scoring.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from ...reproduction.ojw.panel import NativeWorkflowPanel

    if mode not in {"node-panel", "node-panel-worker"}:
        raise CampaignError("node panel requires an explicit panel lifecycle mode")
    flights, cells, members = tuple(flights), tuple(cells), tuple(members)
    if any(not isinstance(s, str) or not s.strip() for s in (owner, expected_session_id)):
        raise CampaignError("panel owner and resident session must be explicit")
    panel = NativeWorkflowPanel(panel_id, members)
    pairs = tuple((m.run_id, m.attempt_id) for m in members)
    if (tuple((f.run_id, f.attempt_id) for f in flights) != pairs
            or tuple((c.run_id, c.attempt_id) for c in cells) != pairs):
        raise CampaignError("panel runtime/cell order differs from its exact registered members")
    for cell in cells:
        cell.assert_mode(mode)
        if cell.document.get("resume_from") is not None:
            raise CampaignError("node panel does not admit resume or seal-only members")
        if cell.dependencies():
            raise CampaignError("node panel requires independently ready members; resolve dependencies before admission")
        readiness = declared_readiness(cell, data_root)
        if readiness.state != "ready":
            raise CampaignError(f"node panel member {cell.run_id} remains {readiness.state}: {readiness.reason}")
    require_clean_study_repo(repo_root)
    resident = resident_finder(data_root)
    if resident is None or resident[1].get("session_id") != expected_session_id:
        raise CampaignError("node panel requires its existing named resident session")
    receipt_refs = {}
    states = {f.run_id: {"state": "preparing"} for f in flights}

    def persist_all(error=None):
        for flight in flights:
            try:
                ref = persist_flight_receipts(data_root, run_id=flight.run_id,
                    attempt_id=flight.attempt_id, receipts=flight.receipts)
                if ref is not None:
                    receipt_refs[flight.run_id] = ref
            except Exception as caught:
                if error is None:
                    raise
                error.add_note(f"Panel receipt preservation failed for {flight.run_id}: {type(caught).__name__}: {caught}")

    try:
        for flight in flights:
            flight.preflight()
            flight.verify_prepared_artifacts()
            assert_identity_matches(resident[1], flight.session_required_identity())
        if len({f.serving_profile_fingerprint() for f in flights}) != 1:
            raise CampaignError("node panel members require different serving profiles")
        for flight in flights:
            flight.preprocess()
        with GenerationLease.acquire_panel(
            data_root, owner=owner, panel_id=panel_id, members=pairs,
            session_id=expected_session_id, study_head=require_clean_study_repo(repo_root),
        ) as lease:
            try:
                for flight in flights:
                    flight.bind_execution_policy(WorkerExecutionPolicy(
                        expected_session_id, lease.token, panel_id=panel_id, panel_members=pairs,
                    ))
                    flight.bind_native_workflow_panel(panel)
                for flight in flights:
                    flight.serve()
                def generate(flight):
                    try:
                        states[flight.run_id] = {"state": "running"}
                        result = flight.run_phases()
                        panel.assert_completed(flight.run_id, flight.attempt_id)
                        return result
                    except BaseException as error:
                        states[flight.run_id] = {"state": "failed", "reason": str(error)}
                        panel.abort(error)
                        raise
                # These are CPU-side runtime owners, not eight generation jobs.
                # Their model callbacks rendezvous on one four-slot event loop.
                with ThreadPoolExecutor(max_workers=len(flights), thread_name_prefix="saea-panel-owner") as pool:
                    futures = [pool.submit(generate, flight) for flight in flights]
                    try:
                        for future in as_completed(futures):
                            future.result()
                    except BaseException as error:
                        panel.abort(error)
                        raise
                for flight in flights:
                    # seal materializes outputs and closes traces; the bound worker
                    # policy defers official finalization to the separate score stage.
                    if mode == "node-panel-worker":
                        flight.seal(defer_scoring=True)
                    else:
                        flight.seal()
                    states[flight.run_id] = {"state": "sealed" if mode == "node-panel" else "generated"}
                persist_all()
            except BaseException as error:
                panel.abort(error)
                # The worker pool above has settled before attempt disposition.
                for flight in flights:
                    try:
                        flight.abort(f"node panel failed: {type(error).__name__}: {error}")
                    except Exception as caught:
                        error.add_note(f"Panel abort failed for {flight.run_id}: {type(caught).__name__}: {caught}")
                raise
        if mode == "node-panel":
            for flight in flights:
                flight.score(include_per_sample=True)
                states[flight.run_id] = {"state": "scored"}
                persist_all()
    except BaseException as error:
        persist_all(error)
        raise
    return {
        "schema": "saea-node-panel-status-v1", "panel_id": panel_id, "mode": mode,
        "states": states, "completed": [f.run_id for f in flights],
        "pending": [], "flight_receipts": receipt_refs,
    }
