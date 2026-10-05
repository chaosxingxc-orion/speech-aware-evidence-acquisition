#!/usr/bin/env python3
"""Load the pinned experiment config and emit derived stage specs; never dispatch."""
import argparse
import json
from pathlib import Path

from speech_aware_evidence_acquisition.rails.experiment_population import (
    load_population_config, population_accounting, population_stage_spec,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--config", required=True, help="Registered repository-relative path")
    parser.add_argument("--sha256", required=True, help="Expected file hash, not recomputed approval")
    args = parser.parse_args()
    pin = {"relpath": args.config, "sha256": args.sha256}
    config = load_population_config(pin, repo_root=args.repo_root)
    print(json.dumps({"experiment_population": pin, "accounting": population_accounting(config),
                      "cohorts": [population_stage_spec(pin, repo_root=args.repo_root,
                                   cohort_id=c["cohort_id"]) for c in config["cohorts"]],
                      "runtime_admission": False}, indent=2))


if __name__ == "__main__":
    main()
