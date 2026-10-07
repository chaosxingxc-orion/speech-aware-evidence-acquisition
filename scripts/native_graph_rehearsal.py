#!/usr/bin/env python3
"""Capture a four-row production-native graph with synthetic replies and no network."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch
from speech_aware_evidence_acquisition.analysis.native_graph_rehearsal import (
    FourPathResponder, ReviewOffResponder, rehearsal_profile, rehearse_native_graph,
)
from speech_aware_evidence_acquisition.core.flight.factory import build_flight_runtime

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("repo-root", "data-root", "runtime-root", "lock-path", "experiment", "session", "output"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--targets", nargs=2, required=True)
    parser.add_argument("--profile", choices=("legacy-four-path-v1", "review-off-v1"), default="legacy-four-path-v1")
    args = parser.parse_args()
    repo, data = Path(args.repo_root), Path(args.data_root)
    document = json.loads((repo / "configs/experiment" / (args.experiment + ".json")).read_text())
    if len(document["cells"]) != 1:
        raise ValueError("Select one four-row engineering configuration")
    cell = document["cells"][0]
    runtime = build_flight_runtime(repo, data, model=cell["model_fragment"],
        dataset=cell["dataset_fragment"], baseline=cell["baseline_fragment"],
        experiment=args.experiment, run_id=cell["run_id"], attempt_id=cell["attempt_id"],
        runtime_root=Path(args.runtime_root), lock_path=Path(args.lock_path), campaign_active=False)
    roster = runtime.preparation_context()["sample_ids"]
    respond = FourPathResponder(roster, args.targets)
    options = {}
    if args.profile == "review-off-v1":
        config = rehearsal_profile(runtime.preparation_context()["values"], args.profile)
        texts = {role: respond({"sample_id": roster[0], "history": [{"role": "control",
                  "contact_id": "synthetic:" + role + ":0"}]})["content"] for role in ("perception", "solver")}
        respond = ReviewOffResponder(roster, args.targets, texts=texts, lookup=config.solver_tool_access is not None)
        options["profile"] = args.profile
    def no_network(*_args, **_kwargs):
        raise RuntimeError("Synthetic rehearsal forbids all network connections")
    with patch("socket.socket.connect", no_network), patch("socket.socket.connect_ex", no_network):
        receipt = rehearse_native_graph(runtime, session_path=Path(args.session), respond=respond,
                                        output=Path(args.output), **options)
    print(json.dumps({key: receipt[key] for key in
        ("schema", "terminal_rows", "synthetic_completions", "synthetic_tool_calls",
         "generation_contacts", "tokenizer_contacts", "capacity_verified")}, sort_keys=True))

if __name__ == "__main__":
    main()

