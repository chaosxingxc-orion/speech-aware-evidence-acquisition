#!/usr/bin/env python3
"""Run the registered nongenerative stress proof through the shared coordinator."""
import argparse
import json
from pathlib import Path
from speech_aware_evidence_acquisition.core.flight.campaign import load_campaign_cells, declared_readiness
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime
from speech_aware_evidence_acquisition.core.flight.lease import WorkerExecutionPolicy
from speech_aware_evidence_acquisition.analysis.system_text_capacity import fit_stress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "output", "lease-token-file", "expected-session-id"):
        parser.add_argument("--" + key, required=True)
    args = parser.parse_args()
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
    result = fit_stress(runtime, output, policy=policy, contact_cap=2048)
    print(json.dumps(result, sort_keys=True))
    measured = json.loads(output.read_text())["output"]
    print(json.dumps(measured, sort_keys=True))
    if not measured["every_request_fits"]:
        raise SystemExit("Capacity proof did not fit; do not admit bulk generation")


if __name__ == "__main__":
    main()
