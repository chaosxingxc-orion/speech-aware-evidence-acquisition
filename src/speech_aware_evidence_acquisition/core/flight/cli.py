"""Shared carrier workers and coordinator campaigns, driven by experiment cells."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .campaign import CampaignError, declared_readiness, load_campaign_cells, run_campaign
from .factory import build_flight_runtime
from .lease import WorkerExecutionPolicy


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=[
        "check", "wire-check", "prepare-supply", "prompt-fit", "coordinate-fit", "worker", "campaign",
    ])
    for name in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--cell")
    parser.add_argument("--owner")
    parser.add_argument("--expected-session-id")
    parser.add_argument("--lease-token-file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--contact-cap", type=int)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args(argv)
    if args.mode in {"worker", "prompt-fit"} and (
        not args.expected_session_id or args.lease_token_file is None
    ):
        parser.error("workers require --expected-session-id and --lease-token-file from root")
    if args.mode == "campaign" and (not args.owner or not args.expected_session_id):
        parser.error("campaign requires explicit --owner and --expected-session-id")
    if args.mode in {"prepare-supply", "prompt-fit"} and args.output is None:
        parser.error("preparation modes require --output")
    if args.mode == "prompt-fit" and (args.contact_cap is None or args.contact_cap < 1):
        parser.error("prompt-fit requires a positive registered --contact-cap")
    if args.mode == "coordinate-fit" and (
        not args.owner or not args.expected_session_id or args.output is None
        or args.contact_cap is None or args.contact_cap < 1
    ):
        parser.error("coordinate-fit requires --owner, --expected-session-id, --output and a positive --contact-cap")
    if args.mode != "campaign" and not args.cell:
        parser.error("single-worker modes require --cell")
    repo, root = Path(args.repo_root).resolve(), Path(args.data_root).resolve()
    package_root = Path(__file__).resolve().parents[4]
    if repo != package_root:
        parser.error("imported package must belong to --repo-root; use its literal PYTHONPATH")
    if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
        parser.error("PYTHONDONTWRITEBYTECODE=1 is required")
    cells = load_campaign_cells(repo, args.experiment)
    if args.cell:
        cells = tuple(cell for cell in cells if cell.document["cell_id"] == args.cell)
        if not cells:
            parser.error("cell is not declared by the experiment")
    if args.mode != "campaign":
        for cell in cells:
            cell.assert_mode("prompt-fit" if args.mode == "coordinate-fit" else args.mode)
    policy = None
    if args.mode in {"worker", "prompt-fit"}:
        document = json.loads(args.lease_token_file.read_text(encoding="utf-8"))
        policy = WorkerExecutionPolicy(args.expected_session_id, document["token"])
        policy.assert_lease(root, run_id=cells[0].run_id, attempt_id=cells[0].attempt_id)
    flights = [
        build_flight_runtime(
            repo, root, model=cell.document["model_fragment"],
            dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
            experiment=args.experiment, run_id=cell.run_id, attempt_id=cell.attempt_id,
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path),
            execution_policy=policy,
        )
        for cell in cells
    ]
    if args.mode == "campaign":
        result = run_campaign(
            flights, cells=cells, repo_root=repo, data_root=root,
            owner=args.owner, expected_session_id=args.expected_session_id,
        )
    else:
        runtime = flights[0]
        if args.mode in {"worker", "check"}:
            state = declared_readiness(cells[0], root)
            if args.mode == "worker" and state.state != "ready":
                raise CampaignError(state.reason)
            if args.mode == "worker" and cells[0].dependencies():
                raise CampaignError("dependent workers require coordinator queue admission")
        if args.mode == "coordinate-fit":
            from .coordinator import coordinate_fit
            result = coordinate_fit(
                runtime, repo_root=repo, data_root=root, runtime_root=Path(args.runtime_root),
                output=args.output, owner=args.owner, expected_session_id=args.expected_session_id,
                contact_cap=args.contact_cap, model_fragment=cells[0].document["model_fragment"],
            )
        elif args.mode == "check":
            result = {
                "preflight": runtime.preflight(),
                "scientific_readiness": {"state": state.state, "reason": state.reason},
                "generation_authorized": False,
            }
        elif args.mode == "wire-check":
            result = runtime.wire_check(seal_and_score=False)
        elif args.mode == "prepare-supply":
            if args.workers == 1:
                result = runtime.prepare_phase_supply(args.output)
            else:
                result = runtime.prepare_phase_supply(args.output, max_workers=args.workers)
        elif args.mode == "prompt-fit":
            from ..preparation_fit import fit_phase_runtime
            result = fit_phase_runtime(
                runtime, args.output, policy=policy, contact_cap=args.contact_cap,
            )
        else:
            runtime.preflight()
            runtime.preprocess()
            runtime.serve()
            runtime.run_phases()
            # Root releases custody after this seal and schedules official scoring
            # independently. A standalone worker never owns the service or lease.
            result = runtime.seal()
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
