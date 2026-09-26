#!/usr/bin/env python3
"""Join a registered complete memory family using the shared offline readers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from speech_aware_evidence_acquisition.analysis.system_feedback import (
    load_system_feedback, write_system_feedback,
)
from speech_aware_evidence_acquisition.analysis.native_episode_source import verify_native_episode_source
from speech_aware_evidence_acquisition.analysis.candidate_memory_evaluation import (
    verify_candidate_memory_evaluation_source,
)
from speech_aware_evidence_acquisition.analysis.system_rollout_groups import (
    load_group_source, group_complete_system_sources,
)
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import _pinned_json
from speech_aware_evidence_acquisition.rails.hashing import content_hash
import slurp_system_trajectory_read as attribution
import slurp_var1_variant_read as var1


def require_complete_family(data_root, registration):
    """Check every actor using operational metadata before reading any quality."""
    root = Path(data_root)
    if not registration.get("arms"):
        raise ValueError("a registered nonempty family is required")
    for label, spec in registration["arms"].items():
        folder = root / "runs" / spec["run_id"] / spec["attempt_id"]
        attempt_path = root / "attempts" / spec["run_id"] / (spec["attempt_id"] + ".json")
        try:
            attempt = json.loads(attempt_path.read_text())
            receipt = json.loads((folder / "flight-receipts.json").read_text())
        except (OSError, ValueError) as error:
            raise ValueError(f"{label}: complete family metadata is unavailable") from error
        stages = receipt.get("stages", {})
        score, seal = stages.get("score", {}), stages.get("seal", {})
        if (attempt.get("state") != "FINALIZED"
                or seal.get("outputs_row_count") != spec["expected_rows"]
                or spec["expected_official_scores"] != 1
                or score.get("job_count") != 1
                or score.get("result", {}).get("succeeded") != 1
                or score.get("result", {}).get("failed") != 0):
            raise ValueError(f"{label}: complete seal and exactly one full score required")


def publish(root, path, document):
    document = dict(document)
    if "content_sha256" not in document:
        document["content_sha256"] = content_hash(document)
    sha = write_system_feedback(path, document)
    return {"relpath": str(path.resolve().relative_to(root.resolve())), "sha256": sha}


def run(args):
    root = args.data_root.resolve()
    authorization, authorization_sha = _pinned_json(
        root, {"relpath": args.authorization_relpath, "sha256": args.authorization_sha256},
        "complete-family read authorization",
    )
    if (authorization.get("schema") != "saea-system-memory-batch-read-authorization-v1"
            or authorization.get("execution_profile") != "model-free-check"
            or authorization.get("status") != "sealed"):
        raise ValueError("a sealed model-free family read authorization is required")
    registration, registration_sha = _pinned_json(
        REPO, authorization["registration"], "prospective read registration",
    )
    if (registration.get("schema") != "saea-system-memory-batch-read-registration-v2"
            or registration.get("feedback_role") != "construction"
            or authorization["read_id"] != registration["read_id"]
            or set(authorization["arms"]) != set(registration["arms"])):
        raise ValueError("authorization differs from the registered construction family")
    require_complete_family(root, registration)
    output = root / registration["output_relpath"]
    output.resolve().relative_to(root)
    gold = var1.load_gold(args.lock_path, root, "train")
    sources, arm_reports, pins = {}, {}, {}
    for label, spec in registration["arms"].items():
        binding = authorization["arms"][label]["binding"]
        source_root = Path(spec["source_repo_root"])
        source = verify_native_episode_source(
            manifest_path=root / binding["manifest"]["relpath"],
            expected_manifest_sha256=binding["manifest"]["sha256"],
            phase_artifact_path=root / binding["phases"]["relpath"],
            expected_phase_sha256=binding["phases"]["sha256"],
            repo_root=source_root, data_root=root,
        )
        if (source.plan.run_id != spec["run_id"]
                or source.plan.attempt_id != spec["attempt_id"]
                or source.bundle.manifest["study_commit"] != spec["source_commit"]):
            raise ValueError(f"{label}: source identity differs from registration")
        feedback = load_system_feedback(data_root=root, repo_root=source_root, binding=binding)
        memory = verify_candidate_memory_evaluation_source(
            manifest_path=root / binding["manifest"]["relpath"],
            expected_manifest_sha256=binding["manifest"]["sha256"],
            phase_artifact_path=root / binding["phases"]["relpath"],
            expected_phase_sha256=binding["phases"]["sha256"],
            repo_root=source_root, data_root=root,
        )
        diagnostic = attribution.analyze_arm(source, feedback, gold["records"])
        feedback_pin = publish(root, output / label / "feedback.json", feedback)
        pins[label] = {
            "feedback": feedback_pin,
            "memory": publish(root, output / label / "memory.json", memory),
            "attribution": publish(root, output / label / "attribution.json", diagnostic),
        }
        sources[label] = load_group_source(data_root=root, feedback_pin=feedback_pin, label=label)
        counts = Counter()
        for row in feedback["terminal_feedback"]:
            for key in ("tp", "fp", "fn"):
                counts[key] += row[key]
        denominator = 2 * counts["tp"] + counts["fp"] + counts["fn"]
        joint = Counter(
            f"intent_{int(row['delivered']['intent_correct'])}_slots_{int(row['delivered']['entity_exact'])}"
            for row in diagnostic["rows"]
        )
        arm_reports[label] = {
            "summary": diagnostic["summary"], "cross_node": diagnostic["cross_node"],
            "joint_intent_slot_counts": dict(joint),
            "official_entity_counts": dict(counts),
            "official_count_micro_f1": 2 * counts["tp"] / denominator if denominator else 0.0,
            "successful_memory_calls": len(memory["successful_memory_calls"]),
            "calls_selecting_records": sum(bool(c["selected_record_sha256s"])
                                          for c in memory["successful_memory_calls"]),
            "selected_record_counts": dict(Counter(
                record for call in memory["successful_memory_calls"]
                for record in call["selected_record_sha256s"])),
            "samples_without_memory_call": memory["samples_without_successful_memory_call"],
            "other_successful_tool_calls": memory["other_successful_call_count"],
            "memory_non_result_events": memory["non_result_events"],
        }
        print(json.dumps({"read": label, "rows": len(diagnostic["rows"])}), flush=True)
    groups = {}
    for arm in ("memory", "empty"):
        labels = [pair[1 if arm == "memory" else 0] for pair in registration["paired_comparisons"]]
        grouped = group_complete_system_sources(
            [sources[label] for label in labels], f0=registration["reward"]["frozen_f0"],
            standard_deviation_floor=registration["reward"]["standard_deviation_floor"],
        )
        groups[arm] = {"summary": grouped["summary"],
                       "artifact": publish(root, output / f"{arm}-groups.json", grouped)}
    report = {
        "schema": "saea-system-memory-batch-read-v1",
        "read_id": registration["read_id"], "registration_sha256": registration_sha,
        "authorization_sha256": authorization_sha, "gold_metadata_sha256": gold["metadata_sha256"],
        "arms": arm_reports, "artifacts": pins,
        "groups": groups, "paired_comparisons": registration["paired_comparisons"],
        "interpretation": "Four distinct inputs with repeated trajectories; descriptive construction only. "
                          "Selection/exposure is not semantic use. Empty controls are not learner feedback.",
        "model_contacts_added": 0, "scorer_contacts_added": 0,
    }
    pin = publish(root, output / "batch-read.json", report)
    print(json.dumps({"complete": pin}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--authorization-relpath", required=True)
    parser.add_argument("--authorization-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
