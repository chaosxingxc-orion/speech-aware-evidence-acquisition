"""Shared carrier workers and coordinator campaigns, driven by experiment cells."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign import CampaignError, declared_readiness, load_campaign_cells, run_campaign, run_node_panel
from .lease import WorkerExecutionPolicy
from .receipts import persist_flight_receipts


def build_flight_runtime(*args, **kwargs):
    """Lazy forwarder to ``factory.build_flight_runtime``.

    The factory pulls in the whole runtime stack (rails, carriers, model), which ``--help``, argument
    errors and the plan loaders do not need. Kept as a module attribute so callers and tests can patch it.
    """
    from .factory import build_flight_runtime as _build

    return _build(*args, **kwargs)


def load_campaign_plan(repo: Path, path: Path):
    """Resolve registered cells across experiment fragments without copying them."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(document, dict)
        or set(document) != {"schema", "cells"}
        or document["schema"] != "saea-campaign-plan-v1"
        or not isinstance(document["cells"], list)
        or not document["cells"]
    ):
        raise CampaignError("campaign plan must declare a nonempty cell list")
    selected, seen = [], set()
    for item in document["cells"]:
        if not isinstance(item, dict) or set(item) != {"experiment", "cell"}:
            raise CampaignError("campaign plan cell requires experiment and cell")
        matches = [
            cell for cell in load_campaign_cells(repo, item["experiment"])
            if cell.document["cell_id"] == item["cell"]
        ]
        if len(matches) != 1:
            raise CampaignError("campaign plan cell must resolve exactly once")
        cell = matches[0]
        cell.assert_mode("campaign")
        if cell.run_id in seen:
            raise CampaignError("campaign plan repeats a run")
        seen.add(cell.run_id)
        selected.append((item["experiment"], cell))
    return tuple(selected)


def load_node_panel_plan(repo: Path, path: Path, *, mode: str = "node-panel"):
    """Bind a complete stage panel to exact registered runtime and job owners."""
    from ...reproduction.ojw.panel import NativePanelMember, NativeWorkflowPanel, NativeWorkflowPanelError

    if mode not in {"node-panel", "node-panel-worker"}:
        raise CampaignError("node panel requires an explicit panel lifecycle mode")
    document = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(document, dict) or set(document) != {"schema", "panel_id", "cells"}
            or document["schema"] != "saea-node-panel-plan-v1"
            or not isinstance(document["cells"], list) or not 2 <= len(document["cells"]) <= 8):
        raise CampaignError("node panel plan requires an id and two to eight exact members")
    selected, members = [], []
    for item in document["cells"]:
        if (not isinstance(item, dict)
                or set(item) != {"experiment", "cell", "run_id", "attempt_id", "job_keys"}):
            raise CampaignError("node panel member requires its exact cell, runtime and job identities")
        matches = [cell for cell in load_campaign_cells(repo, item["experiment"])
                   if cell.document["cell_id"] == item["cell"]]
        if len(matches) != 1:
            raise CampaignError("node panel cell must resolve exactly once")
        cell = matches[0]
        cell.assert_mode(mode)
        if (cell.run_id != item["run_id"] or cell.attempt_id != item["attempt_id"]
                or cell.document.get("resume_from") is not None):
            raise CampaignError("node panel must name the exact fresh registered runtime")
        try:
            member = NativePanelMember(cell.run_id, cell.attempt_id, item["job_keys"])
        except NativeWorkflowPanelError as error:
            raise CampaignError(str(error)) from error
        selected.append((item["experiment"], cell))
        members.append(member)
    try:
        NativeWorkflowPanel(document["panel_id"], members)
    except NativeWorkflowPanelError as error:
        raise CampaignError(str(error)) from error
    return tuple(selected), document["panel_id"], tuple(members)


def assert_prepared_artifacts_current(flights) -> None:
    """Refuse a worker/campaign launch whose prepared artifacts went stale.

    E16 (2026-09-19). Runs BEFORE any lease is used, any service is touched and
    -- decisively -- before ``core.model.adapter.FrozenCoreAdapter`` calls
    ``AttemptStore.open_attempt``, so a stale artifact costs zero contacts and
    leaves no OPENED attempt record behind. The reports are memoized on each
    runtime, so ``FlightRuntime.preflight`` reuses this verdict rather than
    recomputing the identity a second time.
    """

    from ..preparation import PreparationError

    stale: list[str] = []
    for runtime in flights:
        for report in runtime.verify_prepared_artifacts():
            if not report["identity_ok"] or report.get("seed_ok") is False:
                stale.append(
                    f"{runtime.run_id}/{runtime.attempt_id} {report['key']} "
                    f"({report['relpath']}): {report['reason']}"
                )
    if stale:
        raise PreparationError(
            "refusing to launch: "
            f"{len(stale)} prepared artifact(s) no longer match this "
            "implementation and config; re-pin the package on the launch commit "
            "(core.flight.repin) and fly from that commit. " + "; ".join(stale)
        )


def prepared_artifact_blockers(preflight) -> list[str]:
    """One blocker string per prepared artifact this package cannot use.

    E16 (2026-09-19). Empty when ``preflight`` reports no prepared artifact or
    every one of them verified, so ``check`` exits zero exactly as before for
    every package that is actually current. Since 2026-09-23 a pinned
    first-phase supply that verifies and then does NOT compose into a seed
    (``seed_ok`` false) is a blocker of its own, named as such.
    """

    if not isinstance(preflight, dict) or preflight.get("prepared_artifacts_ok") is not False:
        return []
    return [
        (
            "prepared artifact identity mismatch: "
            if not report.get("identity_ok")
            else "prepared artifact does not compose into a first-phase seed: "
        )
        + f"{report.get('key')} ({report.get('relpath')}): {report.get('reason')}"
        for report in preflight.get("prepared_artifacts", ())
        if isinstance(report, dict)
        and (not report.get("identity_ok") or report.get("seed_ok") is False)
    ] or ["prepared artifact identity mismatch (no per-artifact detail reported)"]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=[
        "check", "wire-check", "prepare-supply", "prepare-phase-recall", "prepare-branch-seeds",
        "prepare-window-inventory", "prepare-window-features",
        "prepare-speech-observation-sources", "prompt-fit", "coordinate-fit", "worker", "campaign", "node-panel", "node-panel-worker",
        # E10d (2026-09-29): a resume-recovery whose declared predecessor(s)
        # already cover the whole roster -- seals with zero contacts, no
        # server, no slot, no lease. The batch driver runs this as an
        # ordinary chain step; preflight()'s own gates (clean tree, exposure
        # row, prepared-artifact identity, attempt registration) and the
        # cell's declared readiness stay in force exactly as for "worker".
        # After the seal it runs the one official finalize job itself
        # (runtime.score, CPU scorer only), since no queue follows it.
        "seal-only",
    ])
    for name in ("repo-root", "data-root", "runtime-root", "lock-path"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--experiment")
    parser.add_argument("--campaign-plan", type=Path)
    parser.add_argument("--cell")
    parser.add_argument("--owner")
    parser.add_argument("--expected-session-id")
    parser.add_argument("--lease-token-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--contact-cap", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--phase")
    parser.add_argument(
        "--read-only", action="store_true",
        help="check only (M8, 2026-10-15): suppress the one data-root write preflight makes (the resume declaration); "
             "the check takes no lock and writes no attempt record in any case",
    )
    args = parser.parse_args(argv)
    if args.read_only and args.mode != "check":
        parser.error("--read-only applies to check mode only")
    if bool(args.experiment) == bool(args.campaign_plan):
        parser.error("select either an experiment or a committed campaign plan")
    if args.campaign_plan is not None and (args.mode not in {"campaign", "node-panel", "node-panel-worker"} or args.cell):
        parser.error("campaign plans require campaign or node-panel mode and cannot select a partial cell")
    if args.mode in {"worker", "prompt-fit", "prepare-window-features"} and (
        not args.expected_session_id or args.lease_token_file is None
    ):
        parser.error("workers require --expected-session-id and --lease-token-file from root")
    if args.mode in {"campaign", "node-panel", "node-panel-worker"} and (not args.owner or not args.expected_session_id):
        parser.error("campaign requires explicit --owner and --expected-session-id")
    if args.mode in {
        "prepare-supply", "prepare-phase-recall", "prepare-branch-seeds", "prepare-window-inventory",
        "prepare-window-features", "prepare-speech-observation-sources", "prompt-fit"
    } and args.output is None:
        parser.error("preparation modes require --output")
    if args.mode == "prepare-phase-recall" and not args.phase:
        parser.error("prepare-phase-recall requires --phase")
    if args.mode == "prompt-fit" and (args.contact_cap is None or args.contact_cap < 1):
        parser.error("prompt-fit requires a positive registered --contact-cap")
    if args.mode == "coordinate-fit" and (
        not args.owner or not args.expected_session_id or args.output is None
        or args.contact_cap is None or args.contact_cap < 1
    ):
        parser.error("coordinate-fit requires --owner, --expected-session-id, --output and a positive --contact-cap")
    if args.mode == "coordinate-fit" and args.lease_token_file is not None:
        parser.error("coordinate-fit creates its own root lease; --lease-token-file is forbidden")
    if args.mode in {"node-panel", "node-panel-worker"} and (args.campaign_plan is None or args.lease_token_file is not None):
        parser.error("node-panel requires a committed complete plan and owns its own generation lease")
    if args.mode not in {"campaign", "node-panel", "node-panel-worker"} and not args.cell:
        parser.error("single-worker modes require --cell")
    repo, root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    package_root = Path(__file__).resolve().parents[4]
    if repo != package_root:
        parser.error("imported package must belong to --repo-root; use its literal PYTHONPATH")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    if args.campaign_plan is not None:
        plan_path = args.campaign_plan.resolve()
        if not plan_path.is_relative_to(repo):
            parser.error("campaign plan must be within repo-root")
        if args.mode in {"node-panel", "node-panel-worker"}:
            selected, panel_id, panel_members = load_node_panel_plan(repo, plan_path, mode=args.mode)
        else:
            selected = load_campaign_plan(repo, plan_path)
    else:
        selected = tuple((args.experiment, cell) for cell in load_campaign_cells(repo, args.experiment))
        if args.cell:
            selected = tuple(pair for pair in selected if pair[1].document["cell_id"] == args.cell)
            if not selected:
                parser.error("cell is not declared by the experiment")
    cells = tuple(cell for _experiment, cell in selected)
    if args.mode != "campaign":
        for cell in cells:
            cell.assert_mode("prompt-fit" if args.mode == "coordinate-fit" else args.mode)
    policy = None
    if args.mode in {"worker", "prompt-fit", "prepare-window-features"}:
        document = json.loads(args.lease_token_file.read_text(encoding="utf-8"))
        policy = WorkerExecutionPolicy(args.expected_session_id, document["token"])
        policy.assert_lease(root, run_id=cells[0].run_id, attempt_id=cells[0].attempt_id)
    flights = [
        build_flight_runtime(
            repo, root, model=cell.document["model_fragment"],
            dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
            experiment=experiment, run_id=cell.run_id, attempt_id=cell.attempt_id,
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            execution_policy=policy,
            # E10 (owner decision 22): a recovery cell declares the aborted
            # attempt it resumes in the COMMITTED experiment fragment, pinned
            # by that attempt's trace sha256. There is deliberately no command
            # line flag for it: which rows a run keeps is registered, not
            # typed at launch.
            **({"resume_from": cell.resume_from} if cell.resume_from is not None else {}),
        )
        for experiment, cell in selected
    ]
    if args.mode in {"worker", "campaign", "node-panel", "node-panel-worker", "seal-only"}:
        assert_prepared_artifacts_current(flights)
    if args.mode in {"node-panel", "node-panel-worker"}:
        result = run_node_panel(
            flights, cells=cells, members=panel_members, panel_id=panel_id, mode=args.mode,
            repo_root=repo, data_root=root, owner=args.owner,
            expected_session_id=args.expected_session_id,
        )
    elif args.mode == "campaign":
        result = run_campaign(
            flights, cells=cells, repo_root=repo, data_root=root,
            owner=args.owner, expected_session_id=args.expected_session_id,
        )
    else:
        runtime = flights[0]
        if args.mode in {"worker", "check", "seal-only"}:
            # seal-only (2026-09-29, COMP-1 seal-only registration): a seal-only
            # completion seals and finalizes a real run, so it honours the
            # cell's declared readiness exactly like "worker" -- a HELD cell
            # never seals, whatever its predecessors cover.
            state = declared_readiness(cells[0], root)
            if args.mode in {"worker", "seal-only"} and state.state != "ready":
                raise CampaignError(state.reason)
            if args.mode in {"worker", "seal-only"} and cells[0].dependencies():
                raise CampaignError("dependent workers require coordinator queue admission")
        if args.mode == "coordinate-fit":
            from .coordinator import coordinate_fit
            result = coordinate_fit(
                runtime, repo_root=repo, data_root=root, runtime_root=Path(args.runtime_root),
                output=args.output, owner=args.owner, expected_session_id=args.expected_session_id,
                contact_cap=args.contact_cap, model_fragment=cells[0].document["model_fragment"],
            )
        elif args.mode == "check":
            # E16: report, never refuse -- a check exists to PRINT the verdict.
            # Every launch path keeps the enforcing default, so a stale
            # prepared artifact refuses before an attempt can be opened.
            if args.read_only:
                # Instance-level override: the declaration is the only data-root write preflight makes for a
                # resume cell (runtime._write_resume_declaration); nothing else is touched by a check.
                runtime._write_resume_declaration = lambda plan: None
            preflight = runtime.preflight(enforce_prepared_artifacts=False)
            result = {
                "preflight": preflight,
                "scientific_readiness": {"state": state.state, "reason": state.reason},
                "generation_authorized": False,
                **({"read_only": True} if args.read_only else {}),
            }
            blockers = prepared_artifact_blockers(preflight)
            if blockers:
                result["blockers"] = blockers
        elif args.mode == "wire-check":
            result = runtime.wire_check(seal_and_score=False)
        elif args.mode == "prepare-phase-recall":
            result = runtime.prepare_phase_recall(args.output, phase=args.phase, max_workers=args.workers)
        elif args.mode == "prepare-supply":
            if args.workers == 1:
                result = runtime.prepare_phase_supply(args.output)
            else:
                result = runtime.prepare_phase_supply(args.output, max_workers=args.workers)
        elif args.mode == "prepare-branch-seeds":
            if args.workers == 1:
                result = runtime.prepare_perception_branch_seeds(args.output)
            else:
                result = runtime.prepare_perception_branch_seeds(args.output, max_workers=args.workers)
        elif args.mode == "prepare-speech-observation-sources":
            result = runtime.prepare_speech_observation_sources(args.output)
        elif args.mode == "prepare-window-inventory":
            result = runtime.prepare_window_inventory(
                args.output, **({"max_workers": args.workers} if args.workers != 1 else {}),
            )
        elif args.mode == "prepare-window-features":
            from ..preparation_window_encoding import prepare_window_feature_encoding
            result = prepare_window_feature_encoding(runtime, args.output, policy=policy)
        elif args.mode == "prompt-fit":
            from ..preparation_fit import fit_phase_runtime
            result = fit_phase_runtime(
                runtime, args.output, policy=policy, contact_cap=args.contact_cap,
            )
        else:
            try:
                runtime.preflight()
                if args.mode == "seal-only" and not runtime.is_seal_only:
                    raise CampaignError(
                        f"cell {cells[0].document['cell_id']} is not seal-only: its "
                        "declared predecessor(s) do not yet cover the whole roster, "
                        "so this attempt still has contacts to make; seal-only mode "
                        "never starts a server to fly them -- run it as an ordinary "
                        "'worker' with a coordinator-assigned session instead"
                    )
                runtime.preprocess()
                runtime.serve()
                runtime.run_phases()
                # Root releases custody after this seal and schedules official scoring
                # independently. A standalone worker never owns the service or lease.
                seal_result = runtime.seal()
                score_result = None
                if args.mode == "seal-only":
                    # A seal-only completion has no custody to release and no
                    # coordinator queue behind it, so it runs the queue's own
                    # post-seal step here: the ONE official score job over the
                    # complete merged manifest, which finalizes the attempt
                    # (core.flight.queue.FlightQueue submits exactly this call).
                    # CPU scorer only -- no model, server, slot or lease.
                    score_result = runtime.score(include_per_sample=True)
            except BaseException as error:
                try:
                    persist_flight_receipts(
                        root,
                        run_id=runtime.run_id,
                        attempt_id=runtime.attempt_id,
                        receipts=runtime.receipts,
                    )
                except Exception as receipt_error:
                    error.add_note(
                        "Worker could not preserve the live flight receipts: "
                        f"{type(receipt_error).__name__}: {receipt_error}"
                    )
                raise
            receipt_reference = persist_flight_receipts(
                root,
                run_id=runtime.run_id,
                attempt_id=runtime.attempt_id,
                receipts=runtime.receipts,
            )
            result = dict(seal_result)
            if score_result is not None:
                result["score"] = score_result
            if receipt_reference is not None:
                result["flight_receipts"] = {runtime.run_id: receipt_reference}
    print(json.dumps(result, sort_keys=True, default=str))
    if args.mode == "check" and isinstance(result, dict) and result.get("blockers"):
        return 1
    if args.mode in {"campaign", "node-panel", "node-panel-worker"} and isinstance(result, dict):
        states = result.get("states", {})
        if any(
            isinstance(state, dict)
            and state.get("state") in {"failed", "preflight-failed"}
            for state in states.values()
        ):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
