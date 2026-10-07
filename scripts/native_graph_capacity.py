#!/usr/bin/env python3
"""Measure reachable native requests through a separately registered FIT identity."""
import argparse
import json
from pathlib import Path
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells, declared_readiness
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.flight.lease import WorkerExecutionPolicy
from speech_aware_evidence_acquisition.analysis.native_graph_capacity import fit_native_graph


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "output", "lease-token-file", "expected-session-id", "graph-experiment"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--contact-cap", type=int, default=2048,
                        help="Exact separately registered tokenizer endpoint ceiling.")
    parser.add_argument("--profile", choices=("legacy-four-path-v1", "review-off-v1"), default="legacy-four-path-v1")
    args = parser.parse_args(argv)
    if args.contact_cap < 1:
        parser.error("--contact-cap must be positive")
    repo, data = Path(args.repo_root), Path(args.data_root)
    cells = load_campaign_cells(repo, args.experiment)
    if len(cells) != 1:
        raise ValueError("Capacity registration must have one cell")
    cell = cells[0]
    cell.assert_mode("prompt-fit")
    if declared_readiness(cell, data).state != "ready":
        raise ValueError("Capacity cell not admitted")
    if not cell.run_id.endswith("-FIT-V1"):
        raise ValueError("Only a separately registered FIT identity is accepted")
    runtime = build_flight_runtime(repo, data, model=cell.document["model_fragment"],
        dataset=cell.document["dataset_fragment"], baseline=cell.document["baseline_fragment"],
        experiment=args.experiment, run_id=cell.run_id, attempt_id=cell.attempt_id,
        runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path))
    output = Path(args.output)
    if not output.resolve().is_relative_to(data.resolve()) or output.exists():
        raise ValueError("Use a new output under the data root")
    token = json.loads(Path(args.lease_token_file).read_text())
    policy = WorkerExecutionPolicy(args.expected_session_id, token["token"])
    policy.assert_lease(data, run_id=cell.run_id, attempt_id=cell.attempt_id)
    def graph_factory():
        graph_cells = load_campaign_cells(repo, args.graph_experiment)
        if len(graph_cells) != 1:
            raise ValueError("Select exactly one model-free four-row graph configuration")
        source = graph_cells[0]
        return build_flight_runtime(repo, data, model=source.document["model_fragment"],
            dataset=source.document["dataset_fragment"], baseline=source.document["baseline_fragment"],
            experiment=args.graph_experiment, run_id=source.run_id, attempt_id=source.attempt_id,
            runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path), campaign_active=False)
    options = {} if args.profile == "legacy-four-path-v1" else {"profile": args.profile}
    result = fit_native_graph(runtime, output, policy=policy, graph_factory=graph_factory, contact_cap=args.contact_cap, **options)
    print(json.dumps(result, sort_keys=True))
    measured = json.loads(output.read_text())["output"]
    print(json.dumps(measured, sort_keys=True))
    if not measured["every_request_fits"]:
        raise SystemExit("Capacity proof did not fit; do not admit bulk generation")


if __name__ == "__main__":
    main()
