#!/usr/bin/env python3
"""Export one registered complete system source; no model/scorer invocation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.system_feedback import (
    load_system_feedback, write_system_feedback,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--source-repo-root", type=Path, required=True,
                        help="Retained clean checkout at the source run's recorded commit")
    parser.add_argument("--binding-relpath", required=True)
    parser.add_argument("--binding-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    binding, binding_sha = _pinned_json(args.data_root, {
        "relpath": args.binding_relpath, "sha256": args.binding_sha256,
    }, "system feedback binding")
    report = load_system_feedback(data_root=args.data_root, repo_root=args.source_repo_root,
                                  binding=binding)
    sha = write_system_feedback(args.output, report)
    print(json.dumps({"status": "complete", "rows": len(report["terminal_feedback"]),
                      "report_sha256": sha, "binding_file_sha256": binding_sha,
                      "model_contacts_added": 0, "scorer_contacts_added": 0}))


if __name__ == "__main__":
    main()
