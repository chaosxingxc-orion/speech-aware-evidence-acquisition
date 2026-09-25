#!/usr/bin/env python3
"""Read registered complete construction groups; no inference or policy update."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.analysis.system_rollout_groups import (
    RolloutGroupError, load_group_source, group_complete_system_sources,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--recipe-relpath", required=True)
    parser.add_argument("--recipe-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    recipe, recipe_sha = _pinned_json(REPO, {
        "relpath": args.recipe_relpath, "sha256": args.recipe_sha256,
    }, "registered group read")
    if (recipe["schema"] != "saea-system-rollout-group-read-v1"
            or recipe["execution_profile"] != "model-free-check"
            or recipe["feedback_role"] != "construction"
            or recipe["scope"] != "diagnostic-only"):
        raise RolloutGroupError("recipe does not authorize this complete construction diagnostic")
    sources = [load_group_source(data_root=args.data_root, label=source["label"],
                                 feedback_pin=source["feedback"])
               for source in recipe["sources"]]
    if any(source["ordered_sample_ids"] != recipe["ordered_sample_ids"] for source in sources):
        raise RolloutGroupError("registered complete roster differs")
    if any(source["split_identity_hash"] != recipe["split_identity_hash"] for source in sources):
        raise RolloutGroupError("registered split differs")
    report = group_complete_system_sources(
        sources, f0=recipe["reward"]["frozen_f0"],
        standard_deviation_floor=recipe["reward"]["standard_deviation_floor"],
    )
    report.pop("content_sha256")
    report.update(read_id=recipe["read_id"], recipe_sha256=recipe_sha)
    report["content_sha256"] = content_hash(report)
    sha = write_system_feedback(args.output, report)
    print(json.dumps({"status": "complete", "output_sha256": sha,
                      "groups": report["summary"]["groups"],
                      "learning_authorized": False,
                      "model_contacts_added": 0, "scorer_contacts_added": 0}))


if __name__ == "__main__":
    main()
